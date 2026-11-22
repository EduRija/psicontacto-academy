"""Recepción piloto; no utiliza ORM ni migraciones de Academy/ISC."""
import hashlib
import json
import logging
import uuid

from django.db import connections, DatabaseError, transaction
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

log = logging.getLogger(__name__)
MAX_BODY = 35000
MAX_ANSWER = 6000


# Contador persistente por token, independiente de la transacción de entrevista.
# No sustituye la protección por IP en el proxy contra tokens aleatorios.
def _limitar_token_frani(digest):
    with transaction.atomic(using="frani"):
        with connections["frani"].cursor() as cur:
            # Serializa los intentos del mismo token incluso con varias instancias.
            cur.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                ["frani-rate:" + digest],
            )
            cur.execute(
                """INSERT INTO frani_piloto.intentos (token_sha256, ventana_inicio, cantidad)
                   VALUES (%s, NOW(), 1)
                   ON CONFLICT (token_sha256) DO UPDATE SET
                     ventana_inicio = CASE
                       WHEN frani_piloto.intentos.ventana_inicio <= NOW() - INTERVAL '15 minutes'
                       THEN NOW() ELSE frani_piloto.intentos.ventana_inicio END,
                     cantidad = CASE
                       WHEN frani_piloto.intentos.ventana_inicio <= NOW() - INTERVAL '15 minutes'
                       THEN 1 ELSE frani_piloto.intentos.cantidad + 1 END
                   RETURNING cantidad""",
                [digest],
            )
            return cur.fetchone()[0] <= 10


@csrf_exempt
@require_POST
def recibir_entrevista(request):
    # Token de invitación: control de acceso limitado, no autenticación personal.
    if len(request.body) > MAX_BODY:
        return JsonResponse({"error": "Solicitud demasiado extensa"}, status=413)
    try:
        data = json.loads(request.body)
        if not isinstance(data, dict):
            raise ValueError("Datos inválidos")
        token = data.get("invitacion", "")
        if not isinstance(token, str) or not (32 <= len(token) <= 200):
            raise ValueError("Invitación inválida")
        submission_id = uuid.UUID(data.get("envio_id", ""))
        respuestas = data.get("respuestas")
        if not isinstance(respuestas, list) or len(respuestas) != 10 or not all(
            isinstance(r, str) and 0 < len(r.strip()) and len(r) <= MAX_ANSWER
            for r in respuestas
        ):
            raise ValueError("Se requieren diez respuestas de texto no vacías")
        if data.get("consentimiento") is not True:
            raise ValueError("Falta el consentimiento")
        if data.get("acepta_envio") is not True:
            raise ValueError("Falta la confirmación de envío")
    except (ValueError, TypeError, json.JSONDecodeError, AttributeError) as exc:
        return JsonResponse({"error": str(exc) or "Datos inválidos"}, status=400)

    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    respuestas_json = json.dumps(respuestas, ensure_ascii=False)
    # El contador se confirma antes de intentar guardar la entrevista.
    # Los errores de BD se traducen a 503 sin permitir solicitudes ilimitadas.
    try:
        permitido = _limitar_token_frani(digest)
    except DatabaseError:
        log.exception("Fallo del control de solicitudes de Frani")
        return JsonResponse({"error": "Servicio temporalmente no disponible"}, status=503)
    if not permitido:
        response = JsonResponse(
            {"error": "Demasiados intentos. Volvé a intentar en unos minutos."},
            status=429,
        )
        response["Retry-After"] = "900"
        return response
    try:
        # No FOR UPDATE: el usuario de Frani tiene SELECT sobre invitaciones.
        # La PK de envio_id protege los reintentos concurrentes.
        with transaction.atomic(using="frani"):
            with connections["frani"].cursor() as cur:
                cur.execute(
                    """SELECT id FROM frani_piloto.invitaciones
                       WHERE token_sha256 = %s AND activa = TRUE
                         AND (vence_en IS NULL OR vence_en > NOW())""",
                    [digest],
                )
                invite = cur.fetchone()
                if invite is None:
                    result = ({"error": "Invitación no válida o vencida"}, 403)
                else:
                    cur.execute(
                        """INSERT INTO frani_piloto.entrevistas
                           (envio_id, invitacion_id, respuestas, consentimiento_en, estado)
                           VALUES (%s, %s, %s::jsonb, NOW(), 'recibida')
                           ON CONFLICT (envio_id) DO NOTHING
                           RETURNING envio_id""",
                        [str(submission_id), invite[0], respuestas_json],
                    )
                    inserted = cur.fetchone() is not None
                    if inserted:
                        result = ({"recibida": True, "envio_id": str(submission_id), "duplicada": False}, 201)
                    else:
                        cur.execute(
                            """SELECT invitacion_id, respuestas FROM frani_piloto.entrevistas
                               WHERE envio_id = %s""",
                            [str(submission_id)],
                        )
                        existing = cur.fetchone()
                        if not existing or existing[0] != invite[0] or (json.loads(existing[1]) if isinstance(existing[1], str) else existing[1]) != respuestas:
                            result = ({"error": "Identificador ya utilizado con otros datos"}, 409)
                        else:
                            result = ({"recibida": True, "envio_id": str(submission_id), "duplicada": True}, 200)
        # Solo confirmar recepción después de que atomic haya completado COMMIT.
        return JsonResponse(result[0], status=result[1])
    except (DatabaseError, KeyError):
        log.exception("No se pudo registrar entrevista de Frani")
        return JsonResponse({"error": "No pudimos confirmar la recepción. Intentá nuevamente."}, status=503)
