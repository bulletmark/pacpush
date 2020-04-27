#!/usr/bin/python3
'''
Utility to push this Arch hosts system and AUR package caches to other
host[s] to avoid those other hosts having to download the same new
package lists and updated packages, at least for shared common packages.
Requires root ssh access to other hosts (it is easier with an auth key).
'''
# Author: Mark Blakeney, Mar 2017.

import sys, os, platform, subprocess, argparse, tempfile, pickle
import multiprocessing
from collections import OrderedDict
from pathlib import Path

# Define paths of interest for pacman packages
PACLIST = Path('/var/lib/pacman/sync')
PACPKGS = Path('/var/cache/pacman/pkg')

# Where we fetch AUR versions from
AURWEB = 'https://aur.archlinux.org/rpc'

HOST = platform.node()
MACH = platform.machine()

# Conf file, search first for user file then system file
PROG = Path(sys.argv[0]).stem
CONFNAME = f'{PROG}.conf'
USERCNF = os.getenv('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
CONFDIRS = (USERCNF, f'/usr/share/{PROG}')

# Process command line options
opt = argparse.ArgumentParser(description=__doc__)
opt.add_argument('-n', '--dryrun', action='store_true', help='dry run only')
opt.add_argument('-m', '--no-machcheck', action='store_true',
        help='do not check machine type compatibility')
opt.add_argument('-p', '--parallel-count', type=int, default=10,
        help='max number of hosts to update in parallel. '
        'Default is %(default)d.')
opt.add_argument('-c', '--conffile',
        help='alternative configuration file')
opt.add_argument('-u', '--updates', action='store_true',
        help='just report all installed packages with updates pending, '
        'including AUR packages')
opt.add_argument('-s', '--sys-only', action='store_true',
        help='only sync/report system packages, not AUR')
opt.add_argument('-a', '--aur-only', action='store_true',
        help='only sync/report AUR packages, not system')
opt.add_argument('hosts', nargs='*', help='hosts to update')
opt.add_argument('--env', help=argparse.SUPPRESS)
args = opt.parse_args()
dryrun = '-n ' if args.dryrun else ''

def pacman(opt):
    'Run pacman with given option[s] and return list of result lines'
    res = subprocess.run(f'pacman {opt}'.split(), universal_newlines=True,
            stdout=subprocess.PIPE)

    # Ignore pacman return code since it returns non 0 codes even for
    # valid invocations
    return res.stdout.splitlines()

def report_updates():
    'Report all installed native and AUR packages with updates pending'
    from distutils.version import LooseVersion as Version
    import requests

    # Print out version updates for standard packages
    if not args.aur_only:
        for line in pacman('-Qu'):
            name, oldver, junk, *newvers = line.split()
            if len(newvers) > 1 and 'ignored' in newvers[1]:
                continue

            newver = newvers[0]
            print(f'{name} {oldver} -> {newver}')

    if args.sys_only:
        return

    # Create dict of installed AUR packages and versions
    pkgs = {}
    for line in pacman('-Qm'):
        name, vers = line.split()
        pkgs[name] = Version(vers)

    # Get info for this list of packages from AURWEB
    params = {'v': 5, 'type': 'info', 'arg[]': list(pkgs)}

    try:
        r = requests.get(AURWEB, params=params)
    except Exception as e:
        return f'AURWEB error: {str(e)}'

    if r.status_code != requests.codes.ok:
        return f'AURWEB returned error: {r.text}'

    # Now print out version updates for AUR packages
    # Follow cower format for prepending AUR lines with ':: '.
    for pkg in r.json().get('results', []):
        name = str(pkg.get('Name'))
        newver = Version(pkg.get('Version', ''))
        oldver = pkgs.get(name)
        if oldver:
            # Catch and work around Version bug, see
            # https://bugs.python.org/issue14894
            try:
                update = oldver < newver
            except TypeError:
                update = str(oldver) < str(newver)

            if update:
                print(f':: {name} {oldver} -> {newver}')

def run_user():
    'Run as user to read user config and save environment'
    import ruamel.yaml as yaml
    # Search for configuration file. Use file given as command line
    # argument, else look for file in search dir order.
    if args.conffile:
        conffile = Path(args.conffile)
        if not conffile.exists():
            return f'Conf file "{conffile}" does not exist.'
    else:
        for confdir in CONFDIRS:
            conffile = Path(confdir, CONFNAME)
            if conffile.exists():
                break
        else:
            dirs = ' or '.join(CONFDIRS)
            return f'No file {CONFNAME} in {dirs}.'

    with conffile.open() as fp:
        conf = yaml.safe_load(fp)

    # Clonedir may either be a single dir, or a list of dirs
    clonedir = conf.get('clonedir', [])
    if isinstance(clonedir, str):
        clonedirs = [Path(clonedir).expanduser()]
    else:
        clonedirs = [Path(c).expanduser() for c in clonedir]

    # Can immediately filter out dirs which don't exist
    clonedirs = [c for c in clonedirs if c.exists()]

    # Save ordinary user environment to reference for running as root
    fp = tempfile.NamedTemporaryFile()
    pickle.dump(clonedirs, fp)
    fp.flush()

    # Pass ssh auth so that root uses sudo user's ssh cached key and
    # also pass user environment
    sock = os.getenv('SSH_AUTH_SOCK')
    cmd = ['/usr/bin/sudo', f'SSH_AUTH_SOCK={sock}'] + sys.argv + \
            [f'--env={fp.name}']
    return subprocess.run(cmd).returncode

lock = multiprocessing.Lock()

def synchost(host, clonedirs):
    'Sync to given host'
    def log(error, child, msg):
        'Log messages for update to host'
        fp = sys.stderr if error else sys.stdout
        lead = '* ' if child else ''
        txt = f'{lead}{HOST} -> {host}: {msg}\n'
        with lock:
            fp.write(txt)
            fp.flush()

    if not args.no_machcheck:
        res = subprocess.run(f'/usr/bin/ssh {host} uname -m'.split(),
                universal_newlines=True, stdout=subprocess.PIPE)

        if res.returncode != 0:
            log(1, 0, 'failed to ssh.\n'
                    f'Have you set up root ssh access to {host}?')
            return

        hostmach = res.stdout.strip()
        if hostmach != MACH:
            log(1, 0, f'{HOST} type={MACH} does not match '
                    f'{host} type={hostmach}.')
            return

    # Push the current package lists to the host then work out what
    # package updates are required by this host. Then push all new
    # packages it requires that we already hold, including AUR files.
    if not args.aur_only:
        log(0, 0, f'syncing {MACH} package lists ..')
        res = subprocess.run(
                f'/usr/bin/rsync -aRO --info=name1 {dryrun}'
                f'{PACLIST} {host}:/'.split())

        if res.returncode != 0:
            log(1, 0, 'failed to sync package lists.')
            return

    log(0, 0, f'getting list of required package updates from {host} ..')
    aopt = ' --aur-only' if args.aur_only else ''
    sopt = ' --sys-only' if args.sys_only or not clonedirs else ''
    res = subprocess.run(f'/usr/bin/ssh {host} pacpush{aopt}{sopt} -u'.split(),
            universal_newlines=True, stdout=subprocess.PIPE)

    filelist = []
    name = None
    for line in res.stdout.strip().splitlines():
        if line.startswith(':'):
            # AUR package:
            junk, name, oldver, junk, newver = line.split()

            # Sync the entire clone dir[s], if it exists
            count = len(filelist)
            for clonedir in clonedirs:
                dpkg = clonedir.joinpath(name)
                if dpkg.exists():
                    log(0, 1,
                      f'AUR {clonedir.name}/{name}')
                    filelist.append(dpkg)

            if count == len(filelist):
                log(0, 1, f'AUR {name} (not available)')
        else:
            # System package:
            name, oldver, junk, newver = line.split()

            # Can't be sure of the file (package) extension so get the
            # latest file by time.
            pkg = f'{name}-{newver}'
            dpkg = max(PACPKGS.glob(f'{pkg}-*'),
                    key=lambda p: p.stat().st_mtime, default=None)
            if dpkg:
                log(0, 1, pkg)
                filelist.append(dpkg)
            else:
                log(0, 1, f'{pkg} (not available)')

    if filelist:
        log(0, 0, 'syncing updated packages ..')
        with tempfile.NamedTemporaryFile() as fp:
            fp.writelines(bytes(l) + b'\n' for l in filelist)
            fp.flush()
            subprocess.run(
                f'/usr/bin/rsync -arRO --info=name1 {dryrun}'
                f'--files-from {fp.name} / {host}:/'.split())
    elif name:
        log(0, 0, f'no packages available.')
    else:
        log(0, 0, f'already up to date.')

def run_root():
    'Run as root to do updates'
    # Load calling user's environment for reference. This is a hidden
    # argument passed programmatically.
    with open(args.env, 'rb') as fp:
        clonedirs = pickle.load(fp)

    # Remove any duplicate hosts from argument list
    hosts = list(OrderedDict.fromkeys(args.hosts))

    if len(hosts) == 1 or args.parallel_count <= 1:
        # May as well do in same process if only 1 host or doing in series
        for h in hosts:
            synchost(h, clonedirs)
    else:
        # Farm out the jobs to a pool of processes
        with multiprocessing.Pool(args.parallel_count) as p:
            p.starmap(synchost, ((h, clonedirs) for h in hosts))

def main():
    'Main processing ..'
    if args.updates:
        return report_updates()

    if not args.hosts:
        opt.error('Must specify at least one host')

    # If not invoked as root then re-invoke ourself using sudo
    if os.geteuid() != 0:
        return run_user()

    if not os.getenv('SUDO_USER') or not args.env:
        return 'Do not run as root. Run directly as your normal user.'

    # From here on we are running as root ..
    return run_root()

if __name__ == '__main__':
    sys.exit(main())
