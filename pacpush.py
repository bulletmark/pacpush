#!/usr/bin/python3
'''
Utility to push this Arch hosts system and AUR package caches to other
host[s] to avoid those other hosts having to download the same new
package lists and updated packages, at least for shared common packages.
Requires root ssh access to other hosts (it is easier with an auth key).
'''
# Author: Mark Blakeney, Mar 2017.
import argparse
import multiprocessing
import os
import platform
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

from platformdirs import user_config_path

# Default AUR build dir[s] if not specified as command line argument
AURBUILD = '~/.cache/yay;~/.cache/paru/clone;~/.cache/trizen;'\
        '~/.cache/pikaur/aur_repos;~/.cache/aurman'
SSHCONFIG = '~/.ssh/config'

# Define paths of interest for pacman packages
PACLIST = Path('/var/lib/pacman/sync')
PACPKGS = Path('/var/cache/pacman/pkg')
MIRRORS = Path('/etc/pacman.d/mirrorlist')

# Conf file, search first for user file then system file
PROG = Path(sys.argv[0]).stem
CNFFILE = user_config_path() / PROG / f'{PROG}.conf'

# Define ANSI escape sequences for colors (fg, invert fg+bg)
# Refer https://en.wikipedia.org/wiki/ANSI_escape_code#Colors
COLOR_red = ('\033[31m', '\033[30;41m')
COLOR_green = ('\033[32m', '\033[30;42m')
COLOR_yellow = ('\033[33m', '\033[30;43m')
COLOR_blue = ('\033[34m', '\033[30;44m')
COLOR_magenta = ('\033[35m', '\033[30;45m')
COLOR_cyan = ('\033[36m', '\033[30;46m')

COLOR_reset = '\033[39;49m'

# Colors to output host messages
COLORS = (COLOR_green, COLOR_yellow, COLOR_magenta, COLOR_cyan,
          COLOR_red, COLOR_blue)

# Where we fetch AUR versions from
AURWEB = 'https://aur.archlinux.org/rpc'

HOST = platform.node()
MACH = platform.machine()

args = None

def debug(argv):
    'Output debug info'
    from getpass import getuser
    print(f'# {getuser()}@{HOST}: {sys.argv[0]}', shlex.join(argv))

def pacman(opt):
    'Run pacman with given option[s] and return list of result lines'
    res = subprocess.run(f'pacman {opt}'.split(), text=True,
            stdout=subprocess.PIPE)

    # Ignore pacman return code since it returns non 0 codes even for
    # valid invocations
    return res.stdout.splitlines()

def report_updates():
    '''
    Run on the remote machine to report all installed native and AUR
    packages with updates pending
    '''
    import requests
    from pyalpm import vercmp

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
        pkgs[name] = vers

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
        newver = pkg.get('Version', '?')
        oldver = pkgs.get(name)
        if oldver and vercmp(oldver, newver) < 0:
            print(f':: {name} {oldver} -> {newver}')

def run_user(argv):
    'Run as ordinary user'
    # Pass ssh auth so that root uses sudo user's ssh cached key
    sock = os.getenv('SSH_AUTH_SOCK')
    cmd = ['sudo', f'SSH_AUTH_SOCK={sock}'] + [sys.argv[0]] + argv

    # Build dirs may either be a single dir, or a list of dirs
    build_dirs_str = args.aur_build_dir \
            if args.aur_build_dir is not None else AURBUILD
    build_dirs = [Path(d).expanduser() for d in
                  build_dirs_str.split(';')] if build_dirs_str else []

    # Immediately filter out dirs which don't exist
    build_dirs = [str(d) for d in build_dirs if d.is_dir()]

    # We force set the following dir options even if they are an empty
    # string so that we override any default dirs that don't exist
    build_dirs_str = ';'.join(build_dirs)
    cmd.extend(['--aur-build-dir', build_dirs_str])

    if args.ssh_config_file is None:
        ssh_file = Path(SSHCONFIG).expanduser()
        ssh_config = str(ssh_file) if ssh_file.is_file() else ''
    elif not args.ssh_config_file:
        # If empty string then be sure to disable default ssh config
        ssh_config = ''
    else:
        # If ssh config path is relative then make it relative to config file
        ssh_file = (CNFFILE.parent / args.ssh_config_file).expanduser()
        if not ssh_file.is_file():
            return f'ssh config file {ssh_file} does not exist.'
        ssh_config = str(ssh_file)

    cmd.extend(['--ssh-config-file', ssh_config])
    return subprocess.run(cmd).returncode

# Allocate lock for log messages
log_lock = multiprocessing.Lock()

def synchost(num, host):
    'Sync to given host'
    color = COLORS[num % len(COLORS)]

    ssh_args = ''
    rsync_args = '-n' if args.dryrun else ''

    if args.ssh_config_file:
        ssh_args += f' -F {args.ssh_config_file}'
        rsync_args += f' -e "ssh -F {args.ssh_config_file}"'

    def log(msg, *, priority=False):
        'Log messages for update to host'
        txt = f'{host}: {msg}'
        if not args.no_color:
            txt = color[priority and not args.no_color_invert] + \
                    txt + COLOR_reset

        with log_lock:
            print(txt)

    def rsync(src):
        cmd = f'rsync -arRO --info=name1 {rsync_args} {src} root@{host}:/'
        res = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=1,
                               text=True, shell=True)

        for line in res.stdout:
            log(f'pushed {line.strip()}')

    if not args.no_machcheck:
        res = subprocess.run(f'ssh{ssh_args} root@{host} uname -m',
                             text=True, shell=True, stdout=subprocess.PIPE)

        if res.returncode != 0:
            log(f'ssh check failed. Have you set up root ssh access to {host}?',
                priority=True)
            return

        hostmach = res.stdout.strip()
        if hostmach != MACH:
            log(f'{HOST} type={MACH} does not match {host} type={hostmach}.',
                priority=True)
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

        log(f'pushing {MACH} package{mirtxt} lists ..')
        rsync(arglist)

    build_dirs = [Path(p) for p in args.aur_build_dir.split(';')] if \
            args.aur_build_dir and not args.sys_only else []

    log('getting list of needed package updates ..')
    aopt = ' --aur-only' if args.aur_only else ''
    sopt = ' --sys-only' if not build_dirs else ''
    debug = ' -d' if args.debug else ''

    if aopt and sopt:
        log('Error: both --aur-only and (--sys-only or '
            '!--aur-build-dirs) are set', priority=True)

    res = subprocess.run(f'ssh{ssh_args} root@{host} '
                         f'{sys.argv[0]}{aopt}{sopt}{debug} -u',
                         text=True, shell=True, stdout=subprocess.PIPE)

    if res.returncode != 0:
        log(f'ssh failed. Have you set up root ssh access to {host}?',
            priority=True)
        return

    filelist = []
    name = None
    for line in res.stdout.strip().splitlines():
        if line.startswith('#'):
            if args.debug:
                print(line)
        elif line.startswith(':'):
            # AUR package:
            junk, name, oldver, junk, newver = line.split()

            # Sync the entire build dir[s], if it exists
            count = len(filelist)
            for build_dir in build_dirs:
                dpkg = build_dir.joinpath(name)
                if dpkg.is_dir():
                    log(f'need AUR {build_dir.name}/{name}')
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
        log('pushing updated packages ..', priority=True)
        with tempfile.NamedTemporaryFile() as fp:
            fp.writelines(bytes(line) + b'\n' for line in filelist)
            fp.flush()
            rsync(f'--files-from {fp.name} /')
        log('finished pushing packages.', priority=True)
    elif name:
        log('no packages available.', priority=True)
    else:
        log('already up to date.', priority=True)

def run_root():
    'Run as root to do updates'
    # Remove any duplicate hosts from argument list
    hosts = list(dict.fromkeys(args.hosts))

    if len(hosts) == 1 or args.parallel_count <= 1:
        # May as well do in same process if only 1 host or doing in series
        for n, h in enumerate(hosts):
            synchost(n, h)
    else:
        # Farm out the jobs to a pool of processes
        with multiprocessing.Pool(min(len(hosts), args.parallel_count)) as p:
            p.starmap(synchost, ((n, h) for n, h in enumerate(hosts)))

def main():
    'Main processing ..'
    global args
    is_root = os.geteuid() == 0

    # Process command line options
    opt = argparse.ArgumentParser(description=__doc__,
            epilog=f'Note you can set default starting options in {CNFFILE}.')
    opt.add_argument('-b', '--aur-build-dir',
                     help='AUR build directory[s]. Can specify one, or '
                     'multiple directories separated by ";". '
                     f'Default is "{AURBUILD}". '
                     'Non-existent directories are ignored.')
    opt.add_argument('-n', '--dryrun', action='store_true', help='dry run only')
    opt.add_argument('-m', '--no-machcheck', action='store_true',
            help='do not check machine type compatibility')
    opt.add_argument('-p', '--parallel-count', type=int, default=10,
            help='max number of hosts to update in parallel. '
            'Default is %(default)d.')
    opt.add_argument('-u', '--updates', action='store_true',
            help='just report all installed packages with updates pending, '
            'including AUR packages')
    opt.add_argument('-s', '--sys-only', action='store_true',
            help='only sync/report system packages, not AUR')
    opt.add_argument('-a', '--aur-only', action='store_true',
            help='only sync/report AUR packages, not system')
    opt.add_argument('-C', '--no-color', action='store_true',
            help='do not color output messages')
    opt.add_argument('-N', '--no-color-invert', action='store_true',
            help='do not invert color on error/priority messages')
    opt.add_argument('-M', '--mirrorlist', action='store_true',
            help='also sync mirrorlist file')
    opt.add_argument('-F', '--ssh-config-file',
            help='ssh configuration file to use. Default is '
            f'"{SSHCONFIG}" (if it exists).')
    opt.add_argument('-V', '--version', action='store_true',
            help=f'show {PROG} version')
    opt.add_argument('-d', '--debug', action='store_true',
            help='output debug messages')
    opt.add_argument('hosts', nargs='*', help='hosts to update')

    # Merge in default args from user config file. Then parse the
    # command line.
    if not is_root and CNFFILE.is_file():
        with CNFFILE.open() as fp:
            lines = [re.sub(r'#.*$', '', line).strip() for line in fp]
        cnflines = ' '.join(lines).strip()
    else:
        cnflines = ''

    argv = shlex.split(cnflines) + sys.argv[1:]
    args = opt.parse_args(argv)

    if args.debug:
        debug(argv)

    if args.version:
        from importlib.metadata import version
        try:
            ver = version(PROG)
        except Exception:
            ver = 'unknown'

        print(ver)
        return 0

    # Only use color for terminal output
    if not sys.stdout.isatty():
        args.no_color = True

    if args.updates:
        return report_updates()

    if not args.hosts:
        opt.error('Must specify at least one host')

    # If not invoked as root then re-invoke ourself using sudo
    if not is_root:
        return run_user(argv)

    if not os.getenv('SUDO_USER'):
        return 'Do not run as root. Run directly as your normal user.'

    # From here on we are running as root ..
    return run_root()

if __name__ == '__main__':
    sys.exit(main())
