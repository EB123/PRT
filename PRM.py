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

ny_an = ["nyproxy25", 'nyproxy26', 'nyproxy27', 'nyproxy28', 'nyproxy29', 'nyproxy30', 'nyproxy31']
ny_lb = ["ny4aproxy10", 'ny4aproxy11', 'ny4aproxy12','ny4aproxy13', 'ny4aproxy14', 'ny4aproxy15', 'ny4aproxy16']
ams_an =["ams2proxy25", 'ams2proxy26', 'ams2proxy27', 'ams2proxy28', 'ams2proxy29', 'ams2proxy30']
ams_lb = ["ams2proxy05", 'ams2proxy06', 'ams2proxy07', 'ams2proxy08', 'ams2proxy09']
lax_an = ["laxproxy25", 'laxproxy26', 'laxproxy27', 'laxproxy28', 'laxproxy29']
lax_lb = ["laxproxy15", 'laxproxy16', 'laxproxy17']
sg = ["sgproxy12", 'sgproxy13', 'sgproxy14', 'sgproxy15']

basedir = os.getcwd()
workers_conf_file = os.path.join(basedir, 'workers_for_release.conf')

#######################


def process_validator(func):
    def validator(*args, **kwargs):
        try:
            processes = kwargs['processes']
            site = kwargs['site']
            pid = kwargs['pid']
            proc = processes[site][pid]['proc']
            if prt_utils.check_process(proc):
                return func(*args, **kwargs)
            else:
                #print 'This is not a new server!!'
                #logger.error('Requested process is dead!!') # TODO - implement logger
                raise Exception # TODO - Create custom exception for this screnario
        except Exception as e:
            print "Process is dead!"
            del processes[site][pid] # This should only happen if the custom exception was raised
            raise
    return validator



def proxy_worker(q, conn):


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
        currentStatus = "Idle" # To know the last status when resuming from paused
        currentProxy = None # Still not sure if this will actually be used
        currentStep = None # Still not sure if this will actually be used
        while not stopWorker:
            logger.info("I'M UP!")
            p = None
            logger.info("Waiting for input...")
            while not p:
                try:
                    prt_utils.worker_get_instructions(conn, currentStatus)
                    p = q.get(True, 0.1)
                except Queue.Empty:
                    pass
            currentStatus = "Busy"
            currentProxy = p
            currentStep = "check_dump_age"
            message = [['status', currentStatus], ['working_on', currentProxy], ['step', currentStep]]
            prt_utils.message_to_prm(conn, message)
            logger.info("Got a new proxy to work on: %s" % p)
            proxy = sproxy.sProxy(p)

            while proxy.check_dump_age() > 50: # If dump age is more than 50 minutes - Create new dump
                print "Dump is to old.."
                proxy.dump_cache()
                message = [['step', 'waiting for cacheDump']]
                prt_utils.message_to_prm(conn, message)
                while proxy.check_dump_age() < 0:
                    for i in range(10):
                        prt_utils.worker_get_instructions(conn, currentStatus)
                        time.sleep(1)
                    print "Checking dump again..."
            release_procedure = ["stop_proxy", "release_proxy", "start_proxy"]
            for action in release_procedure:
                message = [['step', action]]
                prt_utils.message_to_prm(conn, message)
                prt_utils.worker_get_instructions(conn, currentStatus)
                print "Process-%s: %s" % (os.getpid(),run_next_step(proxy, action))

            message = [['step', 'waiting_for_start']]
            prt_utils.message_to_prm(conn, message)
            while proxy.check_state() != "Started":
                print "Process-%s: Waiting for %s to become ready..." % (os.getpid(), proxy.name)
                for i in range(10):
                    prt_utils.worker_get_instructions(conn, currentStatus)
                    time.sleep(1)
            proxy.in_rotation()
            stopWorker = talk_with_prm(conn, "toStop?")

    except Exception as e:
        raise

def test():
    return "This Is Test Func"

def active_proxy_workers(**kwargs):
    #sites_dict = kwargs['sites_dict']
    processes = kwargs['processes']
    active_count = {}
    for site in processes.keys():
        active_count[site] = {}
        active_count[site]['workers'] = {}
        active_count[site]['active_workers'] = len(processes[site].keys())
        active_count[site]['proxies'] = globals()[site] # Test purposes only
        for proc in processes[site].keys():
            active_count[site]['workers'][proc] = {}
            active_count[site]['workers'][proc]['status'] = processes[site][proc]['status']
            active_count[site]['workers'][proc]['working_on'] = processes[site][proc]['working_on']
            active_count[site]['workers'][proc]['step'] = processes[site][proc]['step']
    return active_count

def create_process(**kwargs):
    processes = kwargs['processes']
    queues = kwargs['queues']
    site = kwargs['site']
    prm_conn, proc_conn = multiprocessing.Pipe()
    proc = multiprocessing.Process(target=proxy_worker, args=(queues[site], proc_conn))
    proc.daemon = True
    proc.start()
    pid = str(proc.pid)
    processes[site][pid] = {}
    processes[site][pid]['conn'] = prm_conn
    processes[site][pid]['proc'] = proc
    processes[site][pid]['status'] = 'Idle' # Status can be Idle, Busy or Paused
    processes[site][pid]['working_on'] = None # The proxy that worker is currently working on. None of the worker
                                                   # is idle
    processes[site][pid]['step'] = None # The step which the worker is currently on (start/stop/release...)
    return pid

def create_sites_queues(sites_dict):
    for site in sites_dict.keys():
        q = multiprocessing.Queue()
        sites_dict[site]['site_q'] = q

def add_to_pre_q(**kwargs):
    #sites_dict = kwargs['sites_dict']
    pre_queues = kwargs['pre_queues']
    site = kwargs['site']
    proxies = kwargs['proxies']
    #site_q = sites_dict[site]['site_q']
    #site_q.put(proxy_name)
    wasAdded = []
    for proxy in proxies:
        if not proxy in pre_queues[site]:
            pre_queues[site].append(proxy)
            wasAdded.append(proxy)
    return "%s was added to queue!" % wasAdded

def init_dictionaries(SITES):
    processes = {}
    queues = {}
    pre_queues = {}
    for site in SITES:
        processes[site] = {}
        queues[site] = multiprocessing.Queue()
        pre_queues[site] = []
    return processes, queues, pre_queues

def pre_q_to_q(processes, pre_queues, queues, SITES):
    for site in SITES:
        for pid in processes[site]:
            if len(pre_queues[site]) > 0 and processes[site][pid]['status'] == "Idle":
                queues[site].put(pre_queues[site].pop(0))


#TODO - Create a decorator that will validate that the process still exists (that there's someone on the other side
#of the pipe
@process_validator
def pause_or_resume_worker(**kwargs):
    try:
        processes = kwargs['processes']
        site = kwargs['site']
        pid = kwargs['pid']
        action = kwargs['action']
        conn = processes[site][pid]['conn']
        conn.send(action)
        while not conn.poll(0.1):
            pass
        message = conn.recv()
        for item in message:
            processes[site][pid][item[0]] = item[1]
        #conn.send("OK")
        return "Process %s is now %sd" % (pid, action)
    except Exception as e:
        print "Error!"
        print str(e)
        raise


def get_preQs_status(**kwargs):
    return kwargs['pre_queues']


def get_default_num_workers(**kwargs):
    conf = prt_utils.get_conf_from_file(workers_conf_file)
    num_workers_for_release = {}
    for site in conf:
        num_workers_for_release[site] = conf[site]['num_of_workers']
    return num_workers_for_release



def start_workers_for_release(**kwargs):
    numOfWorkers = kwargs['numOfWorkers']
    processes = kwargs['processes']
    queues = kwargs['queues']
    response = {}
    for item in numOfWorkers:
        site = item[0]
        numWorkersInSite = item[1]
        response[site] = []
        for i in range(int(numWorkersInSite)):
            newKwargs = {}
            newKwargs['processes'] = processes
            newKwargs['queues'] = queues
            newKwargs['site'] = site
            pid = create_process(**newKwargs)
            response[site].append(pid)
    return response



#TODO - There should be a regular process_checker, in case for some reasone a process dies


def start_prm(main_conn):
    this_module = sys.modules[__name__]
    SITES = ["ny_an", "ny_lb", "ams_an", "ams_lb", "lax_an", "lax_lb", "sg"]
    processes, queues, pre_queues = init_dictionaries(SITES)
    prmDict = {'processes': processes, 'queues': queues, 'pre_queues': pre_queues} # TODO - There should be an init func that returns prmDict with all its keys
    toExit = False
    prmDict['sites_dict'] = {}
    for site in SITES:
        prmDict['sites_dict'][site] = {}
        prmDict['sites_dict'][site]['procs'] = {}
    ###create_sites_queues(prmDict['sites_dict'])
    ###prmDict['processes'] = []
    q = multiprocessing.Queue()
    socket = prt_utils.create_zmq_connection("127.0.0.1", "5556", zmq.REP, "bind")
    while True:
        while socket.poll(timeout = 10) == 0:
            time.sleep(1)
            multiprocessing.active_children()
            pre_q_to_q(processes, pre_queues, queues, SITES)
            for site in processes.keys():
                for proc in processes[site].keys():
                    if processes[site][proc]['conn'].poll(0.1):
                        message = processes[site][proc]['conn'].recv()
                        for item in message:
                            processes[site][proc][item[0]] = item[1]
                        #processes[site][proc]['conn'].send("OK")
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


if __name__ == '__main__':

    start_prm(conn)
