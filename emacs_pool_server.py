#!/usr/bin/env python3

import socket
import sys
import os
import subprocess
import uuid
import signal
import time
import threading

try:
    from subprocess import DEVNULL # py3k
except ImportError:
    import os
    DEVNULL = open(os.devnull, 'wb')

server_address = os.environ['EMACS_POOL_SOCK']
emacs_path = os.environ['EMACS_POOL_EMACS_PATH'] + '/emacs'
socket_dir = os.environ['EMACS_SOCKET_DIR'] if 'EMACS_SOCKET_DIR' in os.environ else '~/.emacs.d/server-sock'
num_daemons = int(os.environ['EMACS_POOL_SIZE'])
emacs_extra = os.environ['EMACS_POOL_EXTRA'] if 'EMACS_POOL_EXTRA' in os.environ else ''
num_early_daemons = 1

free_daemon_list = list()
active_daemon_list = list()
daemon_list_lock = threading.RLock()

class ClientThread(threading.Thread):
    def __init__(self, client_address, client_socket, daemon):
        threading.Thread.__init__(self)
        self.client_socket = client_socket
        self.client_address = client_address
        self.daemon = daemon
        self.end = threading.Event()

    def run(self):
        print("INFO: Connection from " + self.client_address)
        print("INFO: Sending daemon name {}".format(socket_dir, self.daemon.name))
        self.client_socket.send(('{}/{}'.format(socket_dir, self.daemon.name)).encode())
        while not self.end.is_set():
            self.client_socket.settimeout(4)
            try:
                data = self.client_socket.recv(16).decode()
                if data == '':
                    break
            except socket.timeout as t:
                #print("INFO: Got timeout on recv")
                continue
        self.daemon.kill()
        self.client_socket.close()
        print ("INFO: Client at ", self.client_address , " disconnected...")

    def join(self, timeout=None):
        """ Stop the thread. """
        print("INFO: Ending client thread for " + self.client_address)
        self.end.set()
        threading.Thread.join(self, timeout)

class PollThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.end = threading.Event()

    def run(self):
        while not self.end.is_set():
            # Poll active for dead daemons
            for daemon in active_daemon_list:
                if not self.end.is_set() and not daemon.is_alive():
                    with daemon_list_lock:
                        print("INFO: Cleaning daemon name " + daemon.name)
                        active_daemon_list.remove(daemon)

            # Fill free daemons
            for idx in range(len(free_daemon_list) + len(active_daemon_list), num_daemons):
                if not self.end.is_set():
                    print("INFO: Spawning daemon periodically")
                    spawn_daemon()

            # Sleep 10
            if not self.end.is_set():
                time.sleep(10)

    def join(self, timeout=None):
        """ Stop the thread. """
        print("INFO: Ending poll thread")
        self.end.set()
        threading.Thread.join(self, timeout)

class EmacsDaemon(object):
    def __init__(self, *args, **kwargs):
        self.name = kwargs.get('name')
        self.alive = True
        self.log_name = "/tmp/{}".format(self.name)
        self.log = open(self.log_name, "wb")

        # init daemon
        try:
            cmd = "{} --fg-daemon={}/{}".format(emacs_path, socket_dir, self.name)
            print("New daemon: {}".format(cmd))
            self.proc = subprocess.Popen(cmd.split(), stdout=self.log, stderr=subprocess.STDOUT)
            with open(self.log_name) as f:
                while not 'Starting Emacs daemon' in f.read():
                    time.sleep(1)
        except Exception as e:
            print("ERROR: Got exception: " + str(e))
            sys.exit(1)

    def kill(self):
        self.proc.kill()
        try:
            os.remove(self.log_name)
        except:
            pass
        self.alive = False

    def is_alive(self):
        return self.alive

    def poll(self):
        return self.proc.poll()

def spawn_daemon():
    # Spawn new daemon
    daemon_name = "emacs_pool_" + uuid.uuid4().hex[0:15]
    daemon = EmacsDaemon(name = daemon_name)
    with daemon_list_lock:
        free_daemon_list.append(daemon)

        if len(free_daemon_list) + len(active_daemon_list) > num_daemons:
            print("WARNING: Reached max number of daemons...")

def get_daemon():
    if len(free_daemon_list) == 0:
        # Spawn daemon
        print("WARN: Out of daemons, spawning new")
        spawn_daemon()

    with daemon_list_lock:
        # Get from list
        daemon = free_daemon_list.pop()
        print("INFO: Getting daemon from free list - " + daemon.name)
        # Put into active
        active_daemon_list.append(daemon)

    # Return name
    return daemon

def clean_daemons():
    print("INFO: Teardown closing emacs daemons")
    kill_list = []
    with daemon_list_lock:
        kill_list = active_daemon_list + free_daemon_list
        active_daemon_list.clear()
        free_daemon_list.clear()

    for daemon in kill_list:
        daemon.kill()

def sig_handler(signum, frame):
    print('INFO: Received signal {}'.format(signum))
    sys.exit(0)

poll_thread = PollThread()
client_threads = list()
try:
    # Set the signal handler
    signal.signal(signal.SIGHUP, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    # Make sure the socket does not already exist
    if os.path.exists(server_address):
        print("FATAL: Lock file {} exists, if stale remove and rerun".format(server_address))
        sys.exit(1)

    try:
        os.unlink(server_address)
    except OSError:
        if os.path.exists(server_address):
            raise

    # Create a UDS socket
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    # Bind the socket to the port
    print('INFO: starting emacs_pool_server on %s' % server_address)
    sock.bind(server_address)

    # Listen for incoming connections
    sock.listen(num_daemons)

    # Create daemons
    print("INFO: Creating early {} daemons".format(num_early_daemons))
    for idx in range(0, num_early_daemons):
        spawn_daemon()

    poll_thread.start()

    while True:
        # Wait for a connection
        print('INFO: waiting for a connection from client')

        # Get from emacs daemon from pool
        daemon = get_daemon()
        while daemon.poll() is not None:
            daemon.kill()
            print("WARN: Got stale daemon, get another...")
            daemon = get_daemon()

        # Create client thread
        client_socket, client_address = sock.accept()
        client_thread = ClientThread(client_address, client_socket, daemon)
        client_thread.start()
        client_threads.append(client_thread)

finally:
    print("INFO: Cleaning polling thread")
    try:
        poll_thread.join()
    except RuntimeError:
        pass
    print("INFO: Cleaning client threads")
    for thread in client_threads:
        try:
            thread.join()
        except RuntimeError:
            pass
    print("INFO: Cleaning Emacs daemons")
    clean_daemons()
    print("INFO: Removing socket")
    os.remove(server_address)

print("INFO: Exit")
