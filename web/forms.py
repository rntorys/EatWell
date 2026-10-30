# Este archivo describe el formulario y las reglas que Django comprobará
# cuando reciba los datos. No genera el menú: esa tarea está en planner.py.

# decimal pertenece a Python; no necesita instalarse por separado.
# Decimal representa números decimales como los usados para dinero.
# Por ejemplo, Decimal("0.1") + Decimal("0.2") produce Decimal("0.3").
# Usamos texto entre comillas para evitar convertir primero a float, cuya
# representación binaria puede introducir pequeñas diferencias decimales.
from decimal import Decimal

# forms es un módulo de Django con clases para definir y validar formularios,
# además de generar los campos HTML. No es el forms.py de nuestra aplicación.
from django import forms


# class define una clase: aquí, el tipo de formulario que queremos construir.
# (forms.Form) significa que PresupuestoForm HEREDA de Form y recibe sus
# herramientas, como is_valid(), errors y cleaned_data.
# En views.py creamos un formulario concreto con PresupuestoForm(request.POST).
class PresupuestoForm(forms.Form):
    # presupuesto es el nombre del campo (también será su name en HTML).
    # DecimalField describe un campo decimal; todavía no es el monto ingresado.
    # Tras validar, Django convierte el texto recibido en un objeto Decimal.
    # Es obligatorio porque required=True es el comportamiento predeterminado.
    presupuesto = forms.DecimalField(
        # Texto que mostramos junto al campo del formulario.
        label="Presupuesto semanal (CLP)",
        # Menor monto permitido. Con dos decimales, 0.01 es el menor positivo.
        min_value=Decimal("0.01"),
        # Hasta 12 dígitos en total, sin contar el punto decimal ni el signo.
        max_digits=12,
        # Hasta 2 dígitos decimales: quedan como máximo 10 para la parte entera.
        # Un monto con más decimales se rechaza; este campo no lo redondea.
        decimal_places=2,
        # Un widget decide cómo se representa el campo en HTML.
        # NumberInput genera <input type="number">; attrs contiene atributos
        # que se añaden a esa etiqueta. La validación del servidor la hace
        # DecimalField, incluso si alguien evita los controles del navegador.
        widget=forms.NumberInput(attrs={
            # Ejemplo visual cuando el campo está vacío; no es un valor inicial.
            "placeholder": "Ejemplo: 25000",
            # Paso de los controles del input: permite incrementos de 0.01.
            "step": "0.01",
            # Vincula el input con el texto de ayuda cuyo id es ayuda-presupuesto
            # en home.html. Permite que lectores de pantalla lo relacionen.
            "aria-describedby": "ayuda-presupuesto",
        }),
        # Diccionario: código del error -> mensaje para el usuario.
        # Django elige el mensaje cuando form.is_valid() encuentra ese error.
        error_messages={
            # Campo vacío.
            "required": "Ingresa tu presupuesto semanal.",
            # No se puede convertir en un número decimal válido.
            "invalid": "Ingresa un número válido para el presupuesto.",
            # Monto menor que el min_value definido arriba.
            "min_value": "El presupuesto debe ser mayor que 0.",
            # Excede el máximo de dígitos totales.
            "max_digits": "El presupuesto es demasiado grande. Revisa el monto.",
            # Excede los 10 dígitos permitidos antes del separador decimal.
            "max_whole_digits": "Ingresa un presupuesto de hasta 10 cifras enteras.",
            # Excede los 2 dígitos permitidos después del separador decimal.
            "max_decimal_places": "Usa como máximo dos decimales.",
        },
    )
