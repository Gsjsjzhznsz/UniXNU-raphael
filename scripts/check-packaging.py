#!/usr/bin/env python3
"""Offline packaging adoption checks; --require-release also gates complete image recipes."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import tomllib


def check(device, require_release=False, selected_os=None):
    board = tomllib.loads((device / 'board.toml').read_text())
    package = board.get('package', {})
    runtime = (device / package['unixnu']).resolve()
    revision = package['unixnu_revision']
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('[package] unixnu_revision must be a full commit')
    actual = subprocess.check_output(['git', '-C', str(runtime), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != revision:
        raise ValueError(f'packaging runtime is {actual}, expected {revision}')
    launcher = device / 'scripts/package.sh'
    if launcher.read_bytes() != (runtime / 'templates/package.sh').read_bytes():
        raise ValueError('scripts/package.sh must be copied unchanged from templates/package.sh')
    if not launcher.stat().st_mode & 0o111:
        raise ValueError('scripts/package.sh is not executable')
    profiles = package.get('defconfig', {})
    if board['board']['os_profile'] not in profiles:
        raise ValueError('default OS is missing from [package.defconfig]')
    if selected_os:
        choices = [name for name in profiles if name == selected_os or name.startswith(f'ipados-{selected_os}.')]
        if len(choices) != 1:
            raise ValueError(f'OS {selected_os} is not configured for packaging; choose: ' + ', '.join(profiles))
    for profile, config in profiles.items():
        if not (runtime / 'profiles/os' / profile / 'profile.toml').is_file():
            raise ValueError(f'OS profile not found: {profile}')
        if Path(config).name != config or not (device / 'configs' / config).is_file():
            raise ValueError(f'defconfig not found: {config}')
    if not (device / '.github/workflows/package.yml').is_file():
        raise ValueError('missing .github/workflows/package.yml')
    if not (device / 'unixnu.lock').is_file():
        raise ValueError('missing unixnu.lock')
    record = tomllib.loads((device / 'porting.toml').read_text())
    area = next(a for a in record['area'] if a['id'] == 'packaging')
    if 'scripts/package.sh' not in area['paths']:
        raise ValueError('packaging record does not cover scripts/package.sh')
    missing = []
    # These sections are required by the standard release chain, independently
    # of the diagnostic workspace wrappers. Never invent values to fill them.
    for section, fields in {'firmware': ('config', 'dsc', 'fd', 'packages'),
                            'payload': ('volume', 'size_mib', 'loader'),
                            'bootimg': ('dtb',)}.items():
        for field in fields:
            if not board.get(section, {}).get(field):
                missing.append(f'{section}.{field}')
    report = dict(passed=True, runtime_revision=actual, template_identical=True,
                  supported_profiles=profiles, release_recipe_complete=not missing,
                  missing_recipe_fields=missing, handset_executed=False)
    print(json.dumps(report, indent=2))
    if require_release and missing:
        raise ValueError('step preflight: complete image packaging is not ready; missing board.toml keys: '
                         + ', '.join(missing)
                         + '. See docs/PACKAGING.zh-CN.md; diagnostic images remain a separate gated workflow.')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--require-release', action='store_true')
    parser.add_argument('--os', help='require a configured profile or unambiguous OS major version')
    args = parser.parse_args()
    try:
        check(args.device.resolve(), args.require_release, args.os)
    except (KeyError, StopIteration, ValueError, OSError, subprocess.CalledProcessError) as error:
        sys.exit(f'packaging check: {error}')


if __name__ == '__main__':
    main()
