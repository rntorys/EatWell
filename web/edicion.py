"""Recalcular cambios del plan sin alterar recetas ni precios ya guardados."""
from copy import deepcopy
from decimal import Decimal
from uuid import uuid4

from .catalogo import ingredientes_disponibles, ordenar_catalogo
from .models import PlanGuardado
from .odepa import ErrorODEPA, obtener_precios
from .planner import calcular_costo_receta, crear_lista_compras, numero_json


def catalogo_del_plan(usuario, plan):
    catalogo = deepcopy(plan.get("catalogo", {}))
    if not catalogo:
        # Compatibilidad con planes anteriores a la edición: recuperamos los
        # precios originales de sus compras, aunque ODEPA ya haya cambiado.
        try:
            base, info, publicados = obtener_precios(plan.get("precios", {}).get("region_id", "13"))
            catalogo = ingredientes_disponibles(usuario, base, publicados)
        except ErrorODEPA:
            catalogo = {}
        claves = set()
        for dia in plan["menu"]:
            for comida in dia["comidas"]:
                claves.update(comida["ingredientes"])
        for clave, compra in zip(sorted(claves), plan["compras"]):
            catalogo[compra.get("clave", clave)] = {
                "nombre": compra["nombre"], "unidad": compra["unidad"],
                "precio": compra["precio_unitario"], "fuente": compra.get("fuente", "Ejemplo"),
                "referencia": compra.get("referencia", "Precio original del plan"),
            }
    # Los productos propios creados después también están disponibles.
    for clave, producto in ingredientes_disponibles(usuario, {}, []).items():
        if clave not in catalogo:
            catalogo[clave] = producto
    return ordenar_catalogo(usuario, catalogo)


def recalcular_plan(plan, catalogo):
    total_comidas = 0
    for dia in plan["menu"]:
        for comida in dia["comidas"]:
            comida["costo"] = numero_json(calcular_costo_receta(comida, catalogo))
            if comida["ingredientes"]:
                total_comidas += 1
    plan["compras"] = crear_lista_compras(plan["menu"], catalogo)
    total = sum(Decimal(str(compra["subtotal"])) for compra in plan["compras"])
    plan["costo_total"] = numero_json(total)
    plan["saldo"] = str(Decimal(plan["presupuesto"]) - total)
    plan["cantidad_comidas"] = total_comidas
    plan["cantidad_dias"] = len(plan["menu"])
    plan["catalogo"] = catalogo
    return total <= Decimal(plan["presupuesto"])


def guardar_edicion(usuario, anterior_id, propuesta):
    # Un cambio de otro dispositivo invalida este formulario antiguo.
    propuesta["id"] = str(uuid4())
    propuesta["confirmado"] = False
    return PlanGuardado.objects.filter(usuario=usuario, datos__id=anterior_id).update(datos=propuesta)


def quitar_comida(comida):
    comida["nombre"] = "Comida omitida"
    comida["ingredientes"] = {}
    comida["instrucciones"] = ""
    comida["editada"] = True


def cambiar_producto(plan, anterior, nuevo=None, cantidad=None):
    for dia in plan["menu"]:
        for comida in dia["comidas"]:
            if anterior not in comida["ingredientes"]:
                continue
            original = comida["ingredientes"].pop(anterior)
            if nuevo is not None:
                agregado = original if cantidad is None else cantidad
                comida["ingredientes"][nuevo] = comida["ingredientes"].get(nuevo, 0) + agregado
            comida["editada"] = True
            comida["instrucciones"] = ""
            if not comida["ingredientes"]:
                quitar_comida(comida)
