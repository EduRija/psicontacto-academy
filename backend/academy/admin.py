from django.contrib import admin
from .models import PrimeraConsultaLead
from .models import ProfesionalPrimeraConsulta


@admin.register(PrimeraConsultaLead)
class PrimeraConsultaLeadAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "nombre",
        "modalidad",
        "estado",
        "creado_en",
    )

    search_fields = (
        "nombre",
        "motivo",
    )

    list_filter = (
        "modalidad",
        "estado",
    )

@admin.register(ProfesionalPrimeraConsulta)
class ProfesionalPrimeraConsultaAdmin(admin.ModelAdmin):

    list_display = (
        "nombre",
        "especialidad",
        "email",
        "activo",
    )

    search_fields = (
        "nombre",
        "especialidad",
    )