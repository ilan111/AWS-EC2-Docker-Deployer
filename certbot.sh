sudo apt install certbot
sudo certbot certonly --standalone -d ec2deployer.com -d www.ec2deployer.com
sudo cp /etc/letsencrypt/live/ec2deployer.com/fullchain.pem nginx/certs/
sudo cp /etc/letsencrypt/live/ec2deployer.com/privkey.pem nginx/certs/