"""Real Chromium workflow test; optional Playwright test dependency."""
import tempfile
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from office import make_server


def main():
    with tempfile.TemporaryDirectory() as folder:
        server = make_server(Path(folder) / 'browser.sqlite3', 0)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={'width': 1440, 'height': 1000})
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{server.server_port}')
                expect(page.get_by_role('status')).to_have_text('Workspace up to date.')
                agents = page.locator('#agent-form')
                agents.get_by_label('Name', exact=True).fill('Evidence editor')
                agents.get_by_label('Role / instructions').fill('Check every source.')
                agents.get_by_role('button', name='Save agent').click()
                expect(page.locator('#agents')).to_contain_text('Evidence editor')
                page.get_by_label('Task title').fill('Verify the launch notes')
                page.get_by_label('Brief', exact=True).fill('Check claims and record limits.')
                page.get_by_label('Assigned role').select_option(label='Evidence editor')
                page.get_by_role('button', name='Create task', exact=True).click()
                card = page.locator('article.task').filter(has_text='Verify the launch notes')
                expect(card).to_be_visible()
                card.get_by_role('button', name='Start', exact=True).click()
                expect(card.get_by_role('button', name='Request review')).to_be_visible()
                card.get_by_label('Result / working notes').fill('Claims checked; no live AI provider configured.')
                card.get_by_role('button', name='Request review').click()
                card.get_by_role('button', name='Approve & complete').click()
                expect(card.get_by_role('button', name='Reopen')).to_be_visible()
                page.reload()
                expect(card.get_by_label('Result / working notes')).to_have_value('Claims checked; no live AI provider configured.')
                page.get_by_label('Search tasks').fill('not present')
                expect(page.locator('article.task')).to_have_count(0)
                page.get_by_label('Search tasks').fill('launch')
                expect(card).to_be_visible()
                page.set_viewport_size({'width': 390, 'height': 844})
                expect(card).to_be_visible()
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Mobile overflow'
                assert not errors, errors
                browser.close()
                print('Chromium: agent creation, task lifecycle, reload persistence, search, mobile layout passed.')
        finally:
            server.shutdown(); worker.join(); server.server_close()


if __name__ == '__main__': main()
