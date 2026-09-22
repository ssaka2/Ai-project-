"""Exercise the published booking app through real browsers with disposable data."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

from playwright.sync_api import expect, sync_playwright


def exercise(browser_type, base, output, name, viewport):
    browser = browser_type.launch()
    context = browser.new_context(viewport=viewport, timezone_id='America/Chicago')
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    try:
        page.goto(base)
        expect(page.get_by_role('heading', name='Appointment Desk', exact=True)).to_be_visible()
        expect(page.locator('#service option')).to_have_count(3)
        expect(page.locator('#appointments')).to_have_text('No appointments yet.')
        page.get_by_label('Service', exact=True).select_option('consultation')
        customer = '<img src=x onerror=alert(1)> Demo'
        page.get_by_label('Customer name').fill(customer)
        local_time = page.evaluate('''() => {
            const d = new Date(Date.now() + 48 * 60 * 60 * 1000);
            const pad = n => String(n).padStart(2, '0');
            return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
        }''')
        page.get_by_label('Start time (your local time)').fill(local_time)
        page.get_by_label('Duration in minutes').fill('30')
        submit = page.get_by_role('button', name='Book appointment', exact=True)
        with page.expect_response(lambda r: r.request.method == 'POST' and r.url.endswith('/api/bookings')) as created:
            submit.click()
        assert created.value.status == 201
        booked = created.value.json()
        expected_utc = page.evaluate('(value) => new Date(value).toISOString()', local_time)
        assert datetime.fromisoformat(booked['start'].replace('Z', '+00:00')) == datetime.fromisoformat(expected_utc.replace('Z', '+00:00'))
        expect(page.get_by_role('status')).to_have_text('Appointment booked.')
        expect(page.locator('#appointments article')).to_have_count(1)
        expect(page.locator('#appointments h3')).to_contain_text(customer)
        expect(page.locator('#appointments img')).to_have_count(0)
        expect(submit).to_be_enabled()
        page.screenshot(path=str(output / f'{name}-booked.png'), full_page=True)
        print(f'PASS {name}: create, timezone conversion, safe customer rendering', flush=True)

        with page.expect_response(lambda r: r.request.method == 'POST' and r.url.endswith('/api/bookings')) as duplicate:
            submit.click()
        assert duplicate.value.status == 409
        expect(page.get_by_role('status')).not_to_have_text('Appointment booked.')
        expect(page.get_by_role('status')).not_to_be_empty()
        expect(submit).to_be_enabled()
        expect(page.locator('#appointments article')).to_have_count(1)
        print(f'PASS {name}: duplicate conflict feedback and form recovery', flush=True)

        page.reload()
        expect(page.locator('#appointments article')).to_have_count(1)
        expect(page.locator('#appointments h3')).to_contain_text(customer)
        print(f'PASS {name}: reload preserves displayed booking', flush=True)

        page.route('**/api/bookings', lambda route: route.fulfill(status=503, content_type='application/problem+json', body=json.dumps({'detail': 'Temporary test outage.'})), times=1)
        page.get_by_role('button', name='Refresh', exact=True).click()
        expect(page.get_by_role('status')).to_have_text('Temporary test outage.')
        with page.expect_response(lambda r: r.request.method == 'GET' and r.url.endswith('/api/bookings')) as refreshed:
            page.get_by_role('button', name='Refresh', exact=True).click()
        assert refreshed.value.status == 200
        expect(page.get_by_role('status')).to_have_text('Appointments refreshed.')
        expect(page.locator('#appointments article')).to_have_count(1)
        print(f'PASS {name}: failed refresh preserves data and retry succeeds', flush=True)

        page.get_by_role('button', name='Cancel appointment', exact=True).click()
        expect(page.get_by_role('status')).to_have_text('Appointment cancelled.')
        expect(page.locator('#appointments')).to_have_text('No appointments yet.')
        page.reload()
        expect(page.locator('#appointments')).to_have_text('No appointments yet.')
        assert not errors, errors
        print(f'PASS {name}: cancellation persists, no uncaught JavaScript errors', flush=True)
    except Exception:
        page.screenshot(path=str(output / f'{name}-failure.png'), full_page=True)
        raise
    finally:
        context.tracing.stop(path=str(output / f'{name}-trace.zip'))
        context.close()
        browser.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--published-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path('browser-results'))
    args = parser.parse_args()
    root = args.published_dir.resolve()
    dll = root / 'BookingApi.dll'
    if not dll.is_file():
        parser.error('Publish BookingApi before running browser verification')
    args.output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp, (args.output / 'service.log').open('w+') as log:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        base = f'http://127.0.0.1:{port}'
        env = os.environ | {'ASPNETCORE_URLS': base, 'ASPNETCORE_ENVIRONMENT': 'Production', 'BOOKING_DATA': str(Path(temp) / 'bookings.json')}
        process = subprocess.Popen(['dotnet', str(dll)], cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            for _ in range(150):
                if process.poll() is not None:
                    raise RuntimeError('Booking service exited before readiness')
                try:
                    with urllib.request.urlopen(base + '/health', timeout=1) as response:
                        if response.status == 200:
                            break
                except urllib.error.URLError:
                    pass
                time.sleep(0.1)
            else:
                raise RuntimeError('Booking service did not become ready')
            with sync_playwright() as pw:
                for engine in ['chromium', 'firefox', 'webkit']:
                    exercise(getattr(pw, engine), base, args.output, engine, {'width': 1280, 'height': 800})
                exercise(pw.chromium, base, args.output, 'chromium-narrow', {'width': 390, 'height': 844})
            print('All 4 browser configurations passed.', flush=True)
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


if __name__ == '__main__':
    main()
