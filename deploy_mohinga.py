import digitalocean
import time
import logging
import requests
import paramiko
import stat
import socket
from secrets import TOKEN, NOIP, GIT, machine_ssh_config, config
logging.basicConfig(level=logging.INFO)


def manager(token=TOKEN):
    return digitalocean.Manager(token=token)


def get_droplets_by_name(droplet_name):
    logging.info("Searching API for droplets named {}".format(droplet_name))
    droplets = manager().get_all_droplets()
    return [d for d in droplets if d.name == droplet_name]


def destroy_droplets_by_name(droplet_name):
    """USE WITH CARE!! Remove existing droplets with the same name as the desired server"""
    droplets = get_droplets_by_name(droplet_name)
    for droplet in droplets:
        logging.info("DESTROYING droplet {0} at {1}".format(droplet.name, droplet.ip_address))
        droplet.destroy()


def create(name=config['servername'], region=config['region'], size=config['size'], **kwargs):
    drop = digitalocean.Droplet(
            ssh_keys=kwargs.get('keys', manager().get_all_sshkeys()),
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


def assign_hostname(droplet, hostname):
    action = droplet.get_actions()[0]
    action.load()
    logging.info('Wait for droplet to report completion')
    while action.status != 'completed':
        time.sleep(5)
        logging.info('Waiting for droplet to signal completion')
        action.load()

    logging.info('Wait for droplet to report its IP address')
    while not droplet.ip_address:
        logging.info("Waiting for IP address")
        droplet.load()
        time.sleep(5)
    logging.info('IP address is {}'.format(droplet.ip_address))

    logging.info("Submitting name to no-ip.com")
    data = {
        'username': NOIP['email'],
        'password': NOIP['password'],
        'hostname': hostname,
        'ip': droplet.ip_address,
    }
    print data
    headers = {
        "Host": 'dynupdate.no-ip.com',
        "User-Agent": "DigitalOcean build tool/0.1 joshua@catalpa.io",
        "Authorization": "Basic " + ('{username}:{password}'.format(**data).encode("base64").rstrip())
    }
    url = "https://dynupdate.no-ip.com/nic/update?hostname={hostname}&myip={ip}".format(**data)
    logging.debug('Request DDNS IP address')
    request = requests.get(
            url=url,
            headers=headers
    )
    return request


if __name__ == '__main__':
    destroy_droplets_by_name(config['servername'])
    droplet = create(keys=[1817432], user_data=open(config['cloud_init']).read())
    # droplet = get_droplets_by_name(config['servername'])[0]
    request = assign_hostname(droplet, config['servername'])
    assert request.status_code == 200

    # Set up an ssh connection
    droplet = get_droplets_by_name(config['servername'])[0]

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((droplet.ip_address, machine_ssh_config['port']))
    connection_tries = 1
    wait_seconds = 10
    while result == 0:
        logging.warn("Attempt {}: Port {} is not open, trying again in {} seconds".format(connection_tries,
                                                                                          machine_ssh_config['port'],
                                                                                          wait_seconds))
        time.sleep(wait_seconds)
        connection_tries += 1
        result = sock.connect_ex((droplet.ip_address, machine_ssh_config['port']))

    logging.info("Port {} is open".format(machine_ssh_config['port']))
    client.connect(droplet.ip_address, username=machine_ssh_config['username'], port=machine_ssh_config['port'])
    sftp = client.open_sftp()
    req = requests.get(
            url='https://raw.githubusercontent.com/catalpainternational/openly_mohinga/submodules/deploy.sh',
            params={
                'token': GIT['token']
            })
    assert req.status_code == 200
    with sftp.open('/tmp/deploy.sh', 'w') as deployment_script:
        deployment_script.write(req.text)
        deployment_script.chmod(deployment_script.stat().st_mode | stat.S_IEXEC)
        stdin, stdout, stderr = client.exec_command('/bin/bash /tmp/deploy.sh')
