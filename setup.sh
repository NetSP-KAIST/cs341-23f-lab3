set -ex
sudo apt-get update; sudo apt-get -y upgrade
git clone https://github.com/NetSP-KAIST/mininet.git
./mininet/util/install.sh -nfvp
ln -s ../../../controller.py pox/pox/misc/
make