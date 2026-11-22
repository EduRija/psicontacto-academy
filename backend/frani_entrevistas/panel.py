"""Panel privado de solo lectura de entrevistas de Frani; sin ORM ni migraciones."""
import csv
import io
import json
import logging
import os
import uuid
from datetime import timedelta
from hmac import compare_digest

from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.core import signing
from django.core.cache import cache
from django.db import connections, DatabaseError
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

log = logging.getLogger(__name__)
COOKIE = 'frani_panel_sesion'
SALT = 'frani-panel-v1'
SESSION_SECONDS = 8 * 3600
TEST_IDS = {
    'a0144148-4357-47bd-a201-79612a43f93e',
    '49cffc57-d95a-4194-a950-d381e1855267',
    '4120a98b-43f9-49da-8b3f-280363091941',
}
QUESTIONS = [
    '¿Cuáles son los tres problemas administrativos más frecuentes que observás en las empresas que asesorás?',
    '¿Qué consecuencias generan esos problemas para el funcionamiento de las empresas?',
    '¿Cómo registran habitualmente las empresas sus ventas, compras, pagos, cobranzas y movimientos de mercadería?',
    '¿Qué herramientas utilizan actualmente para administrar sus negocios? (Excel, software de gestión, registros manuales u otros).',
    '¿Qué información necesitan habitualmente los empresarios y no logran obtener de manera rápida o confiable?',
    '¿Qué tareas administrativas demandan demasiado tiempo o generan errores frecuentes?',
    '¿Cuáles son las principales dificultades para obtener de tus clientes la documentación e información necesaria para el trabajo contable?',
    'Si pudieras resolver inicialmente un solo problema mediante inteligencia artificial, ¿cuál elegirías y por qué?',
    '¿Contás con alguna empresa que consideres adecuada para probar una solución? ¿A qué actividad se dedica y qué características tiene? No es necesario identificarla.',
    '¿Qué mejoras concretas deberían observarse para considerar exitosa una experiencia piloto de 30 días?',
]


def _authenticated(request):
    cookie = request.COOKIES.get(COOKIE, '')
    if not cookie:
        return False
    try:
        return signing.loads(cookie, salt=SALT, max_age=SESSION_SECONDS) == 'frani-panel-admin-v1'
    except signing.BadSignature:
        return False


def _private(response):
    response['Cache-Control'] = 'no-store, no-cache, max-age=0, private'
    response['Pragma'] = 'no-cache'
    response['X-Robots-Tag'] = 'noindex, nofollow, noarchive'
    return response


def _get_rows():
    with connections['frani'].cursor() as cur:
        cur.execute('''SELECT e.envio_id, i.etiqueta, e.recibido_en, e.estado
                       FROM frani_piloto.entrevistas e
                       JOIN frani_piloto.invitaciones i ON i.id=e.invitacion_id
                       ORDER BY e.recibido_en DESC LIMIT 200''')
        rows = cur.fetchall()
    return [{'id': str(r[0]), 'etiqueta': r[1], 'fecha': timezone.localtime(r[2]),
             'estado': r[3], 'prueba': str(r[0]) in TEST_IDS} for r in rows]


def _get_one(interview_id):
    with connections['frani'].cursor() as cur:
        cur.execute('''SELECT e.envio_id, i.etiqueta, e.recibido_en, e.estado, e.respuestas
                       FROM frani_piloto.entrevistas e
                       JOIN frani_piloto.invitaciones i ON i.id=e.invitacion_id
                       WHERE e.envio_id=%s''', [str(interview_id)])
        row = cur.fetchone()
    if not row:
        return None
    answers = json.loads(row[4]) if isinstance(row[4], str) else row[4]
    return {'id': str(row[0]), 'etiqueta': row[1], 'fecha': timezone.localtime(row[2]),
            'estado': row[3], 'prueba': str(row[0]) in TEST_IDS,
            'items': list(zip(QUESTIONS, answers))}


@never_cache
@csrf_protect
def panel_login(request):
    if not os.environ.get('FRANI_PANEL_PASSWORD_HASH'):
        return _private(HttpResponse('Panel no configurado.', status=503))
    if _authenticated(request):
        return redirect('frani-panel-lista')
    error = ''
    if request.method == 'POST':
        # Limita intentos en cada proceso. En despliegues multinodo se requiere límite compartido.
        client = request.META.get('REMOTE_ADDR', 'unknown')
        import hashlib
        key = 'frani-login-' + hashlib.sha256(client.encode()).hexdigest()
        count = cache.get(key, 0)
        if count >= 5:
            error = 'Demasiados intentos. Volvé a intentar dentro de 15 minutos.'
        else:
            password = request.POST.get('password', '')
            valid = len(password) <= 512 and check_password(password, os.environ['FRANI_PANEL_PASSWORD_HASH'])
            if valid:
                cache.delete(key)
                response = redirect('frani-panel-lista')
                response.set_cookie(COOKIE, signing.dumps('frani-panel-admin-v1', salt=SALT),
                                    max_age=SESSION_SECONDS, secure=not settings.DEBUG,
                                    httponly=True, samesite='Strict', path='/api/frani/panel/')
                return _private(response)
            cache.set(key, count + 1, timeout=900)
            error = 'Clave incorrecta.'
    elif request.method != 'GET':
        return HttpResponseNotAllowed(['GET', 'POST'])
    return _private(render(request, 'frani_entrevistas/panel.html', {'page': 'login', 'error': error}))


@never_cache
@csrf_protect
def panel_logout(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    response = redirect('frani-panel-login')
    response.delete_cookie(COOKIE, path='/api/frani/panel/', samesite='Strict')
    return _private(response)


@never_cache
def panel_list(request):
    if not _authenticated(request):
        return redirect('frani-panel-login')
    try:
        rows = _get_rows()
    except (DatabaseError, KeyError):
        log.exception('Error leyendo entrevistas Frani')
        return _private(HttpResponse('No se pudo consultar la base de entrevistas.', status=503))
    return _private(render(request, 'frani_entrevistas/panel.html', {'page': 'list', 'rows': rows}))


@never_cache
def panel_detail(request, interview_id):
    if not _authenticated(request):
        return redirect('frani-panel-login')
    try:
        item = _get_one(interview_id)
    except (DatabaseError, KeyError):
        log.exception('Error leyendo entrevista Frani')
        return _private(HttpResponse('No se pudo consultar la entrevista.', status=503))
    if item is None:
        return _private(HttpResponse('Entrevista no encontrada.', status=404))
    if request.GET.get('descargar') == 'txt':
        content = '\n'.join([
            'FRANI | ENTREVISTA', f"Referencia: {item['etiqueta']}",
            f"ID: {item['id']}", f"Fecha: {item['fecha'].strftime('%d/%m/%Y %H:%M')}",
            f"Tipo: {'PRUEBA' if item['prueba'] else 'SIN CLASIFICAR'}", '',
            *[f'{n}. {q}\n{a}\n' for n, (q, a) in enumerate(item['items'], 1)]
        ])
        response = HttpResponse(content, content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="frani_entrevista_{item["id"]}.txt"'
        return _private(response)
    return _private(render(request, 'frani_entrevistas/panel.html', {'page': 'detail', 'item': item}))
