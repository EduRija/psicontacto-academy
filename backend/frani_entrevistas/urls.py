from django.urls import path
from .views import recibir_entrevista
from .panel import panel_login, panel_logout, panel_list, panel_detail

urlpatterns = [
    path('entrevistas/', recibir_entrevista, name='frani-recibir-entrevista'),
    path('panel/', panel_login, name='frani-panel-login'),
    path('panel/salir/', panel_logout, name='frani-panel-logout'),
    path('panel/entrevistas/', panel_list, name='frani-panel-lista'),
    path('panel/entrevistas/<uuid:interview_id>/', panel_detail, name='frani-panel-detalle'),
]
