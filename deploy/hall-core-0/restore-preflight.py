#!/usr/bin/env python3
"""Read-only restore identity check. Never print Compose environment/secrets."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def validate(config, container):
    service = config['services']['hall-core']
    args = service['build']['args']
    uid, gid = str(args['HALL_RUNTIME_UID']), str(args['HALL_RUNTIME_GID'])
    if not all(re.fullmatch(r'[1-9][0-9]*', v) for v in (uid, gid)):
        raise ValueError('Restore requires explicit non-root numeric runtime UID/GID')
    if container['Config']['User'] != f'{uid}:{gid}':
        raise ValueError('Configured UID/GID differs from the existing container; reconcile before restore')
    volumes = [v for v in service['volumes'] if v.get('target') == '/var/lib/hall-core']
    mounts = [v for v in container['Mounts'] if v.get('Destination') == '/var/lib/hall-core']
    if len(volumes) != 1 or len(mounts) != 1:
        raise ValueError('Expected exactly one Hall data mount')
    volume, mount = volumes[0], mounts[0]
    if volume.get('type') != 'bind' or mount.get('Type') != 'bind' or not mount.get('RW'):
        raise ValueError('Hall data must be a writable bind mount')
    data = volume['source']
    if not os.path.isabs(data) or '\n' in data or '\r' in data:
        raise ValueError('Invalid Hall data path')
    if Path(data).resolve() != Path(mount['Source']).resolve():
        raise ValueError('Configured Hall data directory differs from the existing container')
    return uid, gid, data


def main():
    env_file, compose_file = sys.argv[1:]
    command = ['docker', 'compose', '--env-file', env_file, '-f', compose_file]
    # Capture diagnostics too: an invalid configuration may contain secret values.
    def read(args):
        return subprocess.run(args, check=True, capture_output=True, text=True).stdout
    config = json.loads(read(command + ['config', '--format', 'json']))
    ids = read(command + ['ps', '--all', '--quiet', 'hall-core']).split()
    if len(ids) != 1:
        raise ValueError('Expected one existing Hall container; restore does not provision one')
    containers = json.loads(read(['docker', 'inspect', ids[0]]))
    uid, gid, data = validate(config, containers[0])
    stat = Path(data).stat()
    if (stat.st_uid, stat.st_gid) != (int(uid), int(gid)):
        raise ValueError('Hall data directory ownership differs from the runtime; reconcile before restore')
    print(uid, gid, data, sep='\n')


if __name__ == '__main__':
    try:
        main()
    except (KeyError, IndexError, TypeError, ValueError, OSError, subprocess.CalledProcessError) as exc:
        # Do not interpolate raw subprocess/configuration errors into operator logs.
        message = str(exc) if type(exc) is ValueError else 'Cannot verify restore configuration/container identity'
        print(message, file=sys.stderr)
        sys.exit(1)
