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
inefficient to be downloading and building most packages twice for the
same architecture machines.

Using `pacsync`, I now update my PC first then after that update has
finished I run `pacsync lt` on my PC to update `lt` directly via my
local LAN. Pacsync pushes the updated package lists, then queries `lt`
to work out which packages `lt` has out of date (including AUR
packages), then pushes all the system and AUR packages that it has which
`lt` needs.

After running `pacsync`, I run a `pacaur -Su` update on `lt` and it
completes very quickly because `lt` only needs to download the system
and AUR packages my PC did not have. I typically use very similar system
and AUR packages on both machines so typically `lt` doesn't need to
download or build any updated packages at all.

You need to have root ssh access between your machines for
`pacsync` to work. See the SSH KEY CONFIGURATION section below on how
best to set this up.

Obviously this only works for machines of the same architecture, i.e.
compatible package files, so `pacsync` checks for this before syncing any
files.

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

NOTE: You only need to install `pacsync` on the host where you are pushing
packages from. It does not need to be installed on the remote host[s]
you are pushing to although the remote host does need _rsync_, _openssh_,
and _pacaur_ installed.

Most users should just install
[_pacsync from the AUR_](https://aur.archlinux.org/packages/pacsync/) and
skip to the next section.

The host requires _rsync_, _openssh_, _pacaur_, _sudo_, _git_, and
_python_ (3.6 or later) installed. Then type the following to install
this utility.

    git clone http://github.com/bulletmark/pacsync
    cd pacsync
    sudo make install

### USAGE

You run it directly on the command line as your normal user (not as
root) specifying as arguments the host (or hosts) you want to update.
The utility will re-invoke itself using sudo and will sync the _pacaur_
cached AUR build directory of the invoking user (i.e.
`~/.cache/pacaur/`).

````
usage: pacsync [-h] [-n] [-m] hosts [hosts ...]

Utility to push this Arch hosts package and AUR caches to other host[s] to
avoid those other hosts having to download the same new package lists and
updated packages, at least for common packages. Requires root ssh access to
other hosts (it is easier with a auth key). Requires pacaur to be installed on
this host and other hosts.

positional arguments:
  hosts               hosts to update

optional arguments:
  -h, --help          show this help message and exit
  -n, --dryrun        dry run only
  -m, --no-machcheck  do not check machine type compatibility
````

### SSH KEY CONFIGURATION

You need to set up root ssh access between your machines for `pacsync`
to work. For security and convenience, it is best to use an ssh key
otherwise you will have to answer the password prompt for every remote
command executed by `pacsync`. The following procedure sets up the sudo
environment so that remote root logins use your own cached personal ssh
key. Your first need to set up your own personal ssh key pair of course
see Google for that part.

On all remote hosts where you want to `pacsync` to:

    sudo mkdir -p /root/.ssh
    sudo chmod 700 /root/.ssh
    sudo cp ~/.ssh/authorized_keys /root/.ssh

    # Possibly remove any keys you don't want root to allow if you have
    # more than one:
    sudo vim /root/.ssh/authorized_keys

We are also assuming the file `/etc/ssh/sshd_config` contains
`PermitRootLogin prohibit-password` which is the default on Arch. Note
that the `sudo` invoked by `pacsync` on itself uses `-E` to maintain
SSH_AUTH_SOCK for this scheme to work.

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
