import multiprocessing
import time
import sproxy
import sys
import prt_utils
import Queue
import queue_device
import zmq

def proxy_worker(q, conn):

    """"
    def get_instructions(conn):
        try:
            if conn.poll(1):
                instructions = conn.recv()
                while instructions == "pause":
                    if conn.poll(1):
                        instructions = conn.recv()
                if instructions == "stop":
                    raise Exception # TODO - Create sproxy.stop_instruction exception
        except Exception as e:
            raise
    """

    def talk_with_prm(conn, message):
        conn.send(message)
        while not conn.poll(1):
            time.sleep(5)
        answer = conn.recv()
        return answer

    def run_next_step(proxy, step_name):
        method = getattr(proxy, step_name)
        result = method()
        return result


    try:

        stopWorker = False

        while not stopWorker:
            p = None
            while not p:
                try:
                    p = q.get(True, 1)
                    prt_utils.worker_get_instructions(conn)
                except Queue.Empty:
                    pass
            path = "/tmp/process_%s" % p
            sys.stdout = open(path, "w")
            proxy = sproxy.sProxy(p)

            while proxy.check_dump_age() > 50: # If dump age is more than 50 minutes - Create new dump
                print "Dump is to old.."
                proxy.dump_cache()
                while proxy.check_dump_age() < 0:
                    print "Checking dump again..."
                    time.sleep(10)
                    prt_utils.worker_get_instructions(conn)
            release_procedure = ["stop_proxy", "release_proxy", "start_proxy"]
            for action in release_procedure:
                prt_utils.worker_get_instructions(conn)
                print run_next_step(proxy, action)

            while proxy.check_state() != "Started":
                print "Waiting for proxy to start..."
                time.sleep(5)
                prt_utils.worker_get_instructions(conn)
            proxy.in_rotation()
            stopWorker = talk_with_prm(conn, "toStop?")

    except Exception as e:
        raise

def test():
    return "This Is Test Func"

def active_proxy_workers():
    active_count = 0
    for proc in globals()['processes']:
        active_count += 1
    return active_count

def create_process(q):
    my_conn, proc_conn = multiprocessing.Pipe()
    proc = multiprocessing.Process(target=proxy_worker, args=(q, proc_conn))
    proc.daemon = True
    return proc, my_conn


def start_prm(main_conn):
    this_module = sys.modules[__name__]
    toExit = False
    globals()['processes'] = []
    q = multiprocessing.Queue()
    socket = prt_utils.create_zmq_connection("127.0.0.1", "5556", zmq.REP)
    while True:
        while socket.poll(timeout = 10) == 0:
            time.sleep(2)
            multiprocessing.active_children()
            pass
        request = socket.recv_json()
        if request[0] == "start_proc":
            proc, my_conn = create_process(q)
            globals()['processes'].append([proc, my_conn])
            proc.start()
            response = proc.pid
            socket.send_json(response)
        elif request[0] == "put in queue":
            q.put(request[1])
        elif request[0] == "exit":
            socket.send_json("Bye Bye!")
            sys.exit()
        else:
            try:
                method = getattr(this_module, request[0])
                response = method()
            except Exception:
                time.sleep(2)
                response = "sorry, didnt understand"
            finally:
                socket.send_json(response)
    """"
    while not toExit:
        #name = raw_input("Please enter proxy name: ")
        #proc = multiprocessing.Process(target=proxy_worker, args=(q, conn))
        instructions = prt_utils.prm_get_instructions(main_conn)
        if instructions == "start_proc":
            proc, my_conn = create_process(q)
            processes.append([proc, my_conn])
            proc.start()
        elif instructions == "put in queue":
            q.put(proc.name)
        elif instructions == "exit":
            sys.exit()
        time.sleep(3)
    """

if __name__ == '__main__':
    """""
    toExit = False
    processes = []
    q = multiprocessing.Queue()
    while not toExit:
        name = raw_input("Please enter proxy name: ")
        #proc = multiprocessing.Process(target=proxy_worker, args=(q, conn))
        proc, my_conn = create_process(q)
        processes.append([proc, my_conn])
        q.put(name)
        proc.start()
        time.sleep(5)
    """
    start_prm(conn)
