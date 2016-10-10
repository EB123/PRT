from django.shortcuts import render
import zmq
from django.http import  HttpResponse, HttpResponseServerError
import json
import time
import sys
import traceback

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
    socket.send_json(["mon", "active_proxy_workers", ["r1", "r12", "servers", "time_values"], {}])
    resp = socket.recv_json()
    context = {'active_workers': resp}
    return render(request, "ui/index.html", context)


def ajax_create_process(request):
    if request.method == "POST" and request.is_ajax():
        site = request.POST['ajaxarg_site']
        socket = create_zmq_connection("127.0.0.1", "5553", zmq.REQ)
        socket.send_json(["prm", "create_process", ["processes", "queues", "r", "processes_lock", "r13"], {"site": site}])
        resp = socket.recv_json()
        #data = auto_reload(socket)
        socket.close()
        context = {}# TODO - Add custom headers to response
        return HttpResponse(resp)

def ajax_auto_reload(request): # TODO - this func should be called from ajax_create_process and not from jquery
    socket = create_zmq_connection("127.0.0.1", "5553", zmq.REQ)
    #socket.send_json(["prm", "active_proxy_workers", ["processes"], {}])
    socket.send_json(["mon", "active_proxy_workers", ["r1", "r12", "servers", "time_values"], {}])
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
                proc_hash = resp[site]['workers'][pid]
                if proc_hash['is_stuck'] == 'error':
                    data.append("<tr class='tr-alert'>")
                elif proc_hash['is_stuck'] == 'warning':
                    data.append("<tr class='tr-warning'>")
                else:
                    data.append("<tr>")
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
            socket.send_json(["prm", "start_workers_for_release", ["processes", "queues", "r", "processes_lock", "r13"],
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
            config = resp[0]
            time_values = resp[1]
            workers_config = resp[2]
            data = []
            sorted_config_keys = config.keys()
            sorted_config_keys.sort()
            steps = time_values.keys()
            steps.sort()
            data.append("<div id='tabs'>")
            data.append("<ul>")
            data.append("<li><a href='#config'>General</a></li>")
            data.append("<li><a href='#time_values'>Time Values</a></li>")
            data.append("<li><a href='#workers_config_tabs'>Workers Config</a></li>")
            data.append("</ul>")

            ###### Config TAB ######
            data.append("<div id='config'>")
            for key in sorted_config_keys:
                data.append("<div class='enjoy-css5'>")
                if key != 'show_all_proxies':
                    data.append("<p>%s: <input type='text' name='configs' data-confName='config' data-keyName='%s' value='%s'/></p>" % (
                                                                                                key, key, config[key]))
                else:
                    if config[key] == 'True':
                        checked = 'checked'
                    else:
                        checked = ''
                    data.append("<p>%s: <input type='checkbox' name='configs' data-confName='config' data-keyName='%s' %s/></p>" % (
                                                                                                key, key, checked))
                data.append("</div>")
            data.append("</div>")
            ###### End Of Config TAB ######

            ###### Time Values TAB ######
            data.append("<div id='time_values'>")
            data.append("<h4>All values are in minutes</h4>")
            for step in steps:
                data.append("<div class='enjoy-css5'>")
                data.append("<h4>%s</h4>" % step)
                for level in time_values[step]:
                    data.append("<p>%s: <input type='text' name='configs' data-confName='time_values:%s' data-keyName='%s' value='%s'/></p>" % (
                        level, step, level, time_values[step][level]))
                data.append("</div>")
            data.append("</div>")
            ###### End Of Time Values TAB ######

            ###### Workers Config TAB ######
            data.append("<div id='workers_config_tabs'>")
            data.append("<ul>")
            data.append("<li><a href='#workers_config_main'>Main</a></li>")
            for site in workers_config.keys():
                if site != 'main':
                    data.append("<li><a href='#workers_config_%s'>%s</a></li>" % (site, site))
            data.append("</ul>")
            for site in workers_config.keys():
                select = {'default':'', 'restart':'', 'custom':''}
                try:
                    select[workers_config[site]['type']] = 'selected'
                except KeyError:
                    select['default'] = 'selected'
                try:
                    command = workers_config[site]['command']
                except KeyError:
                    command = "N/A"
                try:
                    if workers_config[site]['type'] == 'custom':
                        custom = ''
                    else:
                        custom = 'disabled'
                except KeyError:
                    custom = 'disabled'
                data.append("<div id='workers_config_%s'" % site)
                if site == 'main':
                    try:
                        if workers_config[site]['use_main'] == 'True':
                            checked = 'checked'
                        else:
                            checked = ''
                    except KeyError:
                        checked = ''
                    data.append("<br><input type='checkbox' name='configs' data-confName='workers_config:main' id='workers_config_use_main' %s>Use Same Config For All Sites<br>" % checked)
                data.append("<p>Worker Type: <select class='workers_config_select' name='workers_config_select' data-confName='workers_config:%s'>" % site)
                data.append("<option value='default' data-confName='workers_config:%s' data-keyName='type' data-oldval='%s' %s>Default (Release)</option>"
                                                                                                                        % (site, workers_config[site]['type'], select['default']))
                data.append("<option value='restart' data-confName='workers_config:%s' data-keyName='type' data-oldval='%s' %s>Restart</option>"
                                                                                                                        % (site, workers_config[site]['type'], select['restart']))
                data.append("<option value='custom' data-confName='workers_config:%s' data-keyName='type' data-oldval='%s' %s>Custom</option>"
                                                                                                                        % (site, workers_config[site]['type'], select['custom']))
                data.append("</select></p>")
                data.append("<p>Command: <input type='text' name='configs' %s data-confName='workers_config:%s' data-keyName='command' value='%s' /></p>"
                            % (custom, site, command))
                data.append("</div>")
            data.append("</div>")
            ###### End Of Workers Config TAB ######

            data.append("</div>")
            return HttpResponse(data)
    except Exception:
        return HttpResponseServerError(resp)


def ajax_update_config(request):
    try:
        if request.method == "POST" and request.is_ajax():
            configs = json.loads(request.POST['ajaxarg_configs'])
            socket = create_zmq_connection("127.0.0.1", "5553", zmq.REQ)
            socket.send_json(["prm", "update_config", ["r13", "processes"], {'configs': configs}])
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


def ajax_get_proxies(request):
    try:
        if request.method == "POST" and request.is_ajax():
            site = request.POST['site']
            socket = create_zmq_connection("127.0.0.1", "5553", zmq.REQ)
            socket.send_json(["mon", "get_proxies", ["r12", "r13"], {'site':site}])
            resp = socket.recv_json()
            socket.close()
            data = []
            print resp
            for site in resp[0]:
                data.append("<input type='checkbox' name='selectAll' class='selectAll' id='selectAll-%s' value='{{site}}'>Select All</input><br>" % site)
                proxies = resp[0][site].keys()
                proxies.sort()
                for proxy in proxies:
                    if resp[2] == 'True' or resp[0][site][proxy] != resp[1]:
                        data.append("<input type='checkbox' name='myCheckBoxes' id='myCheckBoxes-%s' class='myCheckBoxes' value='%s' data-version='%s'>%s</input><br>"
                                % (proxy, proxy, resp[0][site][proxy], proxy))
            return HttpResponse(data)
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print "*** print_exception:"
        traceback.print_exception(exc_type, exc_value, exc_traceback,
                                  limit=2, file=sys.stdout)
        return HttpResponseServerError(e)