import multiprocessing
import time
from . import sproxy

def proxy_worker(q, conn):

    def get_instructions(conn):
        try:
            if conn.poll(timeout = 1):
                instructions = conn.recv()
                while instructions == "pause":
                    if conn.poll(timeout = 1):
                        instructions = conn.recv()
                return instructions
        except Exception as e:
            raise e

    def talk_with_prm(conn, message):
        conn.send(message)
        while not conn.poll():
            time.sleep(1)
        answer = conn.recv()
        return answer

    try:
        stopWorker = False
        while not stopWorker:
            p = None
            while not p:
                p = q.get(timeout = 1)
                get_instructions(conn)
            proxy = sproxy(p)
            while proxy.check_dump_age > 50: # If dump age is more than 50 minutes - Create new dump
                proxy.dump_cache()
            proxy.stop()
            proxy.release()
            proxy.start()
            while proxy.check_state() != "Started":
                time.sleep(5)
                get_instructions(conn)
            proxy.in_rotation()
            answer = talk_with_prm(conn, "Finished")
            if answer == "stop":
                stopWorker = True
    except Exception as e:
        raise e


if __name__ == '__main__':

    toExit = False
    while not toExit:
        name = raw_input()
        proc = multiprocessing.Process(target=proxy_worker, args=(name,))
        proc.start()
        proc.join()