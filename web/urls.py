from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("plan/", views.ver_plan, name="plan"),
]
