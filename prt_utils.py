import time
import multiprocessing
import zmq


def worker_get_instructions(conn):
    try:
        if conn.poll(1):
            instructions = conn.recv()
            while instructions == "pause":
                if conn.poll(1):
                    instructions = conn.recv()
            if instructions == "stop":
                raise Exception  # TODO - Create sproxy.stop_instruction exception
    except Exception as e:
        raise


def prm_get_instructions(conn):
    try:
        if conn.poll(1):
            instructions = conn.recv()
            return instructions
    except Exception as e:
        raise


def create_zmq_connection(address, port, socket_type):
    context = zmq.Context()
    socket = context.socket(socket_type)
    socket.connect("tcp://%s:%s" % (address, port))
    return socket