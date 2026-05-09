from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from inventario.models import Equipo
from rentas.models import Cliente, Renta, RentaEquipo


def to_decimal(value):
    """Helper para convertir strings a Decimal"""
    if isinstance(value, str):
        return Decimal(value)
    return value


class ClienteIntegrationTests(TestCase):
    def test_crear_cliente(self):
        cliente = Cliente.objects.create(
            nombre='Empresa ABC',
            telefono='5551234567',
            direccion='Calle 1 #100',
            correo='contacto@abc.com',
            notas='Cliente frecuente',
        )
        self.assertEqual(cliente.nombre, 'Empresa ABC')
        self.assertEqual(cliente.telefono, '5551234567')

    def test_cliente_str(self):
        cliente = Cliente.objects.create(
            nombre='Empresa XYZ',
            telefono='5559876543',
        )
        self.assertEqual(str(cliente), 'Empresa XYZ')

    def test_filtrar_clientes_por_nombre(self):
        Cliente.objects.create(nombre='Cliente A', telefono='1111111111')
        Cliente.objects.create(nombre='Cliente B', telefono='2222222222')

        cliente_a = Cliente.objects.filter(nombre='Cliente A').first()
        self.assertIsNotNone(cliente_a)
        self.assertEqual(cliente_a.nombre, 'Cliente A')

    def test_get_or_create_cliente(self):
        cliente1, created1 = Cliente.objects.get_or_create(
            nombre='Construcciones XYZ',
            telefono='5551234567',
        )
        self.assertTrue(created1)

        cliente2, created2 = Cliente.objects.get_or_create(
            nombre='Construcciones XYZ',
            telefono='5551234567',
        )
        self.assertFalse(created2)
        self.assertEqual(cliente1.id, cliente2.id)

    def test_cliente_campos_opcionales(self):
        cliente = Cliente.objects.create(
            nombre='Cliente minimalista',
            telefono='5559999999',
        )
        self.assertEqual(cliente.direccion, '')
        self.assertEqual(cliente.correo, '')
        self.assertEqual(cliente.notas, '')


class RentaIntegrationTests(TestCase):
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

    def test_crear_renta(self):
        hoy = date.today()
        renta = Renta.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            registrada_por=self.admin,
            fecha_inicio=hoy,
            fecha_vencimiento=hoy + timedelta(days=5),
            precio=Decimal('500.00'),
            deposito=Decimal('100.00'),
            cantidad=2,
            estado='activa',
        )
        self.assertEqual(renta.estado, 'activa')
        self.assertEqual(renta.precio, Decimal('500.00'))
        self.assertEqual(renta.cantidad, 2)

    def test_renta_saldo_pendiente(self):
        renta = Renta.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            registrada_por=self.admin,
            fecha_inicio=date.today(),
            fecha_vencimiento=date.today() + timedelta(days=5),
            precio=Decimal('1000.00'),
            deposito=Decimal('600.00'),
            cantidad=1,
            estado='activa',
        )
        self.assertEqual(renta.saldo_pendiente, Decimal('400.00'))

    def test_renta_saldo_pendiente_cero(self):
        renta = Renta.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            registrada_por=self.admin,
            fecha_inicio=date.today(),
            fecha_vencimiento=date.today() + timedelta(days=5),
            precio=Decimal('500.00'),
            deposito=Decimal('500.00'),
            cantidad=1,
            estado='activa',
        )
        self.assertEqual(renta.saldo_pendiente, Decimal('0.00'))

    def test_renta_saldo_pendiente_negativo(self):
        renta = Renta.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            registrada_por=self.admin,
            fecha_inicio=date.today(),
            fecha_vencimiento=date.today() + timedelta(days=5),
            precio=Decimal('500.00'),
            deposito=Decimal('700.00'),
            cantidad=1,
            estado='activa',
        )
        self.assertEqual(renta.saldo_pendiente, Decimal('0.00'))

    def test_renta_sobrante_deposito(self):
        renta = Renta.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            registrada_por=self.admin,
            fecha_inicio=date.today(),
            fecha_vencimiento=date.today() + timedelta(days=5),
            precio=Decimal('500.00'),
            deposito=Decimal('700.00'),
            cantidad=1,
            estado='activa',
        )
        self.assertEqual(renta.sobrante_deposito, Decimal('200.00'))

    def test_renta_sobrante_deposito_none(self):
        renta = Renta.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            registrada_por=self.admin,
            fecha_inicio=date.today(),
            fecha_vencimiento=date.today() + timedelta(days=5),
            precio=Decimal('500.00'),
            deposito=Decimal('400.00'),
            cantidad=1,
            estado='activa',
        )
        self.assertIsNone(renta.sobrante_deposito)

    def test_renta_dias_para_vencer(self):
        hoy = date.today()
        renta = Renta.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            registrada_por=self.admin,
            fecha_inicio=hoy,
            fecha_vencimiento=hoy + timedelta(days=3),
            precio=Decimal('500.00'),
            cantidad=1,
            estado='activa',
        )
        self.assertEqual(renta.dias_para_vencer, 3)

    def test_renta_dias_para_vencer_cero(self):
        hoy = date.today()
        renta = Renta.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            registrada_por=self.admin,
            fecha_inicio=hoy - timedelta(days=1),
            fecha_vencimiento=hoy,
            precio=Decimal('500.00'),
            cantidad=1,
            estado='activa',
        )
        self.assertEqual(renta.dias_para_vencer, 0)

    def test_renta_esta_por_vencer(self):
        hoy = date.today()
        renta = Renta.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            registrada_por=self.admin,
            fecha_inicio=hoy,
            fecha_vencimiento=hoy + timedelta(days=2),
            precio=Decimal('500.00'),
            cantidad=1,
            estado='activa',
        )
        self.assertTrue(renta.esta_por_vencer)

    def test_renta_no_esta_por_vencer(self):
        hoy = date.today()
        renta = Renta.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            registrada_por=self.admin,
            fecha_inicio=hoy,
            fecha_vencimiento=hoy + timedelta(days=10),
            precio=Decimal('500.00'),
            cantidad=1,
            estado='activa',
        )
        self.assertFalse(renta.esta_por_vencer)

    def test_renta_esta_vencida_sin_cerrar(self):
        hoy = date.today()
        renta = Renta.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            registrada_por=self.admin,
            fecha_inicio=hoy - timedelta(days=10),
            fecha_vencimiento=hoy - timedelta(days=2),
            precio=Decimal('500.00'),
            cantidad=1,
            estado='activa',
        )
        self.assertTrue(renta.esta_vencida_sin_cerrar)

    def test_renta_cambio_a_devolver(self):
        renta = Renta.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            registrada_por=self.admin,
            fecha_inicio=date.today(),
            fecha_vencimiento=date.today() + timedelta(days=5),
            precio=Decimal('500.00'),
            deposito=Decimal('600.00'),
            monto_recibido=Decimal('500.00'),
            cantidad=1,
            estado='finalizada',
        )
        self.assertEqual(renta.cambio_a_devolver, Decimal('500.00'))

    def test_renta_cambio_a_devolver_none(self):
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
        self.assertIsNone(renta.cambio_a_devolver)

    def test_renta_cantidad_total_equipos_simple(self):
        renta = Renta.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            registrada_por=self.admin,
            fecha_inicio=date.today(),
            fecha_vencimiento=date.today() + timedelta(days=5),
            precio=Decimal('500.00'),
            cantidad=3,
            estado='activa',
        )
        self.assertEqual(renta.cantidad_total_equipos, 3)

    def test_renta_cantidad_total_equipos_multi(self):
        equipo2 = Equipo.objects.create(nombre='Sierra', cantidad_total=10)

        renta = Renta.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            registrada_por=self.admin,
            fecha_inicio=date.today(),
            fecha_vencimiento=date.today() + timedelta(days=5),
            precio=Decimal('500.00'),
            cantidad=2,
            estado='activa',
        )

        RentaEquipo.objects.create(renta=renta, equipo=self.equipo, cantidad=2)
        RentaEquipo.objects.create(renta=renta, equipo=equipo2, cantidad=3)

        self.assertEqual(renta.cantidad_total_equipos, 5)

    def test_renta_str(self):
        renta = Renta.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            registrada_por=self.admin,
            fecha_inicio=date.today(),
            fecha_vencimiento=date.today() + timedelta(days=5),
            precio=Decimal('500.00'),
            cantidad=1,
            estado='activa',
        )
        expected = f'{self.equipo.nombre} - {self.cliente.nombre} (activa)'
        self.assertEqual(str(renta), expected)

    def test_renta_estados_choices(self):
        renta_activa = Renta.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            registrada_por=self.admin,
            fecha_inicio=date.today(),
            fecha_vencimiento=date.today() + timedelta(days=5),
            precio=Decimal('500.00'),
            cantidad=1,
            estado='activa',
        )
        self.assertEqual(renta_activa.get_estado_display(), 'Activa')

    def test_renta_condicion_devolucion_choices(self):
        renta = Renta.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            registrada_por=self.admin,
            fecha_inicio=date.today(),
            fecha_vencimiento=date.today() + timedelta(days=5),
            precio=Decimal('500.00'),
            cantidad=1,
            estado='finalizada',
            condicion_devolucion='bueno',
        )
        self.assertEqual(renta.get_condicion_devolucion_display(), 'Bueno — sin daños')

    def test_renta_metodo_pago_choices(self):
        renta = Renta.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            registrada_por=self.admin,
            fecha_inicio=date.today(),
            fecha_vencimiento=date.today() + timedelta(days=5),
            precio=Decimal('500.00'),
            cantidad=1,
            metodo_pago='efectivo',
        )
        self.assertEqual(renta.get_metodo_pago_display(), 'Efectivo')

    def test_renta_cargo_daños(self):
        renta = Renta.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            registrada_por=self.admin,
            fecha_inicio=date.today(),
            fecha_vencimiento=date.today() + timedelta(days=5),
            precio=Decimal('500.00'),
            cargo_daños=Decimal('150.00'),
            cantidad=1,
            estado='finalizada',
        )
        self.assertEqual(renta.cargo_daños, Decimal('150.00'))

    def test_crear_renta_con_multiples_equipos(self):
        equipo2 = Equipo.objects.create(nombre='Sierra', cantidad_total=10)

        renta = Renta.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            registrada_por=self.admin,
            fecha_inicio=date.today(),
            fecha_vencimiento=date.today() + timedelta(days=5),
            precio=Decimal('1000.00'),
            cantidad=1,
        )

        RentaEquipo.objects.create(renta=renta, equipo=self.equipo, cantidad=2)
        RentaEquipo.objects.create(renta=renta, equipo=equipo2, cantidad=1)

        self.assertEqual(renta.items.count(), 2)
        self.assertEqual(renta.cantidad_total_equipos, 3)
