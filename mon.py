import zmq
import redis
import time
import prt_utils
import sys


##### Testing Purposes #############

ny_an = ["nyproxy25", 'nyproxy26', 'nyproxy27', 'nyproxy28', 'nyproxy29', 'nyproxy30', 'nyproxy31']
ny_lb = ["ny4aproxy10", 'ny4aproxy11', 'ny4aproxy12','ny4aproxy13', 'ny4aproxy14', 'ny4aproxy15', 'ny4aproxy16']
ams_an =["ams2proxy25", 'ams2proxy26', 'ams2proxy27', 'ams2proxy28', 'ams2proxy29', 'ams2proxy30']
ams_lb = ["ams2proxy05", 'ams2proxy06', 'ams2proxy07', 'ams2proxy08', 'ams2proxy09']
lax_an = ["laxproxy25", 'laxproxy26', 'laxproxy27', 'laxproxy28', 'laxproxy29']
lax_lb = ["laxproxy15", 'laxproxy16', 'laxproxy17']
sg = ["sgproxy12", 'sgproxy13', 'sgproxy14', 'sgproxy15']

###################################

def active_proxy_workers(**kwargs):
    r = kwargs['r']
    active_count = {}
    sites = r.smembers('processes')
    for site in iter(sites):
        site_processes = r.smembers(site)
        active_count[site] = {}
        active_count[site]['workers'] = {}
        active_count[site]['active_workers'] = r.scard(site_processes)
        active_count[site]['proxies'] = globals()[site]  # Test purposes only
        for pid in iter(site_processes):
            pid_hash = r.hgetall(pid)
            active_count[site]['workers'][pid] = {}
            active_count[site]['workers'][pid]['status'] = pid_hash['status']
            active_count[site]['workers'][pid]['working_on'] = pid_hash['working_on']
            active_count[site]['workers'][pid]['step'] = pid_hash['step']
    return active_count


def start_mon(main_conn):

    try:
        r = redis.StrictRedis(host='localhost', port=6379, db=1)
    except Exception: # TODO - add redis exception
        print "Cant connect to Redis!"
        sys.exit(1)
    monDict = {'r': r}
    this_module = sys.modules[__name__]
    socket = prt_utils.create_zmq_connection("127.0.0.1", "5558", zmq.REP, "bind")
    while True:
        while socket.poll(timeout=10) == 0:
            time.sleep(0.2)
            pass
        request = socket.recv_json()
        try:
            method = getattr(this_module, request[0])
            if len(request) > 1:
                kwargs = {}
                for arg in request[1]:
                    kwargs[arg] = monDict[arg]
                for arg in request[2].keys():
                    kwargs[arg] = request[2][arg]
                response = method(**kwargs)
            else:
                response = method()
        except Exception as e:
            print "MON exception handler"
            time.sleep(2)
            response = str(e)  # TODO - respone should contain a "success/fail" field
            print "%s" % e  # TODO - Make sure the full traceback is printed. right now only e.message is printed.
        finally:
            try:
                socket.send_json(response)
            except Exception as e:  # TODO - this should only refer to socket exceptions
                print "Something went REALLY wrong, unable to send response to UI. Exiting..."
                print e
                sys.exit(1)


if __name__ == '__main__':
    start_mon(conn)