# urls.py

from django.urls import path
from . import views

app_name = "photos"

urlpatterns = [
    # path("", views.main, name="main"),
    path("", views.main, name="index"),
    path("main", views.main, name="main"),
    path("upload", views.upload_file, name="upload"),
    path("scan_qr", views.scan_qr, name="scan_qr"),
]
