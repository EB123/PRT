__author__ = 'Eyal'
import time
import paramiko
import atexit
import prt_utils
import os
import requests
import json

class sProxy:


    def __init__(self, name, port='8080', proxy_pl_port = '8090', user='root', is_test = False):
        self.name = name
        self.user = user
        self.sshconn = self._sshconnect(name, user, is_test)
        self.port = port
        self.proxy_pl_port = proxy_pl_port
        self.base_cmd = '. ./.paramiko_profile ; '
        self.is_test = is_test
        self.compsvc = {'address': 'dev-compsvc01.dev.peer39dom.com', 'port': '8080'}
        # TODO - self.fqdn

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def _sshconnect(self, name, user, is_test):
        if is_test:
            try:
                sshconn = paramiko.SSHClient()
                sshconn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                sshconn.connect(name, username=user)
                atexit.register(paramiko.client.SSHClient.close, sshconn)
                return sshconn
            except Exception: # TODO - specific exceptions
                raise # TODO - consider adding a logger to the class
        else:
            return None

    def jobChangeState(self, job, json_data, group='all'):
        # TODO - Create dump_cache func
        compsvc_url = 'http://%s:%s/ComponentsService/daemon/proxy/%s/%s/%s' % (self.compsvc['address'],
                                                                            self.compsvc['port'], group, self.name, job)
        custHeaders = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        response = requests.put(compsvc_url, headers=custHeaders, data = json_data)
        json_response = json.loads(response.text)
        return response

    def jobCheckState(self, job, group='all'):
        compsvc_url = 'http://%s:%s/ComponentsService/daemon/proxy/%s/%s/%s' % (self.compsvc['address'],
                                                                        self.compsvc['port'], group, self.name, job)
        response = requests.get(compsvc_url)
        return response

    def check_dump_age(self, dump_location = '/workspace/repository/proxy/dump'):
        # TODO - Create check_dump_age func
        if self.is_test:
            cmd = '/bin/ls -l ' + dump_location + " | grep dump | grep rdy$ | awk '{print $9}'"
            exitCode, output, error = prt_utils.ssh_execute(self.sshconn, cmd)
            if exitCode == 0 and len(output) == 1: # TODO - better way for handling errors
                dump_file = os.path.join(dump_location, output[0])
                cmd = "stat --printf '%%Y' %s" % dump_file
                exitCode, dump_last_modified, error = prt_utils.ssh_execute(self.sshconn, cmd)
                if exitCode == 0 and len(dump_last_modified) == 1:
                    dump_last_modified = int(dump_last_modified[0])
                    now = time.time()
                    dump_age = float(now - dump_last_modified) / 3600
                    return dump_age
        else:
            proxy_pl_path = '/ops/cgi-bin/proxy.pl'
            url = 'http://%s:%s%s' % (self.name, self.proxy_pl_port, proxy_pl_path)
            response = requests.get(url, params={'key': 'dump_age_min'})
            return float(response.text.split()[0]) # TODO - check status_code, if not 200 - raise

    def stop_proxy(self, retries = 100):
        '''
        # TODO - Create stop_proxy func
        is_stopped = False
        cmd = "jps -l | grep catalina | awk '{print $1}'"
        exitCode, output, error = prt_utils.ssh_execute(self.sshconn, self.base_cmd + cmd)
        if exitCode == 0:
            catalina_pid = output[0]
            print catalina_pid
        cmd = "jps -l | grep rmi.registry | awk '{print $1}'"
        exitCode, output, error = prt_utils.ssh_execute(self.sshconn, self.base_cmd + cmd)
        if exitCode == 0:
            rmi_pid = output[0]
            print rmi_pid
        pids = {catalina_pid: True, rmi_pid: True}
        retry = 1
        while not is_stopped and retry < retries:
            for pid in pids:
                cmd = 'kill -9 %s' % pid
                exitCode, output, error = prt_utils.ssh_execute(self.sshconn, cmd)
                cmd = 'ps -ef | grep %s' pid
                exitCode, output, error = prt_utils.ssh_execute(self.sshconn, cmd)
                if not exitCode == 0:
                    pids[pid] = False
            if not pids[catalina_pid] and not pid[rmi_pid]:
                is_stopped = True
        '''
        return "Proxy %s Stopped" % self.name

    def release_proxy(self):
        # TODO - Create release_proxy func
        time.sleep(10)
        return "Proxy %s Released" % self.name

    def start_proxy(self):
        # TODO - Create start_proxy func
        time.sleep(10)
        return "Proxy %s Started" % self.name

    def check_state(self):
        # TODO - Create check_proxy_state func
        an_status_path = '/proxy/keepalive?file=/workspace/temp/1'
        lb_status_path = '/proxy/keepalive?file=/workspace/temp/1.txt'
        paths = {'an_status': an_status_path, 'lb_status': lb_status_path}
        status = {}
        for path in paths:
            url = 'http://%s:%s%s' % (self.name, self.port, paths[path])
            response = requests.get(url) # TODO - add timeout
            status[path] = response.text.strip() # TODO - check status_code
        return status

    # TODO - Create decorator that validates that action is 'in' or 'out' and that type is 'an' or 'lb'
    def in_out_rotation(self, proxy_type, action):
        # TODO - Create in_rotation func
        actions = {'an': {'in': '1', 'out': '0'}, 'lb': {'in': 'ppp', 'out': 'rrr'}}
        scripts = '/workspace/test/proxy/peer39-proxy/WEB-INF/scripts'
        change_rotation_script = 'setValue.sh'
        keepalive_url = '/workspace/temp/1'
        if proxy_type == 'lb':
            keepalive_url = keepalive_url + '.txt'
        cmd = '. ./.paramiko_profile ; cd %s && ./%s %s %s' % (scripts, change_rotation_script, keepalive_url, actions[proxy_type][action])
        exitCode, output, error = prt_utils.ssh_execute(self.sshconn, cmd)
        return exitCode, output, error

    """
    def out_rotation(self):
        # TODO - Create out_rotation func
        time.sleep(1)
        return "Proxy is out of rotation"
    """

