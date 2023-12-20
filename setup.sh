set -ex
## Copy source codes into /autograder/
echo $(ls /autograder/source/)
cp /autograder/source/*.py /autograder/
cp /autograder/source/*.c /autograder/
cp /autograder/source/Makefile /autograder/
cp /autograder/source/*.sh /autograder/
cd /autograder/

## Install Mininet and dependencies
#set -ex
apt update; # apt -y upgrade
apt install -y curl sudo
git clone https://github.com/NetSP-KAIST/mininet.git
./mininet/util/install.sh -nfvp
ln -s ../../../controller.py pox/pox/misc/
make
pip3 install scapy paramiko

## Enable SSH to localhost
ssh-keygen -t rsa -P '' -f ~/.ssh/id_rsa

sed -i 's/#AuthorizedKeysFile/AuthorizedKeysFile/g' /etc/ssh/sshd_config
sed -i 's/PermitEmptyPasswords no/PermitEmptyPasswords yes/g' /etc/ssh/sshd_config
service ssh restart
chmod 600 ~/.ssh/authorized_keys
cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys

echo -e "BatchMode yes\nCheckHostIP no\nStrictHostKeyChecking no\nPubkeyAuthentication yes\nPasswordAuthentication no\nForwardX11 no" > ~/.ssh/config
