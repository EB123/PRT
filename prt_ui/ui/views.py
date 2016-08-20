from django.shortcuts import render
import zmq
from django.http import  HttpResponse


#address = "127.0.0.1"
#port = "4141"

def create_zmq_connection(address, port, socket_type): # TODO - should be taken from prt_utils
    context = zmq.Context()
    socket = context.socket(socket_type)
    socket.connect("tcp://%s:%s" % (address, port))
    return socket


def index(request):
    socket = create_zmq_connection("127.0.0.1", "5553", zmq.REQ)
    socket.send_json(["prm", "active_proxy_workers", ["sites_dict"], {}])
    resp = socket.recv_json()
    context = {'active_workers': resp}
    return render(request, "ui/index.html", context)


def ajax_create_process(request):
    if request.method == "POST" and request.is_ajax():
        site = request.POST['ajaxarg_site']
        socket = create_zmq_connection("127.0.0.1", "5553", zmq.REQ)
        socket.send_json(["prm", "create_process", ["sites_dict"], {"site": site}])
        resp = socket.recv_json()
        #data = auto_reload(socket)
        socket.close()
        context = {}# TODO - Add custom headers to response
        return HttpResponse("OK!")

def auto_reload(request): # TODO - this func should be called from ajax_create_process and not from jquery
    socket = create_zmq_connection("127.0.0.1", "5553", zmq.REQ)
    socket.send_json(["prm", "active_proxy_workers", ["sites_dict"], {}])
    resp = socket.recv_json()
    socket.close()
    data = []
    data.append("<ul>")
    for site in resp:
        data.append("<li>%s: %d active workers</li>" % (site, resp[site]))
    data.append("</ul>")
    return HttpResponse(data)
    #return data




"""
def ajax_get_num_proxy_workers(request):

    if request.method == "POST" and request.is_ajax():
"""




"""
def send_ajax_from_ui(request):
    if request.method == "POST" and request.is_ajax():
        create_zmq_connection(address, port)
"""

