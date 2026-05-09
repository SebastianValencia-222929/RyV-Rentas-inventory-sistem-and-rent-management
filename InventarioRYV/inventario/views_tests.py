from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from inventario.models import Equipo
from rentas.models import Cliente, Renta


class InventarioViewsIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.empleado = User.objects.create_user(
            username='empleado',
            password='empleadopass123',
            rol='empleado',
        )
        cls.admin = User.objects.create_user(
            username='admin',
            password='adminpass123',
            rol='administrador',
        )

        cls.equipo = Equipo.objects.create(
            nombre='Taladro',
            descripcion='Taladro de prueba',
            cantidad_total=10,
            cantidad_en_renta=0,
            cantidad_en_mantenimiento=0,
            activo=True,
        )

    def test_acceso_lista_inventario_empleado(self):
        self.client.login(username='empleado', password='empleadopass123')
        response = self.client.get(reverse('inventario:lista'))
        self.assertEqual(response.status_code, 200)

    def test_acceso_lista_inventario_admin(self):
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('inventario:lista'))
        self.assertEqual(response.status_code, 200)

    def test_acceso_disponibles_sin_login_redirige(self):
        response = self.client.get(reverse('inventario:disponibles'), follow=False)
        self.assertNotEqual(response.status_code, 200)

    def test_acceso_disponibles_con_login(self):
        self.client.login(username='empleado', password='empleadopass123')
        response = self.client.get(reverse('inventario:disponibles'))
        self.assertEqual(response.status_code, 200)

    def test_detalle_equipo_existe(self):
        self.client.login(username='empleado', password='empleadopass123')
        response = self.client.get(reverse('inventario:detalle', args=[self.equipo.pk]))
        self.assertEqual(response.status_code, 200)

    def test_detalle_equipo_no_existe(self):
        self.client.login(username='empleado', password='empleadopass123')
        response = self.client.get(reverse('inventario:detalle', args=[999]))
        self.assertEqual(response.status_code, 404)

    def test_solicitar_cambio_accesible(self):
        self.client.login(username='empleado', password='empleadopass123')
        response = self.client.get(reverse('inventario:solicitar'))
        self.assertEqual(response.status_code, 200)

    def test_listar_equipos_con_filtro_nombre(self):
        Equipo.objects.create(
            nombre='Sierra',
            cantidad_total=5,
            activo=True,
        )

        self.client.login(username='empleado', password='empleadopass123')
        response = self.client.get(reverse('inventario:lista'), {'nombre': 'Taladro'})
        self.assertEqual(response.status_code, 200)

    def test_equipos_disponibles_query(self):
        equipo_disponible = Equipo.objects.create(
            nombre='Sierra disponible',
            cantidad_total=5,
            cantidad_en_renta=0,
            activo=True,
        )

        equipo_rentado = Equipo.objects.create(
            nombre='Sierra rentada',
            cantidad_total=5,
            cantidad_en_renta=5,
            activo=True,
        )

        self.client.login(username='empleado', password='empleadopass123')
        response = self.client.get(reverse('inventario:disponibles'))
        self.assertEqual(response.status_code, 200)

    def test_equipos_inactivos_no_se_muestran(self):
        equipo_inactivo = Equipo.objects.create(
            nombre='Taladro inactivo',
            cantidad_total=5,
            activo=False,
        )

        equipos_activos = Equipo.objects.filter(activo=True)
        self.assertNotIn(equipo_inactivo, equipos_activos)

    def test_cantidad_disponible_calculo(self):
        equipo = Equipo.objects.create(
            nombre='Test equipo',
            cantidad_total=20,
            cantidad_en_renta=5,
            cantidad_en_mantenimiento=3,
        )

        self.assertEqual(equipo.cantidad_disponible, 12)

    def test_estado_equipo_parcial(self):
        equipo = Equipo.objects.create(
            nombre='Equipo parcial',
            cantidad_total=10,
            cantidad_en_renta=3,
            cantidad_en_mantenimiento=0,
        )

        self.assertEqual(equipo.estado, 'parcial')

    def test_cantidad_disponible_no_negativa(self):
        equipo = Equipo.objects.create(
            nombre='Test negativo',
            cantidad_total=5,
            cantidad_en_renta=3,
            cantidad_en_mantenimiento=5,
        )

        self.assertGreaterEqual(equipo.cantidad_disponible, 0)
