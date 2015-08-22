#!/usr/bin/env bash

function addtousercron {
    crontab -u user -l > tmp-crontab
    echo "$1" >> tmp-crontab
    crontab -u user tmp-crontab
    rm tmp-crontab
}

sudo -u user mkdir -p ~user/bin
statsfile=~user/bin/gather_stats.sh
echo '#!/usr/bin/env bash

filename=`date +%F`.txt
cd ~/stats

function newline {
    printf "\n" >> $filename
}

function newp {
    newline
    newline
}

newp
date >> $filename
newp
bitcoin-cli getinfo >> $filename
newp
tail -n 1 ~/.bitcoin/debug.log >> $filename
newp


' > $statsfile
chmod +x $statsfile
chown user:user $statsfile

sudo -u user mkdir -p ~user/stats
addtousercron "*/5 * * * *     cd ~user/stats && python3 -m http.server"  # just try to launch it every 5 minutes to keep it up
addtousercron "*/5 * * * *     $statsfile"



