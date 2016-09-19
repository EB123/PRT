import time
import multiprocessing
import zmq
import sys
import ConfigParser
from subprocess import Popen, PIPE
import paramiko
import redis
import os

def worker_get_instructions(conn, currentStatus, r):
    try:
        if conn.poll(0.1):
            notified = False
            instructions = conn.recv()
            while instructions == "pause":
                if not notified:
                    message = [["status", "Paused"]]
                    message_to_prm(conn, message)
                    r.hmset(os.getpid(), {'status': 'Paused'})
                    notified = True
                if conn.poll(0.1):
                    instructions = conn.recv()
                    message = [["status", currentStatus]]
                    message_to_prm(conn, message)
                    r.hmset(os.getpid(), {'status': currentStatus})
            if instructions == "stop":
                raise Exception  # TODO - Create sproxy.stop_instruction exception
    except Exception as e:
        raise


def message_to_prm(conn, message):
    conn.send(message)
    # TODO - Consider using 2 duplex pipes one for incoming (that will receive the "OK") and for outgoing
    """
    while not conn.recv() == "OK":
        pass
    """


def prm_get_instructions(conn):
    try:
        if conn.poll(1):
            instructions = conn.recv()
            return instructions
    except Exception as e:
        raise


def create_zmq_connection(address, port, socket_type, type):
    context = zmq.Context()
    socket = context.socket(socket_type)
    if type == "connect":
        socket.connect("tcp://%s:%s" % (address, port))
    else:
        socket.bind("tcp://%s:%s" % (address, port))
    return socket



def check_process(proc):
    return proc.is_alive()

def process_validator(func):
    def validator(*args, **kwargs):
        proc = args[0]
        if check_process(proc):
            return func(*args, **kwargs)
        else:
            #print 'This is not a new server!!'
            #logger.error('Requested process is dead!!') # TODO - implement logger
            raise Exception # TODO - Create custom exception for this screnario
    return validator


def get_conf_from_file(conf_file):

    conf = {}
    config = ConfigParser.RawConfigParser()
    config.read(conf_file)
    sections = config.sections()
    for section in sections:
        conf[section] = {}
        params = config.items(section)
        for param in params:
            conf[section][param[0]] = param[1]
    return conf


def runCmd(cmd):

    out = None
    err = None
    exitCode = None
    try:
        p = Popen(cmd, stdin = PIPE, stdout = PIPE, stderr = PIPE, shell=True)
        out, err = p.communicate()
        exitCode = p.returncode

    except Exception as e:
        ##print "Caught Exception : " + str(e)
        raise
    return out, err, exitCode


def ssh_execute(sshclient, cmd, timeout = 20.0):

    transport = sshclient.get_transport()
    chan = transport.open_session()
    chan.settimeout(timeout)
    chan.exec_command(cmd)
    stdout = chan.makefile('r', -1)
    tmp_output = []
    while not chan.exit_status_ready():
        tmp_output.append(stdout.readline())
        pass
    for line in stdout:
        tmp_output.append(line)
    output = []
    if len(tmp_output):
        for line in tmp_output:
            if not line == '':
                output.append(line.strip())
    return output


"""
def create_zmqueues_new(address, fe_port, be_port):
    pd = ProcessDevice(zmq.QUEUE, zmq.ROUTER, zmq.DEALER)
    pd.bind_in('tcp://%s:%s' % (address, fe_port))
    pd.connect_out('tcp://%s:%s' % (address, be_port))
    pd.setsockopt_in(zmq.IDENTITY, 'ROUTER')
    pd.setsockopt_out(zmq.IDENTITY, 'DEALER')
    pd.start()
"""


class RedisQueue(object):
    """Simple Queue with Redis Backend"""
    def __init__(self, name, namespace='queue', **redis_kwargs):
        """The default connection parameters are: host='localhost', port=6379, db=0"""
        self.__db= redis.StrictRedis(**redis_kwargs)
        self.key = '%s:%s' %(namespace, name)

    def qsize(self):
        """Return the approximate size of the queue."""
        return self.__db.llen(self.key)

    def empty(self):
        """Return True if the queue is empty, False otherwise."""
        return self.qsize() == 0

    def put(self, item):
        """Put item into the queue."""
        self.__db.rpush(self.key, item)

    def get(self, block=True, timeout=None):
        """Remove and return an item from the queue.

        If optional args block is true and timeout is None (the default), block
        if necessary until an item is available."""
        if block:
            item = self.__db.blpop(self.key, timeout=timeout)
        else:
            item = self.__db.lpop(self.key)

        if item:
            item = item[1]
        return item

    def get_items(self):
        """Get all items in queue"""
        list = self.__db.lrange(self.key, 0, -1)
        return list

    def remove_from_queue(self, item):
        """Remove item from queue"""
        self.__db.lerm(self.key, 1, item)

