"""URLs para el módulo de reportes."""
from django.urls import path
from . import views

app_name = 'reportes'

urlpatterns = [
    path('', views.panel_reportes, name='panel'),
    path(
        'inventario/generar/',
        views.generar_inventario,
        name='generar_inventario',
    ),
    path(
        'rentas/generar/',
        views.generar_rentas,
        name='generar_rentas',
    ),
    path(
        'renta/<int:pk>/comprobante/',
        views.comprobante_renta,
        name='comprobante_renta',
    ),
    path(
        '<int:pk>/descargar/',
        views.descargar_pdf,
        name='descargar',
    ),
    path('historial/', views.historial_reportes, name='historial'),
]
