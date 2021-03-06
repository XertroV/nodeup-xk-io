#!/bin/bash

# very simple lock to prevent starting 2 scripts at once
if [ -e ~/NODE_INSTALL_LOCK ]; then
    if [ -n "`pgrep -f nodeInstall`" ]; then
        exit
    fi
else
    touch ~/NODE_INSTALL_LOCK
fi

FIRSTNAME="$1"
NODE_NAME="$2"
BRANCH="$3"
RSYNC_LOCATION="$4"

if [ "$#" -ne 4 ] ; then
    echo "USAGE: bash nodeInstall.sh \"FIRSTNAME\" \"CLIENT SELECTION\" \"GIT BRANCH\" \"RSYNC LOCATION\""
    exit
fi

function install-another-script {
    scriptname=$1
    origdir=`pwd`
    wget "https://raw.githubusercontent.com/XertroV/nodeup-xk-io/master/$scriptname"
    bash "$scriptname"
    rm "$scriptname"
    cd "$origdir"
}

systemctl stop bitcoind 2>/dev/null

echo "Firstname: $FIRSTNAME"
echo "Node name: $NODE_NAME"
echo "Branch:    $BRANCH"

echo "########### The server will reboot when the script is complete"
echo "########### Changing to home dir"
cd ~

echo "########### Create Bitcoin User"
useradd -m user

if [ -n "$RSYNC_LOCATION" ]; then
    echo "########### Initiating Rsync"
    sudo -u user mkdir -p /home/user/.bitcoin
    sudo -u user rsync -Carz --delete "$RSYNC_LOCATION/blocks/" /home/user/.bitcoin/blocks/ &&
    sudo -u user rsync -Carz --delete "$RSYNC_LOCATION/chainstate/" /home/user/.bitcoin/chainstate/ &
fi

echo "########### Wiping crontabs"
touch tempcron
sudo -u user crontab tempcron  # wipe user crontab
crontab tempcron  # wipe root crontab and replace with reboot
rm tempcron

echo "########### Updating Ubuntu"
add-apt-repository -y ppa:bitcoin/bitcoin
apt-get -y update
# apt-get -y upgrade -- don't upgrade, there is an issue with grub that prompts the user, and to keep this non-interactive it's best just to ignore it
# apt-get -y dist-upgrade
apt-get -y install software-properties-common python-software-properties htop
apt-get -y install git build-essential autoconf libboost-all-dev libssl-dev pkg-config
apt-get -y install libprotobuf-dev protobuf-compiler libqt4-dev libqrencode-dev libtool
apt-get -y install libcurl4-openssl-dev db4.8 automake

echo "########### Creating Swap"
dd if=/dev/zero of=/swapfile bs=1M count=2048
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo "/swapfile swap swap defaults 0 0" >> /etc/fstab

echo "########### Cloning Bitcoin and Compiling"
mkdir -p ~/src && cd ~/src

URL="git://github.com/bitcoinxt/bitcoinxt.git"
if [ "$NODE_NAME" == "Bitcoin XT" ]; then
    URL="git://github.com/bitcoinxt/bitcoinxt.git"
elif [ "$NODE_NAME" == "Bitcoin Core" ]; then
    URL="git://github.com/bitcoin/bitcoin.git"
elif [ "$NODE_NAME" == "Core w/ BIP101" ]; then
    URL="https://bitbucket.org/bitcartel/bitcoinxt.git"
fi

rm -rf bitcoin 2>/dev/null # clean up to enable recompile
git clone "$URL" bitcoin 2>&1
cd bitcoin

if [ -n "$BRANCH" ]; then
    git checkout "$BRANCH"
fi

# Add a marker to track how much nodeup.xk.io is used
if [ -z "$FIRSTNAME" ]; then
  EXTRA=""
else
  EXTRA="; $FIRSTNAME's node"  # keep first space
fi
sed -i "s/if (\!comments.empty())/if (comments.empty()){ ss << \"(NodeUp.xk.io$EXTRA)\"; } else/" src/clientversion.cpp

./autogen.sh
./configure --without-gui --without-upnp --disable-tests --disable-wallet
make
make install

cd ..
echo "########### Creating config"
cd ~user
sudo -u user mkdir -p .bitcoin
config=".bitcoin/bitcoin.conf"
sudo -u user touch $config  # get those permissions right
echo "server=1" > $config
echo "daemon=1" >> $config
echo "connections=40" >> $config
randUser=`< /dev/urandom tr -dc A-Za-z0-9 | head -c30`
randPass=`< /dev/urandom tr -dc A-Za-z0-9 | head -c30`
echo "rpcuser=$randUser" >> $config
echo "rpcpassword=$randPass" >> $config

echo "########### Setting up autostart (cron & systemd)"

echo "[Unit]
Description=Bitcoind service for a node.
After=network.target

[Service]
Type=forking
ExecStart=/usr/local/bin/bitcoind -datadir=/home/user/.bitcoin/
ExecStop=/usr/local/bin/bitcoin-cli -datadir=/home/user/.bitcoin/ stop
PIDFile=/home/user/.bitcoin/bitcoind.pid
Restart=always
User=user

[Install]
WantedBy=multi-user.target
" > /etc/systemd/system/bitcoind.service
systemctl enable bitcoind

echo "############ Add aliases and stuff for easy use"
echo "alias btc=\"sudo -u user bitcoin-cli -datadir=/home/user/.bitcoin\"" >> ~/.bashrc  # example use: btc getinfo
sed -i "s/su user//g" ~/.bashrc
echo "su user" >> ~/.bashrc
echo "alias b=\"bitcoin-cli\"" >> ~user/.bashrc
echo "export PS1=\"\[\e[0;36m\]NodeUp.xk.io \[\e[0;33m\]\t \[\e[0;35m\]\w \[\e[0;37m\]$>> \[\e[0m\]\"" >> ~user/.bashrc

install-another-script "statsInstall.sh"

wait  # wait for background jobs before restarting, important for rsync
rm ~/NODE_INSTALL_LOCK
reboot
