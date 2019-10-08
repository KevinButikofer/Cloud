import errno
import os
import boto3
import boto3.ec2 as ec2


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
    provider = "aws"
    return cp.get(provider, 'keypair'), cp.get(provider, 'secgrp')


def create_connection():
   ''' to Compltete ...'''
   try:
       conn = boto3.resource('ec2', 'eu-central-1a')
       return conn
   except Exception as e:
        print(e)


def delete_server(conn, instance):
    ''' to Compltete ...'''    
    conn.instances.filter(InstanceIds=[instance.id]).stop()
    conn.instances.filter(InstanceIds=[instance.id]).terminate()

def create_server(conn, ami_id, flv, key, grp, userdata=""):
    ''' to Compltete ...'''
    return conn.create_instances(ImageId='<ami-image-id>', MinCount=1, MaxCount=1, InstanceType=flv, SecurityGroups=[grp], KeyName=key, UserData=userdata)
    # pool = conn.run_instances(image_id=ami_id, instance_type=flv, security_groups=[grp],
    #                    key_name=key, user_data=userdata)
    # instance = pool.instances[0]

    # instance.update()

    # return instance

def main():
    SPOTIFY_ID = "3d4a0a832445426aaa0a55dcf8658c55"
    SPOTIFY_SECRET = "9fb2f56364be46e398d0fa169bfb0605"
    EVENTFUL = "qT8gm8TtZS7HRtjm"
    GMAP = "AIzaSyApAmQIU7Hl4-W-gxbt_BxFJyicjxkUSa0"

    MONGO_IMG = 'mongo_ok'
    BACKEND_IMG = 'backend'
    FRONTEND_IMG = 'frontend'

    print("Login phase...")

    keypair, secgrp = get_credentials('aws', 'provider.conf')
    conn = create_connection()
    print("Create MongoDB instance: ")
    mongo = create_server(conn, MONGO_IMG, 't2.micro', keypair, secgrp)

    mongo_ip = mongo["PrivateDnsName"]
    import time
    time.sleep(10)
    database = "mongodb://%s:%d/festivaldb" % (mongo_ip, 27017)

    print("Create BackEnd instance: ")

    userdata = '''#!/usr/bin/env bash
cd /home/ubuntu/FSEArchive/server
echo "SPOTIFY_ID=%s" >> /home/ubuntu/FSEArchive/server/keys.env
echo "SPOTIFY_SECRET=%s" >> /home/ubuntu/FSEArchive/server/keys.env
echo "EVENTFUL=%s" >> /home/ubuntu/FSEArchive/server/keys.env
echo "DATABASE=%s" >> /home/ubuntu/FSEArchive/server/keys.env
nohup /home/ubuntu/FSEArchive/node-v8.11.4-linux-x64/bin/node start.js > /dev/null &
''' % (SPOTIFY_ID, SPOTIFY_SECRET, EVENTFUL, database)

    backend = create_server(conn, BACKEND_IMG, 't2.micro', keypair, secgrp, userdata)

    print("Create FrontEnd instance: ")
    userdata = '''#!/usr/bin/env bash
cd /home/ubuntu/FSEArchive/client
echo "GMAP=%s" >> /home/ubuntu/FSEArchive/client/keys.env
nohup /home/ubuntu/FSEArchive/node-v8.11.4-linux-x64/bin/node start.js --serverPublic=%s > /dev/null &
''' % (GMAP, "http://%s:3000" % backend["PublicDnsName"])
    front = create_server(conn, FRONTEND_IMG, 't2.micro', keypair, secgrp, userdata)

    delete = 'N'

    while delete != 'A':
        delete = input('Abort (A) ?')

    delete_server(conn, mongo)
    delete_server(conn, backend)
    delete_server(conn, front)


if __name__ == "__main__":
    main()
