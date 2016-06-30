#!/bin/bash
TOKEN=$(cat ./DO_token)
SERVERNAME=mohinga-testing.com
REGION=sgp1
SIZE=1GB

curl -X POST "https://api.digitalocean.com/v2/droplets" \
    -d '{"name":"${SERVERNAME}","region":"${REGION}","size":"${SIZE}","image":"ubuntu-14-04-x64","ssh_keys":[1817432],"backups":false,"ipv6":true,"user_data":"'"$(cat ./cloud_config.mohinga.yaml)"'","private_networking":null}' \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${TOKEN}"
    

# curl -X GET -H "Content-Type: application/json" -H "Authorization: Bearer $(cat ~/Desktop/DigitalOceanRemoteAccessToken)" "https://api.digitalocean.com/v2/account/keys"
