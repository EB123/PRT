import zmq
import redis
import time
import prt_utils
import sys
import requests
import json


###SITES = ["ny_an", "ny_lb", "ams_an", "ams_lb", "lax_an", "lax_lb", "sg"]
SITES = ["OPS_PROXY", "OPS_PROXY_2"]

def active_proxy_workers(**kwargs):
    r1 = kwargs['r1']
    r12 = kwargs['r12']
    servers = kwargs['servers']
    active_count = {}
    sites = r1.smembers('processes')
    for site in iter(sites):
        site_processes = r1.smembers(site)
        active_count[site] = {}
        active_count[site]['workers'] = {}
        active_count[site]['active_workers'] = r1.scard(site_processes)
        active_count[site]['proxies'] = r12.lrange(site, 0, -1)
        #active_count[site]['proxies'] = servers[site]
        for pid in iter(site_processes):
            pid_hash = r1.hgetall(pid)
            active_count[site]['workers'][pid] = {}
            active_count[site]['workers'][pid]['status'] = pid_hash['status']
            active_count[site]['workers'][pid]['working_on'] = pid_hash['working_on']
            active_count[site]['workers'][pid]['step'] = pid_hash['step']
    return active_count


def getServersFromComp(comp, env='dev'):
    r = redis.StrictRedis(host='localhost', port=6379, db=12)
    compsvc = {'dev': 'dev-compsvc01.dev.peer39dom.com'} # TODO - Add prod compsvc
    compsvc_port = '8080'
    url = 'http://%s:%s/ComponentsService/component/%s' % (compsvc[env], compsvc_port, comp)
    resp = requests.get(url)
    servers = {}
    if resp.status_code == 200:
        jresp = json.loads(resp.text)
        for server in jresp['result']['components']:
            if server['groupName'] in SITES:
                if not servers.has_key(server['groupName']):
                    servers[server['groupName']] = []
                servers[server['groupName']].append(server['machineName'])
                r.rpush(server['groupName'], server['machineName'])
        return r, servers
    else:
        raise RuntimeError("Failed to get comp list")

def start_mon(main_conn):

    try:
        r1 = redis.StrictRedis(host='localhost', port=6379, db=1)
    except Exception: # TODO - add redis exception
        print "Cant connect to Redis!"
        sys.exit(1)
    r12, servers = getServersFromComp('proxy')
    monDict = {'r1': r1, 'r12': r12, 'servers': servers}
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