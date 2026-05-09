"""
Pruebas unitarias para la app inventario.
Cubre: modelo Equipo (propiedades y métodos),
formularios EquipoForm y SolicitudEquipoForm.
"""
import pytest


# ─── Modelo Equipo ────────────────────────────────────────────────

class TestEquipoCantidadDisponible:

    def test_disponible_sin_renta_ni_mantenimiento(self, equipo):
        equipo.cantidad_total = 10
        equipo.cantidad_en_renta = 0
        equipo.cantidad_en_mantenimiento = 0
        assert equipo.cantidad_disponible == 10

    def test_disponible_descuenta_renta_y_mantenimiento(self, equipo):
        equipo.cantidad_total = 10
        equipo.cantidad_en_renta = 3
        equipo.cantidad_en_mantenimiento = 2
        assert equipo.cantidad_disponible == 5

    def test_disponible_nunca_es_negativo(self, equipo):
        equipo.cantidad_total = 2
        equipo.cantidad_en_renta = 3
        equipo.cantidad_en_mantenimiento = 0
        assert equipo.cantidad_disponible == 0


class TestEquipoEstado:

    def test_estado_disponible_cuando_todo_libre(self, equipo):
        equipo.cantidad_total = 5
        equipo.cantidad_en_renta = 0
        equipo.cantidad_en_mantenimiento = 0
        assert equipo.estado == 'disponible'

    def test_estado_parcial_cuando_algunos_rentados(self, equipo):
        equipo.cantidad_total = 5
        equipo.cantidad_en_renta = 2
        equipo.cantidad_en_mantenimiento = 0
        assert equipo.estado == 'parcial'

    def test_estado_rentado_cuando_todos_en_renta(self, equipo):
        equipo.cantidad_total = 3
        equipo.cantidad_en_renta = 3
        equipo.cantidad_en_mantenimiento = 0
        assert equipo.estado == 'rentado'

    def test_estado_mantenimiento_cuando_sin_disponibles_ni_renta(self, equipo):
        equipo.cantidad_total = 2
        equipo.cantidad_en_renta = 0
        equipo.cantidad_en_mantenimiento = 2
        assert equipo.estado == 'mantenimiento'

    def test_get_estado_display_retorna_texto_legible(self, equipo):
        equipo.cantidad_total = 5
        equipo.cantidad_en_renta = 0
        equipo.cantidad_en_mantenimiento = 0
        assert equipo.get_estado_display() == 'Disponible'


class TestEquipoMetodos:

    def test_tiene_disponibles_con_suficientes_unidades(self, equipo):
        equipo.cantidad_total = 5
        equipo.cantidad_en_renta = 1
        equipo.cantidad_en_mantenimiento = 0
        assert equipo.tiene_disponibles(3) is True

    def test_tiene_disponibles_con_unidades_insuficientes(self, equipo):
        equipo.cantidad_total = 3
        equipo.cantidad_en_renta = 2
        equipo.cantidad_en_mantenimiento = 0
        assert equipo.tiene_disponibles(2) is False

    def test_tiene_disponibles_exactamente_las_necesarias(self, equipo):
        equipo.cantidad_total = 4
        equipo.cantidad_en_renta = 2
        equipo.cantidad_en_mantenimiento = 0
        assert equipo.tiene_disponibles(2) is True

    def test_tiene_renta_activa_true(self, equipo):
        equipo.cantidad_en_renta = 1
        assert equipo.tiene_renta_activa() is True

    def test_tiene_renta_activa_false(self, equipo):
        equipo.cantidad_en_renta = 0
        assert equipo.tiene_renta_activa() is False

    def test_str_retorna_nombre(self, equipo):
        assert str(equipo) == 'Taladro percutor'


# ─── Formulario EquipoForm ────────────────────────────────────────

class TestEquipoForm:

    def test_datos_validos_pasan_validacion(self, db):
        from inventario.forms import EquipoForm
        form = EquipoForm(data={
            'nombre': 'Sierra circular',
            'descripcion': '',
            'cantidad_total': 5,
            'cantidad_en_mantenimiento': 1,
        })
        assert form.is_valid(), form.errors

    def test_mantenimiento_igual_a_total_invalida_formulario(self, db):
        from inventario.forms import EquipoForm
        form = EquipoForm(data={
            'nombre': 'Cortadora',
            'descripcion': '',
            'cantidad_total': 3,
            'cantidad_en_mantenimiento': 3,
        })
        assert not form.is_valid()
        assert '__all__' in form.errors

    def test_mantenimiento_mayor_a_total_invalida_formulario(self, db):
        from inventario.forms import EquipoForm
        form = EquipoForm(data={
            'nombre': 'Cortadora',
            'descripcion': '',
            'cantidad_total': 2,
            'cantidad_en_mantenimiento': 5,
        })
        assert not form.is_valid()

    def test_nombre_vacio_invalida_formulario(self, db):
        from inventario.forms import EquipoForm
        form = EquipoForm(data={
            'nombre': '',
            'cantidad_total': 3,
            'cantidad_en_mantenimiento': 0,
        })
        assert not form.is_valid()
        assert 'nombre' in form.errors


# ─── Formulario SolicitudEquipoForm ──────────────────────────────

class TestSolicitudEquipoForm:

    def test_alta_equipo_sin_nombre_invalida(self, db):
        from inventario.forms import SolicitudEquipoForm
        form = SolicitudEquipoForm(data={
            'tipo': 'alta_equipo',
            'nombre_equipo': '',
            'cantidad_total': 1,
            'comentario': 'solicitud de prueba',
        })
        assert not form.is_valid()
        assert 'nombre_equipo' in form.errors

    def test_alta_equipo_con_datos_completos_es_valido(self, db):
        from inventario.forms import SolicitudEquipoForm
        form = SolicitudEquipoForm(data={
            'tipo': 'alta_equipo',
            'nombre_equipo': 'Compresor',
            'cantidad_total': 2,
            'comentario': 'Se necesita para obra',
        })
        assert form.is_valid(), form.errors

    def test_edicion_sin_equipo_seleccionado_invalida(self, db):
        from inventario.forms import SolicitudEquipoForm
        form = SolicitudEquipoForm(data={
            'tipo': 'edicion_equipo',
            'equipo_existente': '',
            'comentario': 'cambiar descripción',
        })
        assert not form.is_valid()
        assert 'equipo_existente' in form.errors

    def test_baja_sin_cantidad_invalida(self, db, equipo):
        from inventario.forms import SolicitudEquipoForm
        form = SolicitudEquipoForm(data={
            'tipo': 'baja_equipo',
            'equipo_existente': equipo.pk,
            'cantidad_baja': '',
            'comentario': 'equipo dañado',
        })
        assert not form.is_valid()
        assert 'cantidad_baja' in form.errors

    def test_baja_con_datos_completos_es_valido(self, db, equipo):
        from inventario.forms import SolicitudEquipoForm
        form = SolicitudEquipoForm(data={
            'tipo': 'baja_equipo',
            'equipo_existente': equipo.pk,
            'cantidad_baja': 1,
            'comentario': 'equipo dañado sin reparación',
        })
        assert form.is_valid(), form.errors


# ─── Bug: actualizar_estado_equipo ────────────────────────────────

class TestActualizarEstadoEquipo:

    def test_falla_porque_estado_es_propiedad_sin_setter(self, equipo):
        """
        actualizar_estado_equipo intenta asignar equipo.estado = 'rentado',
        pero `estado` es un @property sin setter en el modelo Equipo.
        Esto lanza AttributeError. El test documenta el bug existente.
        """
        from inventario.utils import actualizar_estado_equipo
        import pytest
        with pytest.raises(AttributeError):
            actualizar_estado_equipo(equipo)
