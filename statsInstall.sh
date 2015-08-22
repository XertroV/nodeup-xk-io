#!/usr/bin/env bash

function addtousercron {
    crontab -u user -l > tmp-crontab
    echo "$1" >> tmp-crontab
    crontab -u user tmp-crontab
    rm tmp-crontab
}

mkdir -p ~/bin
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


' > ~/bin/gather_stats.sh
chmod +x ~/bin/gather_stats.sh
chown user:user ~/bin/gather_stats.sh

mkdir -p ~/stats
addtousercron "*/5 * * * *     cd ~/stats && python3 -m http.server"  # just try to launch it every 5 minutes to keep it up
addtousercron "*/5 * * * *     ~/bin/gather_stats.sh"



