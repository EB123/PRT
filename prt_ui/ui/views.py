from django.shortcuts import render
import zmq
from django.http import  HttpResponse


#address = "127.0.0.1"
#port = "4141"

### Proxies For Test Purposes Only ###

SITES = ["ny_an", "ny_lb", "ams_an", "ams_lb", "lax_an", "lax_lb", "sg"]

ny_an = ["nyproxy25", 'nyproxy26', 'nyproxy27']
ny_lb = ["ny4aproxy10", 'ny4aproxy11', 'ny4aproxy12']
ams_an =["ams2proxy25", 'ams2proxy26', 'ams2proxy27']
ams_lb = ["ams2proxy05", 'ams2proxy06', 'ams2proxy07']
lax_an = ["laxproxy25", 'laxproxy26', 'laxproxy27']
lax_lb = ["laxproxy15", 'laxproxy16', 'laxproxy17']
sg = ["sgproxy12", 'sgproxy13', 'sgproxy14']

#######################


def create_zmq_connection(address, port, socket_type): # TODO - should be taken from prt_utils
    context = zmq.Context()
    socket = context.socket(socket_type)
    socket.connect("tcp://%s:%s" % (address, port))
    return socket


def index(request):
    socket = create_zmq_connection("127.0.0.1", "5553", zmq.REQ)
    socket.send_json(["prm", "active_proxy_workers", ["processes"], {}])
    resp = socket.recv_json()
    context = {'active_workers': resp}
    return render(request, "ui/index.html", context)


def ajax_create_process(request):
    if request.method == "POST" and request.is_ajax():
        site = request.POST['ajaxarg_site']
        socket = create_zmq_connection("127.0.0.1", "5553", zmq.REQ)
        socket.send_json(["prm", "create_process", ["processes", "queues"], {"site": site}])
        resp = socket.recv_json()
        #data = auto_reload(socket)
        socket.close()
        context = {}# TODO - Add custom headers to response
        return HttpResponse(resp)

def ajax_auto_reload(request): # TODO - this func should be called from ajax_create_process and not from jquery
    request_site = request.POST['ajaxarg_site']
    socket = create_zmq_connection("127.0.0.1", "5553", zmq.REQ)
    socket.send_json(["prm", "active_proxy_workers", ["processes"], {}])
    resp = socket.recv_json()
    socket.close()
    data = []
    #data.append("<ul>")
    for site in resp:
        data.append("<div id='%s' class='enjoy-css2'>" % site)
        data.append("<button  style='margin-top:0' id='addWorker-%s' data-locked='False' class='Add-Worker'> Add Worker   </button>" % site)
        data.append("<button  style='margin-top:0' id='addToQ-%s' data-locked='False' class='Add-To-Q'> Add To Queue   </button>" % site)
        data.append("<select name='proxies' id='proxies'>")
        for proxy_name in resp[site]['proxies']:
            data.append("<option value='%s'>%s</option>" % (proxy_name, proxy_name))
        data.append("</select>")
        data.append("<h3>%s: %d active workers</h3>" % (site, resp[site]['active_workers']))
        data.append("</div>")
        #data.append("</ul>")
    return HttpResponse(data)
    #return data



def ajax_add_to_queue(request):
    if request.method == "POST" and request.is_ajax():
        site = request.POST['ajaxarg_site']
        proxy_name = request.POST['ajaxarg_proxy_name']
        socket = create_zmq_connection("127.0.0.1", "5553", zmq.REQ)
        socket.send_json(["prm", "add_to_pre_q", ["pre_queues"], {"site": site, "proxy_name": proxy_name}])
        resp = socket.recv_json()
        socket.close()
        return HttpResponse(resp)

"""
def ajax_get_num_proxy_workers(request):

    if request.method == "POST" and request.is_ajax():
"""




"""
def send_ajax_from_ui(request):
    if request.method == "POST" and request.is_ajax():
        create_zmq_connection(address, port)
"""

