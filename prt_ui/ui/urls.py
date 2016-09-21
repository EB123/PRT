from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^ajax_create_process$', views.ajax_create_process, name='ajax_create_process'),
    url(r'^ajax_auto_reload', views.ajax_auto_reload, name='ajax_auto_reload'),
    url(r'^ajax_add_to_queue', views.ajax_add_to_queue, name='ajax_add_to_queue'),
    url(r'^ajax_pause_or_resume_worker', views.ajax_pause_or_resume_worker, name='ajax_pause_or_resume_worker'),
    url(r'^ajax_get_preQs_status', views.ajax_get_preQs_status, name='ajax_get_preQs_status'),
    url(r'^ajax_get_default_num_workers', views.ajax_get_default_num_workers, name='ajax_get_default_num_workers'),
    url(r'^ajax_start_workers_for_release', views.ajax_start_workers_for_release,
                                            name='ajax_start_workers_for_release'),
    url(r'^ajax_get_config', views.ajax_get_config, name='ajax_get_config'),
    url(r'^ajax_update_config', views.ajax_update_config, name='ajax_update_config'),
    url(r'^ajax_show_eventlog', views.ajax_show_eventlog, name='ajax_show_eventlog'),
]
