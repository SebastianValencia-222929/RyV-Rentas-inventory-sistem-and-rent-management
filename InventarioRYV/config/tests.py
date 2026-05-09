"""
Pruebas unitarias para config/context_processors.py.
Cubre la función alertas_globales que inyecta alertas de vencimiento
y conteo de solicitudes pendientes en el contexto global.
"""
import pytest
from datetime import date, timedelta
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser


# ─── alertas_globales ─────────────────────────────────────────────

class TestAlertasGlobales:

    def _request(self, user):
        factory = RequestFactory()
        req = factory.get('/')
        req.user = user
        return req

    def test_usuario_anonimo_retorna_dict_vacio(self):
        from config.context_processors import alertas_globales
        req = self._request(AnonymousUser())
        ctx = alertas_globales(req)
        assert ctx == {}

    def test_admin_ve_solicitudes_pendientes(self, db, usuario_admin, usuario_empleado):
        from solicitudes.models import Solicitud
        from config.context_processors import alertas_globales

        Solicitud.objects.create(
            tipo='alta_equipo',
            solicitante=usuario_empleado,
            comentario='test',
            datos_json={},
        )
        ctx = alertas_globales(self._request(usuario_admin))
        assert ctx['solicitudes_pendientes'] == 1

    def test_empleado_no_ve_solicitudes_de_otros(self, db, usuario_empleado, usuario_admin):
        from solicitudes.models import Solicitud
        from config.context_processors import alertas_globales

        Solicitud.objects.create(
            tipo='alta_equipo',
            solicitante=usuario_admin,
            comentario='test',
            datos_json={},
        )
        ctx = alertas_globales(self._request(usuario_empleado))
        assert ctx['solicitudes_pendientes'] == 0

    def test_empleado_ve_sus_propias_solicitudes(self, db, usuario_empleado):
        from solicitudes.models import Solicitud
        from config.context_processors import alertas_globales

        Solicitud.objects.create(
            tipo='alta_equipo',
            solicitante=usuario_empleado,
            comentario='test',
            datos_json={},
        )
        ctx = alertas_globales(self._request(usuario_empleado))
        assert ctx['mis_solicitudes_pendientes'] == 1

    def test_detecta_rentas_proximas_a_vencer(self, db, renta_activa, usuario_empleado):
        from config.context_processors import alertas_globales

        renta_activa.fecha_vencimiento = date.today() + timedelta(days=2)
        renta_activa.save()
        ctx = alertas_globales(self._request(usuario_empleado))
        ids_proximas = [r.pk for r in ctx['alertas_proximas']]
        assert renta_activa.pk in ids_proximas

    def test_detecta_rentas_vencidas_sin_cerrar(self, db, renta_activa, usuario_empleado):
        from config.context_processors import alertas_globales

        renta_activa.fecha_vencimiento = date.today() - timedelta(days=1)
        renta_activa.save()
        ctx = alertas_globales(self._request(usuario_empleado))
        ids_vencidas = [r.pk for r in ctx['alertas_vencidas']]
        assert renta_activa.pk in ids_vencidas

    def test_total_alertas_admin_incluye_solicitudes(self, db, usuario_admin, usuario_empleado, renta_activa):
        from solicitudes.models import Solicitud
        from config.context_processors import alertas_globales

        renta_activa.fecha_vencimiento = date.today() + timedelta(days=1)
        renta_activa.save()
        Solicitud.objects.create(
            tipo='baja_equipo',
            solicitante=usuario_empleado,
            comentario='test',
            datos_json={},
        )
        ctx = alertas_globales(self._request(usuario_admin))
        # 1 renta próxima + 0 vencidas + 1 solicitud pendiente = 2
        assert ctx['total_alertas'] == 2

    def test_no_incluye_rentas_finalizadas_en_alertas(self, db, usuario_empleado, equipo, cliente):
        from rentas.models import Renta
        from config.context_processors import alertas_globales

        Renta.objects.create(
            equipo=equipo, cliente=cliente, registrada_por=usuario_empleado,
            fecha_inicio=date.today() - timedelta(days=10),
            fecha_vencimiento=date.today() - timedelta(days=5),
            precio='200.00', cantidad=1, estado='finalizada',
        )
        ctx = alertas_globales(self._request(usuario_empleado))
        assert len(ctx['alertas_vencidas']) == 0
