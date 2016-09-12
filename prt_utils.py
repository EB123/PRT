import time
import multiprocessing
import zmq
import sys
import ConfigParser
from subprocess import Popen, PIPE
import paramiko
import logging

logger = logging.getLogger(__name__)


def worker_get_instructions(conn, currentStatus):
    try:
        if conn.poll(0.1):
            notified = False
            instructions = conn.recv()
            while instructions == "pause":
                if not notified:
                    message = [["status", "Paused"]]
                    message_to_prm(conn, message)
                    notified = True
                if conn.poll(0.1):
                    instructions = conn.recv()
                    message = [["status", currentStatus]]
                    message_to_prm(conn, message)
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

    logger.debug("About to execute: %s" % cmd)
    transport = sshclient.get_transport()
    chan = transport.open_session()
    chan.settimeout(timeout)
    chan.exec_command(cmd)
    stdout = chan.makefile('r', -1)
    stderr = chan.makefile_stderr('r', -1)
    tmp_output = []
    tmp_stderr = []
    while not chan.exit_status_ready():
        tmp_output.append(stdout.readline())
        tmp_stderr.append(stderr.readline())
        pass
    exitCode = chan.recv_exit_status()
    for line in stdout:
        tmp_output.append(line)
    for line in stderr:
        tmp_stderr.append(line)
    output = []
    error = []
    if len(tmp_output):
        for line in tmp_output:
            if not line == '':
                output.append(line.strip())
    if len(tmp_stderr):
        for line in tmp_stderr:
            if not line == '':
                error.append(line.strip())
    return exitCode, output, error


"""
def create_zmqueues_new(address, fe_port, be_port):
    pd = ProcessDevice(zmq.QUEUE, zmq.ROUTER, zmq.DEALER)
    pd.bind_in('tcp://%s:%s' % (address, fe_port))
    pd.connect_out('tcp://%s:%s' % (address, be_port))
    pd.setsockopt_in(zmq.IDENTITY, 'ROUTER')
    pd.setsockopt_out(zmq.IDENTITY, 'DEALER')
    pd.start()
"""