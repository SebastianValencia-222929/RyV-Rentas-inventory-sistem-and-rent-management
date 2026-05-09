from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase

from inventario.models import Equipo
from rentas.models import Cliente, Renta
from solicitudes.models import Solicitud
from solicitudes.services import ejecutar_solicitud


class SolicitudIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user(
            username='admin',
            password='adminpass123',
            rol='administrador',
        )
        cls.empleado = User.objects.create_user(
            username='empleado',
            password='empleadopass123',
            rol='empleado',
        )

        cls.equipo = Equipo.objects.create(
            nombre='Taladro',
            cantidad_total=10,
        )

        cls.cliente = Cliente.objects.create(
            nombre='Cliente prueba',
            telefono='5551234567',
        )

    def test_crear_solicitud_alta_equipo(self):
        solicitud = Solicitud.objects.create(
            tipo='alta_equipo',
            solicitante=self.empleado,
            comentario='Solicitar alta de nuevo equipo.',
            datos_json={
                'nombre': 'Martillo',
                'descripcion': 'Martillo de acero',
                'cantidad_total': 5,
            },
        )
        self.assertEqual(solicitud.estado, 'pendiente')
        self.assertEqual(solicitud.tipo, 'alta_equipo')

    def test_ejecutar_solicitud_alta_equipo(self):
        solicitud = Solicitud.objects.create(
            tipo='alta_equipo',
            solicitante=self.empleado,
            comentario='Solicitar alta de nuevo equipo.',
            datos_json={
                'nombre': 'Martillo',
                'descripcion': 'Martillo de acero',
                'cantidad_total': 5,
            },
        )

        ejecutar_solicitud(solicitud)

        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'aprobada')

        equipo = Equipo.objects.get(nombre='Martillo')
        self.assertEqual(equipo.nombre, 'Martillo')
        self.assertEqual(equipo.cantidad_total, 5)

    def test_ejecutar_solicitud_edicion_equipo(self):
        solicitud = Solicitud.objects.create(
            tipo='edicion_equipo',
            solicitante=self.empleado,
            equipo=self.equipo,
            comentario='Editar taladro.',
            datos_json={
                'nombre': 'Taladro Premium',
                'cantidad_en_mantenimiento': 1,
            },
        )

        ejecutar_solicitud(solicitud)

        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.nombre, 'Taladro Premium')
        self.assertEqual(self.equipo.cantidad_en_mantenimiento, 1)

    def test_ejecutar_solicitud_baja_equipo_total(self):
        equipo = Equipo.objects.create(
            nombre='Taladro viejo',
            cantidad_total=5,
            activo=True,
        )

        solicitud = Solicitud.objects.create(
            tipo='baja_equipo',
            solicitante=self.empleado,
            equipo=equipo,
            comentario='Dar de baja equipo.',
            datos_json={'cantidad_baja': 5},
        )

        ejecutar_solicitud(solicitud)

        equipo.refresh_from_db()
        self.assertFalse(equipo.activo)

    def test_ejecutar_solicitud_baja_equipo_parcial(self):
        equipo = Equipo.objects.create(
            nombre='Taladro',
            cantidad_total=10,
            activo=True,
        )

        solicitud = Solicitud.objects.create(
            tipo='baja_equipo',
            solicitante=self.empleado,
            equipo=equipo,
            comentario='Dar de baja parcial.',
            datos_json={'cantidad_baja': 3},
        )

        ejecutar_solicitud(solicitud)

        equipo.refresh_from_db()
        self.assertEqual(equipo.cantidad_total, 7)
        self.assertTrue(equipo.activo)

    def test_ejecutar_solicitud_baja_equipo_con_renta_activa_falla(self):
        equipo = Equipo.objects.create(
            nombre='Taladro en renta',
            cantidad_total=10,
            cantidad_en_renta=2,
        )

        solicitud = Solicitud.objects.create(
            tipo='baja_equipo',
            solicitante=self.empleado,
            equipo=equipo,
            comentario='Dar de baja.',
            datos_json={'cantidad_baja': 10},
        )

        with self.assertRaises(ValueError):
            ejecutar_solicitud(solicitud)

    def test_crear_solicitud_nueva_renta(self):
        solicitud = Solicitud.objects.create(
            tipo='nueva_renta',
            solicitante=self.empleado,
            equipo=self.equipo,
            comentario='Solicitar nueva renta.',
            datos_json={
                'cliente_nombre': 'Nueva empresa',
                'cliente_telefono': '5559999999',
                'fecha_inicio': str(date.today()),
                'fecha_vencimiento': str(date.today() + timedelta(days=5)),
                'precio': '500.00',
                'deposito': '100.00',
            },
        )
        self.assertEqual(solicitud.tipo, 'nueva_renta')

    def test_crear_solicitud_cierre_renta(self):
        renta = Renta.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            registrada_por=self.admin,
            fecha_inicio=date.today(),
            fecha_vencimiento=date.today() + timedelta(days=5),
            precio='500.00',
            cantidad=1,
            estado='activa',
        )

        solicitud = Solicitud.objects.create(
            tipo='cierre_renta',
            solicitante=self.empleado,
            renta=renta,
            equipo=self.equipo,
            comentario='Solicitar cierre de renta.',
        )
        self.assertEqual(solicitud.tipo, 'cierre_renta')
        self.assertEqual(solicitud.renta, renta)

    def test_ejecutar_solicitud_cierre_renta(self):
        renta = Renta.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            registrada_por=self.admin,
            fecha_inicio=date.today() - timedelta(days=5),
            fecha_vencimiento=date.today() + timedelta(days=2),
            precio='500.00',
            cantidad=1,
            estado='activa',
        )

        self.equipo.cantidad_en_renta = 1
        self.equipo.save()

        solicitud = Solicitud.objects.create(
            tipo='cierre_renta',
            solicitante=self.empleado,
            renta=renta,
            equipo=self.equipo,
            comentario='Solicitar cierre.',
        )

        ejecutar_solicitud(solicitud)

        renta.refresh_from_db()
        self.assertEqual(renta.estado, 'finalizada')
        self.assertEqual(renta.fecha_devolucion, date.today())

        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.cantidad_en_renta, 0)

    def test_aprobar_rechazar_solicitud_workflow(self):
        solicitud = Solicitud.objects.create(
            tipo='alta_equipo',
            solicitante=self.empleado,
            comentario='Alta de equipo.',
            datos_json={'nombre': 'Sierra', 'cantidad_total': 5},
        )

        self.assertEqual(solicitud.estado, 'pendiente')
        self.assertIsNone(solicitud.resuelto_por)

        ejecutar_solicitud(solicitud)

        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'aprobada')

    def test_rechazar_solicitud(self):
        solicitud = Solicitud.objects.create(
            tipo='alta_equipo',
            solicitante=self.empleado,
            comentario='Alta de equipo.',
            datos_json={'nombre': 'Sierra', 'cantidad_total': 5},
        )

        solicitud.estado = 'rechazada'
        solicitud.resuelto_por = self.admin
        solicitud.save()

        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'rechazada')
        self.assertEqual(solicitud.resuelto_por, self.admin)

    def test_solicitud_str(self):
        solicitud = Solicitud.objects.create(
            tipo='alta_equipo',
            solicitante=self.empleado,
            comentario='Alta de equipo.',
        )
        str_repr = str(solicitud)
        self.assertIn('Alta de equipo', str_repr)
        self.assertIn('Pendiente', str_repr)

    def test_filtrar_solicitudes_por_solicitante(self):
        Solicitud.objects.create(
            tipo='alta_equipo',
            solicitante=self.empleado,
            comentario='Solicitud 1',
        )
        Solicitud.objects.create(
            tipo='baja_equipo',
            solicitante=self.admin,
            comentario='Solicitud 2',
        )

        solicitudes_empleado = Solicitud.objects.filter(solicitante=self.empleado)
        self.assertEqual(solicitudes_empleado.count(), 1)

    def test_filtrar_solicitudes_por_estado(self):
        sol1 = Solicitud.objects.create(
            tipo='alta_equipo',
            solicitante=self.empleado,
            comentario='Solicitud 1',
            estado='pendiente',
        )
        sol2 = Solicitud.objects.create(
            tipo='baja_equipo',
            solicitante=self.empleado,
            comentario='Solicitud 2',
            estado='aprobada',
        )

        pendientes = Solicitud.objects.filter(estado='pendiente')
        aprobadas = Solicitud.objects.filter(estado='aprobada')

        self.assertEqual(pendientes.count(), 1)
        self.assertEqual(aprobadas.count(), 1)
        self.assertIn(sol1, pendientes)
        self.assertIn(sol2, aprobadas)

    def test_ordenamiento_solicitudes(self):
        sol1 = Solicitud.objects.create(
            tipo='alta_equipo',
            solicitante=self.empleado,
            comentario='Primera',
        )
        sol2 = Solicitud.objects.create(
            tipo='baja_equipo',
            solicitante=self.empleado,
            comentario='Segunda',
        )

        solicitudes = list(Solicitud.objects.all())
        self.assertEqual(solicitudes[0].id, sol2.id)
        self.assertEqual(solicitudes[1].id, sol1.id)
