"""
Pruebas unitarias para la app panel_admin.
Cubre la lógica de negocio de las vistas de administración:
restricción único administrador (RN-011), automodificación de rol,
autoeliminación y flujo de rechazo/aprobación de solicitudes.
"""
import pytest
from django.urls import reverse


# ─── Fixtures auxiliares ─────────────────────────────────────────

@pytest.fixture
def segundo_admin(db):
    from authentication.models import Usuario
    return Usuario.objects.create_user(
        username='admin2', password='admin1234', rol='administrador'
    )


@pytest.fixture
def solicitud_alta(db, usuario_empleado):
    from solicitudes.models import Solicitud
    return Solicitud.objects.create(
        tipo='alta_equipo',
        solicitante=usuario_empleado,
        comentario='Solicitar nuevo equipo',
        datos_json={'nombre': 'Generador', 'cantidad_total': 2},
    )


# ─── Restricción: único administrador (RN-011) ────────────────────

class TestEliminarUsuario:

    def test_no_puede_eliminar_unico_administrador(self, client, usuario_admin):
        client.force_login(usuario_admin)
        url = reverse('panel_admin:eliminar_usuario', kwargs={'pk': usuario_admin.pk})
        # Hay solo un admin → debe redirigir con error, sin eliminar
        respuesta = client.post(url)
        from authentication.models import Usuario
        assert Usuario.objects.filter(pk=usuario_admin.pk).exists()
        assert respuesta.status_code == 302

    def test_puede_eliminar_admin_si_hay_otro(self, client, usuario_admin, segundo_admin):
        client.force_login(usuario_admin)
        url = reverse('panel_admin:eliminar_usuario', kwargs={'pk': segundo_admin.pk})
        respuesta = client.post(url)
        from authentication.models import Usuario
        assert not Usuario.objects.filter(pk=segundo_admin.pk).exists()
        assert respuesta.status_code == 302

    def test_no_puede_eliminar_su_propia_cuenta(self, client, usuario_admin, segundo_admin):
        client.force_login(usuario_admin)
        url = reverse('panel_admin:eliminar_usuario', kwargs={'pk': usuario_admin.pk})
        respuesta = client.post(url)
        from authentication.models import Usuario
        assert Usuario.objects.filter(pk=usuario_admin.pk).exists()
        assert respuesta.status_code == 302

    def test_empleado_no_puede_acceder(self, client, usuario_empleado):
        client.force_login(usuario_empleado)
        url = reverse('panel_admin:eliminar_usuario', kwargs={'pk': usuario_empleado.pk})
        respuesta = client.post(url)
        assert respuesta.status_code == 403

    def test_anonimo_redirige_al_login(self, client, usuario_admin):
        url = reverse('panel_admin:eliminar_usuario', kwargs={'pk': usuario_admin.pk})
        respuesta = client.post(url)
        assert respuesta.status_code == 302
        assert '/login' in respuesta['Location']


# ─── Restricción: no modificar propio rol (RN-011) ────────────────

class TestEditarRol:

    def test_admin_no_puede_editar_su_propio_rol(self, client, usuario_admin):
        client.force_login(usuario_admin)
        url = reverse('panel_admin:editar_rol', kwargs={'pk': usuario_admin.pk})
        respuesta = client.post(url, data={'rol': 'empleado'})
        usuario_admin.refresh_from_db()
        assert usuario_admin.rol == 'administrador'
        assert respuesta.status_code == 302

    def test_admin_puede_editar_rol_de_otro_usuario(self, client, usuario_admin, usuario_empleado):
        client.force_login(usuario_admin)
        url = reverse('panel_admin:editar_rol', kwargs={'pk': usuario_empleado.pk})
        respuesta = client.post(url, data={'rol': 'administrador'})
        usuario_empleado.refresh_from_db()
        assert usuario_empleado.rol == 'administrador'
        assert respuesta.status_code == 302


# ─── Rechazar solicitud ───────────────────────────────────────────

class TestRechazarSolicitud:

    def test_solicitud_queda_rechazada(self, client, usuario_admin, solicitud_alta):
        client.force_login(usuario_admin)
        url = reverse('panel_admin:rechazar', kwargs={'pk': solicitud_alta.pk})
        respuesta = client.post(url)
        solicitud_alta.refresh_from_db()
        assert solicitud_alta.estado == 'rechazada'
        assert solicitud_alta.resuelto_por == usuario_admin
        assert solicitud_alta.fecha_resolucion is not None
        assert respuesta.status_code == 302

    def test_get_no_rechaza_solicitud(self, client, usuario_admin, solicitud_alta):
        client.force_login(usuario_admin)
        url = reverse('panel_admin:rechazar', kwargs={'pk': solicitud_alta.pk})
        client.get(url)
        solicitud_alta.refresh_from_db()
        assert solicitud_alta.estado == 'pendiente'

    def test_empleado_no_puede_rechazar(self, client, usuario_empleado, solicitud_alta):
        client.force_login(usuario_empleado)
        url = reverse('panel_admin:rechazar', kwargs={'pk': solicitud_alta.pk})
        respuesta = client.post(url)
        assert respuesta.status_code == 403


# ─── Aprobar solicitud ────────────────────────────────────────────

class TestAprobarSolicitud:

    def test_aprueba_alta_equipo_y_crea_equipo(self, client, usuario_admin, solicitud_alta):
        from inventario.models import Equipo
        client.force_login(usuario_admin)
        url = reverse('panel_admin:aprobar', kwargs={'pk': solicitud_alta.pk})
        client.post(url)
        solicitud_alta.refresh_from_db()
        assert solicitud_alta.estado == 'aprobada'
        assert Equipo.objects.filter(nombre='Generador').exists()

    def test_empleado_no_puede_aprobar(self, client, usuario_empleado, solicitud_alta):
        client.force_login(usuario_empleado)
        url = reverse('panel_admin:aprobar', kwargs={'pk': solicitud_alta.pk})
        respuesta = client.post(url)
        assert respuesta.status_code == 403
