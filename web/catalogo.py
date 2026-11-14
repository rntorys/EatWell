"""Une los ingredientes regionales con los productos y recetas de cada cuenta."""
from decimal import Decimal
from hashlib import sha256

from .data import RECETAS
from .models import Favorito, ProductoPersonal, RecetaPersonal
from .odepa import redondear


# Solo convertimos unidades cuyo tamaño conocemos; los demás productos se
# pueden consultar, pero no se ofrecen como ingredientes automáticamente.
UNIDADES_ODEPA = {
    "$/kilo": ("g", 1000), "$/envase 1 kilo": ("g", 1000),
    "$/kilo (en envase de 1 kilo)": ("g", 1000),
    "$/bolsa 1 kilo": ("g", 1000), "$/bolsa 800 grs": ("g", 800),
    "$/envase 400 gramos": ("g", 400), "$/pan de 250 gramos": ("g", 250),
    "$/pote 500 gramos": ("g", 500), "$/litro": ("ml", 1000),
    "$/Caja de 1 Litro": ("ml", 1000), "$/botella 900 ml": ("ml", 900),
    "$/unidad": ("unidad", 1), "$/bandeja 12 unidades": ("unidad", 12),
    "$/bandeja 20 unidades": ("unidad", 20), "$/bandeja 30 unidades": ("unidad", 30),
}


def clave_producto_odepa(producto):
    identidad = producto["nombre"] + "|" + producto["unidad"]
    return "odepa_" + sha256(identidad.encode("utf-8")).hexdigest()[:24]


def clave_receta(receta):
    if receta.get("personal_id"):
        return "receta_" + str(receta["personal_id"])
    return "base_" + sha256(receta["nombre"].encode("utf-8")).hexdigest()[:24]


def marcar_favoritos(usuario, tipo, elementos):
    claves = set(Favorito.objects.filter(usuario=usuario, tipo=tipo).values_list("clave", flat=True))
    favoritos = []
    otros = []
    for elemento in elementos:
        elemento = elemento.copy()
        elemento["favorito"] = elemento["clave"] in claves
        if elemento["favorito"]:
            favoritos.append(elemento)
        else:
            otros.append(elemento)
    return favoritos + otros


def ingredientes_disponibles(usuario, regionales, publicados):
    catalogo = {}
    for clave, datos in regionales.items():
        catalogo[clave] = datos.copy()
    for producto in publicados:
        conversion = UNIDADES_ODEPA.get(producto["unidad"])
        if conversion is None:
            continue
        unidad, cantidad = conversion
        precio = redondear(Decimal(producto["precio"]) / cantidad)
        if precio <= 0:
            continue
        # El identificador no depende del orden de la API ni de la región.
        clave = clave_producto_odepa(producto)
        catalogo[clave] = {
            "nombre": producto["nombre"], "unidad": unidad, "precio": str(precio),
            "fuente": "ODEPA", "referencia": producto["unidad"],
        }
    for producto in ProductoPersonal.objects.filter(usuario=usuario).order_by("id"):
        precio = redondear(producto.precio_referencia / producto.cantidad_referencia)
        catalogo["personal_" + str(producto.pk)] = {
            "nombre": producto.nombre, "unidad": producto.unidad, "precio": str(precio),
            "fuente": "Producto personal", "referencia": producto.propiedades or "Precio ingresado por ti",
        }
    return ordenar_catalogo(usuario, catalogo)


def ordenar_catalogo(usuario, catalogo):
    elementos = []
    for clave, datos in catalogo.items():
        elementos.append(dict(datos, clave=clave))
    ordenados = {}
    for producto in marcar_favoritos(usuario, "producto", elementos):
        ordenados[producto["clave"]] = producto
    return ordenados


def recetas_disponibles(usuario, catalogo):
    recetas = []
    omitidas = []
    for receta in RecetaPersonal.objects.filter(usuario=usuario).order_by("-id"):
        faltan = False
        for clave in receta.ingredientes:
            if clave not in catalogo:
                faltan = True
        if faltan:
            omitidas.append(receta.nombre)
            continue
        recetas.append({
            "nombre": receta.nombre, "tipo": receta.tipo, "porciones": 1,
            "ingredientes": receta.ingredientes, "instrucciones": receta.instrucciones,
            "personal_id": receta.pk,
        })
    # Las recetas propias se prueban primero, siempre respetando el presupuesto.
    disponibles = []
    for receta in recetas + RECETAS:
        disponibles.append(dict(receta, clave=clave_receta(receta)))
    return marcar_favoritos(usuario, "receta", disponibles), omitidas


def opciones_ingredientes(catalogo):
    etiquetas = {}
    repeticiones = {}
    for clave, producto in catalogo.items():
        if clave.startswith("personal_"):
            origen = "Mi producto"
        elif clave.startswith("odepa_"):
            origen = "ODEPA: " + producto["referencia"]
        else:
            origen = "Ingrediente de EatWell"
        base = f"{producto['nombre']} ({producto['unidad']}) — {origen}"
        etiquetas[clave] = base
        repeticiones[base] = repeticiones.get(base, 0) + 1
    opciones = {}
    for clave, base in etiquetas.items():
        etiqueta = base
        if repeticiones[base] > 1:
            # Marcar un favorito no debe cambiar qué producto identifica un nombre.
            etiqueta = f"{base} (producto {clave.removeprefix('personal_')})"
        opciones[etiqueta] = clave
    return opciones


def selector_productos(catalogo):
    elementos = []
    for etiqueta, clave in opciones_ingredientes(catalogo).items():
        elementos.append({"clave": clave, "nombre": catalogo[clave]["nombre"], "etiqueta": etiqueta, "favorito": catalogo[clave].get("favorito", False)})
    return elementos
