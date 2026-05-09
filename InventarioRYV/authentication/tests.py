"""
Pruebas unitarias para la app authentication.
Cubre: modelo Usuario, formularios LoginForm/UsuarioForm,
y decoradores admin_required / empleado_o_admin.
"""
import pytest
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser


# ─── Modelo Usuario ───────────────────────────────────────────────

class TestUsuarioRoles:

    def test_es_administrador_retorna_true(self, usuario_admin):
        assert usuario_admin.es_administrador() is True

    def test_es_administrador_retorna_false_para_empleado(self, usuario_empleado):
        assert usuario_empleado.es_administrador() is False

    def test_es_empleado_retorna_true(self, usuario_empleado):
        assert usuario_empleado.es_empleado() is True

    def test_es_empleado_retorna_false_para_admin(self, usuario_admin):
        assert usuario_admin.es_empleado() is False

    def test_rol_por_defecto_es_empleado(self, db):
        from authentication.models import Usuario
        u = Usuario.objects.create_user(username='nuevo', password='pass1234')
        assert u.rol == 'empleado'


# ─── Formulario UsuarioForm ───────────────────────────────────────

class TestUsuarioForm:

    def _datos_base(self, extra=None):
        datos = {
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'rol': 'empleado',
            'password1': 'segura1234',
            'password2': 'segura1234',
        }
        if extra:
            datos.update(extra)
        return datos

    def test_passwords_coinciden_es_valido(self, db):
        from authentication.forms import UsuarioForm
        form = UsuarioForm(data=self._datos_base())
        assert form.is_valid(), form.errors

    def test_passwords_distintos_invalida_formulario(self, db):
        from authentication.forms import UsuarioForm
        form = UsuarioForm(data=self._datos_base({'password2': 'diferente99'}))
        assert not form.is_valid()
        assert 'password2' in form.errors

    def test_save_hashea_contrasena(self, db):
        from authentication.forms import UsuarioForm
        form = UsuarioForm(data=self._datos_base())
        assert form.is_valid()
        usuario = form.save()
        assert usuario.check_password('segura1234')
        assert usuario.password != 'segura1234'

    def test_username_duplicado_invalida_formulario(self, db, usuario_admin):
        from authentication.forms import UsuarioForm
        form = UsuarioForm(data=self._datos_base({'username': 'admin_test'}))
        assert not form.is_valid()
        assert 'username' in form.errors


# ─── Decoradores ─────────────────────────────────────────────────

class TestDecoradores:

    def _vista_dummy(self, request, *args, **kwargs):
        from django.http import HttpResponse
        return HttpResponse('ok')

    def test_admin_required_usuario_no_autenticado_redirige(self):
        from authentication.decorators import admin_required
        factory = RequestFactory()
        request = factory.get('/dummy/')
        request.user = AnonymousUser()
        vista = admin_required(self._vista_dummy)
        respuesta = vista(request)
        assert respuesta.status_code == 302
        assert '/login' in respuesta['Location']

    def test_admin_required_empleado_lanza_permission_denied(self, usuario_empleado):
        from authentication.decorators import admin_required
        factory = RequestFactory()
        request = factory.get('/dummy/')
        request.user = usuario_empleado
        vista = admin_required(self._vista_dummy)
        with pytest.raises(PermissionDenied):
            vista(request)

    def test_admin_required_administrador_accede_correctamente(self, usuario_admin):
        from authentication.decorators import admin_required
        factory = RequestFactory()
        request = factory.get('/dummy/')
        request.user = usuario_admin
        vista = admin_required(self._vista_dummy)
        respuesta = vista(request)
        assert respuesta.status_code == 200

    def test_empleado_o_admin_no_autenticado_redirige(self):
        from authentication.decorators import empleado_o_admin
        factory = RequestFactory()
        request = factory.get('/dummy/')
        request.user = AnonymousUser()
        vista = empleado_o_admin(self._vista_dummy)
        respuesta = vista(request)
        assert respuesta.status_code == 302

    def test_empleado_o_admin_usuario_autenticado_accede(self, usuario_empleado):
        from authentication.decorators import empleado_o_admin
        factory = RequestFactory()
        request = factory.get('/dummy/')
        request.user = usuario_empleado
        vista = empleado_o_admin(self._vista_dummy)
        respuesta = vista(request)
        assert respuesta.status_code == 200
