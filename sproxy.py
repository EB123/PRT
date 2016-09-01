__author__ = 'Eyal'
import time
import paramiko
import atexit
import prt_utils
import os
import requests

class sProxy:

    def __init__(self, name, port='8080', user='root'):
        self.name = name
        self.user = user
        self.sshconn = self._sshconnect(name, user)
        self.port = port
        # TODO - self.fqdn

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def _sshconnect(self, name, user):
        try:
            sshconn = paramiko.SSHClient()
            sshconn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            sshconn.connect(name, username=user)
            atexit.register(paramiko.client.SSHClient.close, sshconn)
            return sshconn
        except Exception: # TODO - specific exceptions
            raise # TODO - consider adding a logger to the class

    def dump_cache(self):
        # TODO - Create dump_cache func
        time.sleep(1)
        return "Dumping Cache"

    def check_dump_age(self, dump_location = '/workspace/repository/proxy/dump'):
        # TODO - Create check_dump_age func
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

    def stop_proxy(self):
        # TODO - Create stop_proxy func
        time.sleep(10)
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

