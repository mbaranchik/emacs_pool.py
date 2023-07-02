#!/usr/bin/env python3

import socket
import sys
import os
import subprocess
import time

server_address = os.environ['EMACS_POOL_SOCK']
emacs_path = os.environ['EMACS_POOL_EMACS_PATH'] + '/emacsclient'

params=['new']
if len(sys.argv) > 2:
    params=sys.argv[2:]

if sys.argv[1] == "file":
    extra_cmd=["-c"]
    extra_cmd.extend(params)
elif sys.argv[1] == "nw":
    extra_cmd=["-t"]
    extra_cmd.extend(params)
elif sys.argv[1] == "everywhere":
    extra_cmd=[
        "-c",
        "--eval",
        "(emacs-everywhere)"
    ]
else:
    print("ERROR: Received bad command... usage: emacs_pool_client.py file|nw ARGS")
    sys.exit(1)

# Connect the socket to the port where the server is listening
print('INFO: Connecting to %s' % server_address)

# Create a UDS socket
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

timeout = 20
while True:
    try:
        sock.connect(server_address)
        break
    except socket.error as e:
        time.sleep(1)
        timeout -= 1
        if timeout < 0:
            sys.exit(1)

try:
    print("INFO: Waiting for daemon name from server")
    data = sock.recv(256).decode()
    print('INFO: Received "{}"'.format(data))
    cmd = [
        emacs_path,
        f"--socket-name={data}"
    ]
    cmd.extend(extra_cmd)
    print("INFO: Executing : {}".format(cmd))
    proc = subprocess.run(cmd)
finally:
    print('INFO: Closing socket')
    sock.close()
