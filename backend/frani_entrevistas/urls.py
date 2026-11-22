from django.urls import path
from .views import recibir_entrevista

urlpatterns = [path("entrevistas/", recibir_entrevista, name="frani-recibir-entrevista")]
