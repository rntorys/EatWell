"""Lectura de la API pública de ODEPA y conversión de precios para EatWell."""

import json
import re
import ssl
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import truststore
from django.utils import timezone

from .data import INGREDIENTES
from .models import PreciosRegion

API = "https://datos.odepa.gob.cl/api/3/action/"
FUENTE = "https://datos.odepa.gob.cl/dataset/precios-consumidor"
REGIONES = [
    ("15", "Arica y Parinacota"), ("4", "Coquimbo"), ("5", "Valparaíso"),
    ("13", "Metropolitana"), ("7", "Maule"), ("16", "Ñuble"),
    ("8", "Biobío"), ("9", "La Araucanía"), ("10", "Los Lagos"),
]

# Equivalencias revisadas. El número indica gramos, ml o unidades del envase.
# Algunos nombres llegan con el carácter � en la API; incluimos ese alias exacto.
EQUIVALENCIAS = {
    "leche": (["Leche Fluida Entera"], {"$/Caja de 1 Litro": 1000}),
    "platano": (["Plátano", "Pl�tano"], {"$/kilo": 1000}),
    "pan": (["Hallulla integral"], {"$/kilo": 1000}),
    "huevo": (["Huevo blanco grande (primera)"], {
        "$/bandeja 12 unidades": 12, "$/bandeja 30 unidades": 30,
    }),
    "arroz": (["Arroz grano largo delgado grado 2"], {"$/kilo": 1000}),
    "lentejas": (["Lentejas 6 mm", "Lentejas 6mm"], {
        "$/kilo": 1000, "$/kilo (en envase de 1 kilo)": 1000,
    }),
    "fideos": (["Spaghetti N°5", "Spaghetti Nº5", "Spaghetti N�5"], {
        "$/envase 400 gramos": 400,
    }),
    "pollo": (["Pollo Pechuga Deshuesada"], {"$/kilo": 1000}),
    "papa": (["Papa"], {"$/kilo": 1000}),
    "zanahoria": (["Zanahoria"], {"$/kilo": 1000}),
    "tomate": (["Tomate"], {"$/kilo": 1000}),
    "cebolla": (["Cebolla"], {"$/kilo": 1000}),
    "aceite": (["Aceite vegetal"], {"$/botella 900 ml": 900}),
}


class ErrorODEPA(Exception):
    """Error que se puede explicar al usuario sin detalles del servidor."""


def consultar_api(accion, parametros):
    url = API + accion + "?" + urlencode(parametros)
    peticion = Request(url, headers={"User-Agent": "EatWell/1.0", "Accept": "application/json"})
    # Certificados del sistema: la verificación HTTPS permanece activada.
    contexto = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    try:
        with urlopen(peticion, timeout=15, context=contexto) as respuesta:
            datos = json.load(respuesta)
        if not isinstance(datos, dict) or datos.get("success") is not True:
            raise ErrorODEPA("ODEPA no pudo entregar los precios. Inténtalo más tarde.")
        resultado = datos.get("result")
        if not isinstance(resultado, dict):
            raise ErrorODEPA("ODEPA entregó una respuesta con un formato inesperado.")
        return resultado
    except (URLError, TimeoutError, OSError, ValueError) as error:
        raise ErrorODEPA("No pudimos conectar con ODEPA. Inténtalo más tarde.") from error


def descargar_region(region):
    paquete = consultar_api("package_show", {"id": "precios-consumidor"})
    recursos = []
    for recurso in paquete.get("resources", []):
        anio = re.search(r"\b(20\d{2})\b", recurso.get("name", ""))
        if anio and recurso.get("datastore_active") and int(anio[1]) <= date.today().year:
            recursos.append((int(anio[1]), recurso["id"]))
    recursos.sort(reverse=True)
    # Al comenzar un año puede que una región solo tenga datos del anterior.
    for anio, recurso_id in recursos[:2]:
        filtros = {"ID region": region}
        ultima = consultar_api("datastore_search", {
            "resource_id": recurso_id, "filters": json.dumps(filtros),
            "sort": "Fecha inicio desc", "limit": 1,
        }).get("records", [])
        if not ultima:
            continue
        semana = ultima[0].get("Fecha inicio", "")
        try:
            date.fromisoformat(semana)
        except (ValueError, TypeError) as error:
            raise ErrorODEPA("ODEPA entregó una fecha que no podemos interpretar.") from error
        filtros["Fecha inicio"] = semana
        filas = []
        offset = 0
        while offset < 20000:
            pagina = consultar_api("datastore_search", {
                "resource_id": recurso_id, "filters": json.dumps(filtros),
                "sort": "_id asc", "limit": 500, "offset": offset,
            })
            registros = pagina.get("records", [])
            if not registros:
                if offset < pagina.get("total", 0):
                    raise ErrorODEPA("La descarga de ODEPA quedó incompleta. Inténtalo más tarde.")
                break
            for fila in registros:
                if str(fila.get("ID region")) != region or fila.get("Fecha inicio") != semana:
                    raise ErrorODEPA("ODEPA devolvió datos de otra región o semana.")
            filas.extend(registros)
            offset += len(registros)
            if offset >= pagina.get("total", 20000):
                break
        else:
            raise ErrorODEPA("La respuesta de ODEPA es demasiado grande. Inténtalo más tarde.")
        if filas:
            return preparar_datos(filas, region, semana, recurso_id)
    raise ErrorODEPA("ODEPA no tiene precios disponibles para esta región.")


def precio_decimal(valor):
    try:
        numero = Decimal(str(valor).strip().replace(",", "."))
    except InvalidOperation:
        return None
    if not numero.is_finite() or numero <= 0:
        return None
    return numero


def redondear(numero):
    return numero.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def preparar_datos(filas, region, semana, recurso_id):
    grupos = {}
    precios_ingredientes = {}
    referencias = {}
    for fila in filas:
        precio = precio_decimal(fila.get("Precio promedio"))
        producto = fila.get("Producto", "")
        unidad = fila.get("Unidad", "")
        if precio is None or not isinstance(producto, str) or not producto or not unidad:
            continue
        clave = (producto, unidad)
        if clave not in grupos:
            grupos[clave] = []
        grupos[clave].append(precio)
        # Las frutas y hortalizas incluyen variedad y calidad después de |.
        especie = producto.split("|")[0]
        for ingrediente, (nombres, unidades) in EQUIVALENCIAS.items():
            if especie in nombres and unidad in unidades:
                if ingrediente not in precios_ingredientes:
                    precios_ingredientes[ingrediente] = []
                    referencias[ingrediente] = set()
                precios_ingredientes[ingrediente].append(precio / unidades[unidad])
                referencias[ingrediente].add(producto)
    if not grupos:
        raise ErrorODEPA("ODEPA no entregó precios válidos para esta región.")

    productos = []
    for (producto, unidad), precios in sorted(grupos.items()):
        productos.append({
            "nombre": producto, "unidad": unidad,
            "precio": str(redondear(sum(precios) / len(precios))),
            "observaciones": len(precios),
        })
    catalogo = {}
    faltantes = []
    for clave, datos in INGREDIENTES.items():
        ingrediente = datos.copy()
        if clave in precios_ingredientes:
            precios = precios_ingredientes[clave]
            precio = redondear(sum(precios) / len(precios))
            if precio <= 0:
                raise ErrorODEPA("Un precio convertido es demasiado pequeño para usarlo.")
            ingrediente["precio"] = str(precio)
            ingrediente["fuente"] = "ODEPA"
            ingrediente["referencia"] = "; ".join(sorted(referencias[clave]))
        else:
            ingrediente["fuente"] = "Ejemplo (sin equivalencia ODEPA)"
            ingrediente["referencia"] = "Precio del catálogo de demostración de EatWell"
            faltantes.append(datos["nombre"])
        catalogo[clave] = ingrediente
    return {
        "catalogo": catalogo, "productos": productos,
        "info": {
            "region_id": region, "region": dict(REGIONES)[region],
            "semana": semana, "recurso_id": recurso_id, "url": FUENTE,
            "faltantes": faltantes,
            "ingredientes_odepa": len(INGREDIENTES) - len(faltantes),
        },
    }


def obtener_precios(region, forzar=False):
    if region not in dict(REGIONES):
        raise ErrorODEPA("Selecciona una región cubierta por ODEPA.")
    guardado = PreciosRegion.objects.filter(region=region).first()
    aviso = ""
    if not forzar and guardado is not None and timezone.now() - guardado.actualizado < timedelta(hours=24):
        datos = guardado.datos
    else:
        try:
            datos = descargar_region(region)
        except ErrorODEPA:
            if guardado is None:
                raise
            datos = guardado.datos
            aviso = "No pudimos actualizar ODEPA. Usamos la última copia guardada; revisa su fecha."
        else:
            guardado, creado = PreciosRegion.objects.update_or_create(
                region=region, defaults={"datos": datos},
            )
    # La fecha y los precios viajan con el plan y no cambian al actualizar ODEPA.
    info = datos["info"].copy()
    info["consultado"] = guardado.actualizado.isoformat()
    info["aviso"] = aviso
    return datos["catalogo"], info, datos["productos"]
