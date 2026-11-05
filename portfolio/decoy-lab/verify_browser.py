"""Exercise the real localhost lab in desktop and mobile Chromium."""
import json
from pathlib import Path
import threading
from playwright.sync_api import sync_playwright, expect
from app import Lab


def main():
    lab = Lab(0)
    worker = threading.Thread(target=lab.serve_forever, daemon=True)
    worker.start()
    base = f'http://127.0.0.1:{lab.server_port}'
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            for width in (1440, 390):
                with lab.lock:
                    lab.events.clear()
                context = browser.new_context(viewport={'width': width, 'height': 900}, accept_downloads=True)
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(base + '/lab')
                expect(page.locator('#cards article')).to_have_count(6)
                expect(page.locator('#events')).to_contain_text('No events yet')
                page.get_by_role('button', name='Run simulated activity').click()
                expect(page.get_by_role('status')).to_contain_text('9 synthetic requests completed')
                expect(page.locator('#events tr')).to_have_count(9)
                expect(page.locator('#events')).to_contain_text('Injection-like input')
                with page.expect_download() as download_info:
                    page.get_by_role('button', name='Download event report').click()
                download = download_info.value
                report = json.loads(Path(download.path()).read_text())
                assert len(report['events']) == 9
                assert report['counts']['credential_attempt'] == 2
                assert 'synthetic-one' not in json.dumps(report)
                # Prove attacker-controlled path text remains inert in the dashboard.
                lab.record('GET', '/<img src=x onerror=alert(1)>', '', 404)
                page.reload()
                expect(page.locator('#events tr')).to_have_count(10)
                expect(page.locator('#events img')).to_have_count(0)
                expect(page.locator('#events')).to_contain_text('<img src=x onerror=alert(1)>')
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Page overflows viewport'
                page.get_by_role('button', name='Clear events').click()
                expect(page.get_by_role('status')).to_have_text('Events cleared.')
                expect(page.locator('#events')).to_contain_text('No events yet')
                assert not errors, errors
                context.close()
                print(f'PASS Chromium {width}px: simulation, timeline, report export, reset, inert event text, layout, no page errors')
            browser.close()
    finally:
        lab.shutdown()
        lab.server_close()
        worker.join()


if __name__ == '__main__':
    main()
