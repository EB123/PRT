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
import traceback


# TODO - scenario1: Proxy is down at the beginning of the release process (before check_dump_age)


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
        r13 = kwargs['r13']
        processes_lock = kwargs['processes_lock']
        prm_conn, proc_conn = multiprocessing.Pipe()
        worker_num = len(processes[site]) + 1
        worker_type = r13.hget('workers_config:%s' % site, 'type')
        if worker_type == 'custom':
            custom_command = r13.hget('workers_config:%s' % site, 'command')
        else:
            custom_command = ''
        proc = multiprocessing.Process(target=proxy_worker.proxy_worker, args=(queues[site], proc_conn, site,
                                                                               worker_num, worker_type, custom_command))
        proc.daemon = True
        proc.start()
        pid = str(proc.pid)
        r.sadd(site, pid)
        processes_lock.acquire()
        processes[site][pid] = {}
        processes[site][pid]['conn'] = prm_conn
        processes[site][pid]['proc'] = proc
        processes_lock.release()
        r.hmset(pid, {'status': 'Idle', 'working_on': None, 'step': None, 'step_start_time': None, 'type': worker_type,
                      'custom_command': custom_command})
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
        conn.recv()
        if action == 'stop':
            while processes[site].has_key(pid):
                time.sleep(0.1)
        #for item in message:
            #processes[site][pid][item[0]] = item[1]
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
    r13 = kwargs['r13']
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
            newKwargs['r13'] = r13
            pid = create_process(**newKwargs)
            response[site].append(pid)
    return response

def get_config(**kwargs):
    r13 = kwargs['r13']
    config = r13.hgetall('config')
    steps = r13.smembers('steps')
    sites = r13.smembers('sites')
    sites.add('main')
    workers_config = {}
    for site in iter(sites):
        workers_config[site] = r13.hgetall('workers_config:%s' % site)
    time_values = {}
    for step in iter(steps):
        time_values[step] = {}
        step_values = r13.hgetall('time_values:%s' % step)
        for key in step_values:
            time_values[step][key] = step_values[key]
    return [config, time_values, workers_config]

def update_config(**kwargs):
    r13 = kwargs['r13']
    configs = kwargs['configs']
    processes = kwargs['processes']
    print configs
    response = []
    #current_config = r13.hgetall('config')
    workers_type_changed = False
    new_workers_config = {}

    for item in configs:
        if item[0] == 'workers_config:main' and item[1] == 'use_main':
            if item[2]:
                item[2] = 'True'
            else:
                item[2] = 'False'
            new_use_main = item[2]
        elif item[0] == 'config' and item[1] == 'show_all_proxies':
            if item[2]:
                item[2] = 'True'
            else:
                item[2] = 'False'
        elif item[0].startswith('workers_config') and item[1] == 'type':
            site = item[0].split(':')[1]
            new_workers_config[site] = {}
            new_workers_config[site]['type'] = item[2]

    for site in new_workers_config:
        if site == 'main':
            for s in processes:
                if len(processes[s].keys()) > 0:
                    raise RuntimeError("Can't change configs for %s's workers while there are active workers" % site)
        else:
            if len(processes[site].keys()) > 0:
                raise RuntimeError("Can't change configs for %s's workers while there are active workers" % site)

    current_use_main = r13.hget('workers_config:main', 'use_main')
    if current_use_main != new_use_main:
        workers_config = {}
        for item in r13.keys('workers_config:*'):
            site = item.split(':')[1]
            workers_config[site] = r13.hgetall(item)
        for site in new_workers_config:
            workers_config[site] = new_workers_config[site]
        main_type = workers_config['main']['type']
        try:
            main_command = workers_config['main']['command']
        except KeyError:
            main_command = ''
        for site in processes:
            if len(processes[site].keys()) > 0:
                site_type = workers_config[site]['type']
                try:
                    site_command = workers_config[site]['command']
                except KeyError:
                    site_command = ''
                if main_type != site_type:
                    raise RuntimeError("Can't change configs for %s's workers while there are active workers" % site)
                if main_type == site_type and main_type == 'custom' and main_command != site_command:
                    raise RuntimeError("Can't change configs for %s's workers while there are active workers" % site)

    for item in configs:
        conf = item[0]
        key = item[1]
        value = item[2]
        current_config = r13.hget(conf, key) # TODO - find a way that only values that are being changed will arrive here
        if current_config != value:
            r13.hmset(conf, {key:value})
            response.append('%s - %s' % (conf, key))
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
                    r.srem(site, pid)
                    r.delete(pid)
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
    r.flushdb() ### Clean all process data before starting
    formatter = logging.Formatter('%(asctime)s %(worker)s: %(levelname)-8s %(message)s')
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    this_module = sys.modules[__name__]
    mpHandler = mplog.MultiProcessingLog(name="/tmp/prm.log", mode='a', maxsize=1024, rotate=0)
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
            exc_type, exc_value, exc_traceback = sys.exc_info()
            #print "%s" % e # TODO - Make sure the full traceback is printed. right now only e.message is printed.
            print "*** print_exception:"
            traceback.print_exception(exc_type, exc_value, exc_traceback,
                                      limit=2, file=sys.stdout)
        finally:
            try:
                socket.send_json(response)
            except Exception as e: # TODO - this should only refer to socket exceptions
                print "Something went REALLY wrong, unable to send response to UI. Exiting..."
                print e
                sys.exit(1)


if __name__ == '__main__':

    start_prm(conn)
