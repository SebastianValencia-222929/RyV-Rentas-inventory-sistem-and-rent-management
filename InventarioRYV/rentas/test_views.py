"""
Pruebas para las vistas del módulo de rentas.
Cubre control de acceso por rol, lógica de negocio en finalizar_renta
y eliminar_renta, y el flujo de solicitudes del Empleado.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.urls import reverse


# ─── Helper ──────────────────────────────────────────────────────

def _datos_renta_post(equipo, extra=None):
    """Datos mínimos válidos para el POST de nueva_renta / solicitar_renta."""
    hoy = date.today()
    datos = {
        'cliente_nombre': 'María Torres',
        'cliente_telefono': '6141234567',
        'cliente_direccion': 'Calle 5',
        'fecha_inicio': str(hoy),
        'fecha_vencimiento': str(hoy + timedelta(days=7)),
        'precio': '800.00',
        'deposito': '400.00',
        'metodo_pago': 'efectivo',
        'notas': '',
        'equipo_0': str(equipo.pk),
        'cantidad_0': '1',
    }
    if extra:
        datos.update(extra)
    return datos


# ─── Vista: rentas_activas ────────────────────────────────────────

@pytest.mark.django_db
class TestRentasActivasView:

    def test_anonimo_redirige_al_login(self, client):
        resp = client.get(reverse('rentas:lista'))
        assert resp.status_code == 302
        assert '/login' in resp['Location']

    def test_usuario_autenticado_puede_acceder(self, client, usuario_empleado):
        client.force_login(usuario_empleado)
        resp = client.get(reverse('rentas:lista'))
        assert resp.status_code == 200

    def test_excluye_rentas_no_activas(self, client, usuario_empleado, renta_activa, db):
        from rentas.models import Renta
        renta_activa.estado = 'finalizada'
        renta_activa.save()
        client.force_login(usuario_empleado)
        resp = client.get(reverse('rentas:lista'))
        ids = [r.pk for r in resp.context['rentas']]
        assert renta_activa.pk not in ids

    def test_filtro_por_cliente(self, client, usuario_empleado, renta_activa):
        client.force_login(usuario_empleado)
        resp = client.get(reverse('rentas:lista'), {'cliente': 'Juan'})
        ids = [r.pk for r in resp.context['rentas']]
        assert renta_activa.pk in ids

    def test_filtro_cliente_inexistente_devuelve_vacio(self, client, usuario_empleado, renta_activa):
        client.force_login(usuario_empleado)
        resp = client.get(reverse('rentas:lista'), {'cliente': 'XYZ_NO_EXISTE'})
        assert resp.context['rentas'].paginator.count == 0


# ─── Vista: detalle_renta ─────────────────────────────────────────

@pytest.mark.django_db
class TestDetalleRentaView:

    def test_anonimo_redirige(self, client, renta_activa):
        url = reverse('rentas:detalle', kwargs={'pk': renta_activa.pk})
        assert client.get(url).status_code == 302

    def test_empleado_puede_ver(self, client, usuario_empleado, renta_activa):
        client.force_login(usuario_empleado)
        resp = client.get(reverse('rentas:detalle', kwargs={'pk': renta_activa.pk}))
        assert resp.status_code == 200

    def test_admin_recibe_formulario_finalizar(self, client, usuario_admin, renta_activa):
        client.force_login(usuario_admin)
        resp = client.get(reverse('rentas:detalle', kwargs={'pk': renta_activa.pk}))
        assert resp.context['form_finalizar'] is not None

    def test_empleado_no_recibe_formulario_finalizar(self, client, usuario_empleado, renta_activa):
        client.force_login(usuario_empleado)
        resp = client.get(reverse('rentas:detalle', kwargs={'pk': renta_activa.pk}))
        assert resp.context['form_finalizar'] is None

    def test_pk_inexistente_retorna_404(self, client, usuario_empleado):
        client.force_login(usuario_empleado)
        resp = client.get(reverse('rentas:detalle', kwargs={'pk': 99999}))
        assert resp.status_code == 404


# ─── Vista: nueva_renta ───────────────────────────────────────────

@pytest.mark.django_db
class TestNuevaRentaView:

    def test_empleado_no_puede_acceder(self, client, usuario_empleado):
        client.force_login(usuario_empleado)
        resp = client.get(reverse('rentas:nueva'))
        assert resp.status_code == 403

    def test_admin_puede_acceder(self, client, usuario_admin):
        client.force_login(usuario_admin)
        resp = client.get(reverse('rentas:nueva'))
        assert resp.status_code == 200

    def test_post_valido_crea_renta_y_redirige(self, client, usuario_admin, equipo):
        from rentas.models import Renta
        equipo.cantidad_total = 3
        equipo.save()
        client.force_login(usuario_admin)
        resp = client.post(reverse('rentas:nueva'), data=_datos_renta_post(equipo))
        assert resp.status_code == 302
        assert Renta.objects.filter(cliente__nombre='María Torres').exists()

    def test_post_sin_equipo_no_crea_renta(self, client, usuario_admin, equipo, db):
        from rentas.models import Renta
        client.force_login(usuario_admin)
        datos = _datos_renta_post(equipo)
        del datos['equipo_0']
        del datos['cantidad_0']
        client.post(reverse('rentas:nueva'), data=datos)
        assert not Renta.objects.filter(cliente__nombre='María Torres').exists()

    def test_post_equipo_sin_stock_no_crea_renta(self, client, usuario_admin, equipo, db):
        from rentas.models import Renta
        equipo.cantidad_total = 1
        equipo.cantidad_en_renta = 1
        equipo.save()
        client.force_login(usuario_admin)
        client.post(reverse('rentas:nueva'), data=_datos_renta_post(equipo))
        assert not Renta.objects.filter(cliente__nombre='María Torres').exists()


# ─── Vista: finalizar_renta ───────────────────────────────────────

@pytest.mark.django_db
class TestFinalizarRentaView:

    def _post_finalizar(self, client, renta_activa, extra=None):
        datos = {
            'condicion_devolucion': 'bueno',
            'cargo_daños': '',
            'monto_recibido': '300.00',
            'metodo_pago_cierre': 'efectivo',
            'notas_devolucion': '',
        }
        if extra:
            datos.update(extra)
        return client.post(
            reverse('rentas:finalizar', kwargs={'pk': renta_activa.pk}),
            data=datos,
        )

    def test_empleado_no_puede_finalizar(self, client, usuario_empleado, renta_activa):
        client.force_login(usuario_empleado)
        resp = self._post_finalizar(client, renta_activa)
        assert resp.status_code == 403

    def test_post_valido_marca_renta_finalizada(self, client, usuario_admin, renta_activa, equipo):
        from rentas.models import RentaEquipo
        equipo.cantidad_en_renta = 1
        equipo.save()
        RentaEquipo.objects.create(renta=renta_activa, equipo=equipo, cantidad=1)
        client.force_login(usuario_admin)
        self._post_finalizar(client, renta_activa)
        renta_activa.refresh_from_db()
        assert renta_activa.estado == 'finalizada'
        assert renta_activa.fecha_devolucion == date.today()

    def test_post_valido_libera_unidades(self, client, usuario_admin, renta_activa, equipo):
        from rentas.models import RentaEquipo
        equipo.cantidad_en_renta = 2
        equipo.save()
        RentaEquipo.objects.create(renta=renta_activa, equipo=equipo, cantidad=2)
        client.force_login(usuario_admin)
        self._post_finalizar(client, renta_activa)
        equipo.refresh_from_db()
        assert equipo.cantidad_en_renta == 0

    def test_monto_insuficiente_no_finaliza(self, client, usuario_admin, renta_activa, equipo):
        from rentas.models import RentaEquipo
        # precio=500, deposito=200 → saldo=300; monto_recibido=100 → insuficiente
        renta_activa.precio = Decimal('500.00')
        renta_activa.deposito = Decimal('200.00')
        renta_activa.save()
        equipo.cantidad_en_renta = 1
        equipo.save()
        RentaEquipo.objects.create(renta=renta_activa, equipo=equipo, cantidad=1)
        client.force_login(usuario_admin)
        self._post_finalizar(client, renta_activa, extra={'monto_recibido': '100.00'})
        renta_activa.refresh_from_db()
        assert renta_activa.estado == 'activa'

    def test_renta_no_activa_devuelve_404(self, client, usuario_admin, renta_activa):
        renta_activa.estado = 'finalizada'
        renta_activa.save()
        client.force_login(usuario_admin)
        resp = self._post_finalizar(client, renta_activa)
        assert resp.status_code == 404


# ─── Vista: eliminar_renta ────────────────────────────────────────

@pytest.mark.django_db
class TestEliminarRentaView:

    def test_empleado_no_puede_eliminar(self, client, usuario_empleado, renta_activa):
        client.force_login(usuario_empleado)
        resp = client.post(reverse('rentas:eliminar', kwargs={'pk': renta_activa.pk}))
        assert resp.status_code == 403

    def test_post_elimina_renta_y_libera_unidades(self, client, usuario_admin, renta_activa, equipo):
        from rentas.models import Renta, RentaEquipo
        equipo.cantidad_en_renta = 2
        equipo.save()
        RentaEquipo.objects.create(renta=renta_activa, equipo=equipo, cantidad=2)
        client.force_login(usuario_admin)
        client.post(reverse('rentas:eliminar', kwargs={'pk': renta_activa.pk}))
        assert not Renta.objects.filter(pk=renta_activa.pk).exists()
        equipo.refresh_from_db()
        assert equipo.cantidad_en_renta == 0

    def test_get_no_elimina_renta(self, client, usuario_admin, renta_activa):
        from rentas.models import Renta
        client.force_login(usuario_admin)
        client.get(reverse('rentas:eliminar', kwargs={'pk': renta_activa.pk}))
        assert Renta.objects.filter(pk=renta_activa.pk).exists()


# ─── Vista: solicitar_renta ───────────────────────────────────────

@pytest.mark.django_db
class TestSolicitarRentaView:

    def test_admin_redirige_a_nueva_renta(self, client, usuario_admin):
        client.force_login(usuario_admin)
        resp = client.get(reverse('rentas:solicitar'))
        assert resp.status_code == 302
        assert resp['Location'].endswith(reverse('rentas:nueva'))

    def test_empleado_puede_acceder(self, client, usuario_empleado):
        client.force_login(usuario_empleado)
        resp = client.get(reverse('rentas:solicitar'))
        assert resp.status_code == 200

    def test_post_valido_crea_solicitud(self, client, usuario_empleado, equipo, db):
        from solicitudes.models import Solicitud
        equipo.cantidad_total = 3
        equipo.save()
        datos = _datos_renta_post(equipo)
        datos['comentario'] = 'necesito el equipo urgente'
        client.force_login(usuario_empleado)
        client.post(reverse('rentas:solicitar'), data=datos)
        assert Solicitud.objects.filter(tipo='nueva_renta', solicitante=usuario_empleado).exists()


# ─── Vista: solicitar_cierre ──────────────────────────────────────

@pytest.mark.django_db
class TestSolicitarCierreView:

    def test_admin_redirige_a_finalizar(self, client, usuario_admin, renta_activa):
        client.force_login(usuario_admin)
        resp = client.get(reverse('rentas:solicitar_cierre', kwargs={'pk': renta_activa.pk}))
        assert resp.status_code == 302
        assert 'finalizar' in resp['Location']

    def test_empleado_puede_solicitar_cierre(self, client, usuario_empleado, renta_activa):
        from solicitudes.models import Solicitud
        client.force_login(usuario_empleado)
        client.post(
            reverse('rentas:solicitar_cierre', kwargs={'pk': renta_activa.pk}),
            data={'comentario': 'el cliente devolvió el equipo'},
        )
        assert Solicitud.objects.filter(tipo='cierre_renta', renta=renta_activa).exists()


# ─── Vista: editar_renta ──────────────────────────────────────────

@pytest.mark.django_db
class TestEditarRentaView:

    def test_empleado_no_puede_editar(self, client, usuario_empleado, renta_activa):
        client.force_login(usuario_empleado)
        resp = client.get(reverse('rentas:editar', kwargs={'pk': renta_activa.pk}))
        assert resp.status_code == 403

    def test_admin_puede_acceder(self, client, usuario_admin, renta_activa):
        client.force_login(usuario_admin)
        resp = client.get(reverse('rentas:editar', kwargs={'pk': renta_activa.pk}))
        assert resp.status_code == 200

    def test_post_valido_actualiza_renta(self, client, usuario_admin, renta_activa):
        hoy = date.today()
        client.force_login(usuario_admin)
        client.post(
            reverse('rentas:editar', kwargs={'pk': renta_activa.pk}),
            data={
                'fecha_inicio': str(hoy),
                'fecha_vencimiento': str(hoy + timedelta(days=14)),
                'precio': '900.00',
                'deposito': '450.00',
                'metodo_pago': 'transferencia',
                'notas': '',
            },
        )
        renta_activa.refresh_from_db()
        assert str(renta_activa.precio) == '900.00'
