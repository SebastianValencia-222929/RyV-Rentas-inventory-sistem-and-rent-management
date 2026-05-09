"""
Archivo: generators.py
Descripción: Generadores de reportes PDF para el módulo de reportes del sistema RYV Rentas.
             Implementa la generación de reportes de inventario, rentas por periodo y
             comprobantes individuales de renta usando la librería ReportLab, según lo
             definido en RF-21, RF-22, RF-24 y RN-012 del SRS.
Fecha: 2026-04-07
Versión: 2.0
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.units import cm
import io
from datetime import date

# ─────────────────────────────────────────────────────────────────────────────
# Paleta de colores corporativos
# ─────────────────────────────────────────────────────────────────────────────
COLOR_CABECERA = colors.HexColor('#2C3E50')
COLOR_FILA_ALT = colors.HexColor('#F2F3F4')
COLOR_VERDE    = colors.HexColor('#1A7A4A')
COLOR_ROJO     = colors.HexColor('#C0392B')
COLOR_AZUL     = colors.HexColor('#2471A3')
COLOR_GRIS     = colors.HexColor('#7F8C8D')

METODOS = {
    'efectivo': 'Efectivo',
    'transferencia': 'Transferencia',
    'tarjeta': 'Tarjeta',
    'otro': 'Otro',
    '': '—',
}

CONDICIONES = {
    'bueno': 'Bueno — sin daños',
    'daños_menores': 'Daños menores',
    'inservible': 'Inservible / Pérdida total',
    'extraviado': 'Extraviado',
    '': '—',
}


def _estilos():
    """Retorna el conjunto de estilos con variantes personalizadas."""
    s = getSampleStyleSheet()
    s.add(ParagraphStyle(
        name='Centrado',
        parent=s['Normal'],
        alignment=TA_CENTER,
    ))
    s.add(ParagraphStyle(
        name='Derecha',
        parent=s['Normal'],
        alignment=TA_RIGHT,
    ))
    s.add(ParagraphStyle(
        name='SeccionTitulo',
        parent=s['Heading2'],
        textColor=COLOR_CABECERA,
        spaceAfter=4,
        spaceBefore=10,
    ))
    s.add(ParagraphStyle(
        name='Etiqueta',
        parent=s['Normal'],
        textColor=COLOR_GRIS,
        fontSize=8,
    ))
    s.add(ParagraphStyle(
        name='Valor',
        parent=s['Normal'],
        fontSize=9,
    ))
    s.add(ParagraphStyle(
        name='ValorMonto',
        parent=s['Normal'],
        fontSize=9,
        fontName='Helvetica-Bold',
    ))
    return s


# ─────────────────────────────────────────────────────────────────────────────
# Reporte de Inventario
# ─────────────────────────────────────────────────────────────────────────────
def generar_pdf_inventario(equipos_qs):
    """
    Genera el reporte PDF con el estado actual del inventario de equipos.

    Construye una tabla con el nombre, cantidad total, unidades en renta,
    en mantenimiento y disponibles de cada equipo activo registrado en el
    sistema, según lo definido en RF-21 y CU-23 del SRS.

    Parámetros:
        equipos_qs (QuerySet): QuerySet de instancias de Equipo activos.

    Retorna:
        bytes: Contenido del archivo PDF generado en memoria.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    s = _estilos()
    elementos = []

    elementos.append(Paragraph('RYV Rentas — Reporte de Inventario', s['Title']))
    elementos.append(Paragraph(f'Generado el: {date.today().strftime("%d/%m/%Y")}', s['Normal']))
    elementos.append(Spacer(1, 16))

    datos = [['Equipo', 'Total', 'En Renta', 'Mantenimiento', 'Disponible']]
    for equipo in equipos_qs:
        datos.append([
            equipo.nombre,
            str(equipo.cantidad_total),
            str(equipo.cantidad_en_renta),
            str(equipo.cantidad_en_mantenimiento),
            str(equipo.cantidad_disponible),
        ])

    tabla = Table(datos, colWidths=[190, 60, 70, 90, 80])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_CABECERA),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_FILA_ALT]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ]))
    elementos.append(tabla)
    doc.build(elementos)
    return buffer.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# Reporte de Rentas por Periodo
# ─────────────────────────────────────────────────────────────────────────────
def generar_pdf_rentas(rentas_qs, periodo_inicio=None, periodo_fin=None):
    """
    Genera el reporte PDF de rentas dentro de un periodo seleccionado.

    Muestra el equipo principal (con indicador de equipos adicionales si los hay),
    cliente, fechas, precio, depósito, monto recibido, cargo por daños y cambio.
    Incluye fila de totales al final, cumpliendo con RF-22, RF-24 y RN-012 del SRS.

    Parámetros:
        rentas_qs (QuerySet): QuerySet de instancias de Renta.
        periodo_inicio (date): Fecha de inicio del periodo. Opcional.
        periodo_fin (date): Fecha de fin del periodo. Opcional.

    Retorna:
        bytes: Contenido del archivo PDF generado en memoria.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    s = _estilos()
    elementos = []

    elementos.append(Paragraph('RYV Rentas — Reporte de Rentas por Periodo', s['Title']))
    if periodo_inicio and periodo_fin:
        elementos.append(Paragraph(
            f'Periodo: {periodo_inicio.strftime("%d/%m/%Y")} al {periodo_fin.strftime("%d/%m/%Y")}',
            s['Normal'],
        ))
    elementos.append(Paragraph(f'Generado el: {date.today().strftime("%d/%m/%Y")}', s['Normal']))
    elementos.append(Spacer(1, 16))

    datos = [[
        'Equipo(s)', 'Cant.', 'Cliente', 'Inicio', 'Vencim.', 'Estado',
        'Precio', 'Depósito', 'Recibido', 'Daños', 'Cambio',
    ]]
    total_precio   = 0
    total_recibido = 0
    total_daños    = 0

    for renta in rentas_qs:
        # Usar propiedades multi-equipo
        nombre_eq = renta.nombre_equipo_display
        cantidad_eq = str(renta.cantidad_total_equipos)

        recibido   = f'${renta.monto_recibido:,.2f}' if renta.monto_recibido is not None else '—'
        daños_str  = f'${renta.cargo_daños:,.2f}'    if renta.cargo_daños else '—'
        cambio_str = ''
        if renta.cambio_entregado is not None:
            cambio_str = f'${renta.cambio_entregado:,.2f}'
        elif renta.deposito > renta.precio:
            cambio_str = f'${renta.deposito - renta.precio:,.2f}*'

        datos.append([
            nombre_eq,
            cantidad_eq,
            renta.cliente.nombre,
            renta.fecha_inicio.strftime('%d/%m/%Y'),
            renta.fecha_vencimiento.strftime('%d/%m/%Y'),
            renta.get_estado_display(),
            f'${renta.precio:,.2f}',
            f'${renta.deposito:,.2f}',
            recibido,
            daños_str,
            cambio_str,
        ])
        total_precio += renta.precio
        if renta.monto_recibido is not None:
            total_recibido += renta.monto_recibido
        if renta.cargo_daños:
            total_daños += renta.cargo_daños

    datos.append([
        '', '', '', '', '', 'TOTAL',
        f'${total_precio:,.2f}', '',
        f'${total_recibido:,.2f}',
        f'${total_daños:,.2f}' if total_daños else '—',
        '',
    ])

    tabla = Table(datos, colWidths=[85, 28, 72, 46, 46, 46, 50, 50, 46, 44, 44])
    tabla.setStyle(TableStyle([
        ('BACKGROUND',   (0, 0), (-1, 0),  COLOR_CABECERA),
        ('TEXTCOLOR',    (0, 0), (-1, 0),  colors.white),
        ('FONTNAME',     (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, COLOR_FILA_ALT]),
        ('BACKGROUND',   (0, -1), (-1, -1), COLOR_CABECERA),
        ('TEXTCOLOR',    (0, -1), (-1, -1), colors.white),
        ('FONTNAME',     (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID',         (0, 0), (-1, -1),  0.5, colors.grey),
        ('ALIGN',        (1, 0), (1, -1),   'CENTER'),
        ('ALIGN',        (6, 0), (-1, -1),  'RIGHT'),
        ('FONTSIZE',     (0, 0), (-1, -1),  7.5),
        ('VALIGN',       (0, 0), (-1, -1),  'MIDDLE'),
        ('TOPPADDING',   (0, 0), (-1, -1),  5),
        ('BOTTOMPADDING',(0, 0), (-1, -1),  5),
    ]))
    elementos.append(tabla)
    elementos.append(Spacer(1, 8))
    elementos.append(Paragraph(
        '* El depósito pagado supera el precio total; el excedente se devuelve al cliente.',
        s['Normal'],
    ))
    doc.build(elementos)
    return buffer.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# Comprobante individual de renta
# ─────────────────────────────────────────────────────────────────────────────
def generar_pdf_comprobante_renta(renta):
    """
    Genera un comprobante PDF completo para una renta específica.

    Incluye todos los datos del cliente, equipos rentados (con soporte para
    rentas con múltiples equipos), fechas, resumen financiero, y —si la renta
    está cerrada— el detalle de la devolución y condición del equipo.

    Parámetros:
        renta (Renta): Instancia de la renta a documentar. Debe tener
        prefetch_related('items__equipo') aplicado previamente.

    Retorna:
        bytes: Contenido del archivo PDF generado en memoria.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=2.5*cm, rightMargin=2.5*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )
    s = _estilos()
    elementos = []

    # ── Encabezado ────────────────────────────────────────────────────────────
    elementos.append(Paragraph('RYV Rentas', s['Title']))
    elementos.append(Paragraph(
        f'Comprobante de Renta #{renta.pk}',
        s['Heading2'],
    ))
    elementos.append(Paragraph(
        f'Estado: <b>{renta.get_estado_display()}</b> &nbsp;&nbsp; '
        f'Generado el: {date.today().strftime("%d/%m/%Y")}',
        s['Normal'],
    ))
    elementos.append(HRFlowable(width='100%', thickness=1,
                                color=COLOR_CABECERA, spaceAfter=10))

    # ── Sección: Cliente ──────────────────────────────────────────────────────
    elementos.append(Paragraph('Datos del cliente', s['SeccionTitulo']))
    datos_cliente = [
        ['Nombre', renta.cliente.nombre],
        ['Teléfono', renta.cliente.telefono],
    ]
    if renta.cliente.direccion:
        datos_cliente.append(['Dirección', renta.cliente.direccion])
    if renta.cliente.correo:
        datos_cliente.append(['Correo', renta.cliente.correo])

    tabla_cliente = Table(datos_cliente, colWidths=[120, 330])
    tabla_cliente.setStyle(TableStyle([
        ('FONTNAME',  (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE',  (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), COLOR_GRIS),
        ('VALIGN',    (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, -1), (-1, -1), 0.5, colors.HexColor('#DDDDDD')),
    ]))
    elementos.append(tabla_cliente)

    # ── Sección: Equipos rentados ─────────────────────────────────────────────
    elementos.append(Spacer(1, 6))
    elementos.append(Paragraph('Equipos rentados', s['SeccionTitulo']))

    items = list(renta.items.select_related('equipo').all())
    if items:
        datos_equipos = [['Equipo', 'Cantidad']]
        for item in items:
            datos_equipos.append([item.equipo.nombre, f'{item.cantidad} unidad(es)'])
    else:
        datos_equipos = [
            ['Equipo', 'Cantidad'],
            [renta.equipo.nombre, f'{renta.cantidad} unidad(es)'],
        ]

    tabla_equipos = Table(datos_equipos, colWidths=[340, 110])
    tabla_equipos.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_CABECERA),
        ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
        ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0, 0), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_FILA_ALT]),
        ('GRID',       (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN',      (1, 0), (1, -1), 'CENTER'),
        ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elementos.append(tabla_equipos)

    # ── Sección: Fechas ───────────────────────────────────────────────────────
    elementos.append(Spacer(1, 6))
    elementos.append(Paragraph('Fechas', s['SeccionTitulo']))
    datos_fechas = [
        ['Fecha de inicio', str(renta.fecha_inicio.strftime('%d/%m/%Y'))],
        ['Fecha de vencimiento', str(renta.fecha_vencimiento.strftime('%d/%m/%Y'))],
    ]
    if renta.fecha_devolucion:
        datos_fechas.append(['Fecha de devolución', renta.fecha_devolucion.strftime('%d/%m/%Y')])

    tabla_fechas = Table(datos_fechas, colWidths=[160, 290])
    tabla_fechas.setStyle(TableStyle([
        ('FONTNAME',  (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE',  (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), COLOR_GRIS),
        ('VALIGN',    (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elementos.append(tabla_fechas)

    # ── Sección: Resumen financiero ───────────────────────────────────────────
    elementos.append(Spacer(1, 6))
    elementos.append(Paragraph('Resumen financiero', s['SeccionTitulo']))

    datos_fin = [
        ['Precio total', f'${renta.precio:,.2f}'],
        ['Depósito pagado',
         f'${renta.deposito:,.2f}'
         + (f'  ({METODOS.get(renta.metodo_pago, "—")})' if renta.metodo_pago else '')],
    ]

    if renta.estado == 'activa':
        datos_fin.append(['Saldo pendiente', f'${renta.saldo_pendiente:,.2f}'])
    else:
        if renta.cargo_daños:
            datos_fin.append(['Cargo por daños', f'${renta.cargo_daños:,.2f}'])
        if renta.monto_recibido is not None:
            metodo_c = METODOS.get(renta.metodo_pago_cierre, '—') if renta.metodo_pago_cierre else ''
            datos_fin.append([
                'Monto recibido al cierre',
                f'${renta.monto_recibido:,.2f}'
                + (f'  ({metodo_c})' if metodo_c else ''),
            ])
        if renta.cambio_entregado is not None:
            datos_fin.append(['Cambio entregado', f'${renta.cambio_entregado:,.2f}'])
        elif renta.sobrante_deposito:
            datos_fin.append(['Cambio a devolver', f'${renta.sobrante_deposito:,.2f}'])

    tabla_fin = Table(datos_fin, colWidths=[180, 270])
    tabla_fin.setStyle(TableStyle([
        ('FONTNAME',  (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE',  (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), COLOR_GRIS),
        ('VALIGN',    (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LINEABOVE', (0, -1), (-1, -1), 0.5, colors.grey),
        ('FONTNAME',  (1, -1), (1, -1), 'Helvetica-Bold'),
    ]))
    elementos.append(tabla_fin)

    # ── Sección: Condición de devolución (solo si está cerrada con condición) ─
    if renta.condicion_devolucion:
        elementos.append(Spacer(1, 6))
        elementos.append(Paragraph('Devolución del equipo', s['SeccionTitulo']))
        datos_dev = [
            ['Condición', CONDICIONES.get(renta.condicion_devolucion, renta.condicion_devolucion)],
        ]
        if renta.cargo_daños:
            datos_dev.append(['Cargo por daños', f'${renta.cargo_daños:,.2f}'])
        tabla_dev = Table(datos_dev, colWidths=[180, 270])
        tabla_dev.setStyle(TableStyle([
            ('FONTNAME',  (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE',  (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (0, -1), COLOR_GRIS),
            ('VALIGN',    (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING',    (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elementos.append(tabla_dev)

    # ── Sección: Notas ────────────────────────────────────────────────────────
    if renta.notas:
        elementos.append(Spacer(1, 6))
        elementos.append(Paragraph('Notas', s['SeccionTitulo']))
        elementos.append(Paragraph(renta.notas, s['Normal']))

    # ── Pie de página ─────────────────────────────────────────────────────────
    elementos.append(Spacer(1, 20))
    elementos.append(HRFlowable(width='100%', thickness=0.5,
                                color=COLOR_GRIS, spaceAfter=6))
    registrado_por = '—'
    if renta.registrada_por:
        registrado_por = (
            renta.registrada_por.get_full_name()
            or renta.registrada_por.username
        )
    elementos.append(Paragraph(
        f'Registrada por: <b>{registrado_por}</b> &nbsp;|&nbsp; '
        f'Fecha de registro: <b>{renta.created_at.strftime("%d/%m/%Y %H:%M")}</b>',
        s['Normal'],
    ))

    doc.build(elementos)
    return buffer.getvalue()
