from django.shortcuts import render
import zmq


#address = "127.0.0.1"
#port = "4141"

def create_zmq_connection(address, port, socket_type): # TODO - should be taken from prt_utils
    context = zmq.Context()
    socket = context.socket(socket_type)
    socket.connect("tcp://%s:%s" % (address, port))
    return socket


def index(request):
    socket = create_zmq_connection("127.0.0.1", "5553", zmq.REQ)
    socket.send_json(["prm", "active_proxy_workers"])
    resp = socket.recv_json()
    context = {'active_workers': resp}
    return render(request, "ui/index.html", context)

"""
def ajax_get_num_proxy_workers(request):

    if request.method == "POST" and request.is_ajax():
"""




"""
def send_ajax_from_ui(request):
    if request.method == "POST" and request.is_ajax():
        create_zmq_connection(address, port)
"""

