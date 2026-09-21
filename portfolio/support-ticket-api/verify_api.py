"""Build, launch, exercise, restart, and verify the local .NET API."""
import concurrent.futures
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request


def main():
    project = Path(__file__).resolve().parent
    subprocess.run(['dotnet', 'build', str(project / 'SupportTickets.csproj'), '-c', 'Release'], check=True)
    with tempfile.TemporaryDirectory() as directory:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        base = f'http://127.0.0.1:{port}'
        env = dict(os.environ, TICKET_DATA_PATH=str(Path(directory) / 'tickets.json'),
                   ASPNETCORE_ENVIRONMENT='Production')
        executable = str(project / 'bin/Release/net10.0/SupportTickets.dll')
        process = None
        checks = 0

        def request(method, route, data=None):
            req = urllib.request.Request(base + route, method=method,
                data=json.dumps(data).encode() if data is not None else None,
                headers={'Content-Type': 'application/json'})
            try:
                response = urllib.request.urlopen(req, timeout=5)
            except urllib.error.HTTPError as exc:
                response = exc
            with response:
                body = response.read()
                return response.status, json.loads(body) if body else None

        def expect(condition, message):
            nonlocal checks
            if not condition:
                raise AssertionError(message)
            checks += 1

        def start(log):
            process = subprocess.Popen(['dotnet', executable, '--urls', base], env=env,
                                       stdout=log, stderr=subprocess.STDOUT)
            try:
                for _ in range(100):
                    if process.poll() is not None:
                        raise RuntimeError('API exited before becoming ready')
                    try:
                        if request('GET', '/health')[0] == 200:
                            return process
                    except (OSError, urllib.error.URLError):
                        pass
                    time.sleep(0.1)
                raise RuntimeError('API did not become ready in time')
            except Exception:
                stop(process)
                raise

        def stop(process):
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

        logfile = Path(directory) / 'api.log'
        try:
            with logfile.open('w') as log:
                process = start(log)
                expect(request('POST', '/tickets', {'title': '', 'description': ''})[0] == 400, 'Blank title accepted')
                status, ticket = request('POST', '/tickets', {'title': 'Login fails', 'description': 'Synthetic example'})
                expect(status == 201 and ticket['version'] == 1, 'Create failed')
                route = '/tickets/' + ticket['id']
                expect(request('GET', route)[1]['title'] == 'Login fails', 'Read failed')
                expect(request('GET', '/tickets?limit=0')[0] == 400, 'Invalid pagination accepted')
                expect(request('GET', '/tickets?status=Unknown')[0] == 400, 'Invalid filter accepted')
                status, ticket = request('PATCH', route + '/status', {'status': 'InProgress', 'expectedVersion': 1})
                expect(status == 200 and ticket['version'] == 2 and len(ticket['history']) == 1, 'Status/history update failed')
                expect(request('PATCH', route + '/status', {'status': 'Closed', 'expectedVersion': 1})[0] == 409, 'Stale edit accepted')
                _, same = request('PATCH', route + '/status', {'status': 'InProgress', 'expectedVersion': 2})
                expect(same['version'] == 2 and len(same['history']) == 1, 'No-op changed history')
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                    results = list(pool.map(lambda status: request('PATCH', route + '/status',
                        {'status': status, 'expectedVersion': 2})[0], ['Open', 'Closed']))
                expect(sorted(results) == [200, 409], 'Concurrent updates both succeeded')
                _, current = request('GET', route)
                request('PATCH', route + '/status', {'status': 'Closed', 'expectedVersion': current['version']})
                _, current = request('GET', route)
                expect(request('PATCH', route + '/status', {'status': 'InProgress', 'expectedVersion': current['version']})[0] == 400,
                       'Invalid Closed -> InProgress transition accepted')
                expect(request('GET', '/tickets?status=Closed')[1]['total'] == 1, 'Filter failed')
                stop(process)
                process = None
                process = start(log)
                expect(request('GET', route)[1] == current, 'State was not preserved across restart')
                status, reopened = request('PATCH', route + '/status', {'status': 'Open', 'expectedVersion': current['version']})
                expect(status == 200 and reopened['status'] == 'Open', 'Reopen failed')
                print(f'{checks} HTTP integration checks passed, including concurrency and restart persistence.')
        except Exception:
            print(logfile.read_text())
            raise
        finally:
            if process is not None:
                stop(process)


if __name__ == '__main__':
    main()
