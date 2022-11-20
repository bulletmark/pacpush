#!/usr/bin/python3
'''
Utility to push this Arch hosts system and AUR package caches to other
host[s] to avoid those other hosts having to download the same new
package lists and updated packages, at least for shared common packages.
Requires root ssh access to other hosts (it is easier with an auth key).
'''
# Author: Mark Blakeney, Mar 2017.

import sys
import os
import platform
import subprocess
import argparse
import tempfile
import pickle
import multiprocessing
from pathlib import Path

# Define paths of interest for pacman packages
PACLIST = Path('/var/lib/pacman/sync')
PACPKGS = Path('/var/cache/pacman/pkg')
MIRRORS = Path('/etc/pacman.d/mirrorlist')

# Define ANSI escape sequences for colors ..
COLOR_red = '\033[31m'
COLOR_green = '\033[32m'
COLOR_yellow = '\033[33m'
COLOR_blue = '\033[34m'
COLOR_magenta = '\033[35m'
COLOR_cyan = '\033[36m'
COLOR_white = '\033[37m'

# Colors to output host messages
COLORS = (COLOR_green, COLOR_yellow, COLOR_magenta, COLOR_cyan,
          COLOR_red, COLOR_blue)

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
opt.add_argument('-C', '--no-color', action='store_true',
        help='do not color output lines')
opt.add_argument('-M', '--mirrorlist', action='store_true',
        help='also sync mirrorlist file')
opt.add_argument('hosts', nargs='*', help='hosts to update')
opt.add_argument('--env', help=argparse.SUPPRESS)
args = opt.parse_args()
dryrun = '-n ' if args.dryrun else ''

console = None

def pacman(opt):
    'Run pacman with given option[s] and return list of result lines'
    res = subprocess.run(f'pacman {opt}'.split(), text=True,
            stdout=subprocess.PIPE)

    # Ignore pacman return code since it returns non 0 codes even for
    # valid invocations
    return res.stdout.splitlines()

def report_updates():
    'Report all installed native and AUR packages with updates pending'
    from packaging import version
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
        pkgs[name] = version.parse(vers)

    # Get info for this list of packages from AURWEB
    params = {'v': 5, 'type': 'info', 'arg[]': list(pkgs)}

    try:
        r = requests.get(AURWEB, params=params)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        return f'AURWEB error: {str(e)}'

    # Now print out version updates for AUR packages
    # Follow cower format for prepending AUR lines with ':: '.
    for pkg in r.json().get('results', []):
        name = str(pkg.get('Name'))
        newver = version.parse(pkg.get('Version', ''))
        oldver = pkgs.get(name)
        if oldver:
            try:
                update = oldver < newver
            except TypeError:
                update = str(oldver) < str(newver)

            if update:
                print(f':: {name} {oldver} -> {newver}')

def run_user():
    'Run as user to read user config and save environment'
    from ruamel.yaml import YAML
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

    conf = YAML(typ='safe').load(conffile)

    # Clonedir may either be a single dir, or a list of dirs
    clonedir = conf.get('clonedir', [])
    if isinstance(clonedir, str):
        clonedirs = [Path(clonedir).expanduser()]
    else:
        clonedirs = [Path(c).expanduser() for c in clonedir]

    # Can immediately filter out dirs which don't exist
    clonedirs = [c for c in clonedirs if c.is_dir()]

    # Save ordinary user environment to reference for running as root
    fp = tempfile.NamedTemporaryFile()
    pickle.dump(clonedirs, fp)
    fp.flush()

    # Pass ssh auth so that root uses sudo user's ssh cached key and
    # also pass user environment
    sock = os.getenv('SSH_AUTH_SOCK')
    cmd = ['/usr/bin/sudo', f'SSH_AUTH_SOCK={sock}'] + sys.argv + \
            [f'--env={fp.name}']

    # Add mirrorlist option if specified in conf file (and not already
    # specified in command line)
    if not args.mirrorlist and conf.get('mirrorlist', False):
        cmd += ' --mirrorlist'

    return subprocess.run(cmd).returncode

lock = multiprocessing.Lock()

def synchost(num, host, clonedirs):
    'Sync to given host'
    color = COLORS[num % len(COLORS)]

    def log(msg):
        'Log messages for update to host'
        txt = f'{host}: {msg}'
        with lock:
            if args.no_color:
                print(txt)
            else:
                print(color + txt)

    def rsync(src):
        cmd = f'/usr/bin/rsync -arRO --info=name1 {dryrun} {src} {host}:/'
        res = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE,
                bufsize=1, text=True)

        for line in res.stdout:
            log(f'synced {line.strip()}')

    if not args.no_machcheck:
        res = subprocess.run(f'/usr/bin/ssh {host} uname -m'.split(),
                text=True, stdout=subprocess.PIPE)

        if res.returncode != 0:
            log(f'ssh failed. Have you set up root ssh access to {host}?')
            return

        hostmach = res.stdout.strip()
        if hostmach != MACH:
            log(f'{HOST} type={MACH} does not match {host} type={hostmach}.')
            return

    # Push the current package lists to the host then work out what
    # package updates are required by this host. Then push all new
    # packages it requires that we already hold, including AUR files.
    if not args.aur_only:
        arglist = str(PACLIST)
        if args.mirrorlist:
            arglist += f' {MIRRORS}'
            mirtxt = ' and mirror'
        else:
            mirtxt = ''

        log(f'syncing {MACH} package{mirtxt} lists ..')
        rsync(arglist)

    log('getting list of needed package updates ..')
    aopt = ' --aur-only' if args.aur_only else ''
    sopt = ' --sys-only' if args.sys_only or not clonedirs else ''
    res = subprocess.run(f'/usr/bin/ssh {host} {PROG}{aopt}{sopt} -u'.split(),
            text=True, stdout=subprocess.PIPE)

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
                    log(f'need AUR {clonedir.name}/{name}')
                    filelist.append(dpkg)

            if count == len(filelist):
                log(f'AUR {name} (not available)')
        else:
            # System package:
            name, oldver, junk, newver = line.split()

            pkg = f'{name}-{newver}'
            pkgfiles = PACPKGS.glob(f'{pkg}-*')
            if pkgfiles:
                log(f'need {pkg}')
                filelist.extend(pkgfiles)
            else:
                log(f'{pkg} (not available)')

    if filelist:
        log('syncing updated packages ..')
        with tempfile.NamedTemporaryFile() as fp:
            fp.writelines(bytes(line) + b'\n' for line in filelist)
            fp.flush()
            rsync(f'--files-from {fp.name} /')
        log('finished syncing packages.')
    elif name:
        log('no packages available.')
    else:
        log('already up to date.')

def run_root():
    'Run as root to do updates'
    # Load calling user's environment for reference. This is a hidden
    # argument passed programmatically.
    with open(args.env, 'rb') as fp:
        clonedirs = pickle.load(fp)

    # Remove any duplicate hosts from argument list
    hosts = list(dict.fromkeys(args.hosts))

    if len(hosts) == 1 or args.parallel_count <= 1:
        # May as well do in same process if only 1 host or doing in series
        for n, h in enumerate(hosts):
            synchost(n, h, clonedirs)
    else:
        # Farm out the jobs to a pool of processes
        with multiprocessing.Pool(min(len(hosts), args.parallel_count)) as p:
            p.starmap(synchost, ((n, h, clonedirs) for n, h in
                enumerate(hosts)))

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
