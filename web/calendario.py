"""Días que cubrirá una planificación. El presupuesto siempre cubre todos ellos."""
import calendar
from datetime import date, timedelta

from django import forms
from django.utils import timezone

NOMBRES_DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


class PeriodoForm(forms.Form):
    modo = forms.ChoiceField(label="Período", choices=[("7", "7 días"), ("28", "28 días"), ("30", "30 días"), ("31", "31 días"), ("mes", "Un mes del calendario")])
    inicio = forms.DateField(label="Fecha inicial (para períodos de días)", required=False, widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    mes = forms.CharField(label="Mes (para un mes del calendario)", required=False, widget=forms.TextInput(attrs={"type": "month"}))
    sin_fines = forms.BooleanField(label="Excluir sábados y domingos", required=False)

    def clean(self):
        datos = super().clean()
        modo = datos.get("modo")
        if modo == "mes":
            try:
                inicio = date.fromisoformat(datos.get("mes", "") + "-01")
            except (ValueError, TypeError):
                self.add_error("mes", "Selecciona un mes válido.")
                return datos
            cantidad = calendar.monthrange(inicio.year, inicio.month)[1]
        elif modo in ["7", "28", "30", "31"]:
            inicio = datos.get("inicio")
            if inicio is None:
                self.add_error("inicio", "Selecciona la fecha inicial.")
                return datos
            cantidad = int(modo)
        else:
            return datos
        if not 2000 <= inicio.year <= 2100:
            self.add_error(None, "Elige una fecha entre los años 2000 y 2100.")
            return datos
        fechas = []
        for numero in range(cantidad):
            dia = inicio + timedelta(days=numero)
            if not datos.get("sin_fines") or dia.weekday() < 5:
                fechas.append(dia)
        datos["fechas"] = fechas
        return datos


def periodo_predeterminado():
    hoy = timezone.localdate()
    return {"modo": "7", "inicio": hoy.isoformat(), "mes": hoy.strftime("%Y-%m")}


def etiqueta_dia(dia):
    return NOMBRES_DIAS[dia.weekday()] + " " + dia.strftime("%d/%m/%Y")


def seleccionar_fechas(form, datos=None):
    if not form.is_valid():
        return [], []
    disponibles = form.cleaned_data["fechas"]
    elegidas = {dia.isoformat() for dia in disponibles}
    if datos is not None and datos.get("calendario_presentado"):
        elegidas = set(datos.getlist("dias"))
        permitidas = {dia.isoformat() for dia in disponibles}
        if not elegidas or not elegidas.issubset(permitidas):
            form.add_error(None, "Selecciona al menos un día válido del período mostrado.")
    calendario = []
    seleccionadas = []
    for dia in disponibles:
        marcado = dia.isoformat() in elegidas
        calendario.append({"valor": dia.isoformat(), "etiqueta": etiqueta_dia(dia), "marcado": marcado})
        if marcado:
            seleccionadas.append({"fecha": dia.isoformat(), "dia": etiqueta_dia(dia)})
    return calendario, seleccionadas
