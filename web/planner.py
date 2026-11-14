from decimal import Decimal
from copy import deepcopy
from .data import INGREDIENTES, RECETAS


DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
TIPOS_COMIDA = ["desayuno", "almuerzo", "cena"]


def numero_json(numero):
    # JSON admite enteros; los decimales se guardan como texto para no usar float.
    if numero == int(numero):
        return int(numero)
    return str(numero)


def calcular_costo_receta(receta, ingredientes=None):
    if ingredientes is None:
        ingredientes = INGREDIENTES
    total = Decimal("0")
    for ingrediente in receta["ingredientes"]:
        cantidad = receta["ingredientes"][ingrediente]
        precio = Decimal(str(ingredientes[ingrediente]["precio"]))
        total += cantidad * precio
    return total


def recetas_por_tipo(ingredientes=None, recetas=None):
    if recetas is None:
        recetas = RECETAS
    grupos = {"desayuno": [], "almuerzo": [], "cena": []}
    for receta in recetas:
        # Copiamos para añadir el costo sin cambiar el catálogo.
        nueva_receta = receta.copy()
        nueva_receta["costo"] = calcular_costo_receta(receta, ingredientes)
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


def calcular_presupuesto_minimo(ingredientes=None, recetas=None, cantidad_dias=7):
    grupos = recetas_por_tipo(ingredientes, recetas)
    minimos = calcular_minimos(grupos)
    if minimos is None:
        return None

    total = 0
    for tipo in TIPOS_COMIDA:
        total += minimos[tipo] * cantidad_dias
    return total


def crear_lista_compras(menu, ingredientes=None):
    if ingredientes is None:
        ingredientes = INGREDIENTES
    cantidades = {}

    # Acumulamos las cantidades de todas las comidas.
    for dia in menu:
        for receta in dia["comidas"]:
            for ingrediente in receta["ingredientes"]:
                if ingrediente not in cantidades:
                    cantidades[ingrediente] = 0

                cantidad = receta["ingredientes"][ingrediente]
                cantidades[ingrediente] += cantidad

    # Construimos una fila por ingrediente con su subtotal.
    compras = []
    for ingrediente in sorted(cantidades):
        datos = ingredientes[ingrediente]
        cantidad = cantidades[ingrediente]
        precio = Decimal(str(datos["precio"]))
        subtotal = cantidad * precio

        compras.append({
            "clave": ingrediente,
            "nombre": datos["nombre"],
            "cantidad": cantidad,
            "unidad": datos["unidad"],
            "precio_unitario": numero_json(precio),
            "subtotal": numero_json(subtotal),
            "fuente": datos.get("fuente", "Ejemplo"),
            "referencia": datos.get("referencia", "Catálogo de demostración"),
        })

    return compras


def generar_plan(presupuesto, ingredientes=None, recetas=None, dias=None):
    if ingredientes is None:
        ingredientes = INGREDIENTES
    if dias is None:
        dias = [{"dia": nombre} for nombre in DIAS]
    if not 1 <= len(dias) <= 31:
        raise ValueError("El plan debe incluir entre 1 y 31 días.")
    presupuesto = Decimal(str(presupuesto))
    if not presupuesto.is_finite() or presupuesto <= 0:
        raise ValueError("El presupuesto debe ser un número mayor que cero.")

    grupos = recetas_por_tipo(ingredientes, recetas)
    minimos = calcular_minimos(grupos)
    if minimos is None:
        return None

    # Reservamos lo necesario para las tres comidas de cada día seleccionado.
    reserva = 0
    for tipo in TIPOS_COMIDA:
        reserva += minimos[tipo] * len(dias)
    if presupuesto < reserva:
        return None

    menu = []
    gastado = 0
    numero_dia = 0

    for dia in dias:
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
                    # Cada comida debe ser independiente para poder editarla después.
                    comidas.append(deepcopy(receta))
                    gastado += receta["costo"]
                    break

                posicion += 1
                if posicion == len(recetas):
                    posicion = 0

        dia_menu = dia.copy()
        dia_menu["comidas"] = comidas
        menu.append(dia_menu)
        numero_dia += 1

    compras = crear_lista_compras(menu, ingredientes)
    costo_total = Decimal("0")
    for compra in compras:
        costo_total += Decimal(str(compra["subtotal"]))

    # Convertimos los costos después de calcular: el plan se guarda como JSON.
    for dia in menu:
        for receta in dia["comidas"]:
            receta["costo"] = numero_json(Decimal(str(receta["costo"])))

    return {
        # Guardamos estos decimales como texto para poder almacenarlos en JSON.
        "presupuesto": str(presupuesto),
        "menu": menu,
        "compras": compras,
        "costo_total": numero_json(costo_total),
        "saldo": str(presupuesto - costo_total),
        "catalogo": deepcopy(ingredientes),
        "cantidad_dias": len(menu),
        "cantidad_comidas": len(menu) * 3,
    }