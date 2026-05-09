from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase

from inventario.models import Equipo
from rentas.models import Cliente, Renta


class EquipoIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user(
            username='admin',
            password='adminpass123',
            rol='administrador',
        )

    def test_equipo_cantidad_disponible(self):
        equipo = Equipo.objects.create(
            nombre='Taladro de prueba',
            cantidad_total=10,
            cantidad_en_renta=3,
            cantidad_en_mantenimiento=2,
        )

        self.assertEqual(equipo.cantidad_disponible, 5)
        self.assertTrue(equipo.tiene_disponibles(5))
        self.assertFalse(equipo.tiene_disponibles(6))

    def test_equipo_estado_disponible(self):
        equipo = Equipo.objects.create(
            nombre='Taladro',
            cantidad_total=5,
            cantidad_en_renta=0,
            cantidad_en_mantenimiento=0,
        )
        self.assertEqual(equipo.estado, 'disponible')

    def test_equipo_estado_parcial(self):
        equipo = Equipo.objects.create(
            nombre='Taladro',
            cantidad_total=10,
            cantidad_en_renta=3,
            cantidad_en_mantenimiento=0,
        )
        self.assertEqual(equipo.estado, 'parcial')

    def test_equipo_estado_rentado(self):
        equipo = Equipo.objects.create(
            nombre='Taladro',
            cantidad_total=5,
            cantidad_en_renta=5,
            cantidad_en_mantenimiento=0,
        )
        self.assertEqual(equipo.estado, 'rentado')

    def test_equipo_estado_mantenimiento(self):
        equipo = Equipo.objects.create(
            nombre='Taladro',
            cantidad_total=5,
            cantidad_en_renta=0,
            cantidad_en_mantenimiento=5,
        )
        self.assertEqual(equipo.estado, 'mantenimiento')

    def test_equipo_tiene_renta_activa(self):
        equipo = Equipo.objects.create(
            nombre='Taladro',
            cantidad_total=10,
            cantidad_en_renta=2,
        )
        self.assertTrue(equipo.tiene_renta_activa())

        equipo.cantidad_en_renta = 0
        equipo.save()
        self.assertFalse(equipo.tiene_renta_activa())

    def test_equipo_get_estado_display(self):
        equipo = Equipo.objects.create(
            nombre='Taladro',
            cantidad_total=10,
            cantidad_en_renta=0,
        )
        self.assertEqual(equipo.get_estado_display(), 'Disponible')

        equipo.cantidad_en_renta = 5
        equipo.save()
        self.assertEqual(equipo.get_estado_display(), 'Parcialmente disponible')

        equipo.cantidad_en_renta = 10
        equipo.save()
        self.assertEqual(equipo.get_estado_display(), 'Todo rentado')

    def test_equipo_desactivacion(self):
        equipo = Equipo.objects.create(
            nombre='Taladro antiguo',
            activo=True,
        )
        self.assertTrue(equipo.activo)

        equipo.activo = False
        equipo.save()
        equipo.refresh_from_db()
        self.assertFalse(equipo.activo)

    def test_equipo_con_descripcion(self):
        equipo = Equipo.objects.create(
            nombre='Taladro',
            descripcion='Taladro de mano de 18v con batería.',
            cantidad_total=5,
        )
        self.assertEqual(equipo.descripcion, 'Taladro de mano de 18v con batería.')

    def test_equipo_cantidad_total_ajuste(self):
        equipo = Equipo.objects.create(
            nombre='Taladro',
            cantidad_total=10,
            cantidad_en_renta=2,
        )
        self.assertEqual(equipo.cantidad_disponible, 8)

        equipo.cantidad_total = 15
        equipo.save()
        self.assertEqual(equipo.cantidad_disponible, 13)

        equipo.cantidad_total = 5
        equipo.save()
        self.assertEqual(equipo.cantidad_disponible, 3)

    def test_equipo_en_mantenimiento_reduce_disponible(self):
        equipo = Equipo.objects.create(
            nombre='Taladro',
            cantidad_total=10,
            cantidad_en_renta=0,
            cantidad_en_mantenimiento=0,
        )
        self.assertEqual(equipo.cantidad_disponible, 10)

        equipo.cantidad_en_mantenimiento = 3
        equipo.save()
        self.assertEqual(equipo.cantidad_disponible, 7)

    def test_relacion_equipo_rentas(self):
        equipo = Equipo.objects.create(
            nombre='Taladro',
            cantidad_total=10,
        )
        cliente = Cliente.objects.create(
            nombre='Cliente A',
            telefono='5551234567',
        )

        renta = Renta.objects.create(
            equipo=equipo,
            cliente=cliente,
            registrada_por=self.admin,
            fecha_inicio=date.today(),
            fecha_vencimiento=date.today() + timedelta(days=5),
            precio='500.00',
            cantidad=1,
            estado='activa',
        )

        self.assertEqual(equipo.rentas.count(), 1)
        self.assertIn(renta, equipo.rentas.all())

    def test_equipo_str(self):
        equipo = Equipo.objects.create(nombre='Taladro Bosch')
        self.assertEqual(str(equipo), 'Taladro Bosch')

    def test_crear_multiples_equipos(self):
        equipos_data = [
            {'nombre': 'Taladro', 'cantidad_total': 5},
            {'nombre': 'Martillo', 'cantidad_total': 10},
            {'nombre': 'Sierra', 'cantidad_total': 3},
        ]
        for data in equipos_data:
            Equipo.objects.create(**data)

        equipos = Equipo.objects.all()
        self.assertEqual(equipos.count(), 3)
        self.assertTrue(equipos.filter(nombre='Taladro').exists())
        self.assertTrue(equipos.filter(nombre='Martillo').exists())
        self.assertTrue(equipos.filter(nombre='Sierra').exists())

    def test_filtrar_equipos_activos(self):
        Equipo.objects.create(nombre='Taladro activo', activo=True)
        Equipo.objects.create(nombre='Taladro inactivo', activo=False)

        activos = Equipo.objects.filter(activo=True)
        inactivos = Equipo.objects.filter(activo=False)

        self.assertEqual(activos.count(), 1)
        self.assertEqual(inactivos.count(), 1)

    def test_ordenamiento_equipos(self):
        Equipo.objects.create(nombre='Zeta')
        Equipo.objects.create(nombre='Alfa')
        Equipo.objects.create(nombre='Bravo')

        equipos = list(Equipo.objects.all())
        nombres = [e.nombre for e in equipos]

        self.assertEqual(nombres, ['Alfa', 'Bravo', 'Zeta'])
