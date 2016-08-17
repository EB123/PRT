import zmq
import time
import multiprocessing
import PRM
import sys

def create_zmq_connection(address, port):
    context = zmq.Context()
    socket = context.socket(zmq.PAIR)
    socket.bind("tcp://%s:%s" % (address, port))
    return socket

def create_process(workerFunc):
    my_conn, proc_conn = multiprocessing.Pipe()
    proc = multiprocessing.Process(target=workerFunc, args=(proc_conn,))
    return proc, my_conn


if __name__ == '__main__':
    try:
        print "Starting!"
        prm_proc, prm_conn = create_process(PRM.start_prm)
        prm_proc.start()
        print prm_proc.pid
        socket = create_zmq_connection("127.0.0.1", "4141")
        toExit = False
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
    except KeyboardInterrupt:
        print "Caught Ctrl+C!"
    except Exception:
        print "Error!"
        print "Error2!"
    finally:
        prm_conn.send("exit")
        while prm_proc.is_alive():
            pass
        sys.exit()



