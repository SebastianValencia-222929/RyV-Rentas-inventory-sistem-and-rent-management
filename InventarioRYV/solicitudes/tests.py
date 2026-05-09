"""
Pruebas unitarias para la app solicitudes.
Cubre: modelo Solicitud y la función ejecutar_solicitud (services.py).
"""
import pytest
from datetime import date, timedelta


# ─── Helpers ─────────────────────────────────────────────────────

def crear_solicitud(db_fixture, tipo, solicitante, equipo=None, renta=None, datos=None):
    from solicitudes.models import Solicitud
    return Solicitud.objects.create(
        tipo=tipo,
        solicitante=solicitante,
        equipo=equipo,
        renta=renta,
        comentario='solicitud de prueba',
        datos_json=datos or {},
    )


# ─── Modelo Solicitud ─────────────────────────────────────────────

class TestSolicitudModelo:

    def test_str_contiene_tipo_y_solicitante(self, db, usuario_empleado):
        from solicitudes.models import Solicitud
        s = Solicitud.objects.create(
            tipo='alta_equipo',
            solicitante=usuario_empleado,
            comentario='prueba',
            datos_json={},
        )
        assert 'Alta de equipo' in str(s)
        assert 'empleado_test' in str(s)

    def test_estado_por_defecto_es_pendiente(self, db, usuario_empleado):
        from solicitudes.models import Solicitud
        s = Solicitud.objects.create(
            tipo='baja_equipo',
            solicitante=usuario_empleado,
            comentario='prueba',
        )
        assert s.estado == 'pendiente'


# ─── ejecutar_solicitud: alta_equipo ─────────────────────────────

class TestEjecutarSolicitudAltaEquipo:

    def test_crea_equipo_en_inventario(self, db, usuario_admin):
        from solicitudes.services import ejecutar_solicitud
        from inventario.models import Equipo

        s = crear_solicitud(db, 'alta_equipo', usuario_admin, datos={
            'nombre': 'Mezcladora',
            'descripcion': 'Para concreto',
            'cantidad_total': 3,
        })
        ejecutar_solicitud(s)

        equipo = Equipo.objects.get(nombre='Mezcladora')
        assert equipo.cantidad_total == 3
        s.refresh_from_db()
        assert s.estado == 'aprobada'

    def test_solicitud_queda_aprobada(self, db, usuario_admin):
        from solicitudes.services import ejecutar_solicitud

        s = crear_solicitud(db, 'alta_equipo', usuario_admin, datos={
            'nombre': 'Compresor',
            'cantidad_total': 1,
        })
        ejecutar_solicitud(s)
        s.refresh_from_db()
        assert s.estado == 'aprobada'
        assert s.fecha_resolucion is not None


# ─── ejecutar_solicitud: edicion_equipo ──────────────────────────

class TestEjecutarSolicitudEdicionEquipo:

    def test_actualiza_nombre_del_equipo(self, db, equipo, usuario_admin):
        from solicitudes.services import ejecutar_solicitud

        s = crear_solicitud(db, 'edicion_equipo', usuario_admin, equipo=equipo, datos={
            'nombre': 'Taladro percutor XL',
        })
        ejecutar_solicitud(s)
        equipo.refresh_from_db()
        assert equipo.nombre == 'Taladro percutor XL'

    def test_actualiza_cantidad_total(self, db, equipo, usuario_admin):
        from solicitudes.services import ejecutar_solicitud

        s = crear_solicitud(db, 'edicion_equipo', usuario_admin, equipo=equipo, datos={
            'cantidad_total': 10,
        })
        ejecutar_solicitud(s)
        equipo.refresh_from_db()
        assert equipo.cantidad_total == 10

    def test_no_modifica_campos_no_permitidos(self, db, equipo, usuario_admin):
        from solicitudes.services import ejecutar_solicitud

        s = crear_solicitud(db, 'edicion_equipo', usuario_admin, equipo=equipo, datos={
            'activo': False,
        })
        ejecutar_solicitud(s)
        equipo.refresh_from_db()
        assert equipo.activo is True


# ─── ejecutar_solicitud: baja_equipo ─────────────────────────────

class TestEjecutarSolicitudBajaEquipo:

    def test_baja_total_desactiva_equipo(self, db, equipo, usuario_admin):
        from solicitudes.services import ejecutar_solicitud

        equipo.cantidad_total = 3
        equipo.save()
        s = crear_solicitud(db, 'baja_equipo', usuario_admin, equipo=equipo, datos={
            'cantidad_baja': 3,
        })
        ejecutar_solicitud(s)
        equipo.refresh_from_db()
        assert equipo.activo is False

    def test_baja_parcial_reduce_cantidad_total(self, db, equipo, usuario_admin):
        from solicitudes.services import ejecutar_solicitud

        equipo.cantidad_total = 5
        equipo.save()
        s = crear_solicitud(db, 'baja_equipo', usuario_admin, equipo=equipo, datos={
            'cantidad_baja': 2,
        })
        ejecutar_solicitud(s)
        equipo.refresh_from_db()
        assert equipo.cantidad_total == 3
        assert equipo.activo is True

    def test_baja_con_renta_activa_lanza_valueerror(self, db, equipo, usuario_admin):
        from solicitudes.services import ejecutar_solicitud

        equipo.cantidad_en_renta = 1
        equipo.save()
        s = crear_solicitud(db, 'baja_equipo', usuario_admin, equipo=equipo, datos={
            'cantidad_baja': 1,
        })
        with pytest.raises(ValueError, match='tiene'):
            ejecutar_solicitud(s)


# ─── ejecutar_solicitud: nueva_renta ─────────────────────────────

class TestEjecutarSolicitudNuevaRenta:

    def _datos_renta(self, equipo_id, cantidad=1):
        return {
            'cliente_nombre': 'Ana Ruiz',
            'cliente_telefono': '6149876543',
            'equipos': [{'equipo_id': equipo_id, 'cantidad': cantidad}],
            'fecha_inicio': str(date.today()),
            'fecha_vencimiento': str(date.today() + timedelta(days=7)),
            'precio': '800.00',
            'deposito': '300.00',
            'metodo_pago': 'efectivo',
        }

    def test_crea_renta_y_cliente(self, db, equipo, usuario_empleado):
        from solicitudes.services import ejecutar_solicitud
        from rentas.models import Renta, Cliente

        equipo.cantidad_total = 3
        equipo.save()
        s = crear_solicitud(db, 'nueva_renta', usuario_empleado,
                            datos=self._datos_renta(equipo.pk))
        ejecutar_solicitud(s)

        assert Renta.objects.count() == 1
        assert Cliente.objects.filter(nombre='Ana Ruiz').exists()

    def test_incrementa_contador_en_renta(self, db, equipo, usuario_empleado):
        from solicitudes.services import ejecutar_solicitud

        equipo.cantidad_total = 5
        equipo.cantidad_en_renta = 0
        equipo.save()
        s = crear_solicitud(db, 'nueva_renta', usuario_empleado,
                            datos=self._datos_renta(equipo.pk, cantidad=2))
        ejecutar_solicitud(s)
        equipo.refresh_from_db()
        assert equipo.cantidad_en_renta == 2

    def test_unidades_insuficientes_lanza_valueerror(self, db, equipo, usuario_empleado):
        from solicitudes.services import ejecutar_solicitud

        equipo.cantidad_total = 1
        equipo.cantidad_en_renta = 1
        equipo.save()
        s = crear_solicitud(db, 'nueva_renta', usuario_empleado,
                            datos=self._datos_renta(equipo.pk, cantidad=2))
        with pytest.raises(ValueError, match='suficientes'):
            ejecutar_solicitud(s)


# ─── ejecutar_solicitud: cierre_renta ────────────────────────────

class TestEjecutarSolicitudCierreRenta:

    def test_renta_queda_finalizada(self, db, renta_activa, equipo, usuario_admin):
        from solicitudes.services import ejecutar_solicitud
        from rentas.models import RentaEquipo

        equipo.cantidad_en_renta = 1
        equipo.save()
        RentaEquipo.objects.create(renta=renta_activa, equipo=equipo, cantidad=1)

        s = crear_solicitud(db, 'cierre_renta', usuario_admin, renta=renta_activa)
        ejecutar_solicitud(s)

        renta_activa.refresh_from_db()
        assert renta_activa.estado == 'finalizada'
        assert renta_activa.fecha_devolucion == date.today()

    def test_libera_unidades_del_equipo(self, db, renta_activa, equipo, usuario_admin):
        from solicitudes.services import ejecutar_solicitud
        from rentas.models import RentaEquipo

        equipo.cantidad_en_renta = 2
        equipo.save()
        RentaEquipo.objects.create(renta=renta_activa, equipo=equipo, cantidad=2)

        s = crear_solicitud(db, 'cierre_renta', usuario_admin, renta=renta_activa)
        ejecutar_solicitud(s)

        equipo.refresh_from_db()
        assert equipo.cantidad_en_renta == 0
