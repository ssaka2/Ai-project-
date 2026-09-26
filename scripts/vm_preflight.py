"""Read-only Linux VM checks for the portfolio. Does not install or start services."""
import json
import os
from pathlib import Path
import platform
import re
import shutil
import sqlite3
import subprocess
import sys


def command(args):
    if not shutil.which(args[0]):
        return None
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=15)
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def main():
    checks = []
    def add(name, passed, detail, required=True):
        checks.append({'check': name, 'status': 'pass' if passed else 'fail' if required else 'warning', 'detail': detail})

    add('Linux x64 host', platform.system() == 'Linux' and platform.machine().lower() in ('x86_64', 'amd64'), 'Target architecture for the repository SQL Server and Linux binary examples.')
    add('Python >=3.11', sys.version_info >= (3, 11), platform.python_version())
    add('Git', command(['git', '--version']) is not None, 'Required to retrieve and update the repository.')
    add('Docker daemon', command(['docker', 'info', '--format', '{{.ServerVersion}}']) is not None, 'Current user must be able to reach the Docker daemon.')
    compose = command(['docker', 'compose', 'version', '--short'])
    add('Docker Compose v2+', bool(compose and re.match(r'^v?[2-9]\.', compose)), compose or 'Compose unavailable.')
    sdks = command(['dotnet', '--list-sdks']) or ''
    add('.NET 10 SDK', any(line.startswith('10.') for line in sdks.splitlines()), 'Required for native CareerDesk and the two ASP.NET API projects.')
    node = command(['node', '--version']) or ''
    add('Node.js 24', node.startswith('v24.'), node or 'Node unavailable.')
    go = command(['go', 'version']) or ''
    add('Go 1.27', bool(re.search(r'go1\.27(?:\.|\s)', go)), go or 'Go unavailable; matches the CI toolchain.')
    rust = command(['rustup', 'run', '1.98.1', 'rustc', '--version']) or ''
    add('Rust 1.98.1', rust.startswith('rustc 1.98.1 '), rust or 'Pinned Rust toolchain unavailable.')
    try:
        with sqlite3.connect(':memory:') as db:
            db.execute('CREATE VIRTUAL TABLE documents USING fts5(body)')
        fts = True
    except sqlite3.Error:
        fts = False
    add('SQLite FTS5', fts, 'Required by Local Knowledge Search.')
    try:
        memory_kib = int(re.search(r'^MemTotal:\s+(\d+)', Path('/proc/meminfo').read_text(), re.M)[1])
        memory_gib = round(memory_kib / 1024**2, 1)
        add('Memory planning', memory_gib >= 7.5, f'{memory_gib} GiB physical memory; 8 GB nominal is a demo starting point, not a concurrency guarantee.', False)
    except (OSError, TypeError, ValueError):
        add('Memory planning', False, 'Unable to read host memory.', False)
    free_gib = round(shutil.disk_usage(Path.cwd()).free / 1024**3, 1)
    add('Free disk planning', free_gib >= 40, f'{free_gib} GiB free on current filesystem; allow room for SDKs, images, databases, and reports.', False)
    add('CPU planning', (os.cpu_count() or 0) >= 4, f'{os.cpu_count()} logical CPUs; four is a demo starting point.', False)
    add('WireGuard tools', command(['wg', '--version']) is not None, 'Needed only for the real VPN tunnel; kernel/network permissions need a separate test.', False)
    print(json.dumps({'ready_for_native_setup': not any(c['status'] == 'fail' for c in checks),
                      'scope': 'Host prerequisites only; no project execution, cloud quota, public access, or production-readiness certification.',
                      'checks': checks}, indent=2))
    return 1 if any(c['status'] == 'fail' for c in checks) else 0


if __name__ == '__main__':
    raise SystemExit(main())
