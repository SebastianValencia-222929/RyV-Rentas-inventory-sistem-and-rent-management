"""
Pruebas unitarias para la app reportes.
Cubre: modelo ReporteGenerado, formulario ReporteRentasForm
y generadores de PDF (inventario, rentas, comprobante).
"""
import pytest
from datetime import date, timedelta


# ─── Modelo ReporteGenerado ───────────────────────────────────────

class TestReporteGenerado:

    def test_str_contiene_tipo_y_fecha(self, db, usuario_admin):
        from reportes.models import ReporteGenerado
        reporte = ReporteGenerado.objects.create(
            tipo='inventario',
            generado_por=usuario_admin,
            archivo_nombre='inventario_2026.pdf',
        )
        resultado = str(reporte)
        assert 'Inventario' in resultado
        assert '2026' in resultado

    def test_str_tipo_rentas(self, db, usuario_admin):
        from reportes.models import ReporteGenerado
        reporte = ReporteGenerado.objects.create(
            tipo='rentas',
            generado_por=usuario_admin,
            archivo_nombre='rentas_mayo.pdf',
            periodo_inicio=date.today(),
            periodo_fin=date.today() + timedelta(days=30),
        )
        assert 'Rentas' in str(reporte)

    def test_orden_por_fecha_descendente(self, db, usuario_admin):
        from reportes.models import ReporteGenerado
        r1 = ReporteGenerado.objects.create(
            tipo='inventario', generado_por=usuario_admin,
            archivo_nombre='a.pdf',
        )
        r2 = ReporteGenerado.objects.create(
            tipo='inventario', generado_por=usuario_admin,
            archivo_nombre='b.pdf',
        )
        primero = ReporteGenerado.objects.first()
        assert primero == r2  # más reciente primero (ordering = ['-fecha_generacion'])

    def test_generado_por_null_al_borrar_usuario(self, db, usuario_admin):
        from reportes.models import ReporteGenerado
        reporte = ReporteGenerado.objects.create(
            tipo='inventario',
            generado_por=usuario_admin,
            archivo_nombre='test.pdf',
        )
        usuario_admin.delete()
        reporte.refresh_from_db()
        assert reporte.generado_por is None


# ─── Formulario ReporteRentasForm ─────────────────────────────────

@pytest.mark.django_db
class TestReporteRentasForm:

    def test_fechas_validas_pasan(self):
        from reportes.forms import ReporteRentasForm
        form = ReporteRentasForm(data={
            'periodo_inicio': '2026-01-01',
            'periodo_fin': '2026-01-31',
        })
        assert form.is_valid(), form.errors

    def test_fechas_iguales_son_validas(self):
        from reportes.forms import ReporteRentasForm
        form = ReporteRentasForm(data={
            'periodo_inicio': '2026-05-01',
            'periodo_fin': '2026-05-01',
        })
        assert form.is_valid(), form.errors

    def test_fin_anterior_a_inicio_invalida(self):
        from reportes.forms import ReporteRentasForm
        form = ReporteRentasForm(data={
            'periodo_inicio': '2026-05-15',
            'periodo_fin': '2026-05-10',
        })
        assert not form.is_valid()
        assert '__all__' in form.errors

    def test_campos_vacios_invalidan(self):
        from reportes.forms import ReporteRentasForm
        form = ReporteRentasForm(data={})
        assert not form.is_valid()
        assert 'periodo_inicio' in form.errors
        assert 'periodo_fin' in form.errors


# ─── Generadores PDF ─────────────────────────────────────────────

class TestGeneradorPDFInventario:

    def test_retorna_bytes_no_vacios(self, db):
        from reportes.generators import generar_pdf_inventario
        from inventario.models import Equipo
        resultado = generar_pdf_inventario(Equipo.objects.none())
        assert isinstance(resultado, bytes)
        assert len(resultado) > 0

    def test_genera_pdf_con_equipos(self, db, equipo):
        from reportes.generators import generar_pdf_inventario
        from inventario.models import Equipo
        resultado = generar_pdf_inventario(Equipo.objects.filter(pk=equipo.pk))
        assert isinstance(resultado, bytes)
        assert len(resultado) > 100

    def test_pdf_comienza_con_firma_pdf(self, db):
        from reportes.generators import generar_pdf_inventario
        from inventario.models import Equipo
        resultado = generar_pdf_inventario(Equipo.objects.none())
        assert resultado[:4] == b'%PDF'


class TestGeneradorPDFRentas:

    def test_retorna_bytes_no_vacios(self, db):
        from reportes.generators import generar_pdf_rentas
        from rentas.models import Renta
        resultado = generar_pdf_rentas(Renta.objects.none())
        assert isinstance(resultado, bytes)
        assert len(resultado) > 0

    def test_genera_pdf_con_periodo(self, db):
        from reportes.generators import generar_pdf_rentas
        from rentas.models import Renta
        inicio = date.today() - timedelta(days=30)
        fin = date.today()
        resultado = generar_pdf_rentas(Renta.objects.none(), inicio, fin)
        assert isinstance(resultado, bytes)
        assert resultado[:4] == b'%PDF'

    def test_genera_pdf_con_rentas(self, db, renta_activa):
        from reportes.generators import generar_pdf_rentas
        from rentas.models import Renta
        resultado = generar_pdf_rentas(
            Renta.objects.filter(pk=renta_activa.pk).select_related('cliente', 'equipo')
        )
        assert isinstance(resultado, bytes)
        assert len(resultado) > 100


class TestGeneradorPDFComprobante:

    def test_retorna_bytes_no_vacios(self, db, renta_activa):
        from reportes.generators import generar_pdf_comprobante_renta
        from rentas.models import Renta
        renta = Renta.objects.prefetch_related('items__equipo').get(pk=renta_activa.pk)
        resultado = generar_pdf_comprobante_renta(renta)
        assert isinstance(resultado, bytes)
        assert len(resultado) > 0

    def test_pdf_comienza_con_firma_pdf(self, db, renta_activa):
        from reportes.generators import generar_pdf_comprobante_renta
        from rentas.models import Renta
        renta = Renta.objects.prefetch_related('items__equipo').get(pk=renta_activa.pk)
        resultado = generar_pdf_comprobante_renta(renta)
        assert resultado[:4] == b'%PDF'
