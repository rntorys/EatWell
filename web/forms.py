from decimal import Decimal
from django import forms


# Django revisa el número y prepara los errores del formulario.
class PresupuestoForm(forms.Form):
    presupuesto = forms.DecimalField(
        label="Presupuesto semanal (CLP)",
        # Decimal permite trabajar con dinero sin usar float.
        min_value=Decimal("0.01"),
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            "placeholder": "Ejemplo: 25000",
            "step": "0.01",
            "aria-describedby": "ayuda-presupuesto",
        }),
        error_messages={
            "required": "Ingresa tu presupuesto semanal.",
            "invalid": "Ingresa un número válido para el presupuesto.",
            "min_value": "El presupuesto debe ser mayor que 0.",
            "max_decimal_places": "Usa como máximo dos decimales.",
        },
    )
