"""Run every standalone portfolio project's test suite from any directory."""
import subprocess
import sys
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent
    projects = sorted(path for path in root.iterdir() if path.is_dir() and list(path.glob('test_*.py')))
    if not projects:
        raise SystemExit('No portfolio tests found')
    failed = []
    for project in projects:
        print(f'Running {project.name}', flush=True)
        result = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', str(project), '-v'])
        if result.returncode:
            failed.append(project.name)
    if failed:
        print('Failed projects: ' + ', '.join(failed), file=sys.stderr)
        return 1
    print(f'All {len(projects)} project suites passed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
