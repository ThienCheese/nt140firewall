static ip (dhcp binding) 192.168.1.100
dns host name : nt140firewall.duckdns.org 192.168.1.100

sudo apt update
sudo apt install git docker.io docker-compose-v2 docker-buildx

sudo nano /etc/systemd/resolved.conf
DNS=127.0.0.1
StubListener=no

cd test
sudo docker compose up --build -d