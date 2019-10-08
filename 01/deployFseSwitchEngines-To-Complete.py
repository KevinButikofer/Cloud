import errno
import os
import subprocess
import openstack
from openstack import connection
from openstack import utils
from getpass import getpass
from base64 import b64encode

def get_credentials(provider, filename):
    """
        The config file should have the follwing format
        [switch]
        project = <your_project_name>
        username = <your_username>
        region = <region>
        keypair = <your_keypair>
        secgrp  = <your_secgrp>
        [aws]
        keypair = <your_keypair>
        secgrp  = <your_secgrp>
        """

    import configparser
    from getpass import getpass
    cp = configparser.ConfigParser()
    cp.read(filename)
    provider = 'switch'
    return (cp.get(provider, 'project') + ':' + cp.get(provider, 'username'), getpass(), cp.get(provider, 'region'),
            cp.get(provider, 'keypair'), cp.get(provider, 'secgrp'))


def create_connection(auth_url, access, password, region):
    ''' to Compltete ...'''
    access = access.split(":")
    return connection.Connection(**{'auth_url':auth_url, 'project_name':access[0], 'username':access[1], 'password':password, 'user_domain_name': 'default', 'project_domain_name': 'default', 'region_name': region})

def delete_server(conn, srv):
    ''' to Compltete ...'''
    conn.compute.delete_server(srv)

def create_server(conn, name, img, flv, net, key, grp, userdata=""):
    ''' to Compltete ...'''
    # "openstack server  create --flavor" + flv + "--image" + img + "--key-name "+ key +
    # "--user-data " + userdata + "security-group " + grp + "--nic net-id= " + net + 
    # "--meta KEY= " + key
    img =  conn.compute.find_image(img)
    flv = conn.compute.find_flavor(flv)
    net = conn.network.find_network(net)
    
    if userdata != "":        
        #userdata = b64encode(userdata.encode())
        return conn.compute.create_server(name=name, image_id=img.id, flavor_id=flv.id, networks=[{"uuid": net.id}], key_name=key, userdata=userdata)
    else:
        return conn.compute.create_server(name=name, image_id=img.id, flavor_id=flv.id, networks=[{"uuid": net.id}], key_name=key)


def get_unused_floating_ip(conn, public_network='public'):
    ''' to Compltete ...'''
    network_id = conn.network.find_network(public_network).id
    floating_ip = conn.network.create_ip (floating_network_id=network_id)
    return conn.network.get_ip (floating_ip)

def attach_floating_ip_to_instance(conn, instance, floating_ip):
    ''' to Compltete ...'''
    conn.network.add_ip_to_port(instance.list_ports()[0], floating_ip)


def main():
    AUTH_URL = "https://keystone.cloud.switch.ch:5000/v3"
    network = 'private'

    SPOTIFY_ID = "3d4a0a832445426aaa0a55dcf8658c55"
    SPOTIFY_SECRET = "9fb2f56364be46e398d0fa169bfb0605"
    EVENTFUL = "qT8gm8TtZS7HRtjm"
    GMAP = "AIzaSyApAmQIU7Hl4-W-gxbt_BxFJyicjxkUSa0"

    MONGO_IMG = 'mongo'
    BACKEND_IMG = 'backend'
    FRONTEND_IMG = 'frontend'

    print("Login phase...")
    access, secret, region, keypair, secgrp = get_credentials('switch', 'provider.conf')
    conn = create_connection(AUTH_URL, access, secret, region)

    print("Creating MongoDB instance: ")
    mongo = create_server(conn, "mongodb", MONGO_IMG, 'm1.small', network, keypair, secgrp)

    mongo = conn.get_server_by_id(mongo.id)  # refresh instance data
    MONGO_IP = mongo.private_v4
    DATABASE = "mongodb://%s:%d/festivaldb" % (MONGO_IP, 27017)

    print("Creating BackEnd instance: ")
    userdata = '''#!/usr/bin/env bash
cd /home/ubuntu/FSEArchive/server
echo "SPOTIFY_ID=%s" > /home/ubuntu/FSEArchive/server/keys.env
echo "SPOTIFY_SECRET=%s" >> /home/ubuntu/FSEArchive/server/keys.env
echo "EVENTFUL=%s" >> /home/ubuntu/FSEArchive/server/keys.env
echo "DATABASE=%s" >> /home/ubuntu/FSEArchive/server/keys.env
nohup /home/ubuntu/FSEArchive/node-v8.11.4-linux-x64/bin/node start.js > /dev/null &
''' % (SPOTIFY_ID, SPOTIFY_SECRET, EVENTFUL, DATABASE)
    api = create_server(conn, 'backend', BACKEND_IMG, 'm1.small', network, keypair, secgrp, userdata)
    floating_ip = get_unused_floating_ip(conn)
    print("Backend IP:", floating_ip.floating_ip_address)
    attach_floating_ip_to_instance(conn, api, floating_ip)
    api = conn.get_server_by_id(api.id)  # refresh instance data

    print("Creating FrontEnd instance: ")
    userdata = '''#!/usr/bin/env bash
cd /home/ubuntu/FSEArchive/client
echo "GMAP=%s" >> /home/ubuntu/FSEArchive/client/keys.env
nohup /home/ubuntu/FSEArchive/node-v8.11.4-linux-x64/bin/node start.js --serverPublic=%s > /dev/null &
''' % (GMAP, "http://" + api.public_v4 + ":3000")
    front = create_server(conn, 'frontend', FRONTEND_IMG, 'm1.small', network, keypair, secgrp, userdata)
    floating_ip = get_unused_floating_ip(conn)
    print("Frontend IP:", floating_ip.floating_ip_address)
    attach_floating_ip_to_instance(conn, front, floating_ip)

    delete = 'N'

    while delete != 'A':
        delete = input('Abort (A) ?')

    delete_server(conn, mongo)
    delete_server(conn, api)
    delete_server(conn, front)


if __name__ == "__main__":
    main()
