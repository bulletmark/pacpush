## PACPUSH
[![AUR](https://img.shields.io/aur/version/pacpush)](https://aur.archlinux.org/packages/pacpush/)
[![PyPi](https://img.shields.io/pypi/v/pacpush)](https://pypi.org/project/pacpush/)

[pacpush](http://github.com/bulletmark/pacpush) is a simple command line
utility which Arch Linux users can use to manually push `pacman` and AUR
helper Arch Linux package updates to other machines to avoid having to
download them more than once via the web.

My use case follows as a good example of what this utility is for.

I update my main Arch PC and my Arch laptop every day using
[`yay`](https://github.com/Jguer/yay). Previously, I would update either
both machines in parallel, or one before the other. So both machines
would download the package lists from the web, then download and install
the out of date system packages, then download, build, and install all
out of date AUR packages. This takes quite some time, particularly on a
slow internet connection, and it is inefficient to be downloading and
building most packages twice for the same architecture machines.

Using `pacpush`, I now update my PC first then after that update has
finished I run `pacpush lt` on my PC to update `lt` directly via my
local LAN. Pacpush pushes the updated package lists, then queries `lt`
to work out which packages `lt` has out of date (including AUR
packages), then pushes all the system and AUR packages that it has which
`lt` needs.

After running `pacpush`, I run a [`yay`](https://github.com/Jguer/yay)
update on `lt` and it completes very quickly because `lt` only needs to
download the system and AUR packages my PC did not have. I typically use
very similar system and AUR packages on both machines so typically `lt`
doesn't need to download or build any updated AUR packages at all.

Obviously this only works for machines of the same architecture, i.e.
compatible package files, so `pacpush` checks for this before pushing any
files.

You need to have root ssh access to the remote machines for `pacpush` to
work. See the [SSH AND KEY CONFIGURATION](#ssh-and-key-configuration)
section below on how best to set this up.

If you specify multiple hosts then the program will update them in
parallel. You can limit, or increase, the number of parallel updates
using the `-p/--parallel-count` option. Update messages are output in a
unique color for each host.

Note that `pacpush` should work with any AUR helper so long as you set
`--aur-build-dir` appropriately in your configuration file, see the
[CONFIGURATION FILE](#configuration-file) section below for details.

The latest version and documentation is available at
https://github.com/bulletmark/pacpush.

## COMPARISION TO PACSERVE

To solve this problem, I originally started using
[pacserve](https://aur.archlinux.org/packages/pacserve/) which is what
is usually recommended for this use case. However pacserve does not sync
the package lists nor does it do anything about AUR packages which is
particularly unfortunate because AUR package downloads often include
huge source and other files and can require long build times. Since
`pacpush` pushes the entire AUR directory for each required package, the
second machine benefits by typically not having to download or rebuild
any updated AUR packages at all.

## INSTALLATION

Just install [_pacpush from the
AUR_](https://aur.archlinux.org/packages/pacpush/) to the local and
remote hosts.

Note pacpush is also available [on
PyPI](https://pypi.org/project/pacpush/) if you prefer so just ensure
that [`pipx`](https://pipx.pypa.io/stable/) is installed then type the
following to install on each machine. Requires Python 3.8 or later.

    $ pipx install pacpush

To upgrade:

    $ pipx upgrade pacpush

## SSH AND KEY CONFIGURATION

You run `pacpush` directly on the command line as your normal user, not
as root and not using `sudo` explicitly. You specify as arguments the
host, or hosts, you want to update. The utility will re-invoke itself
using `sudo` and will push the required package updates.

You need to set up root ssh access from your host machine to the remote
machine[s] for this to work. For security and convenience, it is
essential to use an ssh key. The following procedure copies your
personal public ssh key to the remote root account. Your first need to
set up your own personal ssh key pair of course, see Google for that
part.

On a remote host to which you want to `pacpush` (assuming you have
already set up personal ssh access to that host):

    $ sudo mkdir -p /root/.ssh
    $ sudo chmod 700 /root/.ssh
    $ sudo cp ~/.ssh/authorized_keys /root/.ssh

Possibly remove any keys on that remote host you don't want to allow if you have
more than one for root:

    $ sudoedit /root/.ssh/authorized_keys

Note that the `sudo` invoked by `pacpush` on itself when you run it as
your normal user passes on `$SSH_AUTH_SOCK` so that the remote root ssh
session authenticates against your personal ssh key.

For rsync/ssh configuration convenience, `rsync` and `ssh` commands run
by root are specified with your personal user's ssh configuration file
`~/.ssh/config` if it exists (unless you specify an explicit
`--ssh-config-file` for pacpush usage as described in the next section).
Note `rsync` and `ssh` commands run on behalf of root user explicitly
specify target `root@host` so that any `User` specification in your
personal ssh configuration for any host is ignored.

### TROUBLESHOOTING YOUR SSH CONFIGURATION

If you are having problems with your ssh configuration, you can try what is
described in this section to help diagnose the issue.

Assume we have a `client` machine from where we want to run the `pacpush`
command, and a `server` machine which we want to update from `client` remotely.

Run following commands on `client`:

    $ ssh server ls -l .ssh
    $ rsync server:.ssh

Both the above commands should list the contents of `~/.ssh/` on
`server` and prove you have your personal user key configured and
working correctly.

Again on `client`, run the following commands:

    $ sudo SSH_AUTH_SOCK=$SSH_AUTH_SOCK ssh -F $HOME/.ssh/config root@server ls -l .ssh
    $ sudo SSH_AUTH_SOCK=$SSH_AUTH_SOCK rsync -e "ssh -F $HOME/.ssh/config" root@server:.ssh/

Both the above commands should each list the contents of `/root/.ssh/` on
`server` and prove you have your personal user key configured and
working for root user.

A tip for when you trying to diagnose ssh problems is to use the `-v` flag to make
`ssh` commands more verbose. So, e.g., in the two `sudo` commands above, try also
adding a `-v` before the `-F`. Also check/monitor your server side `sshd` log.
E.g. run `journalctl -f -u sshd` in a server side terminal window as you try to
make the connection.

## CONFIGURATION FILE

:warning: __From pacpush version 3 onwards, the format of the
`~/.config/pacpush/pacpush.conf` file has changed
from [YAML](https://yaml.org/) to a simple text file where you
specify any of the pacpush [startup options](#usage).__

You can add default options to a personal configuration file
`~/.config/pacpush/pacpush.conf`. If that file exists then each line of
options will be concatenated and automatically prepended to your
`pacpush` command line arguments. Comments in the file (i.e. starting
with a `#`) are ignored. Type `pacpush -h` to see all [supported
options](#usage). The configuration file is read for the invoking user
only on the local host client machine. The configuration file is ignored
on any remote machine you are pushing to (because all required options
are passed from the client).

You may want to change the `--aur-build-dir` setting which is the
location of your AUR helpers download/build directory. This is the
directory from which AUR packages are rsync'd from the local host to
remote hosts. `--aur-build-dir` can be set to a single directory string,
or a list of directories by inserting a "`;`" between multiple directory
names. Ensure that `--aur-build-dir` is set to, or at least contains,
the build directory your AUR helper uses. Directories which don't exist
are ignored.

**Example Settings**

AUR Helper | Build directory setting
---------- | -----------------------
`yay` | `--aur-build-dir ~/.cache/yay`.
`paru` | `--aur-build-dir ~/.cache/paru/clone`.

The default configuration is to sync many of the common AUR helper
directories that exist on your host machine. See the default
`--aur-build-dir` directories listed by `pacpush -h`. Pacpush will sync
packages in each `--aur-build-dir` directory which exists, and is
pending an update. E.g. if you were using trizen some time ago, and am
now using yay instead, then you could keep this default setting and just
do a `rm -rf ~/.cache/trizen` because pacpush ignores `--aur-build-dir`
directories which don't exist. Or you could just set `--aur-build-dir
~/.cache/yay` in your `~/.config/pacpush/pacpush.conf` which is the
slightly more efficient approach.

You can also create and specify a custom
[`--ssh-config-file`](https://linux.die.net/man/5/ssh_config) file. This
allows you to specify ssh settings for pacpush use, either globally, or
for each host. See [`man
ssh_config`](https://linux.die.net/man/5/ssh_config) for details on how
to specify ssh (including per host) settings. If the specified
`--ssh-config-file` path is relative then it is taken to be relative to
`~/.config/pacpush/`.

Any of the options specified in the next [Usage](#usage) section can be
specified in `~/.config/pacpush/pacpush.conf`.

## USAGE

Type `pacpush -h` to view the usage summary:

```
usage: pacpush [-h] [-b AUR_BUILD_DIR] [-n] [-m] [-p PARALLEL_COUNT] [-u]
                  [-s] [-a] [-C] [-N] [-M] [-F SSH_CONFIG_FILE] [-V] [-d]
                  [hosts ...]

Utility to push this Arch hosts system and AUR package caches to other host[s]
to avoid those other hosts having to download the same new package lists and
updated packages, at least for shared common packages. Requires root ssh
access to other hosts (it is easier with an auth key).

positional arguments:
  hosts                 hosts to update

options:
  -h, --help            show this help message and exit
  -b, --aur-build-dir AUR_BUILD_DIR
                        AUR build directory[s]. Can specify one, or multiple
                        directories separated by ";". Default is "~/.cache/yay
                        ;~/.cache/paru/clone;~/.cache/trizen;~/.cache/pikaur/a
                        ur_repos;~/.cache/aurman". Non-existent directories
                        are ignored.
  -n, --dryrun          dry run only
  -m, --no-machcheck    do not check machine type compatibility
  -p, --parallel-count PARALLEL_COUNT
                        max number of hosts to update in parallel. Default is
                        10.
  -u, --updates         just report all installed packages with updates
                        pending, including AUR packages
  -s, --sys-only        only sync/report system packages, not AUR
  -a, --aur-only        only sync/report AUR packages, not system
  -C, --no-color        do not color output messages
  -N, --no-color-invert
                        do not invert color on error/priority messages
  -M, --mirrorlist      also sync mirrorlist file
  -F, --ssh-config-file SSH_CONFIG_FILE
                        ssh configuration file to use. Default is
                        "~/.ssh/config" (if it exists).
  -V, --version         show pacpush version
  -d, --debug           output debug messages

Note you can set default starting options in
$HOME/.config/pacpush/pacpush.conf.
```

## LICENSE

Copyright (C) 2017 Mark Blakeney. This program is distributed under the
terms of the GNU General Public License.
This program is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or any later
version.
This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
Public License at <http://www.gnu.org/licenses/> for more details.

<!-- vim: se ai syn=markdown: -->
