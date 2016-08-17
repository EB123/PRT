import time
import multiprocessing


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