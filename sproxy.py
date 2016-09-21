__author__ = 'Eyal'
import time
import paramiko
import atexit
import os
import requests
import json
import logging
from logging.handlers import RotatingFileHandler

class sProxy:


    def __init__(self, name, log_dir = '/tmp', port='8080', proxy_pl_port = '8090', user='root', is_test = False):
        self.name = name
        self.user = user
        self.sshconn = self._sshconnect(name, user, is_test)
        self.port = port
        self.proxy_pl_port = proxy_pl_port
        #self.base_cmd = '. ./.paramiko_profile ; '
        self.base_cmd = ''
        self.is_test = is_test
        self.compsvc = {'address': 'dev-compsvc01.dev.peer39dom.com', 'port': '8080'}
        self.logger = self._configLogger(log_dir)
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

    def _ssh_execute(self, sshclient, cmd, timeout=20.0):

        self.logger.debug("About to execute: %s" % cmd)
        transport = sshclient.get_transport()
        chan = transport.open_session()
        chan.settimeout(timeout)
        chan.exec_command(cmd)
        stdout = chan.makefile('r', -1)
        stderr = chan.makefile_stderr('r', -1)
        tmp_output = []
        tmp_stderr = []
        while not chan.exit_status_ready():
            tmp_output.append(stdout.readline())
            tmp_stderr.append(stderr.readline())
            pass
        exitCode = chan.recv_exit_status()
        for line in stdout:
            tmp_output.append(line)
        for line in stderr:
            tmp_stderr.append(line)
        output = []
        error = []
        if len(tmp_output):
            for line in tmp_output:
                if not line == '':
                    output.append(line.strip())
        if len(tmp_stderr):
            for line in tmp_stderr:
                if not line == '':
                    error.append(line.strip())
        self.logger.debug("Exit code is: %s" % exitCode)
        self.logger.debug("stdout is: %s" % '\n'.join(output))
        self.logger.debug("stderr is: %s" % '\n'.join(error))
        return exitCode, output, error

    def _configLogger(self, log_dir):
        logger = logging.getLogger("%s-%s" %(__name__, self.name.split('.')[0]))
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        logfile = os.path.join(log_dir, "%s.log" % self.name.split('.')[0])
        logfile_handler = RotatingFileHandler(logfile, maxBytes=102400)
        for handler in logger.handlers:
            logger.removeHandler(handler)
        formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s', '%m-%d %H:%M')
        logfile_handler.setFormatter(formatter)
        logfile_handler.setLevel(logging.DEBUG)
        logger.addHandler(logfile_handler)
        logger.debug("=============================================")
        logger.debug("============== Starting =====================")
        logger.debug("=============================================")
        return logger


    def test_logger(self): # TODO - remove this method
        print self.logger.handlers

    def jobChangeState(self, job, json_data, group='all'):
        # TODO - Create dump_cache func
        compsvc_url = 'http://%s:%s/ComponentsService/daemon/proxy/%s/%s/%s' % (self.compsvc['address'],
                                                                            self.compsvc['port'], group, self.name, job)
        custHeaders = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        response = requests.put(compsvc_url, headers=custHeaders, data = json_data)
        #json_response = json.loads(response.text)
        return response

    def jobCheckState(self, job, group='all'):
        compsvc_url = 'http://%s:%s/ComponentsService/daemon/proxy/%s/%s/%s' % (self.compsvc['address'],
                                                                        self.compsvc['port'], group, self.name, job)
        response = requests.get(compsvc_url)
        return response

    def check_dump_age(self, dump_location = '/workspace/repository/proxy/dump'):
        # TODO - Create check_dump_age func
        """
        if self.is_test:
            cmd = '/bin/ls -l ' + dump_location + " | grep dump | grep rdy$ | awk '{print $9}'"
            exitCode, output, error = self._ssh_execute(self.sshconn, cmd)
            if exitCode == 0 and len(output) == 1: # TODO - better way for handling errors
                dump_file = os.path.join(dump_location, output[0])
                cmd = "stat --printf '%%Y' %s" % dump_file
                exitCode, dump_last_modified, error = self._ssh_execute(self.sshconn, cmd)
                if exitCode == 0 and len(dump_last_modified) == 1:
                    dump_last_modified = int(dump_last_modified[0])
                    now = time.time()
                    dump_age = float(now - dump_last_modified) / 3600
                    return dump_age

        else:
        """
        proxy_pl_path = '/ops/cgi-bin/proxy.pl'
        url = 'http://%s:%s%s' % (self.name, self.proxy_pl_port, proxy_pl_path)
        response = requests.get(url, params={'key': 'dump_age_min'})
        return float(response.text.split()[0]) # TODO - check status_code, if not 200 - raise

    def stop_proxy(self, retries = 100): # TODO - handle scenario that proxy is already stopped
        # TODO - Create stop_proxy func
        if self.is_test:
            is_stopped = False
            cmd = "runuser -l peeradmin -c 'jps -l | grep catalina '"
            exitCode, output, error = self._ssh_execute(self.sshconn, self.base_cmd + cmd)
            if exitCode == 0:
                catalina_pid = output[0].split(" ")[0]
            cmd = "jps -l | grep rmi.registry"
            exitCode, output, error = self._ssh_execute(self.sshconn, self.base_cmd + cmd)
            if exitCode == 0:
                rmi_pid = output[0].split(" ")[0]
            pids = {catalina_pid: True, rmi_pid: True}
            retry = 1
            while not is_stopped and retry < retries:
                for pid in pids:
                    cmd = 'runuser -l peeradmin -c "kill -9 %s"' % pid
                    exitCode, output, error = self._ssh_execute(self.sshconn, cmd)
                    time.sleep(0.2)
                    cmd = 'runuser -l peeradmin -c "ps -ef | grep %s | grep -v grep"' % pid
                    exitCode, output, error = self._ssh_execute(self.sshconn, cmd)
                    if not exitCode == 0:
                        pids[pid] = False
                if not pids[catalina_pid] and not pids[rmi_pid]:
                    is_stopped = True
                retry += 1
            cmd = 'runuser -l peeradmin -c "jps -l | grep -v jps | wc -l"'
            exitCode, output, error = self._ssh_execute(self.sshconn, cmd)
            return "jps -l | grep -v jps | wc -l --> output is: %s" % output
        else:
            return "Not allowd on production proxies"

    def release_proxy(self, version, md5, zip_file_dir):
        # TODO - Create release_proxy func
        if self.is_test:
            runuser = 'runuser -l peeradmin -c'
            zip_file = 'peer39-proxy-%s.context.zip' % version
            zip_file_path = os.path.join(zip_file_dir, zip_file)
            cmd = "/usr/bin/md5sum %s | awk '{print $1}'" % zip_file_path
            exitCode, output, error = self._ssh_execute(self.sshconn, cmd)
            if output[0] != md5:
                raise RuntimeError("Wrong MD5!!!")
            base_dir = '/workspace/test/proxy'
            new_ver_path = os.path.join(base_dir, 'peer39-proxy-%s' % version)
            cmd = "rm -rf %s; unlink %s/peer39-proxy" % (new_ver_path, base_dir)
            exitCode, output, error = self._ssh_execute(self.sshconn, cmd)
            if exitCode != 0:
                raise RuntimeError("output is: %s\n error is: %s" % (output, error))
            cmd = "%s 'cd %s && mkdir peer39-proxy-%s && cd peer39-proxy-%s && cp -f %s . && unzip %s'" % \
                  (runuser, base_dir, version, version, zip_file_path, zip_file)
            exitCode, output, error = self._ssh_execute(self.sshconn, cmd)
            if exitCode != 0:
                raise RuntimeError("output is: %s\n error is: %s" % (output, error))
            cmd = "%s 'cd %s && ln -s peer39-proxy-%s peer39-proxy'" % (runuser, base_dir, version)
            exitCode, output, error = self._ssh_execute(self.sshconn, cmd)
            if exitCode != 0:
                raise RuntimeError("output is: %s\n error is: %s" % (output, error))
            scripts_dir = '/workspace/development/org/apache/tomcat/6.0.29/webapps/ROOT/WEB-INF/scripts'
            cmd = "%s 'cd %s && chmod 775 *.sh && dos2unix *.sh'" % (runuser, scripts_dir)
            exitCode, output, error = self._ssh_execute(self.sshconn, cmd)
            if exitCode != 0:
                raise RuntimeError("output is: %s\n error is: %s" % (output, error))
            cmd = "ls -l /workspace/test/proxy | grep -v total | awk '{print $9$10$11}' | head -1"
            exitCode, output, error = self._ssh_execute(self.sshconn, cmd)
        return output

    def start_proxy(self):
        # TODO - Create start_proxy func
        if self.is_test:
            exitCodes = {'rmi': None, 'catalina': None}
            cmd = "runuser -l peeradmin -c 'cd /workspace/development/org/apache/tomcat/6.0.29/webapps/ROOT/WEB-INF/scripts/ && ant rmiregistry'"
            exitCode, output, error = self._ssh_execute(self.sshconn, cmd)
            exitCodes['rmi'] = exitCode
            if exitCode == 0:
                cmd = "runuser -l peeradmin -c 'cd /workspace/development/org/apache/tomcat/6.0.29/bin/ && ./startup.sh'"
                exitCode, output, error = self._ssh_execute(self.sshconn, cmd)
                exitCodes['catalina'] = exitCode
                if exitCode == 0:
                    cmd = "runuser -l peeradmin -c 'jps -l | wc -l'"
                    exitCode, output, error = self._ssh_execute(self.sshconn, cmd)
        return "jps -l | wc -l --> output is: %s" % output

    def check_state(self):
        # TODO - Create check_proxy_state func
        an_status_path = '/proxy/keepalive?file=/workspace/temp/1'
        lb_status_path = '/proxy/keepalive?file=/workspace/temp/1.txt'
        paths = {'an_status': an_status_path, 'lb_status': lb_status_path}
        status = {}
        for path in paths:
            url = 'http://%s:%s%s' % (self.name, self.port, paths[path])
            try:
                response = requests.get(url, timeout=10) # TODO - add timeout
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                return {'lb_status': 'error', 'an_status': 'error'} # TODO - create an exception
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
        exitCode, output, error = self._ssh_execute(self.sshconn, cmd)
        return exitCode, output, error

    """
    def out_rotation(self):
        # TODO - Create out_rotation func
        time.sleep(1)
        return "Proxy is out of rotation"
    """

