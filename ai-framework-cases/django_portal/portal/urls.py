from django.contrib import admin
from django.urls import path
from knowledge import views

urlpatterns = [path("admin/", admin.site.urls), path("demo/", views.demo), path("ask", views.ask)]
