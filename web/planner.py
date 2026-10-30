"""Generación del menú semanal, sin depender de vistas ni de una base de datos."""

# Decimal permite trabajar con el presupuesto decimal sin usar float.
from decimal import Decimal

# El punto inicial significa "dentro del mismo paquete", en este caso web.
# Traemos los diccionarios y la lista definidos en web/data.py.
from .data import INGREDIENTES, RECETAS


# Son tuplas: secuencias que aquí usamos como valores fijos.
# Las mayúsculas indican por convención que se tratan como constantes.
DIAS = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")
TIPOS_COMIDA = ("desayuno", "almuerzo", "cena")


def calcular_costo_receta(receta):
    """Todas las recetas del catálogo rinden una porción."""
    # .items() permite recorrer pares de clave y valor: por ejemplo, "avena", 60.
    # Multiplicamos cada cantidad por su precio. sum() suma esos resultados.
    # El "for" dentro de sum() es una expresión generadora: entrega los importes
    # uno a uno, sin tener que construir primero una lista con todos ellos.
    return sum(
        cantidad * INGREDIENTES[ingrediente]["precio"]
        for ingrediente, cantidad in receta["ingredientes"].items()
    )


def recetas_por_tipo():
    """Añade el costo calculado sin modificar los datos originales."""
    # Esto es una comprensión de diccionario: crea una entrada por cada tipo.
    # Resultado: {"desayuno": [], "almuerzo": [], "cena": []}.
    grupos = {tipo: [] for tipo in TIPOS_COMIDA}
    for receta in RECETAS:
        # receta["tipo"] elige la lista correcta; append() añade un elemento.
        grupos[receta["tipo"]].append({
            # Dentro de {...}, **receta copia sus claves y valores al nuevo
            # diccionario. Luego añadimos "costo". Si ya existiera esa clave,
            # el valor escrito después de **receta sería el que queda.
            # Equivale a: nueva = receta.copy(); nueva["costo"] = ...
            # Es una copia superficial: los diccionarios internos se comparten.
            # Aquí solo los leemos, así que no cambiamos los ingredientes.
            **receta,
            "costo": calcular_costo_receta(receta),
        })
    return grupos


def calcular_presupuesto_minimo():
    """Mínimo para 21 comidas. Se permite repetir recetas durante la semana."""
    grupos = recetas_por_tipo()
    # .values() entrega las listas de recetas. Una lista vacía es falsa;
    # "not recetas" será True si está vacía. any() pregunta si eso ocurre
    # al menos una vez. Si falta algún tipo, no podemos cubrir las 21 comidas.
    if any(not recetas for recetas in grupos.values()):
        # None representa la ausencia de un resultado; no es un costo de cero.
        return None
    # min() obtiene el menor costo de cada tipo; sum() suma los tres mínimos;
    # len(DIAS) vale 7. Es posible repetir esas recetas los siete días.
    return len(DIAS) * sum(
        min(receta["costo"] for receta in grupos[tipo])
        for tipo in TIPOS_COMIDA
    )


def crear_lista_compras(menu):
    """Agrupa cada ingrediente y calcula su subtotal para toda la semana."""
    cantidades = {}
    # Recorremos tres niveles: días -> comidas -> ingredientes de cada comida.
    for dia in menu:
        for receta in dia["comidas"]:
            for ingrediente, cantidad in receta["ingredientes"].items():
                # .get(clave, 0) devuelve el total anterior o 0 si aún no existe.
                # Ejemplo: si ya llevábamos 60 g de arroz y sumamos 80, quedan 140.
                cantidades[ingrediente] = cantidades.get(ingrediente, 0) + cantidad

    compras = []
    for ingrediente, cantidad in cantidades.items():
        # Aquí cantidad ya es el total semanal de ese ingrediente.
        datos = INGREDIENTES[ingrediente]
        compras.append({
            "nombre": datos["nombre"],
            "cantidad": cantidad,
            "unidad": datos["unidad"],
            "precio_unitario": datos["precio"],
            "subtotal": cantidad * datos["precio"],
        })
    # sorted() devuelve una lista nueva ordenada.
    # key recibe una FUNCIÓN que indica qué valor comparar de cada elemento.
    # lambda compra: compra["nombre"] es una función pequeña sin nombre:
    # recibe una compra y devuelve su nombre. Así comparamos los nombres.
    # Equivale a:
    # def obtener_nombre(compra):
    #     return compra["nombre"]
    # return sorted(compras, key=obtener_nombre)
    return sorted(compras, key=lambda compra: compra["nombre"])


def generar_plan(presupuesto):
    """Devuelve un plan completo o None cuando no alcanza el presupuesto.

    Antes de elegir cada receta, reserva el costo mínimo de las comidas
    pendientes. Así una elección más cara nunca deja un día sin comida.
    La preferencia rota según el día para agregar variedad si el monto alcanza.
    """
    # str() convierte a texto y Decimal() lo interpreta como número decimal.
    # Esto permite recibir, por ejemplo, 25000 o Decimal("25000.50").
    presupuesto = Decimal(str(presupuesto))
    # is_finite() descarta valores especiales como infinito o NaN (no numérico).
    # El formulario ya valida, pero esta función también puede llamarse sola.
    if not presupuesto.is_finite() or presupuesto <= 0:
        # raise interrumpe con un error de programación/entrada. Es diferente
        # de devolver None por un presupuesto válido que simplemente no alcanza.
        raise ValueError("El presupuesto debe ser un número mayor que cero.")

    grupos = recetas_por_tipo()
    if any(not recetas for recetas in grupos.values()):
        return None

    # Otro diccionario por comprensión: tipo de comida -> su costo más bajo.
    minimos = {
        tipo: min(receta["costo"] for receta in recetas)
        for tipo, recetas in grupos.items()
    }
    reserva = len(DIAS) * sum(minimos.values())
    # Ni repitiendo las opciones más económicas se puede bajar de esta suma.
    if presupuesto < reserva:
        return None

    menu = []
    gastado = 0
    # enumerate() entrega posición y valor: (0, "Lunes"), (1, "Martes"), etc.
    for numero_dia, nombre_dia in enumerate(DIAS):
        comidas = []
        for tipo in TIPOS_COMIDA:
            # La reserva ahora cubre solo las comidas posteriores a esta.
            reserva -= minimos[tipo]
            recetas = grupos[tipo]
            # % obtiene el resto de la división. Con 3 recetas, produce
            # posiciones 0, 1, 2, 0, 1, 2, 0 al recorrer los siete días.
            inicio = numero_dia % len(recetas)
            # Estos cortes rotan la lista para empezar por otra receta.
            # Si recetas = [A, B, C] e inicio = 1, resulta [B, C] + [A].
            opciones = recetas[inicio:] + recetas[:inicio]

            for receta in opciones:
                # Gastado + esta comida + mínimo de las pendientes debe caber.
                # Como reservamos ese mínimo, siempre queda alguna opción
                # asequible en cada paso cuando el presupuesto inicial alcanza.
                if gastado + receta["costo"] + reserva <= presupuesto:
                    comidas.append(receta)
                    # += suma al valor anterior, igual que gastado = gastado + ...
                    gastado += receta["costo"]
                    # Ya elegimos esta comida: salimos solo del for de opciones.
                    break

        # Después de elegir sus tres comidas, añadimos el día completo al menú.
        menu.append({"dia": nombre_dia, "comidas": comidas})

    compras = crear_lista_compras(menu)
    # Calculamos el total desde las compras para mostrar el mismo importe.
    costo_total = sum(compra["subtotal"] for compra in compras)
    return {
        # La sesión usa JSON, que no maneja Decimal directamente. Guardamos
        # presupuesto y saldo como texto; los cálculos se hicieron antes.
        "presupuesto": str(presupuesto),
        "menu": menu,
        "compras": compras,
        "costo_total": costo_total,
        "saldo": str(presupuesto - costo_total),
    }
