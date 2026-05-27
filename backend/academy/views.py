

from django.utils import timezone
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.response import Response
import mercadopago
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny



from rest_framework.views import APIView

from .models import PrimeraConsultaLead
from .serializers import PrimeraConsultaLeadSerializer


class PrimeraConsultaLeadView(APIView):

    def post(self, request):
        serializer = PrimeraConsultaLeadSerializer(data=request.data)

        if serializer.is_valid():
            lead = serializer.save()

            send_mail(
                subject="Nueva primera consulta organizada - Aula Psicontacto",
                message=f"""
Se recibió una nueva primera consulta.

Nombre:
{lead.nombre}

Motivo:
{lead.motivo}

Desde cuándo:
{lead.desde_cuando}

Manifestación:
{lead.manifestacion}

Expectativa:
{lead.expectativa}

Modalidad:
{lead.modalidad}

Disponibilidad:
{lead.disponibilidad}

Resumen:
{lead.resumen_generado}
""",
                from_email=None,
                recipient_list=["info@psicontacto.ar"],
                fail_silently=False,
            )

            return Response(
                {
                    "ok": True,
                    "mensaje": "Consulta recibida correctamente"
                },
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class PrimeraConsultaLeadListView(APIView):

    def get(self, request):
        leads = PrimeraConsultaLead.objects.all().order_by("-creado_en")
        serializer = PrimeraConsultaLeadSerializer(leads, many=True)
        return Response(serializer.data)
    
class PrimeraConsultaAsignarView(APIView):

    def post(self, request, lead_id):
        try:
            lead = PrimeraConsultaLead.objects.get(id=lead_id)
        except PrimeraConsultaLead.DoesNotExist:
            return Response(
                {"ok": False, "error": "Consulta no encontrada"},
                status=status.HTTP_404_NOT_FOUND
            )

        profesional = request.data.get(
            "profesional_asignado",
            None
        )

        estado = request.data.get(
            "estado",
            None
        )

        if profesional is not None:

            profesional = profesional.strip()

            if profesional:
                lead.profesional_asignado = profesional
                lead.fecha_asignacion = timezone.now()

        if estado:
            lead.estado = estado.strip()

        lead.save()

        serializer = PrimeraConsultaLeadSerializer(lead)

        return Response(
            {
                "ok": True,
                "mensaje": "Consulta asignada correctamente",
                "lead": serializer.data
            },
            status=status.HTTP_200_OK
        )
    
@api_view(["POST"])
@permission_classes([AllowAny])
def crear_pago_ebook_ansiedad(request):

    sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)

    preference_data = {
    "items": [
        {
            "title": "E-Book Curso de Ansiedad - Psicontacto Academy",
            "quantity": 1,
            "currency_id": "ARS",
            "unit_price": 100,
        }
    ],

    "back_urls": {
        "success": "http://127.0.0.1:5500/aula_ansiedad_exito.html",
        "failure": "http://127.0.0.1:5500/cursos/curso_ansiedad.html",
        "pending": "http://127.0.0.1:5500/cursos/curso_ansiedad.html",
    }
}

    preference_response = sdk.preference().create(preference_data)

    return Response({
    "status": preference_response.get("status"),
    "response": preference_response.get("response"),
    "init_point": preference_response.get("response", {}).get("init_point")
})