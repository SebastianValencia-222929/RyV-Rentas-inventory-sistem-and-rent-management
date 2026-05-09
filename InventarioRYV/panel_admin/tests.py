from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase

from inventario.models import Equipo
from rentas.models import Cliente, Renta
from solicitudes.models import Solicitud
from authentication.models import Usuario


class PanelAdminIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user(
            username='admin',
            password='adminpass123',
            first_name='Admin',
            last_name='User',
            rol='administrador',
        )
        cls.empleado = User.objects.create_user(
            username='empleado',
            password='empleadopass123',
            first_name='Empleado',
            last_name='User',
            rol='empleado',
        )

    def test_crear_usuario(self):
        usuario = Usuario.objects.create_user(
            username='nuevo_empleado',
            password='pass123456',
            first_name='Nuevo',
            last_name='Empleado',
            email='nuevo@test.com',
            rol='empleado',
        )
        self.assertEqual(usuario.username, 'nuevo_empleado')
        self.assertEqual(usuario.rol, 'empleado')
        self.assertTrue(usuario.check_password('pass123456'))

    def test_usuario_es_administrador(self):
        self.assertTrue(self.admin.es_administrador())
        self.assertFalse(self.empleado.es_administrador())

    def test_usuario_es_empleado(self):
        self.assertFalse(self.admin.es_empleado())
        self.assertTrue(self.empleado.es_empleado())

    def test_cambiar_rol_usuario(self):
        usuario = Usuario.objects.create_user(
            username='cambio_rol',
            password='pass123',
            rol='empleado',
        )
        self.assertEqual(usuario.rol, 'empleado')

        usuario.rol = 'administrador'
        usuario.save()
        usuario.refresh_from_db()
        self.assertEqual(usuario.rol, 'administrador')
        self.assertTrue(usuario.es_administrador())

    def test_listar_usuarios(self):
        Usuario.objects.create_user(username='user1', password='pass123', rol='empleado')
        Usuario.objects.create_user(username='user2', password='pass123', rol='empleado')

        usuarios = Usuario.objects.all()
        self.assertGreaterEqual(usuarios.count(), 3)

    def test_filtrar_usuarios_por_rol(self):
        Usuario.objects.create_user(username='admin2', password='pass123', rol='administrador')
        Usuario.objects.create_user(username='emp2', password='pass123', rol='empleado')

        admins = Usuario.objects.filter(rol='administrador')
        empleados = Usuario.objects.filter(rol='empleado')

        self.assertGreaterEqual(admins.count(), 2)
        self.assertGreaterEqual(empleados.count(), 2)

    def test_eliminar_usuario(self):
        usuario = Usuario.objects.create_user(
            username='usuario_a_eliminar',
            password='pass123',
            rol='empleado',
        )
        usuario_id = usuario.id

        usuario.delete()

        with self.assertRaises(Usuario.DoesNotExist):
            Usuario.objects.get(id=usuario_id)

    def test_no_eliminar_ultimo_administrador(self):
        Usuario.objects.filter(rol='administrador').exclude(id=self.admin.id).delete()

        admins = Usuario.objects.filter(rol='administrador')
        self.assertEqual(admins.count(), 1)
        self.assertEqual(admins.first(), self.admin)

    def test_solicitudes_pendientes(self):
        equipo = Equipo.objects.create(
            nombre='Taladro',
            cantidad_total=10,
        )

        Solicitud.objects.create(
            tipo='alta_equipo',
            solicitante=self.empleado,
            equipo=equipo,
            comentario='Solicitud 1',
            estado='pendiente',
        )
        Solicitud.objects.create(
            tipo='baja_equipo',
            solicitante=self.empleado,
            equipo=equipo,
            comentario='Solicitud 2',
            estado='pendiente',
        )
        Solicitud.objects.create(
            tipo='alta_equipo',
            solicitante=self.empleado,
            equipo=equipo,
            comentario='Solicitud 3',
            estado='aprobada',
        )

        pendientes = Solicitud.objects.filter(estado='pendiente')
        self.assertEqual(pendientes.count(), 2)

    def test_contar_equipos_activos(self):
        Equipo.objects.create(nombre='Equipo 1', activo=True)
        Equipo.objects.create(nombre='Equipo 2', activo=True)
        Equipo.objects.create(nombre='Equipo 3', activo=False)

        activos = Equipo.objects.filter(activo=True)
        self.assertEqual(activos.count(), 2)

    def test_contar_rentas_activas(self):
        cliente = Cliente.objects.create(
            nombre='Cliente',
            telefono='5551234567',
        )
        equipo = Equipo.objects.create(
            nombre='Taladro',
            cantidad_total=10,
        )

        Renta.objects.create(
            equipo=equipo,
            cliente=cliente,
            registrada_por=self.admin,
            fecha_inicio=date.today(),
            fecha_vencimiento=date.today() + timedelta(days=5),
            precio='500.00',
            cantidad=1,
            estado='activa',
        )
        Renta.objects.create(
            equipo=equipo,
            cliente=cliente,
            registrada_por=self.admin,
            fecha_inicio=date.today() - timedelta(days=10),
            fecha_vencimiento=date.today() - timedelta(days=5),
            precio='500.00',
            cantidad=1,
            estado='finalizada',
        )

        activas = Renta.objects.filter(estado='activa')
        self.assertEqual(activas.count(), 1)

    def test_alertas_rentas_por_vencer(self):
        cliente = Cliente.objects.create(
            nombre='Cliente',
            telefono='5551234567',
        )
        equipo = Equipo.objects.create(
            nombre='Taladro',
            cantidad_total=10,
        )
        hoy = date.today()

        renta_proxima = Renta.objects.create(
            equipo=equipo,
            cliente=cliente,
            registrada_por=self.admin,
            fecha_inicio=hoy,
            fecha_vencimiento=hoy + timedelta(days=2),
            precio='500.00',
            cantidad=1,
            estado='activa',
        )

        renta_lejana = Renta.objects.create(
            equipo=equipo,
            cliente=cliente,
            registrada_por=self.admin,
            fecha_inicio=hoy,
            fecha_vencimiento=hoy + timedelta(days=10),
            precio='500.00',
            cantidad=1,
            estado='activa',
        )

        self.assertTrue(renta_proxima.esta_por_vencer)
        self.assertFalse(renta_lejana.esta_por_vencer)

    def test_rentas_vencidas_sin_cerrar(self):
        cliente = Cliente.objects.create(
            nombre='Cliente',
            telefono='5551234567',
        )
        equipo = Equipo.objects.create(
            nombre='Taladro',
            cantidad_total=10,
        )
        hoy = date.today()

        renta_vencida = Renta.objects.create(
            equipo=equipo,
            cliente=cliente,
            registrada_por=self.admin,
            fecha_inicio=hoy - timedelta(days=10),
            fecha_vencimiento=hoy - timedelta(days=3),
            precio='500.00',
            cantidad=1,
            estado='activa',
        )

        self.assertTrue(renta_vencida.esta_vencida_sin_cerrar)

    def test_dashboard_metricas_equipos(self):
        Equipo.objects.create(
            nombre='Eq1',
            cantidad_total=10,
            cantidad_en_renta=0,
            cantidad_en_mantenimiento=0,
            activo=True,
        )
        Equipo.objects.create(
            nombre='Eq2',
            cantidad_total=5,
            cantidad_en_renta=3,
            cantidad_en_mantenimiento=0,
            activo=True,
        )
        Equipo.objects.create(
            nombre='Eq3',
            cantidad_total=8,
            cantidad_en_renta=0,
            cantidad_en_mantenimiento=2,
            activo=True,
        )

        activos = Equipo.objects.filter(activo=True)
        self.assertEqual(activos.count(), 3)

        en_renta = activos.filter(cantidad_en_renta__gt=0)
        self.assertEqual(en_renta.count(), 1)

        en_mantenimiento = activos.filter(cantidad_en_mantenimiento__gt=0)
        self.assertEqual(en_mantenimiento.count(), 1)

    def test_aprobar_solicitud_workflow(self):
        equipo = Equipo.objects.create(
            nombre='Taladro',
            cantidad_total=10,
        )

        solicitud = Solicitud.objects.create(
            tipo='baja_equipo',
            solicitante=self.empleado,
            equipo=equipo,
            comentario='Solicitud de baja.',
            estado='pendiente',
        )

        self.assertEqual(solicitud.estado, 'pendiente')

        solicitud.estado = 'aprobada'
        solicitud.resuelto_por = self.admin
        solicitud.save()

        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'aprobada')
        self.assertEqual(solicitud.resuelto_por, self.admin)

    def test_rechazar_solicitud_workflow(self):
        equipo = Equipo.objects.create(
            nombre='Taladro',
            cantidad_total=10,
        )

        solicitud = Solicitud.objects.create(
            tipo='baja_equipo',
            solicitante=self.empleado,
            equipo=equipo,
            comentario='Solicitud de baja.',
            estado='pendiente',
        )

        self.assertEqual(solicitud.estado, 'pendiente')

        solicitud.estado = 'rechazada'
        solicitud.resuelto_por = self.admin
        solicitud.save()

        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'rechazada')
