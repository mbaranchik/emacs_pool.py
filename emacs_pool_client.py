#!/usr/bin/env python3

import socket
import sys
import os
import subprocess

# Create a UDS socket
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

server_address = os.environ['EMACS_POOL_SOCK'] if 'EMACS_POOL_SOCK' in os.environ \
    else '{}/.emacs_pool.sock'.format(os.environ['HOME'])
emacs_path = (os.environ['EMACS_POOL_EMACS_PATH'] + '/emacsclient') if 'EMACS_POOL_EMACS_PATH' in os.environ \
    else '/usr/local/bin/emacsclient'

if sys.argv[1] == "file":
    extra_cmd="-c"
elif sys.argv[1] == "nw":
    extra_cmd="-t"
else:
    print("ERROR: Received bad command... usage: emacs_pool_client.py file|nw ARGS")
    sys.exit(1)

# Connect the socket to the port where the server is listening
print('INFO: Connecting to %s' % server_address)

try:
    sock.connect(server_address)
except socket.error as e:
    print(str(e))
    sys.exit(1)

try:
    print("INFO: Waiting for daemon name from server")
    data = sock.recv(256).decode()
    print('INFO: Received "{}"'.format(data))
    cmd = "{} {} -s {} {}".format(emacs_path, extra_cmd, data, ' '.join(sys.argv[2:]))
    print("INFO: Executing : {}".format(cmd))
    proc = subprocess.run(cmd.split(' '))
finally:
    print('INFO: Closing socket')
    sock.close()