## PACSYNC

[pacsync](http://github.com/bulletmark/pacsync) is a small and simple
command line utility which you can use to manually sync `pacman` and
`pacaur` Arch Linux package updates between machines to avoid having to
download them more than once via the web. It requires you to be using
the [pacaur](https://aur.archlinux.org/packages/pacaur/) AUR helper.

My use case follows as a good example of what this utility is for.

I update my main Arch PC and my Arch laptop every day using `pacaur -Syu`.
Previously, I would update either both machines in parallel, or one before the
other. So both machines would download the package lists from the web,
then download and install the out of date system packages, then
download, build, and install all out of date AUR packages. This takes
quite some time, particularly on a slow internet connection, and it is
inefficient to be downloading most packages twice.

Using `pacsync`, I now update my PC first then after that update has
finished I run `pacsync lt` on my PC to update `lt` directly via my
local LAN. Pacsync pushes the updated package lists, then queries `lt`
to work out which packages `lt` has out of date (including AUR
packages), then pushes all the system and AUR packages that it has which
`lt` needs.

After running `pacsync`, I run a `pacaur -Syu` update on `lt` and it
completes very quickly because `lt` only needs to download the system
and AUR packages my PC did not have. I typically use very similar system
and AUR packages on both machines so typically `lt` doesn't need to
download or build any updated packages at all.

You need to have root ssh access between your machines for
`pacsync` to work. For security and also convenience, it is best to
configure `/etc/ssh/sshd_config` with `PermitRootLogin
prohibit-password` and use an ssh key for root.

Obviously this only works for machines of the same architecture, i.e.
compatible package files.

### COMPARISION TO PACSERVE

To solve this problem, I originally started using
[pacserve](https://aur.archlinux.org/packages/pacserve/) which is what
is usually recommended for this use case. However pacserve does not sync
the package lists nor does it do anything about AUR packages which is
particularly unfortunate because AUR package downloads often include
huge source and other files and can require long build times. Since
`pacsync` syncs the entire AUR directory for each required package, the
second machine benefits by typically not having to download or rebuild
any updated AUR packages at all.

### INSTALLATION

NOTE: Most users should just install
[_pacsync from the AUR_](https://aur.archlinux.org/packages/pacsync/) and
skip to the next section.

Requires python (3.6 or later), sudo, rsync, openssh, git, and pacaur
installed.

Then type the following to install this utility.

    git clone http://github.com/bulletmark/pacsync
    cd pacsync
    sudo make install

### USAGE

````
usage: pacsync [-h] [-n] hosts [hosts ...]

Utility to push this Arch hosts package and AUR caches to other host[s] to
avoid those other hosts having to download the same new package lists and
updated packages, at least for common packages. Requires root ssh access to
other hosts (it is easier with a auth key). Requires pacaur to be installed on
this host and other hosts.

positional arguments:
  hosts         hosts to update

optional arguments:
  -h, --help    show this help message and exit
  -n, --dryrun  dry run only
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
