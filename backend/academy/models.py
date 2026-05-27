from django.db import models


class PrimeraConsultaLead(models.Model):
    nombre = models.CharField(max_length=150, blank=True)
    contacto = models.CharField(max_length=180, blank=True) 
    motivo = models.TextField(blank=True)
    desde_cuando = models.TextField(blank=True)
    manifestacion = models.TextField(blank=True)
    expectativa = models.TextField(blank=True)
    modalidad = models.CharField(max_length=80, blank=True)
    disponibilidad = models.TextField(blank=True)
    resumen_generado = models.TextField(blank=True)

    profesional_destino = models.CharField(max_length=120, blank=True)
    profesional_asignado = models.CharField(max_length=180, blank=True)

    fecha_asignacion = models.DateTimeField(
        null=True,
        blank=True
    )

    estado = models.CharField(
        max_length=40,
        default="pendiente"
    )

    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Primera consulta - {self.nombre or 'Sin nombre'}"
    
class ProfesionalPrimeraConsulta(models.Model):

    nombre = models.CharField(max_length=180)

    especialidad = models.CharField(
        max_length=180,
        blank=True
    )

    email = models.EmailField()

    whatsapp = models.CharField(
        max_length=80,
        blank=True
    )

    activo = models.BooleanField(default=True)

    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre   
