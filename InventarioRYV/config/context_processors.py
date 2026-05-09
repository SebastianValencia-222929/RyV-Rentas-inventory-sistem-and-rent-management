"""
Archivo: context_processors.py
Descripción: Procesadores de contexto globales para el sistema RYV Rentas.
             Inyecta en todas las plantillas las alertas de vencimiento de rentas
             y el conteo de solicitudes pendientes, según lo definido en RF-19,
             RN-004 y CU-27 del SRS.
Fecha: 2026-04-07
Versión: 1.0
"""
def alertas_globales(request):
    """
    Inyecta variables de alertas y solicitudes en el contexto de todas las plantillas.

    Calcula y expone las rentas próximas a vencer, las rentas ya vencidas sin cerrar
    y el conteo de solicitudes pendientes para el Administrador. Si el usuario no está
    autenticado, retorna un diccionario vacío sin realizar consultas a la base de datos,
    según lo definido en RF-19 y RN-004 del SRS.

    Parámetros:
        request (HttpRequest): Solicitud HTTP con el usuario autenticado.

    Retorna:
        dict: Diccionario con las siguientes claves disponibles en todas las plantillas:
            - alertas_proximas (QuerySet): Rentas activas con vencimiento en 3 días o menos.
            - alertas_vencidas (QuerySet): Rentas activas cuya fecha de vencimiento ya pasó.
            - total_alertas (int): Suma de rentas próximas a vencer y rentas vencidas.
            - solicitudes_pendientes (int): Conteo de solicitudes pendientes. Solo se
              calcula si el usuario autenticado es Administrador, en caso contrario es 0.
            O un diccionario vacío si el usuario no está autenticado.
    """
    if not request.user.is_authenticated:
        return {}

    from rentas.models import Renta
    from solicitudes.models import Solicitud
    from datetime import date, timedelta

    hoy = date.today()
    limite = hoy + timedelta(days=3)

    rentas_activas = Renta.objects.filter(estado='activa')

    alertas_proximas = rentas_activas.filter(
        fecha_vencimiento__gte=hoy,
        fecha_vencimiento__lte=limite
    ).select_related('equipo', 'cliente')

    alertas_vencidas = rentas_activas.filter(
        fecha_vencimiento__lt=hoy
    ).select_related('equipo', 'cliente')

    solicitudes_pendientes = 0
    mis_solicitudes_pendientes = 0
    if request.user.es_administrador():
        solicitudes_pendientes = Solicitud.objects.filter(
            estado='pendiente'
        ).count()
    else:
        mis_solicitudes_pendientes = Solicitud.objects.filter(
            solicitante=request.user,
            estado='pendiente'
        ).count()

    cuenta_proximas = alertas_proximas.count()
    cuenta_vencidas = alertas_vencidas.count()

    # Para admin: proximas + vencidas + solicitudes pendientes de empleados
    # Para empleado: proximas + vencidas + sus propias solicitudes pendientes
    if request.user.es_administrador():
        total_alertas = cuenta_proximas + cuenta_vencidas + solicitudes_pendientes
    else:
        total_alertas = cuenta_proximas + cuenta_vencidas + mis_solicitudes_pendientes

    return {
        'alertas_proximas': alertas_proximas,
        'alertas_vencidas': alertas_vencidas,
        'total_alertas': total_alertas,
        'solicitudes_pendientes': solicitudes_pendientes,
        'mis_solicitudes_pendientes': mis_solicitudes_pendientes,
    }
