## PACPUSH

[pacpush](http://github.com/bulletmark/pacpush) is a small and simple
command line utility which you can use to manually push `pacman` and
your AUR helper Arch Linux package updates to other machines to avoid
having to download them more than once via the web.

My use case follows as a good example of what this utility is for.

I update my main Arch PC and my Arch laptop every day using `pacaur -Syu`.
Previously, I would update either both machines in parallel, or one
before the other. So both machines would download the package lists from
the web, then download and install the out of date system packages, then
download, build, and install all out of date AUR packages. This takes
quite some time, particularly on a slow internet connection, and it is
inefficient to be downloading and building most packages twice for the
same architecture machines.

Using `pacpush`, I now update my PC first then after that update has
finished I run `pacpush lt` on my PC to update `lt` directly via my
local LAN. Pacpush pushes the updated package lists, then queries `lt`
to work out which packages `lt` has out of date (including AUR
packages), then pushes all the system and AUR packages that it has which
`lt` needs. Note you can specify multiple hosts which will get queried
and updated in parallel.

After running `pacpush`, I run a `pacaur -Su` update on `lt` and it
completes very quickly because `lt` only needs to download the system
and AUR packages my PC did not have. I typically use very similar system
and AUR packages on both machines so typically `lt` doesn't need to
download or build any updated packages at all.

You need to have root ssh access to the remote machines for `pacpush` to
work. See the SSH KEY CONFIGURATION section below on how best to set
this up.

Obviously this only works for machines of the same architecture, i.e.
compatible package files, so `pacpush` checks for this before pushing any
files.

Note that `pacpush` should work with any AUR helper so long as you set
`clonedir` appropriately in your configuration file, see the
CONFIGURATION section below for details.

The latest version and documentation is available at
https://github.com/bulletmark/pacpush.

### COMPARISION TO PACSERVE

To solve this problem, I originally started using
[pacserve](https://aur.archlinux.org/packages/pacserve/) which is what
is usually recommended for this use case. However pacserve does not sync
the package lists nor does it do anything about AUR packages which is
particularly unfortunate because AUR package downloads often include
huge source and other files and can require long build times. Since
`pacpush` pushes the entire AUR directory for each required package, the
second machine benefits by typically not having to download or rebuild
any updated AUR packages at all.

### INSTALLATION

Just install [_pacpush from the
AUR_](https://aur.archlinux.org/packages/pacpush/) to the local and
remote hosts.

### CONFIGURATION

The default configuration file is installed to `/etc/pacpush.conf`. Copy
this file to your personal `~/.config/pacpush.conf` if you want to
change it. Currently the only configuration value is `clonedir` which is
the location of your AUR helpers download/build directory. This is the
directory from which AUR packages are rsync'd from the local host to
remote hosts. It only needs to be configured on the local host.
`clonedir` can be set to a single directory, or a list of directories.
Ensure that `clonedir` is set to, or at least contains, the directory
your AUR helper is using. See the default setting and examples in the
default configuration file. If you use multiple AUR helpers then set
each one's directory in a list in `clonedir`.

### SSH KEY CONFIGURATION

You need to set up root ssh access from your host machine to the remote
machine[s] for `pacpush` to work. For security and convenience, it is
essential to use an ssh key. The following procedure copies your
personal public ssh key to the remote root account. Your first need to set
up your own personal ssh key pair of course, see Google for that part.

On a remote host to which you want to `pacpush` (assuming you have
already set up personal ssh access to that host):

    sudo mkdir -p /root/.ssh
    sudo chmod 700 /root/.ssh
    sudo cp ~/.ssh/authorized_keys /root/.ssh

    # Possibly remove any keys you don't want root to allow if you have
    # more than one:
    sudo vim /root/.ssh/authorized_keys

Note that the `sudo` invoked by `pacpush` on itself when you run it as
your normal user passes on SSH_AUTH_SOCK so that the remote root ssh
session authenticates against your personal ssh key.

### USAGE

You run it directly on the command line as your normal user (not as root
and not using sudo explicitly) specifying as arguments the host, or
hosts, you want to update. The utility will re-invoke itself using sudo
and will push the cached AUR build directory of the invoking
user (i.e. the `clonedir` location[s] from the configuration file).

If you specify multiple hosts then the program will update them in
parallel. You can limit, or increase, the number of parallel updates
using the `-p/--parallel-count` option.

````
usage: pacpush [-h] [-n] [-m] [-p PARALLEL_COUNT] [-c CONFFILE] [-u] [-s] [-a]
               [hosts [hosts ...]]

Utility to push this Arch hosts system and AUR package caches to other host[s]
to avoid those other hosts having to download the same new package lists and
updated packages, at least for shared common packages. Requires root ssh
access to other hosts (it is easier with an auth key).

positional arguments:
  hosts                 hosts to update

optional arguments:
  -h, --help            show this help message and exit
  -n, --dryrun          dry run only
  -m, --no-machcheck    do not check machine type compatibility
  -p PARALLEL_COUNT, --parallel-count PARALLEL_COUNT
                        max number of hosts to update in parallel. Default is
                        10.
  -c CONFFILE, --conffile CONFFILE
                        alternative configuration file
  -u, --updates         just report all installed packages with updates
                        pending, including AUR packages
  -s, --sys-only        only sync/report system packages, not AUR
  -a, --aur-only        only sync/report AUR packages, not system
````

### LICENSE

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
