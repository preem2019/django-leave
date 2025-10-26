# db_manager/urls.py

from django.urls import path
from . import views

app_name = 'db_manager'

urlpatterns = [
    path('', views.db_view, name='db_view'),
]