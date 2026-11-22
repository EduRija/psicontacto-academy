import json
from django.test import SimpleTestCase, RequestFactory
from .views import recibir_entrevista

class ValidacionTest(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_sin_consentimiento(self):
        data = {"invitacion": "a" * 40, "envio_id": "d0183c49-b3f4-4c3e-89a8-3c89bdac1122", "respuestas": ["ok"] * 10, "consentimiento": False, "acepta_envio": True}
        response = recibir_entrevista(self.factory.post("/api/frani/entrevistas/", data=json.dumps(data), content_type="application/json"))
        self.assertEqual(response.status_code, 400)

    def test_respuestas_incompletas(self):
        data = {"invitacion": "a" * 40, "envio_id": "d0183c49-b3f4-4c3e-89a8-3c89bdac1122", "respuestas": ["ok"] * 9, "consentimiento": True, "acepta_envio": True}
        response = recibir_entrevista(self.factory.post("/api/frani/entrevistas/", data=json.dumps(data), content_type="application/json"))
        self.assertEqual(response.status_code, 400)
