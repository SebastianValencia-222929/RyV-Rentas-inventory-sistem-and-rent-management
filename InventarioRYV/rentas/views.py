"""
Archivo: views.py
Descripción: Vistas para el módulo de rentas del sistema RYV Rentas.
             Gestiona el registro, visualización, finalización y solicitud
             de rentas, así como el cierre solicitado por el Empleado,
             según lo definido en RF-13 al RF-19 y RN-001 al RN-005,
             RN-008 del SRS.
Fecha: 2026-04-07
Versión: 1.0
"""
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from datetime import date
from .models import Renta, Cliente, RentaEquipo
from .forms import RentaForm, SolicitudRentaForm, FinalizarRentaForm, RentaEditForm, equipos_con_disponibles
from inventario.models import Equipo
from authentication.decorators import admin_required, empleado_o_admin
from solicitudes.models import Solicitud


@empleado_o_admin
def rentas_activas(request):
    """
    Muestra el listado paginado de todas las rentas con estado activa.

    Permite filtrar por nombre de cliente y nombre de equipo. Los resultados
    se ordenan por fecha de vencimiento ascendente para priorizar las rentas
    más próximas a vencer, según lo definido en RF-15 del SRS.

    Parámetros:
        request (HttpRequest): Solicitud HTTP. Puede incluir los parámetros
        GET 'cliente' y 'equipo' para filtrar los resultados.

    Retorna:
        HttpResponse: Renderiza la plantilla rentas/activas.html con el
        listado paginado de rentas activas y los filtros aplicados.
    """
    rentas = Renta.objects.filter(
        estado='activa'
    ).select_related('equipo', 'cliente', 'registrada_por')

    cliente_nombre = request.GET.get('cliente', '').strip()
    equipo_nombre = request.GET.get('equipo', '').strip()

    if cliente_nombre:
        rentas = rentas.filter(
            cliente__nombre__icontains=cliente_nombre
        )
    if equipo_nombre:
        rentas = rentas.filter(
            equipo__nombre__icontains=equipo_nombre
        )

    rentas = rentas.order_by('fecha_vencimiento')

    paginator = Paginator(rentas, 20)
    page = request.GET.get('page', 1)
    rentas_page = paginator.get_page(page)

    contexto = {
        'rentas': rentas_page,
        'filtro_cliente': cliente_nombre,
        'filtro_equipo': equipo_nombre,
        'hoy': date.today(),
    }
    return render(request, 'rentas/activas.html', contexto)


@empleado_o_admin
def detalle_renta(request, pk):
    """
    Muestra el detalle completo de una renta.

    Si el usuario es Administrador y la renta está activa, incluye el
    formulario de finalización para registrar la devolución del equipo,
    según lo definido en RF-16 del SRS.

    Parámetros:
        request (HttpRequest): Solicitud HTTP.
        pk (int): Identificador único de la renta a consultar.

    Retorna:
        HttpResponse: Renderiza la plantilla rentas/detalle.html con los
        datos completos de la renta y el formulario de finalización si aplica,
        o devuelve 404 si la renta no existe.
    """
    renta = get_object_or_404(
        Renta.objects.select_related(
            'equipo', 'cliente', 'registrada_por'
        ),
        pk=pk,
    )
    form_finalizar = None
    if (
        renta.estado == 'activa'
        and request.user.es_administrador()
    ):
        form_finalizar = FinalizarRentaForm()

    contexto = {
        'renta': renta,
        'hoy': date.today(),
        'form_finalizar': form_finalizar,
    }
    return render(request, 'rentas/detalle.html', contexto)


def _parsear_equipos_post(post_data):
    """
    Extrae las filas de equipos y cantidades enviadas desde el formulario POST.

    Lee los campos con formato equipo_0/cantidad_0, equipo_1/cantidad_1, etc.,
    hasta que no encuentre más índices consecutivos.

    Parámetros:
        post_data (QueryDict): Datos del formulario POST de la solicitud HTTP.

    Retorna:
        list[tuple[str, int]]: Lista de tuplas con el pk del equipo como cadena
        y la cantidad como entero. Retorna una lista vacía si no hay filas.
    """
    items = []
    i = 0
    while True:
        pk_str = post_data.get(f'equipo_{i}')
        if pk_str is None:
            break
        cantidad_str = post_data.get(f'cantidad_{i}', '1')
        try:
            cantidad = max(1, int(cantidad_str))
        except (ValueError, TypeError):
            cantidad = 1
        items.append((pk_str, cantidad))
        i += 1
    return items


@admin_required
def nueva_renta(request):
    """
    Gestiona el registro de una nueva renta directamente por el Administrador.

    Valida la disponibilidad de los equipos seleccionados, crea o recupera
    el cliente, registra la renta y actualiza los contadores de unidades en
    renta de cada equipo, según lo definido en RF-13 y RN-001, RN-002 del SRS.

    Parámetros:
        request (HttpRequest): Solicitud HTTP. En método POST debe contener
        los datos del formulario de nueva renta y las filas de equipos con
        formato equipo_N/cantidad_N. Puede incluir el parámetro GET 'equipo'
        para preseleccionar un equipo.

    Retorna:
        HttpResponse: Redirige al listado de rentas activas si el registro
        es exitoso, o renderiza el formulario con errores si falla.
    """
    equipo_pk = request.GET.get('equipo')
    equipos_qs = equipos_con_disponibles()

    if request.method == 'POST':
        form = RentaForm(request.POST)

        # Parsear filas de equipos del POST
        filas_raw = _parsear_equipos_post(request.POST)
        equipo_items = []
        errores_equipos = []

        if not filas_raw:
            errores_equipos.append('Debes seleccionar al menos un equipo.')
        else:
            equipos_vistos = {}  # pk → cantidad acumulada (para detectar duplicados)
            for pk_str, cantidad in filas_raw:
                try:
                    equipo = Equipo.objects.get(pk=pk_str, activo=True)
                except Equipo.DoesNotExist:
                    errores_equipos.append(f'Equipo con ID {pk_str} no válido.')
                    continue
                # Acumular si el mismo equipo aparece varias veces
                if equipo.pk in equipos_vistos:
                    equipos_vistos[equipo.pk] = (equipo, equipos_vistos[equipo.pk][1] + cantidad)
                else:
                    equipos_vistos[equipo.pk] = (equipo, cantidad)

            for equipo, cantidad in equipos_vistos.values():
                if not equipo.tiene_disponibles(cantidad):
                    errores_equipos.append(
                        f'Solo hay {equipo.cantidad_disponible} unidad(es) '
                        f'disponible(s) de "{equipo.nombre}".'
                    )
                else:
                    equipo_items.append((equipo, cantidad))

        if errores_equipos or not equipo_items:
            for err in errores_equipos:
                messages.error(request, err)
            # Mantener los valores seleccionados para re-render
            return render(request, 'rentas/nueva.html', {
                'form': form,
                'equipos_disponibles': equipos_qs,
                'equipo_inicial_pk': equipo_pk,
            })

        if form.is_valid():
            try:
                cliente, _ = Cliente.objects.get_or_create(
                    nombre=form.cleaned_data['cliente_nombre'],
                    telefono=form.cleaned_data['cliente_telefono'],
                    defaults={
                        'direccion': form.cleaned_data.get('cliente_direccion', ''),
                        'correo': form.cleaned_data.get('cliente_correo', ''),
                    },
                )

                primer_equipo, primer_cantidad = equipo_items[0]
                renta = Renta.objects.create(
                    equipo=primer_equipo,
                    cliente=cliente,
                    registrada_por=request.user,
                    cantidad=primer_cantidad,
                    fecha_inicio=form.cleaned_data['fecha_inicio'],
                    fecha_vencimiento=form.cleaned_data['fecha_vencimiento'],
                    precio=form.cleaned_data['precio'],
                    deposito=form.cleaned_data.get('deposito') or 0,
                    metodo_pago=form.cleaned_data.get('metodo_pago', ''),
                    notas=form.cleaned_data.get('notas', ''),
                )

                # Crear RentaEquipo y actualizar contadores
                for equipo, cantidad in equipo_items:
                    RentaEquipo.objects.create(
                        renta=renta, equipo=equipo, cantidad=cantidad
                    )
                    equipo.cantidad_en_renta += cantidad
                    equipo.save()

                nombres = ', '.join(
                    f'{cantidad}x "{eq.nombre}"'
                    for eq, cantidad in equipo_items
                )
                messages.success(
                    request,
                    f'Renta registrada: {nombres} para {cliente.nombre}.',
                )
                return redirect('rentas:lista')

            except Exception:
                messages.error(
                    request,
                    'Ocurrió un error al crear la renta. Intenta de nuevo.',
                )
    else:
        form = RentaForm()

    return render(request, 'rentas/nueva.html', {
        'form': form,
        'equipos_disponibles': equipos_qs,
        'equipo_inicial_pk': equipo_pk,
    })


@admin_required
def finalizar_renta(request, pk):
    """
    Gestiona la finalización de una renta activa y la liberación de los equipos.

    Valida el monto recibido contra el saldo pendiente incluyendo cargos por
    daños, registra la condición de devolución del equipo y actualiza los
    contadores de unidades en renta, cumpliendo con RF-17 y RN-003 del SRS.

    Parámetros:
        request (HttpRequest): Solicitud HTTP. Debe ser de método POST con
        los datos del formulario de finalización: monto recibido, método de
        pago al cierre, condición de devolución y notas opcionales.
        pk (int): Identificador único de la renta a finalizar.

    Retorna:
        HttpResponse: Redirige al detalle del historial si la finalización
        es exitosa, renderiza el formulario con errores si la validación
        falla, o redirige al detalle de la renta si la solicitud es GET.
    """
    renta = get_object_or_404(Renta, pk=pk, estado='activa')

    if request.method == 'POST':
        form = FinalizarRentaForm(request.POST)
        if form.is_valid():
            try:
                monto_recibido = form.cleaned_data.get('monto_recibido')
                cargo_daños = form.cleaned_data.get('cargo_daños') or Decimal('0')

                # Cálculo neto: precio - depósito + daños
                neto = renta.precio - renta.deposito + cargo_daños

                # Validar que si hay saldo pendiente el cliente haya pagado
                if neto > 0:
                    if monto_recibido is None:
                        form.add_error(
                            'monto_recibido',
                            f'El cliente debe pagar ${neto:.2f}. '
                            'Ingresa el monto recibido.',
                        )
                    elif monto_recibido < neto:
                        form.add_error(
                            'monto_recibido',
                            f'El monto recibido (${monto_recibido:.2f}) '
                            f'no cubre el saldo pendiente (${neto:.2f}). '
                            f'Faltan ${neto - monto_recibido:.2f}.',
                        )
                    if not form.cleaned_data.get('metodo_pago_cierre'):
                        form.add_error(
                            'metodo_pago_cierre',
                            'Selecciona el método de pago al cierre.',
                        )

                if form.errors:
                    contexto = {
                        'renta': renta,
                        'hoy': date.today(),
                        'form_finalizar': form,
                    }
                    return render(request, 'rentas/detalle.html', contexto)

                renta.estado = 'finalizada'
                renta.fecha_devolucion = date.today()
                renta.metodo_pago_cierre = form.cleaned_data.get('metodo_pago_cierre', '')
                renta.condicion_devolucion = form.cleaned_data.get('condicion_devolucion', '')
                renta.cargo_daños = cargo_daños if cargo_daños > 0 else None

                if neto <= 0:
                    renta.monto_recibido = Decimal('0')
                    renta.cambio_entregado = abs(neto)
                else:
                    renta.monto_recibido = monto_recibido
                    renta.cambio_entregado = monto_recibido - neto

                notas_dev = form.cleaned_data.get('notas_devolucion', '')
                if notas_dev:
                    separador = '\n' if renta.notas else ''
                    renta.notas = renta.notas + separador + '[Devolución] ' + notas_dev

                renta.save()

                # RN-003: liberar unidades (soporta multi-equipo)
                items = list(renta.items.select_related('equipo').all())
                if items:
                    for item in items:
                        item.equipo.cantidad_en_renta = max(
                            0, item.equipo.cantidad_en_renta - item.cantidad
                        )
                        item.equipo.save()
                    nombres = ', '.join(
                        f'{i.cantidad}x "{i.equipo.nombre}"' for i in items
                    )
                else:
                    equipo = renta.equipo
                    equipo.cantidad_en_renta = max(
                        0, equipo.cantidad_en_renta - renta.cantidad
                    )
                    equipo.save()
                    items = []
                    nombres = f'{renta.cantidad}x "{equipo.nombre}"'

                # Ajuste de inventario por daños/pérdida
                condicion_final = form.cleaned_data.get('condicion_devolucion', '')
                if condicion_final and condicion_final != 'bueno':
                    if items:
                        for item in items:
                            try:
                                afectados = max(
                                    0,
                                    min(
                                        int(request.POST.get(f'afectados_{item.pk}', 0)),
                                        item.cantidad,
                                    ),
                                )
                            except (ValueError, TypeError):
                                afectados = 0
                            destino = request.POST.get(f'destino_{item.pk}', 'eliminar')
                            if afectados > 0:
                                eq = item.equipo
                                if destino == 'eliminar':
                                    eq.cantidad_total = max(0, eq.cantidad_total - afectados)
                                elif destino == 'mantenimiento':
                                    eq.cantidad_en_mantenimiento = (
                                        eq.cantidad_en_mantenimiento + afectados
                                    )
                                eq.save()
                    else:
                        # Legado: renta sin items, usa equipo principal
                        try:
                            afectados = max(
                                0,
                                min(
                                    int(request.POST.get('afectados_legacy', 0)),
                                    renta.cantidad,
                                ),
                            )
                        except (ValueError, TypeError):
                            afectados = 0
                        destino = request.POST.get('destino_legacy', 'eliminar')
                        if afectados > 0:
                            eq = renta.equipo
                            if destino == 'eliminar':
                                eq.cantidad_total = max(0, eq.cantidad_total - afectados)
                            elif destino == 'mantenimiento':
                                eq.cantidad_en_mantenimiento = (
                                    eq.cantidad_en_mantenimiento + afectados
                                )
                            eq.save()

                messages.success(
                    request,
                    f'Renta finalizada. {nombres} liberado(s).',
                )
                return redirect('historial:detalle', pk=renta.pk)

            except Exception:
                messages.error(
                    request,
                    'Error al finalizar la renta. Intenta de nuevo.',
                )
        else:
            # Errores de validación del form (ej. cargo_daños faltante)
            contexto = {
                'renta': renta,
                'hoy': date.today(),
                'form_finalizar': form,
            }
            return render(request, 'rentas/detalle.html', contexto)

    return redirect('rentas:detalle', pk=pk)


@empleado_o_admin
def solicitar_renta(request):
    """
    Gestiona el envío de una solicitud de nueva renta por parte del Empleado.

    Valida la disponibilidad de los equipos seleccionados y crea una solicitud
    pendiente de aprobación por el Administrador. Si el usuario es Administrador,
    redirige directamente a la vista de nueva renta, cumpliendo con RF-14
    y RN-008 del SRS.

    Parámetros:
        request (HttpRequest): Solicitud HTTP. En método POST debe contener
        los datos del formulario de solicitud y las filas de equipos con
        formato equipo_N/cantidad_N. Puede incluir el parámetro GET 'equipo'
        para preseleccionar un equipo.

    Retorna:
        HttpResponse: Redirige al listado de rentas activas si la solicitud
        se envía exitosamente, redirige a nueva renta si el usuario es
        Administrador, o renderiza el formulario con errores si falla.
    """
    if request.user.es_administrador():
        return redirect('rentas:nueva')

    equipos_qs = equipos_con_disponibles()
    equipo_pk = request.GET.get('equipo')

    if request.method == 'POST':
        form = SolicitudRentaForm(request.POST)

        # Parsear filas de equipos del POST
        filas_raw = _parsear_equipos_post(request.POST)
        equipo_items = []
        errores_equipos = []

        if not filas_raw:
            errores_equipos.append('Debes seleccionar al menos un equipo.')
        else:
            equipos_vistos = {}
            for pk_str, cantidad in filas_raw:
                try:
                    equipo = Equipo.objects.get(pk=pk_str, activo=True)
                except Equipo.DoesNotExist:
                    errores_equipos.append(f'Equipo con ID {pk_str} no válido.')
                    continue
                if equipo.pk in equipos_vistos:
                    equipos_vistos[equipo.pk] = (equipo, equipos_vistos[equipo.pk][1] + cantidad)
                else:
                    equipos_vistos[equipo.pk] = (equipo, cantidad)

            for equipo, cantidad in equipos_vistos.values():
                if not equipo.tiene_disponibles(cantidad):
                    errores_equipos.append(
                        f'Solo hay {equipo.cantidad_disponible} unidad(es) '
                        f'disponible(s) de "{equipo.nombre}".'
                    )
                else:
                    equipo_items.append((equipo, cantidad))

        if errores_equipos or not equipo_items:
            for err in errores_equipos:
                messages.error(request, err)
            return render(request, 'rentas/solicitar.html', {
                'form': form,
                'equipos_disponibles': equipos_qs,
                'equipo_inicial_pk': equipo_pk,
            })

        if form.is_valid():
            primer_equipo = equipo_items[0][0]
            datos_json = {
                'equipos': [
                    {'equipo_id': eq.pk, 'cantidad': cant}
                    for eq, cant in equipo_items
                ],
                'cliente_nombre': form.cleaned_data['cliente_nombre'],
                'cliente_telefono': form.cleaned_data['cliente_telefono'],
                'cliente_direccion': form.cleaned_data.get('cliente_direccion', ''),
                'cliente_correo': form.cleaned_data.get('cliente_correo', ''),
                'fecha_inicio': str(form.cleaned_data['fecha_inicio']),
                'fecha_vencimiento': str(form.cleaned_data['fecha_vencimiento']),
                'precio': str(form.cleaned_data['precio']),
                'deposito': str(form.cleaned_data.get('deposito') or 0),
                'metodo_pago': form.cleaned_data.get('metodo_pago', ''),
                'notas': form.cleaned_data.get('notas', ''),
            }

            Solicitud.objects.create(
                tipo='nueva_renta',
                solicitante=request.user,
                equipo=primer_equipo,
                comentario=form.cleaned_data['comentario'],
                datos_json=datos_json,
            )
            messages.success(
                request,
                'Solicitud de renta enviada al administrador.',
            )
            return redirect('rentas:lista')
    else:
        form = SolicitudRentaForm()

    return render(request, 'rentas/solicitar.html', {
        'form': form,
        'equipos_disponibles': equipos_qs,
        'equipo_inicial_pk': equipo_pk,
    })


@empleado_o_admin
def solicitar_cierre(request, pk):
    """
    Gestiona el envío de una solicitud de cierre de renta por parte del Empleado.

    Crea una solicitud de tipo cierre_renta pendiente de aprobación por el
    Administrador. Si el usuario es Administrador, redirige directamente a
    la vista de finalización, cumpliendo con RF-18 y RN-008 del SRS.

    Parámetros:
        request (HttpRequest): Solicitud HTTP. En método POST puede incluir
        un comentario opcional explicando el motivo del cierre.
        pk (int): Identificador único de la renta activa a cerrar.

    Retorna:
        HttpResponse: Redirige al detalle de la renta si la solicitud se
        envía exitosamente, redirige a finalizar renta si el usuario es
        Administrador, o renderiza la plantilla de detalle con el formulario
        de cierre si la solicitud es GET.
    """
    if request.user.es_administrador():
        return redirect('rentas:finalizar', pk=pk)

    renta = get_object_or_404(Renta, pk=pk, estado='activa')

    if request.method == 'POST':
        comentario = request.POST.get('comentario', '').strip()
        if not comentario:
            comentario = 'Solicitud de cierre de renta.'

        Solicitud.objects.create(
            tipo='cierre_renta',
            solicitante=request.user,
            renta=renta,
            equipo=renta.equipo,
            comentario=comentario,
        )
        messages.success(
            request,
            'Solicitud de cierre enviada al administrador.',
        )
        return redirect('rentas:detalle', pk=pk)

    contexto = {
        'renta': renta,
        'hoy': date.today(),
        'solicitar_cierre': True,
    }
    return render(request, 'rentas/detalle.html', contexto)


@admin_required
def editar_renta(request, pk):
    """
    Permite al Administrador modificar los datos de una renta activa.

    Actualiza fechas, precio, depósito, método de pago y notas. No permite
    editar equipos ni cliente directamente desde esta vista.

    Parámetros:
        request (HttpRequest): Solicitud HTTP.
        pk (int): Identificador único de la renta a editar.

    Retorna:
        HttpResponse: Redirige al detalle de la renta si la edición es exitosa,
        o renderiza el formulario con errores si la validación falla.
    """
    renta = get_object_or_404(Renta, pk=pk, estado='activa')

    if request.method == 'POST':
        form = RentaEditForm(request.POST, instance=renta)
        if form.is_valid():
            form.save()
            messages.success(request, 'Renta actualizada correctamente.')
            return redirect('rentas:detalle', pk=renta.pk)
    else:
        form = RentaEditForm(instance=renta)

    return render(request, 'rentas/editar.html', {
        'form': form,
        'renta': renta,
    })


@admin_required
def eliminar_renta(request, pk):
    """
    Permite al Administrador eliminar una renta activa y liberar sus equipos.

    Libera las unidades en renta de cada equipo asociado antes de eliminar
    el registro. Solo acepta método POST para evitar eliminaciones accidentales.

    Parámetros:
        request (HttpRequest): Solicitud HTTP. Debe ser de método POST.
        pk (int): Identificador único de la renta a eliminar.

    Retorna:
        HttpResponse: Redirige al listado de rentas activas si la eliminación
        es exitosa, o al detalle si la solicitud es GET.
    """
    renta = get_object_or_404(Renta, pk=pk, estado='activa')

    if request.method == 'POST':
        # Liberar unidades antes de eliminar
        items = renta.items.select_related('equipo').all()
        if items:
            for item in items:
                item.equipo.cantidad_en_renta = max(
                    0, item.equipo.cantidad_en_renta - item.cantidad
                )
                item.equipo.save()
        else:
            equipo = renta.equipo
            equipo.cantidad_en_renta = max(
                0, equipo.cantidad_en_renta - renta.cantidad
            )
            equipo.save()

        nombre_cliente = renta.cliente.nombre
        renta.delete()
        messages.success(
            request,
            f'Renta de {nombre_cliente} eliminada. Unidades liberadas.',
        )
        return redirect('rentas:lista')

    return redirect('rentas:detalle', pk=pk)
