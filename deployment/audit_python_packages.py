"""Check pinned installed packages against PyPI's per-version advisory records."""
import argparse
import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
import httpx


async def audit(packages):
    semaphore = asyncio.Semaphore(6)
    async with httpx.AsyncClient(timeout=25, follow_redirects=True) as client:
        async def check(name, installed):
            version = installed.split('+', 1)[0]
            url = f'https://pypi.org/pypi/{quote(name)}/{quote(version)}/json'
            result = {'name': name, 'installed_version': installed, 'public_version': version,
                      'source_url': url, 'local_version_suffix_removed': installed != version}
            try:
                async with semaphore:
                    response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                if 'vulnerabilities' not in data:
                    result.update(status='missing_advisory_field')
                else:
                    result.update(status='checked', vulnerabilities=data['vulnerabilities'])
            except httpx.HTTPError as exc:
                result.update(status='lookup_failed', error_type=type(exc).__name__,
                              http_status=getattr(getattr(exc, 'response', None), 'status_code', None))
            return result
        return await asyncio.gather(*(check(name, version) for name, version in packages))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packages', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    if not args.output.resolve().is_relative_to(root) or args.output.exists():
        raise SystemExit('Choose a new output inside the project.')
    packages = []
    for line in args.packages.read_text(encoding='utf-8').splitlines():
        match = re.fullmatch(r'([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+!-]+)', line)
        if not match:
            raise ValueError('Input must contain only pinned public package versions.')
        packages.append(match.groups())
    results = asyncio.run(audit(packages))
    checked = sum(item['status'] == 'checked' for item in results)
    vulnerable = sum(bool(item.get('vulnerabilities')) for item in results)
    report = {'recorded_at': datetime.now(timezone.utc).isoformat(), 'source': 'PyPI per-release JSON API',
              'package_list': args.packages.name, 'planned': len(packages), 'checked': checked,
              'vulnerable_packages': vulnerable, 'coverage_complete': checked == len(packages),
              'passed': checked == len(packages) and vulnerable == 0, 'results': results,
              'limitations': ['Advisories reflect PyPI known vulnerabilities at the recorded time; not a security certification.',
                              'Local suffixes such as +cpu are checked against the matching public version.',
                              'OS/base-image packages, configuration and unknown vulnerabilities are outside this check.']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps({key: report[key] for key in ('planned', 'checked', 'vulnerable_packages', 'coverage_complete', 'passed')}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
