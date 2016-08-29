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




def proxy_worker(q, conn, logging_q, site, worker_num):


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
        #me = {'worker': 'Worker-%s-%s' % (site, worker_num)}
        me = 'Worker-%s-%s' % (site, worker_num)
        stopWorker = False
        #logger = temp_logger(logging_q)
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        pid = os.getpid()
        currentStatus = "Idle" # To know the last status when resuming from paused
        currentProxy = None # Still not sure if this will actually be used
        currentStep = None # Still not sure if this will actually be used
        while not stopWorker:
            logger.info("%s: I'M UP!" % me )
            p = None
            logger.info("%s: Waiting for input..." % me)
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