import zmq
import redis
import time
import prt_utils
import sys
import requests
import json
import traceback
import sproxy
import threading
import datetime

###SITES = ["ny_an", "ny_lb", "ams_an", "ams_lb", "lax_an", "lax_lb", "sg"]
SITES = ["OPS_PROXY", "OPS_PROXY_2"]

def proxy_query(r1, r12):

    sites = r1.smembers('processes')
    proxies = {}
    keys = ['version', 'dump_age_min']
    for site in sites:
        proxies[site] = {}
        proxy_list = r12.lrange(site, 0, -1)
        for proxy in proxy_list:
            proxies[site][proxy] = {}
    while True:
        for site in iter(sites):
            for proxy in proxies[site]:
                p = sproxy.sProxy(proxy, light=True)
                resp = p.query_proxy(keys)
                resp = resp.split() # TODO - handle scenario that status_code is not 200
                for i in range(len(keys)):
                    proxies[site][proxy][keys[i]] = resp[i]
                proxies[site][proxy]['timestamp'] = datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                r12.hmset(proxy, proxies[site][proxy])
        time.sleep(20)


def active_proxy_workers(**kwargs):
    r1 = kwargs['r1']
    r12 = kwargs['r12']
    servers = kwargs['servers']
    time_values =  kwargs['time_values']
    active_count = {}
    sites = r1.smembers('processes')
    now = time.time()
    for site in iter(sites):
        site_processes = r1.smembers(site)
        active_count[site] = {}
        active_count[site]['workers'] = {}
        active_count[site]['active_workers'] = r1.scard(site)
        active_count[site]['proxies'] = r12.lrange(site, 0, -1)
        active_count[site]['proxies'].sort()
        active_count[site]['proxy_stats'] = {}
        for i in range(len(active_count[site]['proxies'])):
            proxy_name = active_count[site]['proxies'][i]
            proxy_stats = r12.hgetall(proxy_name)
            active_count[site]['proxy_stats'][proxy_name] = proxy_stats
            active_count[site]['proxies'][i] = [proxy_name, proxy_stats['version']]

        #active_count[site]['proxies'] = servers[site]
        for pid in iter(site_processes):
            pid_hash = r1.hgetall(pid)
            active_count[site]['workers'][pid] = {}
            active_count[site]['workers'][pid]['status'] = pid_hash['status']
            active_count[site]['workers'][pid]['working_on'] = pid_hash['working_on'].split('.')[0]
            active_count[site]['workers'][pid]['step'] = pid_hash['step']
            active_count[site]['workers'][pid]['type'] = pid_hash['type']
            active_count[site]['workers'][pid]['is_stuck'] = 'ok'
            if time_values.has_key(pid_hash['step']):
                print time_values[pid_hash['step']]
                if pid_hash['step_start_time'] != 'None':
                    step_start_time = float(pid_hash['step_start_time'])
                    if (now - step_start_time)/ (float(60)) > float(time_values[pid_hash['step']]['error']):
                        active_count[site]['workers'][pid]['is_stuck'] = 'error'
                    elif (now - step_start_time) / (float(60)) > float(time_values[pid_hash['step']]['warning']):
                        active_count[site]['workers'][pid]['is_stuck'] = 'warning'
    return active_count

def get_eventlog(**kwargs):
    r14 = kwargs['r14']
    events_list = r14.keys(pattern='Event-*')
    all_events = []
    for event in events_list:
        event_hash = r14.hgetall(event)
        try:
            event_hash['Proxy'] = event_hash['Proxy'].split('.')[0]
        except KeyError:
            pass
        all_events.append([event, event_hash])
    all_events.sort(key = lambda x:int(x[0].split('-')[1]), reverse=True)
    return all_events

def get_proxies(**kwargs):
    r12 = kwargs['r12']
    r13 = kwargs['r13']
    site = kwargs['site']
    proxies = {}
    proxies[site] = {}
    proxies_list = r12.lrange(site, 0, -1)
    for proxy in proxies_list:
        proxies[site][proxy] = r12.hget(proxy, 'version')
    current_version = r13.hget('config', 'version')
    show_all_proxies = r13.hget('config', 'show_all_proxies')
    return [proxies, current_version, show_all_proxies]




def getServersFromComp(r12, comp, env='dev'):

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
                r12.rpush(server['groupName'], server['machineName'])
        return servers
    else:
        raise RuntimeError("Failed to get comp list")


def load_time_values(r13):
    steps = r13.smembers('steps')
    time_values = {}
    for step in iter(steps):
        time_values[step] = r13.hgetall('time_values:%s' % step)
    return time_values


def start_mon(main_conn):

    try:
        r1 = redis.StrictRedis(host='localhost', port=6379, db=1)
        r12 = redis.StrictRedis(host='localhost', port=6379, db=12)
        r13 = redis.StrictRedis(host='localhost', port=6379, db=13)
        r14 = redis.StrictRedis(host='localhost', port=6379, db=14)
    except Exception: # TODO - add redis exception
        print "Cant connect to Redis!"
        sys.exit(1)
    servers = getServersFromComp(r12, 'proxy')
    time_values = load_time_values(r13)
    print time_values
    monDict = {'r1': r1, 'r12': r12, 'r14': r14, 'r13': r13, 'servers': servers, 'time_values':time_values}
    this_module = sys.modules[__name__]
    socket = prt_utils.create_zmq_connection("127.0.0.1", "5558", zmq.REP, "bind")
    proxy_query_thread = threading.Thread(target=proxy_query, args=(r1, r12))
    proxy_query_thread.daemon = True
    proxy_query_thread.start()
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
            #print "%s" % e  # TODO - Make sure the full traceback is printed. right now only e.message is printed.
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print "*** print_exception:"
            traceback.print_exception(exc_type, exc_value, exc_traceback,
                                      limit=2, file=sys.stdout)
        finally:
            try:
                socket.send_json(response)
            except Exception as e:  # TODO - this should only refer to socket exceptions
                print "Something went REALLY wrong, unable to send response to UI. Exiting..."
                print e
                sys.exit(1)


if __name__ == '__main__':
    start_mon(conn)