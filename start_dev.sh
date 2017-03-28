#!/bin/bash

# expose admin server 
sudo apt-get install -y socat
socat TCP-LISTEN:8084,fork,reuseaddr,mode=777 TCP:127.0.0.1:8000 &

# start dev server using service account
GOOGLE_APPLICATION_CREDENTIALS='./service_account_credentials.json' dev_appserver.py app.yaml worker.yaml