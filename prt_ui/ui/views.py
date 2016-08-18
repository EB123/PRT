from django.shortcuts import render
import zmq


address = "127.0.0.1"
port = "4141"

def index(request):
    context = {}
    return render(request, "ui/index.html", context)

"""
def ajax_get_num_proxy_workers(request):

    if request.method == "POST" and request.is_ajax():
"""

def create_zmq_connection(address, port):
    context = zmq.Context()
    socket = context.socket(zmq.PAIR)
    socket.connect("tcp://%s:%s" % (address, port))
    return socket

def send_ajax_from_ui(request):
    if request.method == "POST" and request.is_ajax():
        create_zmq_connection(address, port)

