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
import datetime

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

    def update_eventlog(r14, eventid, **kwargs):
        for kwarg in kwargs:
            r14.hmset(eventid, {kwarg:kwargs[kwarg]})
        return


    def index_eventid(r14, eventid, *args):
        for arg in args:
            r14.sadd(arg, eventid)
        return



    try:
        try:
            r = redis.StrictRedis(host='localhost', port=6379, db=1) # Processes DB
            r13 = redis.StrictRedis(host='localhost', port=6379, db=13) # Queues DB
            r14 = redis.StrictRedis(host='localhost', port=6379, db=14) # EventLog DB
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
                        p = q.get(block=False)
                    time.sleep(0.3)
                except Queue.Empty:
                    pass

            """Got new proxy to work on, starting release process"""

            proxy = sproxy.sProxy(p, is_test=True)
            currentStatus = "Busy"
            currentProxy = p
            currentStep = "check_dump_age"
            r.hmset(pid, {'status': currentStatus, 'working_on': currentProxy, 'step': currentStep})
            logger.info("Got a new proxy to work on: %s" % p, extra=me)
            eventid_num = r14.incr('last_eventid')
            eventid = "Event-%s" % eventid_num
            start_date = datetime.datetime.now()
            start_date_day = start_date.strftime('%d/%m/%Y')
            start_date_month = start_date.strftime('%m/%Y')
            start_date_year = start_date.strftime('%Y')
            config = r13.hgetall('config')
            currentVersion = proxy.query_proxy('version').rstrip()
            update_eventlog(r14, eventid, **{'Start Time': start_date.strftime('%d/%m/%Y %H:%M:%S'),
                                            'Finish Time': '-', 'Proxy': proxy.name, 'Old Version': currentVersion,
                                                                'New Version': config['version'], 'Status': 'Started'})
            index_eventid(r14, eventid, *[start_date_day, start_date_month, start_date_year])
            release_procedure_kwargs = {'release_proxy': {'version': config['version'],
                                                        'md5': config['md5'], 'zip_file_dir': config['zip_file_dir']}}
            ###message = [['status', currentStatus], ['working_on', currentProxy], ['step', currentStep]]
            ###prt_utils.message_to_prm(conn, message)
            while proxy.check_dump_age() > 50: # If dump age is more than 54 minutes - Create new dump
                logger.info("Dump is to old, creating new dump file", extra=me)
                proxy.jobChangeState('CacheDumpJob', json.dumps(CacheDumpJob_data['reschedule1h']))
                i = 1
                while 'PAUSED' in json.loads(proxy.jobCheckState('CacheDumpJob').text)['result']['daemons'][0]['state']:
                    if i % 10 == 0:
                        proxy.jobChangeState('CacheDumpJob', json.dumps(CacheDumpJob_data['reschedule1h']))
                    time.sleep(1)
                proxy.jobChangeState('CacheDumpJob', json.dumps(CacheDumpJob_data['pause']))
                ###message = [['step', 'waiting for cacheDump']]
                r.hmset(pid, {'step': 'waiting for cacheDump'})
                ###prt_utils.message_to_prm(conn, message)
                while proxy.check_dump_age() > 50: # TODO - if for some reason the dump creation failed, this will be
                                                   # an infinite loop
                    for i in range(30):
                        prt_utils.worker_get_instructions(conn, currentStatus, r)
                        time.sleep(1)
                    logger.info("Checking dump again...", extra=me)
            release_procedure = ["stop_proxy", "release_proxy", "start_proxy"]


            for action in release_procedure:
                ###message = [['step', action]]
                ###prt_utils.message_to_prm(conn, message)
                r.hmset(pid, {'step': action})
                logger.info("Next step: %s" % action, extra=me)
                prt_utils.worker_get_instructions(conn, currentStatus, r)
                kwargs = None
                if release_procedure_kwargs.has_key(action):
                    kwargs = release_procedure_kwargs[action]
                    result = run_next_step(proxy, action, **kwargs)
                else:
                    result = run_next_step(proxy, action)
                logger.info("Step result: %s" % result, extra=me)
                update_eventlog(r14, eventid, **{'Status': action})


            ###message = [['step', 'waiting_for_start']]
            ###prt_utils.message_to_prm(conn, message)
            r.hmset(pid, {'step': 'waiting_for_start'})
            update_eventlog(r14, eventid, **{'Status': 'Proxy Started'})
            proxy_state = proxy.check_state()
            while proxy_state['lb_status'] != "rrr":
                logger.info("Process-%s: Waiting for %s to become ready..." % (os.getpid(), proxy.name), extra=me)
                for i in range(10):
                    prt_utils.worker_get_instructions(conn, currentStatus, r)
                    time.sleep(1)
                proxy_state = proxy.check_state()
            proxy.in_out_rotation('an', 'in')
            proxy.in_out_rotation('lb', 'in')
            logger.info("Finished release process for %s" % proxy.name, extra=me)
            finish_date = datetime.datetime.now()
            update_eventlog(r14, eventid, **{'Status': 'Finished',
                                             'Finish Time':finish_date.strftime('%d/%m/%Y %H:%M:%S')})
            r.hmset(pid, {'status': 'Idle', 'working_on': None, 'step': None})
            ##stopWorker = talk_with_prm(conn, "toStop?")

    except Exception as e:
        update_eventlog(r14, eventid, **{'Status': 'Failed'})
        raise