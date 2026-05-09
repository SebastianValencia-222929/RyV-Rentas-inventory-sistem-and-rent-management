"""URLs para el módulo de rentas."""
from django.urls import path
from . import views

app_name = 'rentas'

urlpatterns = [
    path('', views.rentas_activas, name='lista'),
    path('<int:pk>/', views.detalle_renta, name='detalle'),
    path('nueva/', views.nueva_renta, name='nueva'),
    path('<int:pk>/editar/', views.editar_renta, name='editar'),
    path('<int:pk>/eliminar/', views.eliminar_renta, name='eliminar'),
    path(
        '<int:pk>/finalizar/',
        views.finalizar_renta,
        name='finalizar',
    ),
    path('solicitar/', views.solicitar_renta, name='solicitar'),
    path(
        '<int:pk>/solicitar-cierre/',
        views.solicitar_cierre,
        name='solicitar_cierre',
    ),
]
