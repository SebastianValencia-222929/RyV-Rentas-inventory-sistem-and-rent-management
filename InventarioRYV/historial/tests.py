"""
Pruebas unitarias para la app historial.
Cubre la lógica de filtrado de las vistas historial_lista
e historial_detalle.
"""
import pytest
from datetime import date, timedelta
from django.urls import reverse


# ─── Fixtures auxiliares ─────────────────────────────────────────

@pytest.fixture
def renta_finalizada(db, equipo, cliente, usuario_empleado):
    from rentas.models import Renta
    return Renta.objects.create(
        equipo=equipo, cliente=cliente, registrada_por=usuario_empleado,
        fecha_inicio=date.today() - timedelta(days=10),
        fecha_vencimiento=date.today() - timedelta(days=3),
        fecha_devolucion=date.today() - timedelta(days=3),
        precio='400.00', cantidad=1, estado='finalizada',
    )


@pytest.fixture
def renta_vencida(db, equipo, cliente, usuario_empleado):
    from inventario.models import Equipo
    equipo2 = Equipo.objects.create(
        nombre='Cortadora', cantidad_total=2,
    )
    from rentas.models import Renta
    return Renta.objects.create(
        equipo=equipo2, cliente=cliente, registrada_por=usuario_empleado,
        fecha_inicio=date.today() - timedelta(days=15),
        fecha_vencimiento=date.today() - timedelta(days=5),
        precio='300.00', cantidad=1, estado='vencida',
    )


# ─── Vista historial_lista ────────────────────────────────────────

class TestHistorialLista:

    def test_anonimo_redirige_al_login(self, client):
        url = reverse('historial:lista')
        respuesta = client.get(url)
        assert respuesta.status_code == 302
        assert '/login' in respuesta['Location']

    def test_usuario_autenticado_puede_acceder(self, client, usuario_empleado):
        client.force_login(usuario_empleado)
        url = reverse('historial:lista')
        respuesta = client.get(url)
        assert respuesta.status_code == 200

    def test_excluye_rentas_activas(self, client, usuario_empleado, renta_activa, renta_finalizada):
        client.force_login(usuario_empleado)
        url = reverse('historial:lista')
        respuesta = client.get(url)
        ids_en_contexto = [r.pk for r in respuesta.context['rentas']]
        assert renta_finalizada.pk in ids_en_contexto
        assert renta_activa.pk not in ids_en_contexto

    def test_filtro_por_estado_finalizada(self, client, usuario_empleado, renta_finalizada, renta_vencida):
        client.force_login(usuario_empleado)
        url = reverse('historial:lista')
        respuesta = client.get(url, {'estado': 'finalizada'})
        ids = [r.pk for r in respuesta.context['rentas']]
        assert renta_finalizada.pk in ids
        assert renta_vencida.pk not in ids

    def test_filtro_por_cliente_nombre(self, client, usuario_empleado, renta_finalizada):
        client.force_login(usuario_empleado)
        url = reverse('historial:lista')
        respuesta = client.get(url, {'cliente': 'Juan'})
        ids = [r.pk for r in respuesta.context['rentas']]
        assert renta_finalizada.pk in ids

    def test_filtro_por_cliente_inexistente_retorna_vacio(self, client, usuario_empleado, renta_finalizada):
        client.force_login(usuario_empleado)
        url = reverse('historial:lista')
        respuesta = client.get(url, {'cliente': 'XYZ_INEXISTENTE'})
        assert respuesta.context['rentas'].paginator.count == 0


# ─── Vista historial_detalle ──────────────────────────────────────

class TestHistorialDetalle:

    def test_anonimo_redirige_al_login(self, client, renta_finalizada):
        url = reverse('historial:detalle', kwargs={'pk': renta_finalizada.pk})
        respuesta = client.get(url)
        assert respuesta.status_code == 302

    def test_usuario_autenticado_ve_detalle(self, client, usuario_empleado, renta_finalizada):
        client.force_login(usuario_empleado)
        url = reverse('historial:detalle', kwargs={'pk': renta_finalizada.pk})
        respuesta = client.get(url)
        assert respuesta.status_code == 200
        assert respuesta.context['renta'].pk == renta_finalizada.pk

    def test_pk_inexistente_retorna_404(self, client, usuario_empleado):
        client.force_login(usuario_empleado)
        url = reverse('historial:detalle', kwargs={'pk': 99999})
        respuesta = client.get(url)
        assert respuesta.status_code == 404
