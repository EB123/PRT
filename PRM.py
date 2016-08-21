import multiprocessing
import time
import sproxy
import sys
import prt_utils
import Queue
import queue_device
import zmq
import os
import logging



### Proxies For Test Purposes Only ###

SITES = ["ny_an", "ny_lb", "ams_an", "ams_lb", "lax_an", "lax_lb", "sg"]

ny_an = ["nyproxy25", 'nyproxy26', 'nyproxy27']
ny_lb = ["ny4aproxy10", 'ny4aproxy11', 'ny4aproxy12']
ams_an =["ams2proxy25", 'ams2proxy26', 'ams2proxy27']
ams_lb = ["ams2proxy05", 'ams2proxy06', 'ams2proxy07']
lax_an = ["laxproxy25", 'laxproxy26', 'laxproxy27']
lax_lb = ["laxproxy15", 'laxproxy16', 'laxproxy17']
sg = ["sgproxy12", 'sgproxy13', 'sgproxy14']

#######################



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

    def temp_logger(): # TODO - Create an async logging feature
        log_base_dir = "/tmp/prt_logs"
        log_file = os.path.join(log_base_dir, "ProxyWorker-%s" % str(os.getpid()))
        logging.basicConfig(level=logging.INFO,
            format='%(asctime)s %(levelname)-8s %(message)s',
            datefmt='%m-%d %H:%M',
            filename=log_file)
        logger = logging.getLogger(__name__)
        ch = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s', '%m-%d %H:%M')
        ch.setFormatter(formatter)
        ch.setLevel(logging.INFO)
        logger.root.addHandler(ch)
        return logger

    try:

        stopWorker = False
        logger = temp_logger()
        while not stopWorker:
            logger.info("I'M UP!")
            p = None
            logger.info("Waiting for input...")
            while not p:
                try:
                    p = q.get(True, 1)
                    prt_utils.worker_get_instructions(conn)
                except Queue.Empty:
                    pass
            logger.info("Got a new proxy to work on: %s" % p)
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
                print "Process-%s: %s" % (os.getpid(),run_next_step(proxy, action))

            while proxy.check_state() != "Started":
                print "Process-%s: Waiting for proxy to start..." % os.getpid()
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
        active_count[site] = {}
        active_count[site]['active_workers'] = len(sites_dict[site]['procs'].keys())
        active_count[site]['proxies'] = globals()[site]
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

def add_to_site_q(**kwargs):
    sites_dict = kwargs['sites_dict']
    site = kwargs['site']
    proxy_name = kwargs['proxy_name']
    site_q = sites_dict[site]['site_q']
    site_q.put(proxy_name)
    return "%s was added to queue!" % proxy_name


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
    socket = prt_utils.create_zmq_connection("127.0.0.1", "5556", zmq.REP, "bind")
    while True:
        while socket.poll(timeout = 10) == 0:
            time.sleep(1)
            multiprocessing.active_children()
            pass
        request = socket.recv_json()
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
