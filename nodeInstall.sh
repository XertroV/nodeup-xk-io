#!/bin/bash

FIRSTNAME="$1"
NODE_NAME="$2"

function install-another-script {
    scriptname=$1
    origdir=`pwd`
    wget "https://raw.githubusercontent.com/XertroV/nodeup-xk-io/master/$scriptname"
    bash "$scriptname"
    rm "$scriptname"
    cd "$origdir"
}

echo "Firstname: $FIRSTNAME"
echo "Node name: $NODE_NAME"

echo "########### The server will reboot when the script is complete"
echo "########### Changing to home dir"
cd ~
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
dd if=/dev/zero of=/swapfile bs=1M count=2048 ; mkswap /swapfile ; swapon /swapfile
echo "/swapfile swap swap defaults 0 0" >> /etc/fstab

echo "########### Cloning Bitcoin and Compiling"
mkdir -p ~/src && cd ~/src

URL="https://github.com/bitcoinxt/bitcoinxt.git"
if [ "$NODE_NAME" == "Bitcoin XT" ]; then
    URL="https://github.com/bitcoinxt/bitcoinxt.git"
elif [ "$NODE_NAME" == "Bitcoin Core" ]; then
    URL="https://github.com/bitcoin/bitcoin.git"
elif [ "$NODE_NAME" == "Core w/ BIP101" ]; then
    URL="https://bitbucket.org/bitcartel/bitcoinxt.git"
fi

git clone "$URL" bitcoin 2>&1
cd bitcoin

# Add a market to track how much BitcoinAutoNode is used
# Insert [B.A.N.] at the end of the client name, probably not compatible with BIP 14 but eh
#sed -i 's/\(CLIENT_NAME(".*\)\(")\)/\1 \[B.A.N.\]\2/' src/clientversion.cpp
if [ -z $FIRSTNAME ]; then
  EXTRA=""
else
  EXTRA="; $FIRSTNAME's node"  # keep first space
fi
sed -i "s/std::ostringstream ss;/std::ostringstream ss; comments.push_back(\"NodeUp.xk.io$EXTRA\");/" src/clientversion.cpp

./autogen.sh
./configure --without-gui --without-upnp --disable-tests --disable-wallet
make
make install

cd ..
rm -r bitcoin  # clean up to enable recompile

echo "########### Create Bitcoin User"
useradd -m user

echo "########### Creating config"
cd ~user
sudo -u user mkdir .bitcoin
config=".bitcoin/bitcoin.conf"
sudo -u user touch $config
echo "server=1" > $config
echo "daemon=1" >> $config
echo "connections=40" >> $config
randUser=`< /dev/urandom tr -dc A-Za-z0-9 | head -c30`
randPass=`< /dev/urandom tr -dc A-Za-z0-9 | head -c30`
echo "rpcuser=$randUser" >> $config
echo "rpcpassword=$randPass" >> $config

# don't need to prune on large volumes, yay!
# # set prune amount to size of `/` 60% (and then by /1000 to turn KB to MB) => /1666
# # echo "prune="$(expr $(df | grep '/$' | tr -s ' ' | cut -d ' ' -f 2) / 1666) >> $config # safe enough for now

echo "########### Setting up autostart (cron)"
crontab -l > tempcron
echo "0 3 * * * reboot" >> tempcron  # reboot at 3am to keep things working okay
crontab tempcron
rm tempcron

# only way I've been able to get it reliably to start on boot
# (didn't want to use a service with systemd so it could be used with older ubuntu versions, but systemd is preferred)
# sed -i '2a\
#sudo -u bitcoin /usr/local/bin/bitcoind' /etc/rc.local

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

echo "############ Add an alias for easy use"
echo "alias btc=\"sudo -u user bitcoin-cli -datadir=/home/user/.bitcoin\"" >> ~/.bashrc  # example use: btc getinfo

install-another-script "statsInstall.sh"

reboot
