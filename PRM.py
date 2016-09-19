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
import threading
import mplog
import proxy_worker
import redis
import requests
import json

### Proxies For Test Purposes Only ###

###SITES = ["ny_an", "ny_lb", "ams_an", "ams_lb", "lax_an", "lax_lb", "sg"]

SITES = ["OPS_PROXY", "OPS_PROXY_2"]
"""
ny_an = ["nyproxy25", 'nyproxy26', 'nyproxy27', 'nyproxy28', 'nyproxy29', 'nyproxy30', 'nyproxy31']
ny_lb = ["ny4aproxy10", 'ny4aproxy11', 'ny4aproxy12','ny4aproxy13', 'ny4aproxy14', 'ny4aproxy15', 'ny4aproxy16']
ams_an =["ams2proxy25", 'ams2proxy26', 'ams2proxy27', 'ams2proxy28', 'ams2proxy29', 'ams2proxy30']
ams_lb = ["ams2proxy05", 'ams2proxy06', 'ams2proxy07', 'ams2proxy08', 'ams2proxy09']
lax_an = ["laxproxy25", 'laxproxy26', 'laxproxy27', 'laxproxy28', 'laxproxy29']
lax_lb = ["laxproxy15", 'laxproxy16', 'laxproxy17']
sg = ["sgproxy12", 'sgproxy13', 'sgproxy14', 'sgproxy15']
"""

basedir = os.getcwd()
workers_conf_file = os.path.join(basedir, 'workers_for_release-dev.conf')

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
        active_count[site]['proxies'] = globals()['comp_servers'][site] # Test purposes only
        for proc in processes[site].keys():
            active_count[site]['workers'][proc] = {}
            active_count[site]['workers'][proc]['status'] = processes[site][proc]['status']
            active_count[site]['workers'][proc]['working_on'] = processes[site][proc]['working_on']
            active_count[site]['workers'][proc]['step'] = processes[site][proc]['step']
    return active_count

def create_process(**kwargs):
    try:
        processes = kwargs['processes']
        queues = kwargs['queues']
        site = kwargs['site']
        r = kwargs['r']
        processes_lock = kwargs['processes_lock']
        prm_conn, proc_conn = multiprocessing.Pipe()
        worker_num = len(processes[site]) + 1
        proc = multiprocessing.Process(target=proxy_worker.proxy_worker, args=(queues[site], proc_conn, site, worker_num))
        proc.daemon = True
        proc.start()
        pid = str(proc.pid)
        r.sadd(site, pid)
        processes_lock.acquire()
        processes[site][pid] = {}
        processes[site][pid]['conn'] = prm_conn
        processes[site][pid]['proc'] = proc
        processes_lock.release()
        r.hmset(pid, {'status': 'Idle', 'working_on': None, 'step': None})
        return pid
    except Exception:
        raise

def create_sites_queues(sites_dict):
    for site in sites_dict.keys():
        q = multiprocessing.Queue()
        sites_dict[site]['site_q'] = q

def add_to_q(**kwargs):
    #sites_dict = kwargs['sites_dict']
    ##pre_queues = kwargs['pre_queues']
    queues = kwargs['queues']
    site = kwargs['site']
    proxies = kwargs['proxies']
    #site_q = sites_dict[site]['site_q']
    #site_q.put(proxy_name)
    wasAdded = []
    q = queues[site]
    q_items = q.get_items()
    for proxy in proxies:
        if not proxy in q_items:
            q.put(proxy)
            wasAdded.append(proxy)
    return "%s was added to queue!" % wasAdded

def init_dictionaries(r):
    processes = {}
    queues = {}
    pre_queues = {}
    for site in SITES:
        processes[site] = {}
        #queues[site] = multiprocessing.Queue() # Replaced by redisQueue
        queues[site] = prt_utils.RedisQueue(site, host='localhost', port=6379, db=11)
        pre_queues[site] = []
        r.sadd('processes', site)
    return processes, queues, pre_queues

"""
def pre_q_to_q(processes, pre_queues, queues, SITES):
    for site in SITES:
        for pid in processes[site]:
            if len(pre_queues[site]) > 0 and processes[site][pid]['status'] == "Idle":
                queues[site].put(pre_queues[site].pop(0))
"""


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


def get_Qs_status(**kwargs):
    queues = kwargs['queues']
    queues_status = {}
    for site in SITES:
        queues_status[site] = queues[site].get_items()
    return queues_status


def get_default_num_workers(**kwargs):
    conf = prt_utils.get_conf_from_file(workers_conf_file) # TODO - Conf file should only be read once at the start.
    num_workers_for_release = {}
    for site in conf:
        num_workers_for_release[site] = conf[site]['num_of_workers']
    return num_workers_for_release



def start_workers_for_release(**kwargs):
    numOfWorkers = kwargs['numOfWorkers']
    processes = kwargs['processes']
    queues = kwargs['queues']
    r = kwargs['r']
    processes_lock = kwargs['processes_lock']
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
            newKwargs['r'] = r
            newKwargs['processes_lock'] = processes_lock
            pid = create_process(**newKwargs)
            response[site].append(pid)
    return response

def get_config(**kwargs):
    r13 = kwargs['r13']
    config = r13.hgetall('config')
    return config

def update_config(**kwargs):
    r13 = kwargs['r13']
    configs = kwargs['configs']
    response = []
    current_config = r13.hgetall('config')
    for item in configs:
        key = item[0]
        value = item[1]
        if current_config[key] != value:
            r13.hmset('config', {key:value})
            response.append(key)
    return response


def get_workers_status(processes, pre_queues, queues, SITES, lock):
    while True:
        for site in SITES:
            for pid in processes[site]:
                if len(pre_queues[site]) > 0 and processes[site][pid]['status'] == "Idle":
                    lock.acquire() # TODO - make the lock useful...
                    queues[site].put(pre_queues[site].pop(0))
                    lock.release()
        time.sleep(2)


def processes_gc(processes, r, processes_lock):
    while True:
        for site in processes.keys():
            for pid in processes[site].keys():
                if not processes[site][pid]['proc'].is_alive():
                    r.srem(site, processes[site][pid]['pid'])
                    r.delete(processes[site][pid]['pid'])
                    processes_lock.acquire()
                    processes[site].pop(pid)
                    processes_lock.release()
        time.sleep(3)

#TODO - There should be a regular process_checker, in case for some reason a process dies



def start_prm(main_conn):
    try:
        r = redis.StrictRedis(host='localhost', port=6379, db=1)
        r13 = redis.StrictRedis(host='localhost', port=6379, db=13)
    except Exception: # TODO - add redis exception
        print "Cant connect to Redis!"
        sys.exit(1)
    formatter = logging.Formatter('%(asctime)s %(worker)s: %(levelname)-8s %(message)s')
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    this_module = sys.modules[__name__]
    mpHandler = mplog.MultiProcessingLog(name="/tmp/testmplog.txt", mode='a', maxsize=1024, rotate=0)
    mpHandler.setFormatter(formatter)
    #logger.addHandler(mplog.MultiProcessingLog(name="/tmp/testmplog.txt", mode='a', maxsize=1024, rotate=0))
    logger.root.addHandler(mpHandler)
    me = {'worker': 'PRM'}
    logger.info("============================================================================", extra=me)
    logger.info("================================   PRM Has Started!  =======================", extra=me)
    logger.info("============================================================================", extra=me)
    processes, queues, pre_queues = init_dictionaries(r)
    processes_lock = threading.Lock()
    prmDict = {'processes': processes, 'queues': queues, 'pre_queues': pre_queues, 'r': r, 'r13': r13,
        'processes_lock': processes_lock} # TODO - There should be an init func that returns prmDict with all its keys
    toExit = False
    prmDict['sites_dict'] = {}
    for site in SITES:
        prmDict['sites_dict'][site] = {}
        prmDict['sites_dict'][site]['procs'] = {}
    ###create_sites_queues(prmDict['sites_dict'])
    ###prmDict['processes'] = []

    lock = threading.Lock()

    socket = prt_utils.create_zmq_connection("127.0.0.1", "5556", zmq.REP, "bind")
    ##msg_checker = threading.Thread(target=get_workers_status, args=(processes, pre_queues, queues, SITES, lock))
    processesGC = threading.Thread(target=processes_gc, args=(processes, r, processes_lock))
    ##msg_checker.daemon = True
    processesGC.daemon = True
    ##msg_checker.start()
    processesGC.start()
    while True:
        while socket.poll(timeout = 10) == 0:
            time.sleep(0.1)
            multiprocessing.active_children()
            #pre_q_to_q(processes, pre_queues, queues, SITES)
            ###msg_checker.join(0.1) # TODO - moved to redis
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
            print "PRM exception handler"
            time.sleep(2)
            response = str(e) # TODO - respone should contain a "success/fail" field
            print "%s" % e # TODO - Make sure the full traceback is printed. right now only e.message is printed.
        finally:
            try:
                socket.send_json(response)
            except Exception as e: # TODO - this should only refer to socket exceptions
                print "Something went REALLY wrong, unable to send response to UI. Exiting..."
                print e
                sys.exit(1)


if __name__ == '__main__':

    start_prm(conn)
