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

The local host needs _python-ruamel-yaml_ installed.
The remote hosts need _cower_ installed.
Both the local and the remote hosts need _rsync_ and _openssh_ installed.

You only need to install `pacpush` on the local host where you are
pushing packages from. It does not need to be installed on the remote
host[s] you are pushing to. Most users should just install [_pacpush
from the AUR_](https://aur.archlinux.org/packages/pacpush/) and skip to
the next section.

The local host also requires _sudo_, _git_, and _python_ (3.6 or later)
installed. Then type the following to install this utility.

    git clone http://github.com/bulletmark/pacpush
    cd pacpush
    sudo make install (or sudo ./pacpush-setup install)

### CONFIGURATION

The default configuration file is installed to `/etc/pacpush.conf`. Copy
this file to your personal `~/.config/pacpush.conf` if you want to
change it. Currently the only configuration value is `clonedir` which is
the location of your AUR helpers download/build directory. This is the
directory from which AUR packages are rsync'd from the local host to
remote hosts. Ensure that `clonedir` is set to point to the directory
your AUR helper is using. E.g. the default is `~/.cache/pacaur` for
_pacaur_ but this will have to be changed if you are not using _pacaur_.
Remember to change this location if you change your AUR helper.

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
user (i.e. the _clonedir_ location from the configuration file).

If you specify multiple hosts then the program will update them in
parallel (unless you disable this with `-s/--series`).

````
usage: pacpush [-h] [-n] [-m] [-s] [-c CONFFILE] hosts [hosts ...]

Utility to push this Arch hosts package and AUR caches to other host[s] to
avoid those other hosts having to download the same new package lists and
updated packages, at least for common packages. Requires root ssh access to
other hosts (it is easier with a auth key). Requires cower to be installed on
all target hosts.

positional arguments:
  hosts                 hosts to update

optional arguments:
  -h, --help            show this help message and exit
  -n, --dryrun          dry run only
  -m, --no-machcheck    do not check machine type compatibility
  -s, --series          Run remote host updates in series not parallel
  -c CONFFILE, --conffile CONFFILE
                        alternative configuration file
````

### UPGRADE

    cd pacpush  # Source dir, as above
    git pull
    sudo make install (or sudo ./pacpush-setup install)

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
