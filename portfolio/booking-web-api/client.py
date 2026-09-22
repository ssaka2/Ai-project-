"""Call the local booking Web API from a separate Python process."""
import argparse
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone


def request(base, method, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(base.rstrip('/') + path, data=data, method=method,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=10) as response:
        raw = response.read()
        return json.loads(raw) if raw else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default='http://127.0.0.1:5080')
    parser.add_argument('action', choices=['list', 'demo'])
    args = parser.parse_args()
    try:
        if args.action == 'list':
            print(json.dumps(request(args.base, 'GET', '/api/bookings'), indent=2))
            return
        start = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        booking = request(args.base, 'POST', '/api/bookings',
                          {'service': 'consultation', 'customer': 'Synthetic Python client', 'start': start, 'minutes': 30})
        try:
            print(json.dumps(request(args.base, 'GET', '/api/bookings/' + booking['id']), indent=2))
        finally:
            request(args.base, 'DELETE', '/api/bookings/' + booking['id'])
        print('Created, retrieved, and cancelled the synthetic booking.')
    except (urllib.error.URLError, ValueError) as exc:
        parser.exit(1, f'Web service request failed: {exc}\n')


if __name__ == '__main__':
    main()
