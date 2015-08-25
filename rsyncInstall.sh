#!/usr/bin/env bash

echo "FOR SERVERS ONLY, NOT NODES"

echo "
[bitcoin]
path = /home/user/bitcoin-source/
comment = Bitcoin blocks dir
uid = user
gid = user
read only = true
list = yes
" > /etc/rsyncd.conf

systemctl enable rsync

useradd -m user

sudo -u user mkdir -p /home/user/bitcoin-source
sudo -u user rsync -avz --delete --progress rsync://blocks.xk.io/bitcoin/ /home/user/bitcoin-source/

wait
reboot

