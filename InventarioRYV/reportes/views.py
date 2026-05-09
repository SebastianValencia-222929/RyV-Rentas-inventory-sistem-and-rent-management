"""
Archivo: views.py
Descripción: Vistas para el módulo de reportes del sistema RYV Rentas.
             Gestiona la generación y descarga de reportes PDF de inventario,
             rentas por periodo, comprobantes individuales de renta y el
             historial de reportes generados, según lo definido en RF-21 al
             RF-25 y RN-012 del SRS.
Fecha: 2026-04-07
Versión: 2.0
"""
import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.contrib import messages
from .models import ReporteGenerado
from .forms import ReporteRentasForm
from .generators import (
    generar_pdf_inventario,
    generar_pdf_rentas,
    generar_pdf_comprobante_renta,
)
from inventario.models import Equipo
from rentas.models import Renta
from authentication.decorators import admin_required


@admin_required
def panel_reportes(request):
    """
    Muestra el panel principal de generación de reportes.

    Presenta los formularios para generar reportes de inventario y de rentas
    por periodo, junto con los cinco reportes más recientes generados,
    según lo definido en RF-21, RF-22 y CU-22 del SRS.

    Parámetros:
        request (HttpRequest): Solicitud HTTP.

    Retorna:
        HttpResponse: Renderiza la plantilla reportes/panel.html con el
        formulario de rentas y los reportes recientes.
    """
    form_rentas = ReporteRentasForm()
    reportes_recientes = ReporteGenerado.objects.select_related(
        'generado_por'
    )[:5]

    contexto = {
        'form_rentas': form_rentas,
        'reportes_recientes': reportes_recientes,
    }
    return render(request, 'reportes/panel.html', contexto)


@admin_required
def generar_inventario(request):
    """
    Genera y descarga el reporte PDF del estado actual del inventario.

    Consulta todos los equipos activos, genera el PDF y registra el reporte
    en el historial para su descarga posterior, según lo definido en RF-21
    y CU-23 del SRS.

    Parámetros:
        request (HttpRequest): Solicitud HTTP. Debe ser de método POST.

    Retorna:
        HttpResponse: Descarga directa del archivo PDF si la generación
        es exitosa, o redirige al panel de reportes con mensaje de error si falla.
    """
    if request.method == 'POST':
        try:
            equipos = Equipo.objects.filter(activo=True).order_by('nombre')
            pdf_bytes = generar_pdf_inventario(equipos)

            nombre_archivo = (
                'inventario_'
                + datetime.date.today().strftime('%Y%m%d')
                + '.pdf'
            )

            ReporteGenerado.objects.create(
                tipo='inventario',
                generado_por=request.user,
                archivo_nombre=nombre_archivo,
            )

            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = (
                f'attachment; filename="{nombre_archivo}"'
            )
            return response

        except Exception:
            messages.error(request, 'Error al generar el reporte de inventario.')

    return redirect('reportes:panel')


@admin_required
def generar_rentas(request):
    """
    Genera y descarga el reporte PDF de rentas dentro de un periodo seleccionado.

    Filtra las rentas por el rango de fechas indicado, genera el PDF con el
    listado de rentas, precios e ingreso total del periodo, y registra el
    reporte en el historial, según lo definido en RF-22, RN-012 y CU-24 del SRS.

    Parámetros:
        request (HttpRequest): Solicitud HTTP. Debe ser de método POST con
        los campos periodo_inicio y periodo_fin del formulario de rentas.

    Retorna:
        HttpResponse: Descarga directa del archivo PDF si la generación
        es exitosa, o redirige al panel de reportes con mensaje de error si falla.
    """
    if request.method == 'POST':
        form = ReporteRentasForm(request.POST)
        if form.is_valid():
            try:
                inicio = form.cleaned_data['periodo_inicio']
                fin    = form.cleaned_data['periodo_fin']

                rentas = (
                    Renta.objects
                    .filter(fecha_inicio__gte=inicio, fecha_inicio__lte=fin)
                    .select_related('equipo', 'cliente', 'registrada_por')
                    .prefetch_related('items__equipo')
                    .order_by('fecha_inicio')
                )

                pdf_bytes = generar_pdf_rentas(rentas, inicio, fin)

                nombre_archivo = (
                    'rentas_'
                    + inicio.strftime('%Y%m%d')
                    + '_'
                    + fin.strftime('%Y%m%d')
                    + '.pdf'
                )

                ReporteGenerado.objects.create(
                    tipo='rentas',
                    generado_por=request.user,
                    archivo_nombre=nombre_archivo,
                    periodo_inicio=inicio,
                    periodo_fin=fin,
                )

                response = HttpResponse(pdf_bytes, content_type='application/pdf')
                response['Content-Disposition'] = (
                    f'attachment; filename="{nombre_archivo}"'
                )
                return response

            except Exception:
                messages.error(request, 'Error al generar el reporte de rentas.')
        else:
            messages.error(request, 'Fechas inválidas.')

    return redirect('reportes:panel')


@admin_required
def comprobante_renta(request, pk):
    """
    Genera y descarga el comprobante PDF completo de una renta específica.

    Incluye datos del cliente, equipos rentados, fechas, resumen financiero
    y —si la renta está finalizada— la información de devolución y condición
    del equipo.

    Parámetros:
        request (HttpRequest): Solicitud HTTP.
        pk (int): Identificador único de la renta.

    Retorna:
        HttpResponse: Descarga directa del archivo PDF del comprobante.
    """
    renta = get_object_or_404(
        Renta.objects
        .select_related('equipo', 'cliente', 'registrada_por')
        .prefetch_related('items__equipo'),
        pk=pk,
    )

    try:
        pdf_bytes = generar_pdf_comprobante_renta(renta)

        nombre_archivo = f'renta_{renta.pk}_{datetime.date.today().strftime("%Y%m%d")}.pdf'

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'attachment; filename="{nombre_archivo}"'
        )
        return response

    except Exception:
        messages.error(request, 'Error al generar el comprobante de la renta.')
        # Redirigir al detalle correcto según el estado
        if renta.estado == 'activa':
            return redirect('rentas:detalle', pk=pk)
        return redirect('historial:detalle', pk=pk)


@admin_required
def descargar_pdf(request, pk):
    """
    Regenera y descarga un reporte PDF previamente registrado en el historial.

    Recupera los metadatos del reporte y lo regenera con los datos actuales
    del sistema, sin almacenar el archivo físico, según lo definido en
    RF-25 y CU-25 del SRS.

    Parámetros:
        request (HttpRequest): Solicitud HTTP.
        pk (int): Identificador único del reporte a descargar.

    Retorna:
        HttpResponse: Descarga directa del archivo PDF regenerado si es exitoso,
        o redirige al historial de reportes con mensaje de error si falla.
    """
    reporte = get_object_or_404(ReporteGenerado, pk=pk)

    try:
        if reporte.tipo == 'inventario':
            equipos = Equipo.objects.filter(activo=True).order_by('nombre')
            pdf_bytes = generar_pdf_inventario(equipos)
        else:
            rentas = (
                Renta.objects
                .filter(
                    fecha_inicio__gte=reporte.periodo_inicio,
                    fecha_inicio__lte=reporte.periodo_fin,
                )
                .select_related('equipo', 'cliente', 'registrada_por')
                .prefetch_related('items__equipo')
            )
            pdf_bytes = generar_pdf_rentas(
                rentas,
                reporte.periodo_inicio,
                reporte.periodo_fin,
            )

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'attachment; filename="{reporte.archivo_nombre}"'
        )
        return response

    except Exception:
        messages.error(request, 'Error al re-generar el reporte.')
        return redirect('reportes:historial')


@admin_required
def historial_reportes(request):
    """
    Muestra el listado completo de reportes generados anteriormente.

    Presenta todos los reportes registrados en el historial ordenados por
    fecha de generación descendente, permitiendo identificarlos por tipo,
    fecha y periodo cubierto, según lo definido en RF-25 y CU-26 del SRS.

    Parámetros:
        request (HttpRequest): Solicitud HTTP.

    Retorna:
        HttpResponse: Renderiza la plantilla reportes/historial.html con
        el listado completo de reportes generados.
    """
    reportes = ReporteGenerado.objects.select_related(
        'generado_por'
    ).order_by('-fecha_generacion')

    return render(
        request,
        'reportes/historial.html',
        {'reportes': reportes},
    )
