import digitalocean
import time
import logging
import requests
import paramiko
import stat
import socket
from secrets import TOKEN, NOIP, GIT, machine_ssh_config, config
logging.basicConfig(level=logging.INFO)


class Droplet(digitalocean.Droplet):

    def __init__(self, *args, **kwargs):
        super(Droplet, self).__init__(*args, **kwargs)
        self.client = None
        self.set_dns_request = None

    def assert_completed(self, wait_seconds=5):
        action = self.get_actions()[0]
        action.load()
        while action.status == 'in-progress':
            logging.info('Waiting for droplet to signal completion... try again in {} seconds'.format(wait_seconds))
            time.sleep(5)
            action.load()
        assert action.status == "completed"

    def assert_ip(self, wait_seconds=5):
        logging.info('Wait for droplet to report its IP address... try again in {} seconds'.format(wait_seconds))
        while not self.ip_address:
            logging.info("Waiting for IP address")
            time.sleep(5)
            self.load()
        logging.info('IP address is {}'.format(self.ip_address))

    def assert_port_is_open(self, port=22, wait_seconds=10):
        """
        Wait until we can get a connection to given port on the server
        :param port:
        :param wait_seconds:
        :return:
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((droplet.ip_address, port))
        connection_tries = 1
        while result == 0:
            logging.warn("Attempt {}: Port {} is not open, trying again in {} seconds".format(connection_tries,
                                                                                              machine_ssh_config['port'],
                                                                                              wait_seconds))
            time.sleep(wait_seconds)
            connection_tries += 1
            result = sock.connect_ex((droplet.ip_address, machine_ssh_config['port']))
        logging.info("Port {} is open".format(machine_ssh_config['port']))

    def assign_hostname(self, hostname):
        self.assert_completed()
        self.assert_ip()

        data = {
            'username': NOIP['email'],
            'password': NOIP['password'],
            'hostname': hostname,
            'ip': self.ip_address,
        }
        headers = {
            "Host": 'dynupdate.no-ip.com',
            "User-Agent": "DigitalOcean build tool/0.1 joshua@catalpa.io",
            "Authorization": "Basic " + ('{username}:{password}'.format(**data).encode("base64").rstrip())
        }
        url = "https://dynupdate.no-ip.com/nic/update?hostname={hostname}&myip={ip}".format(**data)
        logging.info('Requesting DNS record from no-ip.com')
        self.set_dns_request = requests.get(
                url=url,
                headers=headers
        )

        assert self.set_dns_request.status_code == 200

    def connect(self):
        self.assert_port_is_open(port=machine_ssh_config['port'])
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(droplet.ip_address, username=machine_ssh_config['username'], port=machine_ssh_config['port'])

    # def sftp(self, file, content):
    #
    #     if not self.client:
    #         self.connect()
    #     sftp = self.client.open_sftp()
    #
    #     req = requests.get(
    #             url='https://raw.githubusercontent.com/catalpainternational/openly_mohinga/submodules/deploy.sh',
    #             params={
    #                 'token': GIT['token']
    #             })
    #     assert req.status_code == 200
    #     with sftp.open('/tmp/deploy.sh', 'w') as deployment_script:
    #         deployment_script.write(req.text)
    #         deployment_script.chmod(deployment_script.stat().st_mode | stat.S_IEXEC)
    #         stdin, stdout, stderr = self.client.exec_command('/bin/bash /tmp/deploy.sh')

    def sftp_from_git(self, url):

        if not self.client:
            self.connect()
        sftp = self.client.open_sftp()

        params = {}
        # Add GIT token for private repo access
        if url.startswith('https://raw.githubusercontent.com'):
            params['token'] = GIT['token']
        req = requests.get(
                url=url,
                params=params
        )
        assert req.status_code == 200

        with sftp.open('/tmp/deploy.sh', 'w') as deployment_script:
            deployment_script.write(req.text)
            deployment_script.chmod(deployment_script.stat().st_mode | stat.S_IEXEC)
            stdin, stdout, stderr = self.client.exec_command('/bin/bash /tmp/deploy.sh')
            return stdin, stdout, stderr


class Manager(digitalocean.Manager):
    """
    Add functionality to DigitalOcean's manager
    """
    def __init__(self, *args, **kwargs):
        super(Manager, self).__init__(*args, **kwargs)

    def get_droplets_by_name(self, droplet_name):
        logging.info("Searching API for droplets named {}".format(droplet_name))
        droplets = self.get_all_droplets()
        return [d for d in droplets if d.name == droplet_name]

    def destroy_droplets_by_name(self, droplet_name):
        """USE WITH CARE!! Remove existing droplets with the same name as the desired server"""
        droplets = self.get_droplets_by_name(droplet_name)
        for drop in droplets:
            logging.info("DESTROYING droplet {0} at {1}".format(drop.name, drop.ip_address))
            drop.destroy()

    def create(self, name, region, size, **kwargs):

        drop = Droplet(
                ssh_keys=kwargs.get('keys', self.get_all_sshkeys()),
                token=TOKEN,
                name=name,
                region=region,  # New York 2
                image=kwargs.get('image', 'ubuntu-14-04-x64'),  # Ubuntu 14.04 x64
                size_slug=size,
                backups=False,
                user_data=kwargs.get('user_data', None)
        )

        logging.info('Creating droplet')
        drop.create()
        logging.info('droplet created')
        logging.debug('Action ID: {}'.format(drop.action_ids[0]))
        return drop

if __name__ == '__main__':
    manager = Manager(token=TOKEN)
    manager.destroy_droplets_by_name(config['servername'])
    droplet = manager.create(name=config['servername'], region=config['region'], size=config['size'], keys=[1817432], user_data=open(config['cloud_init']).read())
    droplet.assign_hostname(config['servername'])
    stdin, stdout, stderr = droplet.sftp_from_git(
        url='https://raw.githubusercontent.com/catalpainternational/openly_mohinga/submodules/deploy.sh'
        )