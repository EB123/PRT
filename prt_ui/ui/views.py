from django.shortcuts import render
import zmq
from django.http import  HttpResponse, HttpResponseServerError
import json
import time

#address = "127.0.0.1"
#port = "4141"


def create_zmq_connection(address, port, socket_type): # TODO - should be taken from prt_utils
    context = zmq.Context()
    socket = context.socket(socket_type)
    socket.connect("tcp://%s:%s" % (address, port))
    return socket


def index(request):
    socket = create_zmq_connection("127.0.0.1", "5553", zmq.REQ)
    #socket.send_json(["prm", "active_proxy_workers", ["processes"], {}])
    socket.send_json(["mon", "active_proxy_workers", ["r1", "r12", "servers"], {}])
    resp = socket.recv_json()
    context = {'active_workers': resp}
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
    socket.send_json(["mon", "active_proxy_workers", ["r1", "r12", "servers"], {}])
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
        data.append("<table>")
        if resp[site]['workers']:
            data.append("<tr>")
            data.append("<th>Worker ID</th>")
            data.append("<th>Status</th>")
            data.append("<th>Working On</th>")
            data.append("<th>Step</th>")
            data.append("</tr>")
            for pid in resp[site]['workers']:
                data.append("<tr>")
                proc_hash = resp[site]['workers'][pid]
                data.append("<td>%s</td>" % pid)
                data.append("<td>%s</td>" % proc_hash['status'])
                data.append("<td>%s</td>" % proc_hash['working_on'])
                data.append("<td>%s</td>" % proc_hash['step'])
                data.append("<td>")
                data.append("<button  style='margin-right:4px; margin-left:6px' id='%s-start' value='%s' data-pressed='%s' class='resume_worker'>&#9658;</button>" % (pid, pid, proc_hash['status']))
                data.append("<button  style='margin-top:0;margin-right:4px' id='%s-pause' value='%s' data-pressed='%s' class='pause_worker'>&#9646;&#9646;</button>" % (pid, pid, proc_hash['status']))
                data.append("<button  style='margin-top:0' id='%s-stop' value='%s' class='stop_worker'>&#9609;</button></td>" % (pid, pid))
                data.append("</tr>")
        data.append("</table>")
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


def ajax_get_config(request):
    try:
        if request.method == "POST" and request.is_ajax():
            socket = create_zmq_connection("127.0.0.1", "5553", zmq.REQ)
            socket.send_json(["prm", "get_config", ["r13"], {}])
            resp = socket.recv_json()
            socket.close()
            data = []
            sorted_keys = resp.keys()
            sorted_keys.sort()
            for key in sorted_keys:
                data.append("<div class='enjoy-css4'>")
                data.append("<p>%s: <input type='text' name='configs' data-confName='%s' value='%s'/></p>" % (
                                                                                                key, key, resp[key]))
                data.append("</div>")
            return HttpResponse(data)
    except Exception:
        return HttpResponseServerError(resp)


def ajax_update_config(request):
    try:
        if request.method == "POST" and request.is_ajax():
            configs = json.loads(request.POST['ajaxarg_configs'])
            socket = create_zmq_connection("127.0.0.1", "5553", zmq.REQ)
            socket.send_json(["prm", "update_config", ["r13"], {'configs': configs}])
            resp = socket.recv_json()
            socket.close()
            return HttpResponse(json.dumps(resp))
    except Exception:
        return HttpResponseServerError(resp)


def ajax_show_eventlog(request):
    try:
        if request.method == "POST" and request.is_ajax():
            socket = create_zmq_connection("127.0.0.1", "5553", zmq.REQ)
            socket.send_json(["mon", "get_eventlog", ["r14"], {}])
            resp = socket.recv_json()
            socket.close()
            data = []
            keys = ['Proxy', 'Start Time', 'Finish Time', 'Status', 'Old Version', 'New Version']
            data.append("<table>")
            data.append("<div id='search_list'>")
            data.append("<tr>")
            data.append("<th>Event</th>")
            """
            data.append("<th>Proxy</th>")
            data.append("<th>Start Time</th>")
            data.append("<th>Finish Time</th>")
            data.append("<th>Version</th>")
            data.append("<th>Status</th>")
            """
            for key in keys:
                data.append("<th>%s</th>" % key)
            data.append("</tr>")
            for event in resp:
                data.append("<tr>")
                data.append("<td>%s</td>" % event[0])
                for key in keys:
                    try:
                        data.append("<td>%s</td>" % event[1][key])
                    except KeyError:
                        data.append("<td>-</td>")
                data.append("</tr>")
            data.append("</div>")
            data.append("</table>")
            return HttpResponse(data)
    except Exception as e:
        return HttpResponseServerError(e)