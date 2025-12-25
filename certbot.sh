#!/bin/bash

#Edit the domain variable and run the script to create letsencrypt SSL certifications
DOMAIN=yourdomain

sudo apt install certbot
sudo certbot certonly --standalone -d ${DOMAIN}.com -d www.${DOMAIN}.com
sudo cp /etc/letsencrypt/live/${DOMAIN}.com/fullchain.pem nginx/certs/
sudo cp /etc/letsencrypt/live/${DOMAIN}.com/privkey.pem nginx/certs/
