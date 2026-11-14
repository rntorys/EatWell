from copy import deepcopy
from decimal import Decimal

from django import forms
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render

from .catalogo import opciones_ingredientes, recetas_disponibles, selector_productos
from .edicion import cambiar_producto, catalogo_del_plan, guardar_edicion, quitar_comida, recalcular_plan
from .forms import IngredienteRecetaForm, IngredientesFormSet
from .models import PlanGuardado


class NombreComidaForm(forms.Form):
    nombre = forms.CharField(label="Nombre de esta comida", max_length=100)


class ReemplazoProductoForm(IngredienteRecetaForm):
    cantidad = forms.IntegerField(label="Nueva cantidad en cada comida (opcional si mantienes la unidad)", min_value=1, max_value=100000, required=False)


class PresupuestoPlanForm(forms.Form):
    presupuesto = forms.DecimalField(label="Presupuesto total del plan (CLP)", min_value=Decimal("0.01"), max_digits=12, decimal_places=2)


def resultado_edicion(request, plan, catalogo, original_id):
    if not recalcular_plan(plan, catalogo):
        return "El cambio supera tu presupuesto. Ajusta los ingredientes o aumenta el presupuesto del plan."
    if not guardar_edicion(request.user, original_id, plan):
        return "La planificación cambió en otra pestaña o dispositivo. Vuelve al plan y revisa los cambios."
    return ""


@login_required
def editar_comida(request, dia, comida):
    if request.method not in ["GET", "POST"]:
        return HttpResponseNotAllowed(["GET", "POST"])
    guardado = get_object_or_404(PlanGuardado, usuario=request.user)
    plan = guardado.datos
    if dia >= len(plan["menu"]) or comida >= len(plan["menu"][dia]["comidas"]):
        raise Http404
    actual = plan["menu"][dia]["comidas"][comida]
    catalogo = catalogo_del_plan(request.user, plan)
    disponibles, omitidas = recetas_disponibles(request.user, catalogo)
    opciones_recetas = {}
    for receta in disponibles:
        if all(clave in catalogo for clave in receta["ingredientes"]):
            opciones_recetas[receta["clave"]] = receta
    opciones = opciones_ingredientes(catalogo)
    etiquetas = {clave: etiqueta for etiqueta, clave in opciones.items()}
    inicial = [{"ingrediente": etiquetas[clave], "cantidad": cantidad} for clave, cantidad in actual["ingredientes"].items()]
    error = ""
    propuesta = None
    propuesta_calculada = None
    accion = request.POST.get("accion")
    manual = request.method == "POST" and accion == "editar"
    nombre_form = NombreComidaForm(request.POST if manual else None, initial={"nombre": actual["nombre"]})
    filas = IngredientesFormSet(request.POST if manual else None, initial=inicial if not manual else None,
                               form_kwargs={"catalogo": catalogo}, prefix="ingredientes")
    if request.method == "POST":
        if request.POST.get("plan_id") != plan["id"]:
            error = "La planificación cambió. Vuelve al plan antes de editar."
        else:
            propuesta = deepcopy(plan)
            nueva = propuesta["menu"][dia]["comidas"][comida]
            if accion == "quitar":
                quitar_comida(nueva)
            elif accion == "reemplazar":
                elegida = opciones_recetas.get(request.POST.get("receta"))
                if elegida is None:
                    error = "Selecciona una receta disponible."
                else:
                    tipo = nueva["tipo"]
                    nueva = deepcopy(elegida)
                    nueva["tipo"] = tipo
                    nueva["editada"] = True
                    propuesta["menu"][dia]["comidas"][comida] = nueva
            elif accion == "editar":
                nombre_valido = nombre_form.is_valid()
                filas_validas = filas.is_valid()
                if nombre_valido and filas_validas:
                    nueva["nombre"] = nombre_form.cleaned_data["nombre"]
                    nueva["ingredientes"] = {}
                    for fila in filas:
                        if fila.cleaned_data and not fila.cleaned_data.get("DELETE"):
                            nueva["ingredientes"][fila.cleaned_data["ingrediente"]] = fila.cleaned_data["cantidad"]
                    nueva["editada"] = True
                    nueva["instrucciones"] = ""
                else:
                    error = "Revisa el nombre y las cantidades de los ingredientes."
            else:
                error = "Selecciona una acción válida."
            if not error:
                error = resultado_edicion(request, propuesta, catalogo, plan["id"])
                propuesta_calculada = propuesta
                if not error:
                    return redirect("plan")
    return render(request, "web/editar_comida.html", {
        "plan": plan, "dia": plan["menu"][dia], "comida": actual,
        "nombre_form": nombre_form, "filas": filas, "opciones": opciones,
        "selector_productos": selector_productos(catalogo), "recetas": opciones_recetas.values(),
        "error": error, "propuesta": propuesta_calculada,
    })


@login_required
def editar_producto_plan(request, clave):
    if request.method not in ["GET", "POST"]:
        return HttpResponseNotAllowed(["GET", "POST"])
    guardado = get_object_or_404(PlanGuardado, usuario=request.user)
    plan = guardado.datos
    catalogo = catalogo_del_plan(request.user, plan)
    usados = set()
    for dia in plan["menu"]:
        for comida in dia["comidas"]:
            usados.update(comida["ingredientes"])
    if clave not in usados:
        raise Http404
    form = ReemplazoProductoForm(request.POST if request.method == "POST" else None, catalogo=catalogo)
    error = ""
    propuesta = None
    propuesta_calculada = None
    if request.method == "POST":
        if request.POST.get("plan_id") != plan["id"]:
            error = "La planificación cambió. Vuelve al plan antes de editar."
        else:
            propuesta = deepcopy(plan)
            accion = request.POST.get("accion")
            if accion == "quitar":
                cambiar_producto(propuesta, clave)
            elif accion == "reemplazar" and form.is_valid():
                nueva = form.cleaned_data["ingrediente"]
                cantidad = form.cleaned_data["cantidad"]
                if catalogo[nueva]["unidad"] != catalogo[clave]["unidad"] and cantidad is None:
                    form.add_error("cantidad", "La unidad cambió. Indica explícitamente la cantidad para cada comida.")
                    error = "No podemos convertir automáticamente gramos, mililitros y unidades."
                else:
                    cambiar_producto(propuesta, clave, nueva, cantidad)
            else:
                error = "Selecciona un producto y una cantidad válida."
            if not error:
                error = resultado_edicion(request, propuesta, catalogo, plan["id"])
                propuesta_calculada = propuesta
                if not error:
                    return redirect("plan")
    return render(request, "web/editar_producto_plan.html", {
        "plan": plan, "producto": catalogo[clave], "form": form,
        "opciones": opciones_ingredientes(catalogo), "selector_productos": selector_productos(catalogo),
        "error": error, "propuesta": propuesta_calculada,
    })


@login_required
def presupuesto_plan(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    guardado = get_object_or_404(PlanGuardado, usuario=request.user)
    plan = guardado.datos
    form = PresupuestoPlanForm(request.POST)
    error = ""
    if request.POST.get("plan_id") != plan["id"]:
        error = "La planificación cambió. Revisa el plan actual."
    elif form.is_valid():
        monto = form.cleaned_data["presupuesto"]
        if monto < Decimal(str(plan["costo_total"])):
            error = "El presupuesto no puede ser menor que el costo del plan actual."
        else:
            propuesta = deepcopy(plan)
            propuesta["presupuesto"] = str(monto)
            propuesta["saldo"] = str(monto - Decimal(str(plan["costo_total"])))
            if guardar_edicion(request.user, plan["id"], propuesta):
                return redirect("plan")
            error = "La planificación cambió. Revisa el plan actual."
    else:
        error = "Ingresa un presupuesto válido, mayor que cero y con hasta dos decimales."
    return render(request, "web/plan.html", {"plan": plan, "error": error})
