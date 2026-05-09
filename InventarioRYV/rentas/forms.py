"""
Archivo: forms.py
Descripción: Formularios para el módulo de rentas del sistema RYV Rentas.
             Define los formularios de creación de rentas, solicitudes de
             renta por parte del Empleado y finalización de rentas, así como
             la función auxiliar para obtener equipos disponibles, según lo
             definido en RF-13, RF-14, RF-17, RF-18 y RN-005 del SRS.
Fecha: 2026-04-07
Versión: 1.0
"""
from decimal import Decimal
from django import forms
from django.core.validators import RegexValidator
from django.db.models import F, ExpressionWrapper, IntegerField
from .models import Renta, Cliente
from inventario.models import Equipo

# Validador reutilizable: solo dígitos, entre 7 y 15 caracteres
_telefono_validator = RegexValidator(
    regex=r'^\d{7,15}$',
    message='El teléfono debe contener solo dígitos (entre 7 y 15).',
)


def equipos_con_disponibles():
    """
    Retorna un QuerySet de equipos activos con al menos una unidad disponible.

    Calcula la disponibilidad directamente en la base de datos mediante
    anotación ORM para evitar cargar todos los equipos en memoria.

    Retorna:
        QuerySet: Equipos activos con campo anotado calc_disp mayor a cero,
        ordenados según la configuración del modelo.
    """
    return Equipo.objects.filter(activo=True).annotate(
        calc_disp=ExpressionWrapper(
            F('cantidad_total')
            - F('cantidad_en_renta')
            - F('cantidad_en_mantenimiento'),
            output_field=IntegerField(),
        )
    ).filter(calc_disp__gt=0)


class RentaForm(forms.ModelForm):
    """
    Formulario para que el Administrador registre una nueva renta.

    Incluye campos del cliente y de la renta. Los equipos se agregan como
    filas dinámicas desde la plantilla y se procesan en la vista,
    según lo definido en RF-13 y RN-005 del SRS.

    Atributos:
        cliente_nombre (CharField): Nombre completo del cliente. Obligatorio.
        cliente_telefono (CharField): Teléfono de contacto del cliente. Obligatorio.
        cliente_direccion (CharField): Dirección del cliente. Campo opcional.
        cliente_correo (EmailField): Correo electrónico del cliente. Campo opcional.
    """

    # Campos del cliente
    cliente_nombre = forms.CharField(
        label='Nombre del cliente',
        widget=forms.TextInput(attrs={'class': 'input-campo'}),
    )
    cliente_telefono = forms.CharField(
        label='Teléfono del cliente',
        validators=[_telefono_validator],
        widget=forms.TextInput(attrs={
            'class': 'input-campo',
            'type': 'tel',
            'inputmode': 'numeric',
            'pattern': r'\d{7,15}',
            'placeholder': 'Ej. 5512345678',
            'maxlength': '15',
        }),
    )
    cliente_direccion = forms.CharField(
        label='Dirección',
        widget=forms.TextInput(attrs={'class': 'input-campo'}),
    )
    cliente_correo = forms.EmailField(
        label='Correo electrónico (opcional)',
        required=False,
        widget=forms.EmailInput(attrs={'class': 'input-campo'}),
    )

    class Meta:
        model = Renta
        fields = [
            'fecha_inicio',
            'fecha_vencimiento',
            'precio',
            'deposito',
            'metodo_pago',
            'notas',
        ]
        widgets = {
            'fecha_inicio': forms.DateInput(
                attrs={'class': 'input-campo', 'type': 'date'},
                format='%Y-%m-%d',
            ),
            'fecha_vencimiento': forms.DateInput(
                attrs={'class': 'input-campo', 'type': 'date'},
                format='%Y-%m-%d',
            ),
            'precio': forms.NumberInput(
                attrs={'class': 'input-campo', 'step': '0.01',
                       'id': 'id_precio_renta'}
            ),
            'deposito': forms.NumberInput(
                attrs={'class': 'input-campo', 'step': '0.01',
                       'id': 'id_deposito_renta'}
            ),
            'metodo_pago': forms.Select(
                attrs={'class': 'input-campo'}
            ),
            'notas': forms.Textarea(
                attrs={'class': 'input-campo', 'rows': 2}
            ),
        }
        labels = {
            'fecha_inicio': 'Fecha de inicio',
            'fecha_vencimiento': 'Fecha de vencimiento',
            'precio': 'Precio total (MXN)',
            'deposito': 'Depósito (MXN)',
            'metodo_pago': 'Método de pago del depósito',
            'notas': 'Notas (opcional)',
        }

    def clean(self):
        """
        Valida que las fechas sean coherentes y que el depósito cumpla el mínimo requerido.

        La fecha de vencimiento debe ser posterior a la fecha de inicio.
        El depósito mínimo es el 50% del precio total. Si se ingresa un depósito
        mayor a cero, el método de pago es obligatorio.

        Retorna:
            dict: Los datos limpios del formulario si la validación es exitosa.

        Lanza:
            ValidationError: Si la fecha de vencimiento no es posterior a la
            fecha de inicio, o si el depósito es menor al mínimo requerido.
        """
        cleaned = super().clean()
        fecha_inicio = cleaned.get('fecha_inicio')
        fecha_vencimiento = cleaned.get('fecha_vencimiento')
        precio = cleaned.get('precio')
        deposito = cleaned.get('deposito') or Decimal('0')

        if fecha_inicio and fecha_vencimiento:
            if fecha_vencimiento <= fecha_inicio:
                raise forms.ValidationError(
                    'La fecha de vencimiento debe ser posterior '
                    'a la fecha de inicio.'
                )

        if precio and precio > 0:
            minimo = (precio * Decimal('0.5')).quantize(Decimal('0.01'))
            if deposito < minimo:
                self.add_error(
                    'deposito',
                    f'El depósito mínimo es el 50% del precio '
                    f'(${minimo}). Ingresa al menos ${minimo}.',
                )

        if deposito and deposito > 0:
            if not cleaned.get('metodo_pago'):
                self.add_error(
                    'metodo_pago',
                    'Selecciona el método de pago del depósito.',
                )

        return cleaned


class SolicitudRentaForm(forms.Form):
    """
    Formulario para que el Empleado solicite una nueva renta.

    Los equipos se agregan como filas dinámicas desde la plantilla y se
    procesan en la vista. La solicitud queda pendiente de aprobación por
    el Administrador, cumpliendo con RF-14 y RN-008 del SRS.

    Atributos:
        cliente_nombre (CharField): Nombre completo del cliente. Obligatorio.
        cliente_telefono (CharField): Teléfono de contacto del cliente. Obligatorio.
        cliente_direccion (CharField): Dirección del cliente. Campo opcional.
        cliente_correo (EmailField): Correo electrónico del cliente. Campo opcional.
        fecha_inicio (DateField): Fecha de inicio de la renta.
        fecha_vencimiento (DateField): Fecha límite de devolución del equipo.
        precio (DecimalField): Precio total de la renta en MXN.
        deposito (DecimalField): Depósito de garantía en MXN. Campo opcional.
        metodo_pago (ChoiceField): Método de pago del depósito. Campo opcional.
        notas (CharField): Observaciones adicionales. Campo opcional.
        comentario (CharField): Comentario obligatorio para el Administrador.
    """

    cliente_nombre = forms.CharField(
        label='Nombre del cliente',
        widget=forms.TextInput(attrs={'class': 'input-campo'}),
    )
    cliente_telefono = forms.CharField(
        label='Teléfono del cliente',
        validators=[_telefono_validator],
        widget=forms.TextInput(attrs={
            'class': 'input-campo',
            'type': 'tel',
            'inputmode': 'numeric',
            'pattern': r'\d{7,15}',
            'placeholder': 'Ej. 5512345678',
            'maxlength': '15',
        }),
    )
    cliente_direccion = forms.CharField(
        label='Dirección',
        widget=forms.TextInput(attrs={'class': 'input-campo'}),
    )
    cliente_correo = forms.EmailField(
        label='Correo electrónico (opcional)',
        required=False,
        widget=forms.EmailInput(attrs={'class': 'input-campo'}),
    )
    fecha_inicio = forms.DateField(
        label='Fecha de inicio',
        widget=forms.DateInput(
            attrs={'class': 'input-campo', 'type': 'date'},
            format='%Y-%m-%d',
        ),
    )
    fecha_vencimiento = forms.DateField(
        label='Fecha de vencimiento',
        widget=forms.DateInput(
            attrs={'class': 'input-campo', 'type': 'date'},
            format='%Y-%m-%d',
        ),
    )
    precio = forms.DecimalField(
        label='Precio total (MXN)',
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={'class': 'input-campo', 'step': '0.01',
                   'id': 'id_precio_solic'}
        ),
    )
    deposito = forms.DecimalField(
        label='Depósito (MXN)',
        max_digits=10,
        decimal_places=2,
        required=False,
        initial=0,
        widget=forms.NumberInput(
            attrs={'class': 'input-campo', 'step': '0.01',
                   'id': 'id_deposito_solic'}
        ),
    )
    metodo_pago = forms.ChoiceField(
        label='Método de pago del depósito',
        choices=[('', '— Selecciona —')] + [
            ('efectivo', 'Efectivo'),
            ('transferencia', 'Transferencia bancaria'),
            ('tarjeta', 'Tarjeta'),
            ('otro', 'Otro'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'input-campo'}),
    )
    notas = forms.CharField(
        label='Notas (opcional)',
        required=False,
        widget=forms.Textarea(
            attrs={'class': 'input-campo', 'rows': 2}
        ),
    )
    comentario = forms.CharField(
        label='Comentario para el administrador',
        widget=forms.Textarea(
            attrs={'class': 'input-campo', 'rows': 2}
        ),
    )

    def clean(self):
        """
        Valida que las fechas sean coherentes y que el depósito cumpla el mínimo requerido.

        La fecha de vencimiento debe ser posterior a la fecha de inicio.
        El depósito mínimo es el 50% del precio total. Si se ingresa un depósito
        mayor a cero, el método de pago es obligatorio.

        Retorna:
            dict: Los datos limpios del formulario si la validación es exitosa.

        Lanza:
            ValidationError: Si la fecha de vencimiento no es posterior a la
            fecha de inicio.
        """
        cleaned = super().clean()
        inicio = cleaned.get('fecha_inicio')
        vencimiento = cleaned.get('fecha_vencimiento')
        precio = cleaned.get('precio')
        deposito = cleaned.get('deposito') or Decimal('0')

        if inicio and vencimiento and vencimiento <= inicio:
            raise forms.ValidationError(
                'La fecha de vencimiento debe ser posterior '
                'a la fecha de inicio.'
            )

        if precio and precio > 0:
            minimo = (precio * Decimal('0.5')).quantize(Decimal('0.01'))
            if deposito < minimo:
                self.add_error(
                    'deposito',
                    f'El depósito mínimo es el 50% del precio '
                    f'(${minimo}). Ingresa al menos ${minimo}.',
                )

        if deposito and deposito > 0:
            if not cleaned.get('metodo_pago'):
                self.add_error(
                    'metodo_pago',
                    'Selecciona el método de pago del depósito.',
                )

        return cleaned


class RentaEditForm(forms.ModelForm):
    """
    Formulario para editar datos básicos de una renta activa (admin).

    Sobreescribe los campos de fecha para garantizar que el formato YYYY-MM-DD
    enviado por los inputs HTML de tipo date sea interpretado correctamente,
    independientemente de la configuración regional del servidor.
    """

    # Sobreescribir campos de fecha para fijar input_formats y evitar
    # problemas de parseo con USE_L10N activado.
    fecha_inicio = forms.DateField(
        label='Fecha de inicio',
        input_formats=['%Y-%m-%d'],
        widget=forms.DateInput(
            attrs={'class': 'input-campo', 'type': 'date'},
            format='%Y-%m-%d',
        ),
    )
    fecha_vencimiento = forms.DateField(
        label='Fecha de vencimiento',
        input_formats=['%Y-%m-%d'],
        widget=forms.DateInput(
            attrs={'class': 'input-campo', 'type': 'date'},
            format='%Y-%m-%d',
        ),
    )

    class Meta:
        model = Renta
        fields = ['fecha_inicio', 'fecha_vencimiento', 'precio', 'deposito', 'metodo_pago', 'notas']
        widgets = {
            'precio': forms.NumberInput(attrs={'class': 'input-campo', 'step': '0.01'}),
            'deposito': forms.NumberInput(attrs={'class': 'input-campo', 'step': '0.01'}),
            'metodo_pago': forms.Select(attrs={'class': 'input-campo'}),
            'notas': forms.Textarea(attrs={'class': 'input-campo', 'rows': 2}),
        }
        labels = {
            'precio': 'Precio total (MXN)',
            'deposito': 'Depósito (MXN)',
            'metodo_pago': 'Método de pago del depósito',
            'notas': 'Notas (opcional)',
        }

    def clean(self):
        cleaned = super().clean()
        inicio = cleaned.get('fecha_inicio')
        vencimiento = cleaned.get('fecha_vencimiento')
        if inicio and vencimiento and vencimiento <= inicio:
            raise forms.ValidationError('La fecha de vencimiento debe ser posterior a la de inicio.')
        return cleaned


class FinalizarRentaForm(forms.Form):
    """
    Formulario para que el Administrador registre la devolución de un equipo.

    Captura la condición del equipo devuelto, el cargo por daños si aplica,
    el monto recibido del cliente y el método de pago al cierre, según lo
    definido en RF-17 del SRS.

    Atributos:
        condicion_devolucion (ChoiceField): Estado del equipo al momento de
        la devolución. Obligatorio.
        cargo_daños (DecimalField): Monto adicional por daños en MXN.
        Obligatorio si la condición no es 'bueno'.
        monto_recibido (DecimalField): Cantidad recibida del cliente al cierre.
        Campo opcional si el saldo neto es cero o negativo.
        metodo_pago_cierre (ChoiceField): Método de pago utilizado al cerrar.
        Obligatorio si hay saldo pendiente.
        notas_devolucion (CharField): Observaciones adicionales sobre la
        devolución. Campo opcional.
    """

    condicion_devolucion = forms.ChoiceField(
        label='Condición del equipo al devolver',
        choices=[
            ('bueno', 'Bueno — sin daños'),
            ('daños_menores', 'Daños menores'),
            ('inservible', 'Inservible / Pérdida total'),
            ('extraviado', 'Extraviado'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'radio-condicion'}),
    )
    cargo_daños = forms.DecimalField(
        label='Cargo por daños (MXN)',
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.01'),
        required=False,
        widget=forms.NumberInput(
            attrs={'class': 'input-campo', 'step': '0.01',
                   'placeholder': '0.00'}
        ),
        help_text='Monto adicional a cobrar por daños al equipo.',
    )
    monto_recibido = forms.DecimalField(
        label='Monto recibido del cliente (MXN)',
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=False,
        widget=forms.NumberInput(
            attrs={'class': 'input-campo', 'step': '0.01',
                   'placeholder': '0.00', 'id': 'id_monto_recibido'}
        ),
    )
    metodo_pago_cierre = forms.ChoiceField(
        label='Método de pago al cierre',
        choices=[('', '— Selecciona —')] + [
            ('efectivo', 'Efectivo'),
            ('transferencia', 'Transferencia bancaria'),
            ('tarjeta', 'Tarjeta'),
            ('otro', 'Otro'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'input-campo'}),
    )
    notas_devolucion = forms.CharField(
        label='Notas de devolución (opcional)',
        required=False,
        widget=forms.Textarea(
            attrs={'class': 'input-campo', 'rows': 2}
        ),
    )

    def clean(self):
        """
        Valida que se ingrese el cargo por daños cuando la condición no es 'bueno'.

        Retorna:
            dict: Los datos limpios del formulario si la validación es exitosa.

        Lanza:
            ValidationError: Por campo específico si la condición de devolución
            indica daños pero no se ingresó el cargo correspondiente.
        """
        cleaned = super().clean()
        condicion = cleaned.get('condicion_devolucion')
        cargo = cleaned.get('cargo_daños')

        if condicion and condicion != 'bueno':
            if not cargo:
                self.add_error(
                    'cargo_daños',
                    'Debes indicar el cargo por daños '
                    '(obligatorio para esta condición).',
                )
        return cleaned
