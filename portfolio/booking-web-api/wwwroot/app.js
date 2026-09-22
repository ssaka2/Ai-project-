const $ = id => document.getElementById(id);
async function api(path, options) {
  const response = await fetch(path, options);
  if (!response.ok) {
    let problem; try { problem = await response.json(); } catch {}
    throw new Error(problem?.detail || `Request failed (${response.status}).`);
  }
  return response.status === 204 ? null : response.json();
}
async function refresh() {
  const bookings = await api('/api/bookings');
  const nodes = bookings.map(b => {
    const article = document.createElement('article');
    const title = document.createElement('h3'); title.textContent = `${b.service} · ${b.customer}`;
    const detail = document.createElement('p'); detail.textContent = `${new Date(b.start).toLocaleString()} · ${b.minutes} minutes`;
    const cancel = document.createElement('button'); cancel.textContent = 'Cancel appointment';
    cancel.addEventListener('click', async () => {
      cancel.disabled = true;
      try { await api(`/api/bookings/${b.id}`, {method:'DELETE'}); await refresh(); $('message').textContent='Appointment cancelled.'; }
      catch(e) { $('message').textContent=e.message; cancel.disabled=false; }
    });
    article.append(title, detail, cancel); return article;
  });
  if (!nodes.length) { const empty=document.createElement('p');empty.textContent='No appointments yet.';nodes.push(empty); }
  $('appointments').replaceChildren(...nodes);
}
$('booking').addEventListener('submit', async e => {
  e.preventDefault(); $('submit').disabled=true;
  try {
    const start=new Date($('start').value);
    if (!Number.isFinite(start.getTime())) throw new Error('Enter a valid start time.');
    await api('/api/bookings', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({service:$('service').value,customer:$('customer').value,start:start.toISOString(),minutes:Number($('minutes').value)})});
    $('message').textContent='Appointment booked.'; await refresh();
  } catch(e) { $('message').textContent=e.message; }
  finally { $('submit').disabled=false; }
});
$('refresh').addEventListener('click', () => refresh().catch(e => $('message').textContent=e.message));
(async () => {
  try {
    const services=await api('/api/services');
    $('service').replaceChildren(...services.map(s=>{const option=document.createElement('option');option.value=s;option.textContent=s;return option;}));
    await refresh();
  } catch(e) { $('message').textContent=e.message; }
})();
