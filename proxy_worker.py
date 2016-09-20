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
import redis
import json


def proxy_worker(q, conn, site, worker_num):

    #### A few constant dict for changing job states ####
    CacheDumpJob_pause = {'daemon': {'state' : 'JOB_PAUSED'}}
    CacheDumpJob_resume = {'daemon': {'state' : 'JOB_ACTIVE'}}
    CacheDumpJob_reschedule1h = {'daemon': {'scheduling': {'interval': '3600000', 'type': 'interval'}}}
    CacheDumpJob_reschedule_cron = {'daemon': {'scheduling': {'cronString' : '0 0 11 * * ?', 'type': 'cron'}}}
    CacheDumpJob_data = {'pause': CacheDumpJob_pause, 'resume': CacheDumpJob_resume,
                            'reschedule1h': CacheDumpJob_reschedule1h, 'reschedule_cron': CacheDumpJob_reschedule_cron}

    def talk_with_prm(conn, message):
        conn.send(message)
        while not conn.poll(1):
            time.sleep(5)
        answer = conn.recv()
        return answer

    def run_next_step(proxy, step_name, **kwargs):
        method = getattr(proxy, step_name)
        result = method(**kwargs)
        return result

    def temp_logger(logging_q): # TODO - Create an async logging feature
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
        try:
            r = redis.StrictRedis(host='localhost', port=6379, db=1)
            r13 = redis.StrictRedis(host='localhost', port=6379, db=13)
        except Exception:  # TODO - add redis exception
            print "Cant connect to Redis!"
            sys.exit(1)
        me = {'worker': 'Worker-%s-%s' % (site, worker_num)}
        #me = 'Worker-%s-%s' % (site, worker_num)
        stopWorker = False
        #logger = temp_logger(logging_q)
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        pid = os.getpid()
        currentStatus = "Idle" # To know the last status when resuming from paused
        currentProxy = None # Still not sure if this will actually be used
        currentStep = None # Still not sure if this will actually be used
        logger.info("I'M UP!", extra=me)
        while not stopWorker:
            p = None
            logger.info("Waiting for input...", extra=me)
            while not p:
                try:
                    prt_utils.worker_get_instructions(conn, currentStatus, r)
                    if not q.empty():
                        print q.get_items()
                        p = q.get(block=False)
                        print p
                    time.sleep(0.3)
                except Queue.Empty:
                    pass

            """Got new proxy to work on, starting release process"""

            currentStatus = "Busy"
            currentProxy = p
            currentStep = "check_dump_age"
            message = [['status', currentStatus], ['working_on', currentProxy], ['step', currentStep]]
            ###prt_utils.message_to_prm(conn, message)
            r.hmset(pid, {'status': currentStatus, 'working_on': currentProxy, 'step': currentStep})
            logger.info("Got a new proxy to work on: %s" % p, extra=me)
            proxy = sproxy.sProxy(p, is_test=True)
            while proxy.check_dump_age() > 50: # If dump age is more than 54 minutes - Create new dump
                logger.info("Dump is to old...", extra=me)
                proxy.jobChangeState('CacheDumpJob', json.dumps(CacheDumpJob_data['reschedule1h']))
                proxy.jobChangeState('CacheDumpJob', json.dumps(CacheDumpJob_data['pause']))
                ###message = [['step', 'waiting for cacheDump']]
                r.hmset(pid, {'step': 'waiting for cacheDump'})
                ###prt_utils.message_to_prm(conn, message)
                while proxy.check_dump_age() > 50:
                    for i in range(30):
                        prt_utils.worker_get_instructions(conn, currentStatus, r)
                        time.sleep(1)
                    logger.info("Checking dump again...", extra=me)
            release_procedure = ["stop_proxy", "release_proxy", "start_proxy"]
            config = r13.hgetall('config')
            release_procedure_kwargs = {'release_proxy': {'version': config['version'],
                                                    'md5': config['md5'], 'zip_file_dir': config['zip_file_dir']}}
            for action in release_procedure:
                ###message = [['step', action]]
                ###prt_utils.message_to_prm(conn, message)
                r.hmset(pid, {'step': action})
                prt_utils.worker_get_instructions(conn, currentStatus, r)
                kwargs = None
                if release_procedure_kwargs.has_key(action):
                    kwargs = release_procedure_kwargs[action]
                    result = run_next_step(proxy, action, **kwargs)
                else:
                    result = run_next_step(proxy, action)
                logger.info("Process-%s: %s" % (os.getpid(), result), extra=me)


            ###message = [['step', 'waiting_for_start']]
            ###prt_utils.message_to_prm(conn, message)
            r.hmset(pid, {'step': 'waiting_for_start'})
            proxy_state = proxy.check_state()
            while proxy_state['lb_status'] != "rrr":
                logger.info("Process-%s: Waiting for %s to become ready..." % (os.getpid(), proxy.name), extra=me)
                for i in range(10):
                    prt_utils.worker_get_instructions(conn, currentStatus, r)
                    time.sleep(1)
                proxy_state = proxy.check_state()
            proxy.in_out_rotation('an', 'in')
            proxy.in_out_rotation('lb', 'in')
            r.hmset(pid, {'status': 'Idle', 'working_on': None, 'step': None})
            ##stopWorker = talk_with_prm(conn, "toStop?")

    except Exception as e:
        raise