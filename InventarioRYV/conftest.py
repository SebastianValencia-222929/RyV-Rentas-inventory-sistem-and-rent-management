"""Fixtures compartidos para las pruebas del proyecto RYV Rentas."""
import pytest
from datetime import date, timedelta


@pytest.fixture
def usuario_admin(db):
    from authentication.models import Usuario
    return Usuario.objects.create_user(
        username='admin_test',
        password='admin1234',
        rol='administrador',
    )


@pytest.fixture
def usuario_empleado(db):
    from authentication.models import Usuario
    return Usuario.objects.create_user(
        username='empleado_test',
        password='empleado1234',
        rol='empleado',
    )


@pytest.fixture
def equipo(db):
    from inventario.models import Equipo
    return Equipo.objects.create(
        nombre='Taladro percutor',
        cantidad_total=5,
        cantidad_en_renta=0,
        cantidad_en_mantenimiento=0,
    )


@pytest.fixture
def cliente(db):
    from rentas.models import Cliente
    return Cliente.objects.create(
        nombre='Juan Pérez',
        telefono='6141234567',
    )


@pytest.fixture
def renta_activa(db, equipo, cliente, usuario_empleado):
    from rentas.models import Renta
    return Renta.objects.create(
        equipo=equipo,
        cliente=cliente,
        registrada_por=usuario_empleado,
        fecha_inicio=date.today(),
        fecha_vencimiento=date.today() + timedelta(days=7),
        precio='500.00',
        deposito='200.00',
        cantidad=1,
        estado='activa',
    )
