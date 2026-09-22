"""Build and exercise the actual ASP.NET HTTP service using disposable data."""
import argparse
import json
import os
from pathlib import Path
import socket
import sys
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

ROOT = Path(__file__).resolve().parent
checks = 0


def check(condition, name):
    global checks
    if not condition:
        raise AssertionError(name)
    checks += 1
    print('PASS:', name, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--published-dir', type=Path, help='Verify a published package without building source')
    args = parser.parse_args()
    app_root = args.published_dir.resolve() if args.published_dir else ROOT
    if args.published_dir:
        dll = app_root / 'BookingApi.dll'
        for relative in ['BookingApi.dll', 'BookingApi.deps.json', 'BookingApi.runtimeconfig.json',
                         'wwwroot/index.html', 'wwwroot/app.js', 'wwwroot/style.css', 'client.py']:
            if not (app_root / relative).is_file():
                parser.error(f'Published package is missing {relative}')
    else:
        subprocess.run(['dotnet', 'build', '-c', 'Release', '--nologo'], cwd=ROOT, check=True)
        dll = ROOT / 'bin/Release/net10.0/BookingApi.dll'
    with tempfile.TemporaryDirectory() as temp:
        data = Path(temp) / 'bookings.json'
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        base = f'http://127.0.0.1:{port}'
        env = os.environ | {'ASPNETCORE_URLS': base, 'BOOKING_DATA': str(data), 'ASPNETCORE_ENVIRONMENT': 'Production'}
        command = ['dotnet', str(dll)]
        log = open(Path(temp) / 'service.log', 'w+')
        process = None

        def call(method, path, body=None, raw=None):
            payload = raw if raw is not None else None if body is None else json.dumps(body).encode()
            req = urllib.request.Request(base + path, data=payload, method=method, headers={'Content-Type': 'application/json'})
            try:
                response = urllib.request.urlopen(req, timeout=5)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                content = response.read()
                try:
                    result = json.loads(content)
                except ValueError:
                    result = content.decode()
                return response.status, result, dict(response.headers)

        def start():
            nonlocal process
            process = subprocess.Popen(command, cwd=app_root, env=env, stdout=log, stderr=subprocess.STDOUT)
            for _ in range(100):
                if process.poll() is not None:
                    raise RuntimeError('Service exited before readiness')
                try:
                    if call('GET', '/health')[0] == 200:
                        return
                except urllib.error.URLError:
                    pass
                time.sleep(0.1)
            raise RuntimeError('Readiness deadline exceeded')

        def stop():
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

        try:
            start()
            status, page, _ = call('GET', '/')
            check(status == 200 and 'Appointment Desk' in page, 'browser interface served')
            check(call('GET', '/app.js')[0] == 200, 'browser API client served')
            check(call('GET', '/style.css')[0] == 200, 'browser stylesheet served')
            check(call('GET', '/api/services')[1] == ['consultation', 'code-review', 'career-coaching'], 'service catalog')
            check(call('GET', '/api/bookings')[1] == [], 'empty booking list')
            tomorrow = datetime.now(timezone.utc).replace(second=0, microsecond=0) + timedelta(days=1)
            body = {'service': 'consultation', 'customer': ' Test Customer ', 'start': tomorrow.isoformat(), 'minutes': 30}
            status, booked, headers = call('POST', '/api/bookings', body)
            check(status == 201 and booked['customer'] == 'Test Customer', 'create and normalize booking')
            location = headers.get('Location', headers.get('location'))
            check(location == '/api/bookings/' + booked['id'] and call('GET', location)[1] == booked, 'resource location and lookup')
            check(call('POST', '/api/bookings', body)[0] == 409, 'duplicate interval rejected')
            overlap = body | {'start': (tomorrow + timedelta(minutes=15)).isoformat()}
            check(call('POST', '/api/bookings', overlap)[0] == 409, 'partial overlap rejected')
            adjacent = body | {'start': (tomorrow + timedelta(minutes=30)).isoformat()}
            check(call('POST', '/api/bookings', adjacent)[0] == 201, 'adjacent intervals allowed')
            check(call('POST', '/api/bookings', body | {'service': 'code-review'})[0] == 201, 'separate services may overlap')
            for changes in [{'service': 'unknown'}, {'customer': ' '}, {'minutes': 0}, {'minutes': 241}, {'start': '2000-01-01T00:00:00Z'}, {'start': (tomorrow + timedelta(days=366)).isoformat()}]:
                check(call('POST', '/api/bookings', body | changes)[0] == 400, f'input validation {changes}')
            check(call('POST', '/api/bookings', raw=b'{bad json')[0] == 400, 'malformed JSON rejected')
            check(call('POST', '/api/bookings', raw=b' ' * 20000)[0] == 413, 'request size bounded')
            concurrent = body | {'service': 'career-coaching'}
            with ThreadPoolExecutor(max_workers=6) as pool:
                statuses = list(pool.map(lambda _: call('POST', '/api/bookings', concurrent)[0], range(6)))
            check(statuses.count(201) == 1 and statuses.count(409) == 5, 'concurrent booking conflict is atomic')
            before = call('GET', '/api/bookings')[1]
            stop(); start()
            check(call('GET', '/api/bookings')[1] == before, 'bookings survive process restart')
            check(call('DELETE', location)[0] == 204 and call('GET', location)[0] == 404, 'cancellation removes resource')
            check(call('DELETE', location)[0] == 404, 'repeat cancellation returns not found')
            check(call('POST', '/api/bookings', body)[0] == 201, 'cancelled slot can be booked again')
            subprocess.run([sys.executable, str(app_root / 'client.py'), '--base', base, 'demo'], check=True)
            check(len(call('GET', '/api/bookings')[1]) == len(before), 'Python web-service client cleans up its booking')
            stop()
            data.write_text('invalid store')
            process = subprocess.Popen(command, cwd=app_root, env=env, stdout=log, stderr=subprocess.STDOUT)
            check(process.wait(timeout=15) != 0, 'corrupt persisted data fails startup')
            print(f'{checks} HTTP and persistence checks passed.', flush=True)
        except Exception:
            log.flush(); log.seek(0)
            print(log.read()[-12000:])
            raise
        finally:
            stop(); log.close()


if __name__ == '__main__':
    main()
