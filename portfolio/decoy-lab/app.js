'use strict';
const token = document.querySelector('meta[name="lab-token"]').content;
const status = document.querySelector('#status');
let snapshot;
function element(tag, value) { const node = document.createElement(tag); node.textContent = value; return node; }
async function refresh() {
  const response = await fetch('/lab/events');
  if (!response.ok) throw new Error('Unable to read events');
  snapshot = await response.json();
  const cards = document.querySelector('#cards'); cards.replaceChildren();
  for (const [key, lesson] of Object.entries(snapshot.lessons)) {
    const card = element('article', '');
    card.append(element('strong', String(snapshot.counts[key] || 0)), element('h3', lesson[0]), element('p', lesson[1]));
    cards.append(card);
  }
  const rows = document.querySelector('#events'); rows.replaceChildren();
  for (const event of [...snapshot.events].reverse()) {
    const row = element('tr', '');
    for (const value of [event.time.slice(11, 19), `${event.method} ${event.path}`, snapshot.lessons[event.category][0], event.status]) row.append(element('td', value));
    rows.append(row);
  }
  if (!snapshot.events.length) { const row = element('tr', ''); const cell = element('td', 'No events yet. Run the simulation to begin.'); cell.colSpan = 4; row.append(cell); rows.append(row); }
}
async function command(name) {
  document.querySelectorAll('button').forEach(b => b.disabled = true);
  try {
    const response = await fetch(`/lab/${name}`, {method: 'POST', headers: {'X-Lab-Token': token}});
    if (!response.ok) throw new Error(`Operation failed (${response.status})`);
    const data = await response.json(); await refresh();
    status.textContent = name === 'simulate' ? `${data.requests} synthetic requests completed. Review the patterns below.` : 'Events cleared.';
  } catch (error) { status.textContent = error.message; }
  finally { document.querySelectorAll('button').forEach(b => b.disabled = false); }
}
document.querySelector('#simulate').onclick = () => command('simulate');
document.querySelector('#clear').onclick = () => command('clear');
document.querySelector('#download').onclick = async () => {
  try {
    await refresh();
    const url = URL.createObjectURL(new Blob([JSON.stringify(snapshot, null, 2)], {type: 'application/json'}));
    const link = element('a', ''); link.href = url; link.download = 'decoy-lab-events.json'; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (error) { status.textContent = error.message; }
};
refresh().catch(error => { status.textContent = error.message; });
setInterval(() => refresh().catch(() => {}), 3000);
