import zmq
import time
import multiprocessing
import PRM
import sys
import queue_device
import prt_utils
import os
import Queue
import redis
import mon
#from zmq.devices import ProcessDevice

def create_process(workerFunc):
    my_conn, proc_conn = multiprocessing.Pipe()
    proc = multiprocessing.Process(target=workerFunc, args=(proc_conn,))
    return proc, my_conn

def create_zmqueues(address, fe_port, be_port, be_type = 'connect'):
    proc = multiprocessing.Process(target=queue_device.main, args=(address, fe_port, be_port, be_type))
    return proc


def main_worker(q, zmq_address, zmq_ui_port, zmq_prm_port, zmq_mon_port):

    def talk_with_agent(socket, request):
        request.pop(0)
        socket.send_json(request)
        while socket.poll(timeout = 10) == 0:
            time.sleep(1)
        response = socket.recv_json()
        return response

    try:
        toExit = False
        socket_ui = prt_utils.create_zmq_connection(zmq_address, zmq_ui_port, zmq.REP, "connect")
        socket_prm = prt_utils.create_zmq_connection(zmq_address, zmq_prm_port, zmq.REQ, "connect")
        socket_mon = prt_utils.create_zmq_connection(zmq_address, zmq_mon_port, zmq.REQ, "connect")
        while not toExit:
            while socket_ui.poll(timeout = 10) == 0:
                time.sleep(1)
                pass
            print "got request %s" % os.getpid()
            request = socket_ui.recv_json()
            if request[0] == "prm":
                #active_socket = socket_prm
                response = talk_with_agent(socket_prm, request)
                print "got response: %s" % response
            elif request[0] == "mon":
                #active_socket = socket_prm # TODO - should be socket_mon, but mon is not yet ready
                response = talk_with_agent(socket_mon, request)
                print "got response: %s" % response
            elif request[0] == "main":
                talk_with_agent(socket_prm, ["", "exit"])
                q.put(request[1])
                sys.exit()
            """"
            request.pop(0)
            active_socket.send_json(request)
            while active_socket.poll(timeout = 10) == 0:
                time.sleep(2)
                pass
            response = active_socket.recv_json()
            """
            socket_ui.send_json(response)
    except KeyboardInterrupt:
        "Exiting from Process - %s" % os.getgid()
        sys.exit()


def ui_garbage_collector(zmq_addres, zmq_ui_port):
    socket = prt_utils.create_zmq_connection(zmq_addres, zmq_ui_port, zmq.REP, "connect")
    while socket.poll(timeout = 100) > 0:
        socket.recv()
        socket.send_json("Garbage Collected!")
    socket.close()


def create_main_workers(num_main_workers):
    main_workers_pool = []
    for i in range(num_main_workers):
        main_worker_proc = multiprocessing.Process(target=main_worker, args=(q, zmq_address, "5554", "5555", "5557"))
        main_workers_pool.append(main_worker_proc)
        main_worker_proc.daemon = True
        main_worker_proc.start()
        print "Started main worker with pid - %s" % main_worker_proc.pid
    return main_workers_pool


if __name__ == '__main__':
    try:
        print "Starting!"
        try:
            r = redis.StrictRedis(host='localhost', port=6379, db=1)
        except Exception:  # TODO - add redis exception
            print "Cant connect to Redis!"
            sys.exit(1)
        zmq_address = "127.0.0.1"
        zmq_procs = []
        num_main_workers = 2
        # Create zmq queues with the following ports:
        # First port (currently 5553) - UI sends to Main. Type - zmq.REQ
        # Second port (currently 5554) - Main receives from UI. Type - zmq.REP
        # Third port (currently 5555) - Main sens to PRM. Type - zmq.REQ
        # Fourth port (currently 5556) - PRM receives from Main. Type - zmq.REP
        # Fifth port (currently 5557) - Main sends to Monitor_agent. Type - zmq.REQ
        # Sixth port (currently 5558) - Monitor_agent receives from Main. Type - zmq.REP
        """"
        for i in range(5553, 5559, 2): # TODO - change ports numbers to vars
            proc = create_zmqueues(zmq_address, i, i+1)
            proc.start()
            zmq_procs.append(proc)
        """
        #time.sleep(10)
        ui_garbage_collector(zmq_address, "5553")
        for i in range(5553, 5559, 2): # TODO - change ports numbers to vars
            if i == 5553:
                proc = create_zmqueues(zmq_address, i, i+1, "bind")
            else:
                proc = create_zmqueues(zmq_address, i, i + 1)
            proc.daemon = True
            proc.start() # TODO - handle scenario when there is a message in the queue but there are no servers to reply (cpu goes to 100%)
            print "Started zmqueue with pid - %s" % proc.pid
            zmq_procs.append(proc)
        print "starting PRM"
        prm_proc, prm_conn = create_process(PRM.start_prm)
        prm_proc.start()
        print "prm pid - %s" % prm_proc.pid
        print "Starting MON"
        mon_proc, mon_conn = create_process(mon.start_mon)
        mon_proc.start()
        print "prm pid - %s" % mon_proc.pid
        #time.sleep(15)
        #socket = create_zmq_connection(zmq_address, "5554")
        toExit = False
        q = multiprocessing.Queue()
        main_workers_pool = create_main_workers(num_main_workers)
        """
        for i in range(num_main_workers):
            main_worker_proc = multiprocessing.Process(target=main_worker, args=(q, zmq_address, "5554", "5555", "5557"))
            main_workers_pool.append(main_worker_proc)
            main_worker_proc.daemon = True
            main_worker_proc.start()
            print "Started main worker with pid - %s" % main_worker_proc.pid
        """
        main_worker_exist = True
        while not toExit:
            if not main_worker_exist:
                main_workers_pool = create_main_workers(num_main_workers)
            main_worker_exist = False
            for proc in main_workers_pool:
                proc.join(timeout=0.1)
                if proc.is_alive():
                    main_worker_exist = True
            #for proc in zmq_procs:
                #proc.join(timeout=0.1)
            try:
                p = q.get(True, 1)
                print "got exit!"
                toExit = p
            except Queue.Empty:
                pass
            time.sleep(1)

        raise
        """""
        while not toExit:
            while socket.poll(timeout = 1000) == 0:
                pass
            choice = socket.recv()
            if choice == "start proxy worker":
                prm_conn.send("start_proc")
            elif choice == "enter to queue":
                prm_conn.send("put in queue")
            elif choice == "exit!":
                print "Bye!"
                sys.exit()
            else:
                raise
        """
    except KeyboardInterrupt:
        print "Caught Ctrl+C!"
    except Exception as e:
        print "Error!"
        print "Error2!"
        print str(e)
    finally:
        multiprocessing.active_children()
        r.flushdb()
        sys.exit()



