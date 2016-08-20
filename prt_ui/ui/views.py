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
    test = []
    for i in range(50):
        test.append(i)
    context = {'active_workers': resp, 'test': test}
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
    request_site = request.POST['ajaxarg_site']
    socket = create_zmq_connection("127.0.0.1", "5553", zmq.REQ)
    socket.send_json(["prm", "active_proxy_workers", ["sites_dict"], {}])
    resp = socket.recv_json()
    socket.close()
    data = []
    #data.append("<ul>")
    data.append("<button  style='margin-top:0' id='1' value='1' data-wasLoaded='false'> Add Worker   </button>")
    for i in range(50):
        for site in resp:
            if request_site == site:
                data.append("<h3>%s: %d active workers</h3>" % (site, resp[site]))
        #data.append("</ul>")
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

