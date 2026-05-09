from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from inventario.models import Equipo
from rentas.models import Cliente, Renta


class HistorialIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user(
            username='admin',
            password='adminpass123',
            rol='administrador',
        )

        cls.cliente = Cliente.objects.create(
            nombre='Cliente prueba',
            telefono='5551234567',
        )

        cls.equipo = Equipo.objects.create(
            nombre='Taladro',
            cantidad_total=10,
        )

    def test_renta_finalizada_en_historial(self):
        hoy = date.today()
        renta = Renta.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            registrada_por=self.admin,
            fecha_inicio=hoy - timedelta(days=10),
            fecha_vencimiento=hoy - timedelta(days=3),
            fecha_devolucion=hoy - timedelta(days=2),
            precio=Decimal('500.00'),
            deposito=Decimal('100.00'),
            monto_recibido=Decimal('500.00'),
            cantidad=1,
            estado='finalizada',
            condicion_devolucion='bueno',
        )

        historial = Renta.objects.exclude(estado='activa')
        self.assertIn(renta, historial)

    def test_renta_vencida_en_historial(self):
        hoy = date.today()
        renta = Renta.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            registrada_por=self.admin,
            fecha_inicio=hoy - timedelta(days=10),
            fecha_vencimiento=hoy - timedelta(days=2),
            precio=Decimal('500.00'),
            cantidad=1,
            estado='vencida',
        )

        historial = Renta.objects.exclude(estado='activa')
        self.assertIn(renta, historial)

    def test_filtrar_historial_por_cliente(self):
        cliente2 = Cliente.objects.create(
            nombre='Cliente 2',
            telefono='5559999999',
        )
        hoy = date.today()

        renta1 = Renta.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            registrada_por=self.admin,
            fecha_inicio=hoy - timedelta(days=10),
            fecha_vencimiento=hoy - timedelta(days=3),
            precio=Decimal('500.00'),
            cantidad=1,
            estado='finalizada',
        )

        renta2 = Renta.objects.create(
            equipo=self.equipo,
            cliente=cliente2,
            registrada_por=self.admin,
            fecha_inicio=hoy - timedelta(days=5),
            fecha_vencimiento=hoy - timedelta(days=1),
            precio=Decimal('600.00'),
            cantidad=1,
            estado='finalizada',
        )

        historial_cliente1 = Renta.objects.filter(
            cliente=self.cliente,
            estado='finalizada',
        )
        historial_cliente2 = Renta.objects.filter(
            cliente=cliente2,
            estado='finalizada',
        )

        self.assertEqual(historial_cliente1.count(), 1)
        self.assertEqual(historial_cliente2.count(), 1)
        self.assertIn(renta1, historial_cliente1)
        self.assertIn(renta2, historial_cliente2)

    def test_filtrar_historial_por_equipo(self):
        equipo2 = Equipo.objects.create(
            nombre='Sierra',
            cantidad_total=5,
        )
        hoy = date.today()

        renta1 = Renta.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            registrada_por=self.admin,
            fecha_inicio=hoy - timedelta(days=10),
            fecha_vencimiento=hoy - timedelta(days=3),
            precio=Decimal('500.00'),
            cantidad=1,
            estado='finalizada',
        )

        renta2 = Renta.objects.create(
            equipo=equipo2,
            cliente=self.cliente,
            registrada_por=self.admin,
            fecha_inicio=hoy - timedelta(days=5),
            fecha_vencimiento=hoy - timedelta(days=1),
            precio=Decimal('400.00'),
            cantidad=1,
            estado='finalizada',
        )

        historial_eq1 = Renta.objects.filter(equipo=self.equipo)
        historial_eq2 = Renta.objects.filter(equipo=equipo2)

        self.assertEqual(historial_eq1.count(), 1)
        self.assertEqual(historial_eq2.count(), 1)
        self.assertIn(renta1, historial_eq1)
        self.assertIn(renta2, historial_eq2)

    def test_filtrar_historial_por_estado(self):
        hoy = date.today()

        renta_finalizada = Renta.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            registrada_por=self.admin,
            fecha_inicio=hoy - timedelta(days=10),
            fecha_vencimiento=hoy - timedelta(days=3),
            precio=Decimal('500.00'),
            cantidad=1,
            estado='finalizada',
        )

        renta_vencida = Renta.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            registrada_por=self.admin,
            fecha_inicio=hoy - timedelta(days=10),
            fecha_vencimiento=hoy - timedelta(days=2),
            precio=Decimal('600.00'),
            cantidad=1,
            estado='vencida',
        )

        finalizadas = Renta.objects.filter(estado='finalizada')
        vencidas = Renta.objects.filter(estado='vencida')

        self.assertEqual(finalizadas.count(), 1)
        self.assertEqual(vencidas.count(), 1)
        self.assertIn(renta_finalizada, finalizadas)
        self.assertIn(renta_vencida, vencidas)

    def test_filtrar_historial_por_rango_fechas(self):
        hoy = date.today()
        inicio_periodo = hoy - timedelta(days=30)
        fin_periodo = hoy

        renta_dentro = Renta.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            registrada_por=self.admin,
            fecha_inicio=hoy - timedelta(days=15),
            fecha_vencimiento=hoy - timedelta(days=10),
            precio=Decimal('500.00'),
            cantidad=1,
            estado='finalizada',
        )

        renta_fuera = Renta.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            registrada_por=self.admin,
            fecha_inicio=hoy - timedelta(days=60),
            fecha_vencimiento=hoy - timedelta(days=55),
            precio=Decimal('500.00'),
            cantidad=1,
            estado='finalizada',
        )

        historial_periodo = Renta.objects.filter(
            fecha_inicio__gte=inicio_periodo,
            fecha_inicio__lte=fin_periodo,
        )

        self.assertEqual(historial_periodo.count(), 1)
        self.assertIn(renta_dentro, historial_periodo)
        self.assertNotIn(renta_fuera, historial_periodo)

    def test_historial_ordena_por_fecha_inicio_descendente(self):
        hoy = date.today()

        renta1 = Renta.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            registrada_por=self.admin,
            fecha_inicio=hoy - timedelta(days=10),
            fecha_vencimiento=hoy - timedelta(days=5),
            precio=Decimal('500.00'),
            cantidad=1,
            estado='finalizada',
        )

        renta2 = Renta.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            registrada_por=self.admin,
            fecha_inicio=hoy - timedelta(days=5),
            fecha_vencimiento=hoy,
            precio=Decimal('600.00'),
            cantidad=1,
            estado='finalizada',
        )

        historial = list(Renta.objects.exclude(estado='activa').order_by('-fecha_inicio'))

        self.assertEqual(historial[0].id, renta2.id)
        self.assertEqual(historial[1].id, renta1.id)

    def test_datos_detalle_renta_historial(self):
        hoy = date.today()
        renta = Renta.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            registrada_por=self.admin,
            fecha_inicio=hoy - timedelta(days=10),
            fecha_vencimiento=hoy - timedelta(days=5),
            fecha_devolucion=hoy - timedelta(days=4),
            precio=Decimal('500.00'),
            deposito=Decimal('100.00'),
            monto_recibido=Decimal('500.00'),
            cambio_entregado=Decimal('100.00'),
            cantidad=2,
            estado='finalizada',
            condicion_devolucion='bueno',
            metodo_pago='efectivo',
            metodo_pago_cierre='efectivo',
            notas='Renta completada sin incidentes.',
        )

        renta.refresh_from_db()

        self.assertEqual(renta.equipo, self.equipo)
        self.assertEqual(renta.cliente, self.cliente)
        self.assertEqual(renta.registrada_por, self.admin)
        self.assertEqual(renta.precio, 500)
        self.assertEqual(renta.deposito, 100)
        self.assertEqual(renta.monto_recibido, 500)
        self.assertEqual(renta.cambio_entregado, 100)
        self.assertEqual(renta.cantidad, 2)
        self.assertEqual(renta.condicion_devolucion, 'bueno')

    def test_contar_rentas_historial(self):
        hoy = date.today()

        for i in range(5):
            Renta.objects.create(
                equipo=self.equipo,
                cliente=self.cliente,
                registrada_por=self.admin,
                fecha_inicio=hoy - timedelta(days=20 + i),
                fecha_vencimiento=hoy - timedelta(days=15 + i),
                precio=Decimal('500.00'),
                cantidad=1,
                estado='finalizada',
            )

        historial = Renta.objects.exclude(estado='activa')
        self.assertEqual(historial.count(), 5)

    def test_historial_con_cargo_daños(self):
        hoy = date.today()
        renta = Renta.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            registrada_por=self.admin,
            fecha_inicio=hoy - timedelta(days=10),
            fecha_vencimiento=hoy - timedelta(days=5),
            fecha_devolucion=hoy - timedelta(days=4),
            precio=Decimal('500.00'),
            deposito=Decimal('100.00'),
            monto_recibido=Decimal('650.00'),
            cargo_daños=Decimal('150.00'),
            cantidad=1,
            estado='finalizada',
            condicion_devolucion='daños_menores',
        )

        self.assertEqual(renta.cargo_daños, 150)
        self.assertEqual(renta.condicion_devolucion, 'daños_menores')

    def test_historial_relaciona_equipos_y_clientes(self):
        equipo2 = Equipo.objects.create(
            nombre='Sierra',
            cantidad_total=5,
        )
        cliente2 = Cliente.objects.create(
            nombre='Cliente 2',
            telefono='5559999999',
        )
        hoy = date.today()

        rentas = [
            Renta.objects.create(
                equipo=self.equipo,
                cliente=self.cliente,
                registrada_por=self.admin,
                fecha_inicio=hoy - timedelta(days=10),
                fecha_vencimiento=hoy - timedelta(days=5),
                precio=Decimal('500.00'),
                cantidad=1,
                estado='finalizada',
            ),
            Renta.objects.create(
                equipo=equipo2,
                cliente=cliente2,
                registrada_por=self.admin,
                fecha_inicio=hoy - timedelta(days=5),
                fecha_vencimiento=hoy - timedelta(days=1),
                precio=Decimal('600.00'),
                cantidad=1,
                estado='finalizada',
            ),
        ]

        historial = Renta.objects.exclude(estado='activa')
        self.assertEqual(historial.count(), 2)

        for renta in rentas:
            self.assertIsNotNone(renta.equipo)
            self.assertIsNotNone(renta.cliente)
