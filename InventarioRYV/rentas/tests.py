"""
Pruebas unitarias para la app rentas.
Cubre: modelo Renta (propiedades financieras y de tiempo),
modelo Cliente, función marcar_rentas_vencidas y formularios
RentaForm, SolicitudRentaForm, FinalizarRentaForm y equipos_con_disponibles.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal


# ─── Modelo Cliente ───────────────────────────────────────────────

class TestCliente:

    def test_str_retorna_nombre(self, cliente):
        assert str(cliente) == 'Juan Pérez'

    def test_campos_opcionales_en_blanco(self, db):
        from rentas.models import Cliente
        c = Cliente.objects.create(nombre='Sin correo', telefono='0000000000')
        assert c.correo == ''
        assert c.direccion == ''


# ─── Modelo Renta: propiedades financieras ────────────────────────

class TestRentaSaldoPendiente:

    def test_saldo_pendiente_es_precio_menos_deposito(self, renta_activa):
        renta_activa.precio = Decimal('500.00')
        renta_activa.deposito = Decimal('200.00')
        assert renta_activa.saldo_pendiente == Decimal('300.00')

    def test_saldo_pendiente_nunca_es_negativo(self, renta_activa):
        renta_activa.precio = Decimal('100.00')
        renta_activa.deposito = Decimal('300.00')
        assert renta_activa.saldo_pendiente == Decimal('0')

    def test_saldo_pendiente_con_deposito_igual_a_precio(self, renta_activa):
        renta_activa.precio = Decimal('400.00')
        renta_activa.deposito = Decimal('400.00')
        assert renta_activa.saldo_pendiente == Decimal('0')


class TestRentaSobranteDeposito:

    def test_sobrante_es_none_cuando_deposito_menor_a_precio(self, renta_activa):
        renta_activa.precio = Decimal('500.00')
        renta_activa.deposito = Decimal('200.00')
        assert renta_activa.sobrante_deposito is None

    def test_sobrante_es_none_cuando_deposito_igual_a_precio(self, renta_activa):
        renta_activa.precio = Decimal('300.00')
        renta_activa.deposito = Decimal('300.00')
        assert renta_activa.sobrante_deposito is None

    def test_sobrante_retorna_diferencia_cuando_deposito_mayor(self, renta_activa):
        renta_activa.precio = Decimal('200.00')
        renta_activa.deposito = Decimal('350.00')
        assert renta_activa.sobrante_deposito == Decimal('150.00')


class TestRentaCambioADevolver:

    def test_cambio_es_none_sin_monto_recibido(self, renta_activa):
        renta_activa.monto_recibido = None
        assert renta_activa.cambio_a_devolver is None

    def test_cambio_positivo_cuando_pago_excede_saldo(self, renta_activa):
        renta_activa.precio = Decimal('500.00')
        renta_activa.deposito = Decimal('200.00')
        renta_activa.monto_recibido = Decimal('400.00')
        assert renta_activa.cambio_a_devolver == Decimal('100.00')

    def test_cambio_negativo_cuando_pago_insuficiente(self, renta_activa):
        renta_activa.precio = Decimal('500.00')
        renta_activa.deposito = Decimal('100.00')
        renta_activa.monto_recibido = Decimal('200.00')
        assert renta_activa.cambio_a_devolver == Decimal('-200.00')


# ─── Modelo Renta: propiedades de tiempo ─────────────────────────

class TestRentaDiasParaVencer:

    def test_dias_para_vencer_retorna_none_si_no_activa(self, renta_activa):
        renta_activa.estado = 'finalizada'
        assert renta_activa.dias_para_vencer is None

    def test_dias_para_vencer_retorna_entero_para_activa(self, renta_activa):
        renta_activa.estado = 'activa'
        renta_activa.fecha_vencimiento = date.today() + timedelta(days=5)
        assert renta_activa.dias_para_vencer == 5

    def test_dias_para_vencer_negativo_cuando_ya_vencio(self, renta_activa):
        renta_activa.estado = 'activa'
        renta_activa.fecha_vencimiento = date.today() - timedelta(days=2)
        assert renta_activa.dias_para_vencer == -2


class TestRentaAlertasVencimiento:

    def test_esta_por_vencer_true_dentro_de_3_dias(self, renta_activa):
        renta_activa.estado = 'activa'
        renta_activa.fecha_vencimiento = date.today() + timedelta(days=2)
        assert renta_activa.esta_por_vencer is True

    def test_esta_por_vencer_true_vence_hoy(self, renta_activa):
        renta_activa.estado = 'activa'
        renta_activa.fecha_vencimiento = date.today()
        assert renta_activa.esta_por_vencer is True

    def test_esta_por_vencer_false_mas_de_3_dias(self, renta_activa):
        renta_activa.estado = 'activa'
        renta_activa.fecha_vencimiento = date.today() + timedelta(days=10)
        assert renta_activa.esta_por_vencer is False

    def test_esta_por_vencer_false_si_ya_vencio(self, renta_activa):
        renta_activa.estado = 'activa'
        renta_activa.fecha_vencimiento = date.today() - timedelta(days=1)
        assert renta_activa.esta_por_vencer is False

    def test_esta_vencida_sin_cerrar_true(self, renta_activa):
        renta_activa.estado = 'activa'
        renta_activa.fecha_vencimiento = date.today() - timedelta(days=3)
        assert renta_activa.esta_vencida_sin_cerrar is True

    def test_esta_vencida_sin_cerrar_false_si_no_vencio(self, renta_activa):
        renta_activa.estado = 'activa'
        renta_activa.fecha_vencimiento = date.today() + timedelta(days=1)
        assert renta_activa.esta_vencida_sin_cerrar is False

    def test_esta_vencida_sin_cerrar_false_si_finalizada(self, renta_activa):
        renta_activa.estado = 'finalizada'
        renta_activa.fecha_vencimiento = date.today() - timedelta(days=5)
        assert renta_activa.esta_vencida_sin_cerrar is False


# ─── Función marcar_rentas_vencidas ──────────────────────────────

class TestMarcarRentasVencidas:

    def test_marca_rentas_activas_expiradas(self, db, equipo, cliente, usuario_empleado):
        from rentas.models import Renta
        from rentas.utils import marcar_rentas_vencidas

        Renta.objects.create(
            equipo=equipo, cliente=cliente, registrada_por=usuario_empleado,
            fecha_inicio=date.today() - timedelta(days=10),
            fecha_vencimiento=date.today() - timedelta(days=3),
            precio='300.00', cantidad=1, estado='activa',
        )
        count = marcar_rentas_vencidas()
        assert count == 1
        assert Renta.objects.filter(estado='vencida').count() == 1

    def test_no_marca_rentas_futuras(self, db, equipo, cliente, usuario_empleado):
        from rentas.models import Renta
        from rentas.utils import marcar_rentas_vencidas

        Renta.objects.create(
            equipo=equipo, cliente=cliente, registrada_por=usuario_empleado,
            fecha_inicio=date.today(),
            fecha_vencimiento=date.today() + timedelta(days=5),
            precio='300.00', cantidad=1, estado='activa',
        )
        count = marcar_rentas_vencidas()
        assert count == 0

    def test_no_marca_rentas_ya_finalizadas(self, db, equipo, cliente, usuario_empleado):
        from rentas.models import Renta
        from rentas.utils import marcar_rentas_vencidas

        Renta.objects.create(
            equipo=equipo, cliente=cliente, registrada_por=usuario_empleado,
            fecha_inicio=date.today() - timedelta(days=10),
            fecha_vencimiento=date.today() - timedelta(days=2),
            precio='300.00', cantidad=1, estado='finalizada',
        )
        count = marcar_rentas_vencidas()
        assert count == 0


# ─── equipos_con_disponibles ─────────────────────────────────────

class TestEquiposConDisponibles:

    def test_retorna_equipos_con_unidades_libres(self, db, equipo):
        from rentas.forms import equipos_con_disponibles
        equipo.cantidad_total = 5
        equipo.cantidad_en_renta = 1
        equipo.cantidad_en_mantenimiento = 0
        equipo.save()
        assert equipo in equipos_con_disponibles()

    def test_excluye_equipos_sin_disponibles(self, db, equipo):
        from rentas.forms import equipos_con_disponibles
        equipo.cantidad_total = 2
        equipo.cantidad_en_renta = 2
        equipo.cantidad_en_mantenimiento = 0
        equipo.save()
        assert equipo not in equipos_con_disponibles()

    def test_excluye_equipos_inactivos(self, db, equipo):
        from rentas.forms import equipos_con_disponibles
        equipo.activo = False
        equipo.save()
        assert equipo not in equipos_con_disponibles()


# ─── Formulario RentaForm ─────────────────────────────────────────

class TestRentaForm:

    def _datos_base(self, extra=None):
        hoy = date.today()
        datos = {
            'cliente_nombre': 'Pedro López',
            'cliente_telefono': '6141112233',
            'cliente_direccion': 'Calle 1',
            'fecha_inicio': str(hoy),
            'fecha_vencimiento': str(hoy + timedelta(days=5)),
            'precio': '1000.00',
            'deposito': '500.00',
            'metodo_pago': 'efectivo',
            'notas': '',
        }
        if extra:
            datos.update(extra)
        return datos

    def test_datos_validos_pasan(self, db):
        from rentas.forms import RentaForm
        form = RentaForm(data=self._datos_base())
        assert form.is_valid(), form.errors

    def test_fecha_vencimiento_igual_a_inicio_invalida(self, db):
        from rentas.forms import RentaForm
        hoy = date.today()
        form = RentaForm(data=self._datos_base({
            'fecha_inicio': str(hoy),
            'fecha_vencimiento': str(hoy),
        }))
        assert not form.is_valid()

    def test_fecha_vencimiento_anterior_a_inicio_invalida(self, db):
        from rentas.forms import RentaForm
        hoy = date.today()
        form = RentaForm(data=self._datos_base({
            'fecha_inicio': str(hoy),
            'fecha_vencimiento': str(hoy - timedelta(days=1)),
        }))
        assert not form.is_valid()

    def test_deposito_menor_al_50_invalida(self, db):
        from rentas.forms import RentaForm
        form = RentaForm(data=self._datos_base({
            'precio': '1000.00',
            'deposito': '400.00',
        }))
        assert not form.is_valid()
        assert 'deposito' in form.errors

    def test_deposito_sin_metodo_pago_invalida(self, db):
        from rentas.forms import RentaForm
        form = RentaForm(data=self._datos_base({
            'deposito': '600.00',
            'metodo_pago': '',
        }))
        assert not form.is_valid()
        assert 'metodo_pago' in form.errors


# ─── Formulario FinalizarRentaForm ────────────────────────────────

class TestFinalizarRentaForm:

    def test_condicion_bueno_sin_cargo_es_valido(self, db):
        from rentas.forms import FinalizarRentaForm
        form = FinalizarRentaForm(data={
            'condicion_devolucion': 'bueno',
            'cargo_daños': '',
            'monto_recibido': '300.00',
            'metodo_pago_cierre': 'efectivo',
        })
        assert form.is_valid(), form.errors

    def test_daños_menores_sin_cargo_invalida(self, db):
        from rentas.forms import FinalizarRentaForm
        form = FinalizarRentaForm(data={
            'condicion_devolucion': 'daños_menores',
            'cargo_daños': '',
            'monto_recibido': '',
            'metodo_pago_cierre': '',
        })
        assert not form.is_valid()
        assert 'cargo_daños' in form.errors

    def test_inservible_con_cargo_es_valido(self, db):
        from rentas.forms import FinalizarRentaForm
        form = FinalizarRentaForm(data={
            'condicion_devolucion': 'inservible',
            'cargo_daños': '500.00',
            'monto_recibido': '',
            'metodo_pago_cierre': '',
        })
        assert form.is_valid(), form.errors

    def test_extraviado_con_cargo_es_valido(self, db):
        from rentas.forms import FinalizarRentaForm
        form = FinalizarRentaForm(data={
            'condicion_devolucion': 'extraviado',
            'cargo_daños': '1500.00',
            'monto_recibido': '',
            'metodo_pago_cierre': '',
        })
        assert form.is_valid(), form.errors


# ─── Función auxiliar _parsear_equipos_post ───────────────────────

class TestParsearEquiposPost:

    def _make_post(self, items):
        """Construye un dict que simula request.POST con filas equipo_N/cantidad_N."""
        data = {}
        for i, (pk, cant) in enumerate(items):
            data[f'equipo_{i}'] = str(pk)
            data[f'cantidad_{i}'] = str(cant)
        return data

    def test_parsea_una_fila(self):
        from rentas.views import _parsear_equipos_post
        from django.http import QueryDict
        qd = QueryDict(mutable=True)
        qd.update(self._make_post([(5, 2)]))
        result = _parsear_equipos_post(qd)
        assert result == [('5', 2)]

    def test_parsea_multiples_filas(self):
        from rentas.views import _parsear_equipos_post
        from django.http import QueryDict
        qd = QueryDict(mutable=True)
        qd.update(self._make_post([(1, 1), (3, 4)]))
        result = _parsear_equipos_post(qd)
        assert result == [('1', 1), ('3', 4)]

    def test_retorna_lista_vacia_sin_datos(self):
        from rentas.views import _parsear_equipos_post
        from django.http import QueryDict
        result = _parsear_equipos_post(QueryDict())
        assert result == []

    def test_cantidad_invalida_usa_1_por_defecto(self):
        from rentas.views import _parsear_equipos_post
        from django.http import QueryDict
        qd = QueryDict(mutable=True)
        qd.update({'equipo_0': '7', 'cantidad_0': 'abc'})
        result = _parsear_equipos_post(qd)
        assert result == [('7', 1)]

    def test_cantidad_cero_se_normaliza_a_1(self):
        from rentas.views import _parsear_equipos_post
        from django.http import QueryDict
        qd = QueryDict(mutable=True)
        qd.update({'equipo_0': '7', 'cantidad_0': '0'})
        result = _parsear_equipos_post(qd)
        assert result[0][1] == 1


# ─── Propiedades multi-equipo de Renta ───────────────────────────

class TestRentaMultiEquipo:

    def test_nombre_equipo_display_sin_items_usa_equipo_principal(self, renta_activa, equipo):
        assert renta_activa.nombre_equipo_display == equipo.nombre

    def test_nombre_equipo_display_con_un_item(self, db, renta_activa, equipo):
        from rentas.models import RentaEquipo
        RentaEquipo.objects.create(renta=renta_activa, equipo=equipo, cantidad=1)
        assert renta_activa.nombre_equipo_display == equipo.nombre

    def test_nombre_equipo_display_con_multiples_items(self, db, renta_activa, equipo):
        from rentas.models import RentaEquipo
        from inventario.models import Equipo
        equipo2 = Equipo.objects.create(nombre='Cortadora', cantidad_total=2)
        RentaEquipo.objects.create(renta=renta_activa, equipo=equipo, cantidad=1)
        RentaEquipo.objects.create(renta=renta_activa, equipo=equipo2, cantidad=1)
        display = renta_activa.nombre_equipo_display
        assert '+1 más' in display

    def test_cantidad_total_equipos_sin_items_usa_cantidad_renta(self, renta_activa):
        renta_activa.cantidad = 3
        assert renta_activa.cantidad_total_equipos == 3

    def test_cantidad_total_equipos_suma_items(self, db, renta_activa, equipo):
        from rentas.models import RentaEquipo
        from inventario.models import Equipo
        equipo2 = Equipo.objects.create(nombre='Sierra', cantidad_total=3)
        RentaEquipo.objects.create(renta=renta_activa, equipo=equipo, cantidad=2)
        RentaEquipo.objects.create(renta=renta_activa, equipo=equipo2, cantidad=3)
        assert renta_activa.cantidad_total_equipos == 5


# ─── Formulario SolicitudRentaForm ────────────────────────────────

class TestSolicitudRentaForm:

    def _datos_base(self, extra=None):
        hoy = date.today()
        datos = {
            'cliente_nombre': 'Carlos Ruiz',
            'cliente_telefono': '6148887766',
            'cliente_direccion': 'Av. Central 10',
            'fecha_inicio': str(hoy),
            'fecha_vencimiento': str(hoy + timedelta(days=5)),
            'precio': '600.00',
            'deposito': '300.00',
            'metodo_pago': 'efectivo',
            'notas': '',
            'comentario': 'necesitamos el equipo para mañana',
        }
        if extra:
            datos.update(extra)
        return datos

    def test_datos_validos_pasan(self, db):
        from rentas.forms import SolicitudRentaForm
        form = SolicitudRentaForm(data=self._datos_base())
        assert form.is_valid(), form.errors

    def test_fecha_vencimiento_igual_a_inicio_invalida(self, db):
        from rentas.forms import SolicitudRentaForm
        hoy = date.today()
        form = SolicitudRentaForm(data=self._datos_base({
            'fecha_inicio': str(hoy),
            'fecha_vencimiento': str(hoy),
        }))
        assert not form.is_valid()

    def test_deposito_menor_al_50_invalida(self, db):
        from rentas.forms import SolicitudRentaForm
        form = SolicitudRentaForm(data=self._datos_base({
            'precio': '1000.00',
            'deposito': '400.00',
        }))
        assert not form.is_valid()
        assert 'deposito' in form.errors

    def test_deposito_sin_metodo_pago_invalida(self, db):
        from rentas.forms import SolicitudRentaForm
        form = SolicitudRentaForm(data=self._datos_base({
            'deposito': '400.00',
            'metodo_pago': '',
        }))
        assert not form.is_valid()
        assert 'metodo_pago' in form.errors
