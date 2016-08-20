from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^ajax_create_process$', views.ajax_create_process, name='ajax_create_process'),
    url(r'^auto_reload', views.auto_reload, name='auto_reload'),
]
