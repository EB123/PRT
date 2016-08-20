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

def active_proxy_workers(**kwargs):
    sites_dict = kwargs['sites_dict']
    active_count = {}
    for site in sites_dict.keys():
        active_count[site] = len(sites_dict[site]['procs'].keys())
    return active_count

def create_process(**kwargs):
    sites_dict = kwargs['sites_dict']
    site = kwargs['site']
    prm_conn, proc_conn = multiprocessing.Pipe()
    proc = multiprocessing.Process(target=proxy_worker, args=(sites_dict[site]['site_q'], proc_conn))
    proc.daemon = True
    proc.start()
    sites_dict[site]['procs'][proc.pid] = {}
    sites_dict[site]['procs'][proc.pid]['conn'] = prm_conn
    return proc.pid

def create_sites_queues(sites_dict):
    for site in sites_dict.keys():
        q = multiprocessing.Queue()
        sites_dict[site]['site_q'] = q



def start_prm(main_conn):
    this_module = sys.modules[__name__]
    prmDict = {} # TODO - There should be an init func that returns prmDict with all its keys (sites_dict and so on...)
    toExit = False
    SITES = ["ny_an", "ny_lb", "ams_an", "ams_lb", "lax_an", "lax_lb", "sg"]
    prmDict['sites_dict'] = {}
    for site in SITES:
        prmDict['sites_dict'][site] = {}
        prmDict['sites_dict'][site]['procs'] = {}
    create_sites_queues(prmDict['sites_dict'])
    prmDict['processes'] = []
    q = multiprocessing.Queue()
    socket = prt_utils.create_zmq_connection("127.0.0.1", "5556", zmq.REP)
    while True:
        while socket.poll(timeout = 10) == 0:
            time.sleep(1)
            multiprocessing.active_children()
            pass
        request = socket.recv_json()
        if request[0] == "start_proc":
            proc, my_conn = create_process(q)
            prmDict['processes'].append([proc, my_conn])
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
                if len(request) > 1:
                    kwargs = {}
                    for arg in request[1]:
                        kwargs[arg] = prmDict[arg]
                    for arg in request[2].keys():
                        kwargs[arg] = request[2][arg]
                    response = method(**kwargs)
                else:
                    response = method()
            except Exception as e:
                time.sleep(2)
                response = str(e) # TODO - respone should contain a "success/fail" field
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
