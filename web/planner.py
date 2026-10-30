from decimal import Decimal
from .data import INGREDIENTES, RECETAS


DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
TIPOS_COMIDA = ["desayuno", "almuerzo", "cena"]


def calcular_costo_receta(receta):
    total = 0
    for ingrediente in receta["ingredientes"]:
        cantidad = receta["ingredientes"][ingrediente]
        precio = INGREDIENTES[ingrediente]["precio"]
        total += cantidad * precio
    return total


def recetas_por_tipo():
    grupos = {"desayuno": [], "almuerzo": [], "cena": []}
    for receta in RECETAS:
        # Copiamos para añadir el costo sin cambiar el catálogo.
        nueva_receta = receta.copy()
        nueva_receta["costo"] = calcular_costo_receta(receta)
        tipo = receta["tipo"]
        grupos[tipo].append(nueva_receta)
    return grupos


def calcular_minimos(grupos):
    minimos = {}
    for tipo in TIPOS_COMIDA:
        recetas = grupos[tipo]
        if len(recetas) == 0:
            return None

        menor = recetas[0]["costo"]
        for receta in recetas:
            if receta["costo"] < menor:
                menor = receta["costo"]
        minimos[tipo] = menor
    return minimos


def calcular_presupuesto_minimo():
    grupos = recetas_por_tipo()
    minimos = calcular_minimos(grupos)
    if minimos is None:
        return None

    total = 0
    for tipo in TIPOS_COMIDA:
        total += minimos[tipo] * len(DIAS)
    return total


def crear_lista_compras(menu):
    cantidades = {}
    for dia in menu:
        for receta in dia["comidas"]:
            for ingrediente in receta["ingredientes"]:
                if ingrediente not in cantidades:
                    cantidades[ingrediente] = 0
                cantidades[ingrediente] += receta["ingredientes"][ingrediente]

    compras = []
    # sorted ordena los nombres internos de los ingredientes.
    for ingrediente in sorted(cantidades):
        datos = INGREDIENTES[ingrediente]
        cantidad = cantidades[ingrediente]
        compras.append({
            "nombre": datos["nombre"],
            "cantidad": cantidad,
            "unidad": datos["unidad"],
            "precio_unitario": datos["precio"],
            "subtotal": cantidad * datos["precio"],
        })
    return compras


def generar_plan(presupuesto):
    presupuesto = Decimal(str(presupuesto))
    if not presupuesto.is_finite() or presupuesto <= 0:
        raise ValueError("El presupuesto debe ser un número mayor que cero.")

    grupos = recetas_por_tipo()
    minimos = calcular_minimos(grupos)
    if minimos is None:
        return None

    # Apartamos lo necesario para cubrir las 21 comidas más económicas.
    reserva = 0
    for tipo in TIPOS_COMIDA:
        reserva += minimos[tipo] * len(DIAS)
    if presupuesto < reserva:
        return None

    menu = []
    gastado = 0
    numero_dia = 0

    for nombre_dia in DIAS:
        comidas = []
        for tipo in TIPOS_COMIDA:
            reserva -= minimos[tipo]
            recetas = grupos[tipo]

            # % permite volver al inicio al llegar al final de las recetas.
            # Con tres recetas, los días empiezan por 0, 1, 2, 0, 1, 2, 0.
            posicion = numero_dia % len(recetas)
            for intento in range(len(recetas)):
                receta = recetas[posicion]
                # Debe quedar dinero para todas las comidas pendientes.
                if gastado + receta["costo"] + reserva <= presupuesto:
                    comidas.append(receta)
                    gastado += receta["costo"]
                    break

                posicion += 1
                if posicion == len(recetas):
                    posicion = 0

        menu.append({"dia": nombre_dia, "comidas": comidas})
        numero_dia += 1

    compras = crear_lista_compras(menu)
    costo_total = 0
    for compra in compras:
        costo_total += compra["subtotal"]

    return {
        # La sesión guarda estos decimales como texto.
        "presupuesto": str(presupuesto),
        "menu": menu,
        "compras": compras,
        "costo_total": costo_total,
        "saldo": str(presupuesto - costo_total),
    }
