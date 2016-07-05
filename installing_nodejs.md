# Script to download node.js with NPM and make them available system-wide

cd /usr/src
sudo wget https://nodejs.org/dist/v4.4.7/node-v4.4.7-linux-x64.tar.gz
sudo tar -zxvf node-v4.4.7-linux-x64.tar.gz
sudo ln -s /usr/src/node-v4.4.7-linux-x64/bin/node /usr/bin/node
sudo ln -s /usr/src/node-v4.4.7-linux-x64/
sudo ln -s /usr/src/node-v4.4.7-linux-x64/lib/node_modules/npm/bin/npm-cli.js /usr/bin/npm
