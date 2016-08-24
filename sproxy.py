__author__ = 'Eyal'
import time


class sProxy:

    def __init__(self, name):
        self.name = name
        # TODO - self.fqdn

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def dump_cache(self):
        # TODO - Create dump_cache func
        time.sleep(1)
        return "Dumping Cache"

    def check_dump_age(self):
        # TODO - Create check_dump_age func
        time.sleep(1)
        return 30

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

    def check_proxy_state(self):
        # TODO - Create check_proxy_state func
        time.sleep(1)
        return "State Checked"

    def in_rotation(self):
        # TODO - Create in_rotation func
        time.sleep(1)
        return "Proxy is in rotation"

    def out_rotation(self):
        # TODO - Create out_rotation func
        time.sleep(1)
        return "Proxy is out of rotation"

    def check_state(self):
        # TODO - Create check_state func
        time.sleep(1)
        return "Stopped"
