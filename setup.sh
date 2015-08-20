#!/usr/bin/env bash
origpwd=`pwd`

sudo apt-get -y install python3-setuptools tcl8.5 build-essential
sudo easy_install3 pip
sudo pip3 install tweepy tornado simplejson blockchain walrus pycoin paramiko python-digitalocean

cd ~
mkdir -p src
cd src
wget http://download.redis.io/releases/redis-stable.tar.gz
tar zxf redis-stable.tar.gz
cd redis-stable
make
sudo make install
cd utils
sudo ./install_server.sh

cd ~/src
git clone https://github.com/XertroV/bitcoin-python3
cd bitcoin-python3
sudo python3 setup.py install

cd $origpwd/systemd_services
for service in `ls`; do
    sudo cp $service /etc/systemd/system
    sudo systemctl enable $service
    sudo systemctl start $service
done