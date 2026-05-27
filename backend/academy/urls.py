from django.urls import path
from .views import PrimeraConsultaLeadView, PrimeraConsultaLeadListView, PrimeraConsultaAsignarView
urlpatterns = [
    path(
        "primera-consulta/",
        PrimeraConsultaLeadView.as_view(),
        name="primera-consulta"
    ),
    path(
    "primera-consulta/listado/",
    PrimeraConsultaLeadListView.as_view(),
    name="primera-consulta-listado"
),

    path(
        "primera-consulta/<int:lead_id>/asignar/",
        PrimeraConsultaAsignarView.as_view(),
        name="primera-consulta-asignar"
),
]