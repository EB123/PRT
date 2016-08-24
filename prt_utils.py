import time
import multiprocessing
import zmq


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


"""
def create_zmqueues_new(address, fe_port, be_port):
    pd = ProcessDevice(zmq.QUEUE, zmq.ROUTER, zmq.DEALER)
    pd.bind_in('tcp://%s:%s' % (address, fe_port))
    pd.connect_out('tcp://%s:%s' % (address, be_port))
    pd.setsockopt_in(zmq.IDENTITY, 'ROUTER')
    pd.setsockopt_out(zmq.IDENTITY, 'DEALER')
    pd.start()
"""