"""Exercise the static evaluator in Chromium without calling any AI provider."""
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from playwright.sync_api import sync_playwright, expect

root = Path(__file__).resolve().parent / 'dist'
server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(SimpleHTTPRequestHandler, directory=str(root)))
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
try:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            for width in [1440, 390]:
                page = browser.new_page(viewport={'width': width, 'height': 900})
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{server.server_port}')
                expect(page.locator('#stats')).to_contain_text('All selected rules passed')
                expect(page.locator('#cards article')).to_have_count(12)
                with page.expect_download() as pending:
                    page.get_by_role('button', name='Download JSON report').click()
                report = json.loads(Path(pending.value.path()).read_text())
                assert report['passed'] == report['total']
                page.get_by_role('button', name='Load failing example').click()
                expect(page.locator('#stats')).to_contain_text('Review the failed checks')
                assert page.locator('#checks .fail').count() > 0
                page.get_by_label('Response to evaluate').fill('{"status":"ready"}')
                expect(page.get_by_role('button', name='Download JSON report')).to_be_disabled()
                page.get_by_label('Required terms').fill('ready')
                page.get_by_label('Forbidden terms').fill('')
                page.get_by_label('Require valid JSON').check()
                page.get_by_role('button', name='Evaluate response', exact=True).click()
                expect(page.locator('#stats')).to_contain_text('All selected rules passed')
                page.get_by_label('Response to evaluate').fill('invalid JSON')
                page.get_by_role('button', name='Evaluate response', exact=True).click()
                expect(page.locator('#stats')).to_contain_text('Review the failed checks')
                assert page.locator('#checks .fail').count() > 0
                assert not errors, errors
                page.close()
                print(f'PASS Chromium {width}px: evaluation, failure feedback, JSON rules, report download, stale report prevention, project cards.')
        finally:
            browser.close()
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)
