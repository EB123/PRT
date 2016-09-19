from django.shortcuts import render
import zmq
from django.http import  HttpResponse, HttpResponseServerError
import json

#address = "127.0.0.1"
#port = "4141"

### Proxies For Test Purposes Only ###

SITES = ["ny_an", "ny_lb", "ams_an", "ams_lb", "lax_an", "lax_lb", "sg"]

ny_an = ["nyproxy25", 'nyproxy26', 'nyproxy27', 'nyproxy28', 'nyproxy29', 'nyproxy30', 'nyproxy31']
ny_lb = ["ny4aproxy10", 'ny4aproxy11', 'ny4aproxy12','ny4aproxy13', 'ny4aproxy14', 'ny4aproxy15', 'ny4aproxy16']
ams_an =["ams2proxy25", 'ams2proxy26', 'ams2proxy27', 'ams2proxy28', 'ams2proxy29', 'ams2proxy30']
ams_lb = ["ams2proxy05", 'ams2proxy06', 'ams2proxy07', 'ams2proxy08', 'ams2proxy09']
lax_an = ["laxproxy25", 'laxproxy26', 'laxproxy27', 'laxproxy28', 'laxproxy29']
lax_lb = ["laxproxy15", 'laxproxy16', 'laxproxy17']
sg = ["sgproxy12", 'sgproxy13', 'sgproxy14', 'sgproxy15']

#######################


def create_zmq_connection(address, port, socket_type): # TODO - should be taken from prt_utils
    context = zmq.Context()
    socket = context.socket(socket_type)
    socket.connect("tcp://%s:%s" % (address, port))
    return socket


def index(request):
    socket = create_zmq_connection("127.0.0.1", "5553", zmq.REQ)
    #socket.send_json(["prm", "active_proxy_workers", ["processes"], {}])
    socket.send_json(["mon", "active_proxy_workers", ["r"], {}])
    resp = socket.recv_json()
    context = {'active_workers': resp, 'sites': SITES}
    return render(request, "ui/index.html", context)


def ajax_create_process(request):
    if request.method == "POST" and request.is_ajax():
        site = request.POST['ajaxarg_site']
        socket = create_zmq_connection("127.0.0.1", "5553", zmq.REQ)
        socket.send_json(["prm", "create_process", ["processes", "queues", "r", "processes_lock"], {"site": site}])
        resp = socket.recv_json()
        #data = auto_reload(socket)
        socket.close()
        context = {}# TODO - Add custom headers to response
        return HttpResponse(resp)

def ajax_auto_reload(request): # TODO - this func should be called from ajax_create_process and not from jquery
    socket = create_zmq_connection("127.0.0.1", "5553", zmq.REQ)
    #socket.send_json(["prm", "active_proxy_workers", ["processes"], {}])
    socket.send_json(["mon", "active_proxy_workers", ["r"], {}])
    resp = socket.recv_json()
    socket.close()
    data = []
    #data.append("<ul>")
    for site in resp:
        data.append("<div id='%s' class='enjoy-css2'>" % site)
        data.append("<button  style='margin-right:6px' id='addWorker-%s' data-locked='False' class='Add-Worker'> Add Worker   </button>" % site)
        data.append("<button  style='margin-top:0' id='addToQ-%s' data-locked='False' class='Add-To-Q2'> Add To Queue   </button>" % site)
        data.append("<form id='addToQueue-%s' value='%s' style='display:none'>" % (site, site))
        data.append("<fieldset>")
        data.append(" <input type='checkbox' name='selectAll' class='selectAll' id='selectAll-%s' value='%s'>Select All</input><br>" % (site, site))
        for proxy_name in resp[site]['proxies']:
            data.append("<input type='checkbox' name='myCheckBoxes' id='myCheckBoxes-%s' class='myCheckBoxes' value='%s'>%s</input><br>" % (proxy_name, proxy_name, proxy_name))
        data.append("</fieldset>")
        data.append("</form>")
        data.append("<h3>%s: %d active workers</h3>" % (site, resp[site]['active_workers']))
        data.append("<ul>")
        for pid in resp[site]['workers']:
            proc_hash = resp[site]['workers'][pid]
            data.append("<li class='workers'>%s - status: %s, currently working on: %s, step: %s" % (pid, proc_hash['status'], proc_hash['working_on'],
                                                                                                           proc_hash['step']))
            data.append("<button  style='margin-right:4px; margin-left:6px' id='%s-start' value='%s' data-pressed='%s' class='resume_worker'>&#9658;</button>" % (pid, pid, proc_hash['status']))
            data.append("<button  style='margin-top:0' id='%s-pause' value='%s' data-pressed='%s' class='pause_worker'>&#9646;&#9646;</button></li>" % (pid, pid, proc_hash['status']))
        data.append("</ul>")
        data.append("</div>")
    return HttpResponse(data)
    #return data



def ajax_add_to_queue(request):
    if request.method == "POST" and request.is_ajax():
        site = request.POST['ajaxarg_site']
        proxies = json.loads(request.POST['ajaxarg_proxy_name'])
        socket = create_zmq_connection("127.0.0.1", "5553", zmq.REQ)
        socket.send_json(["prm", "add_to_q", ["queues"], {"site": site, "proxies": proxies}])
        resp = socket.recv_json()
        socket.close()
        return HttpResponse(resp)


def ajax_pause_or_resume_worker(request):
    if request.method == "POST" and request.is_ajax():
        site = request.POST['ajaxarg_site']
        pid = request.POST['ajaxarg_pid']
        action = request.POST['ajaxarg_action'].split('_')[0]
        socket = create_zmq_connection("127.0.0.1", "5553", zmq.REQ)
        socket.send_json(["prm", "pause_or_resume_worker", ["processes"], {"site": site, "pid": pid, 'action': action}])
        resp = socket.recv_json()
        socket.close()
        return HttpResponse(resp)


def ajax_get_preQs_status(request):
    if request.method == "POST" and request.is_ajax():
        socket = create_zmq_connection("127.0.0.1", "5553", zmq.REQ)
        socket.send_json(["prm", "get_Qs_status", ["queues"], {}])
        resp = socket.recv_json()
        socket.close()
        data = []
        for site in resp:
            data.append("<div id='%s-queue' class='enjoy-css3'>" % site)
            data.append("<p>%s queues</p>" % site)
            data.append("<ul>")
            for proxy in resp[site]:
                data.append("<li>%s</li>" % proxy)
            data.append("</ul>")
            data.append("</div>")
        return HttpResponse(data)


def ajax_get_default_num_workers(request):
    try:
        if request.method =="POST" and request.is_ajax():
            socket = create_zmq_connection("127.0.0.1", "5553", zmq.REQ)
            socket.send_json(["prm", "get_default_num_workers", [], {}])
            resp = socket.recv_json()
            socket.close()
            data = []
            for site in resp:
                data.append("<div class='enjoy-css4'>")
                data.append("<p>%s: <input type='text' name='numOfWorkers' data-siteName='%s' value='%s'/></p>" % (site, site, resp[site]))
                data.append("</div>")
            return HttpResponse(data)
    except Exception:
        return HttpResponseServerError(resp)


def ajax_start_workers_for_release(request):
    try:
        if request.method == "POST" and request.is_ajax():
            numOfWorkers = json.loads(request.POST['ajaxarg_numOfWorkers'])
            socket = create_zmq_connection("127.0.0.1", "5553", zmq.REQ)
            socket.send_json(["prm", "start_workers_for_release", ["processes", "queues", "r", "processes_lock"],
                                                                                    {'numOfWorkers': numOfWorkers}])
            resp = socket.recv_json()
            socket.close()
            return HttpResponse(json.dumps(resp))
    except Exception:
        return HttpResponseServerError(resp)


