from django.contrib import admin
from django.urls import path, include
from academy.views import crear_pago_ebook_ansiedad

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/academy/", include("academy.urls")),
    path("api/pagos/ebook-ansiedad/", crear_pago_ebook_ansiedad),
]