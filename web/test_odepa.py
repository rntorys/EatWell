"""Pruebas sin internet: la API se simula para obtener resultados repetibles."""

import json
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch
from urllib.error import URLError

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from .data import INGREDIENTES
from .models import PlanGuardado, PreciosRegion
from .odepa import ErrorODEPA, consultar_api, descargar_region, obtener_precios, preparar_datos
from .planner import calcular_presupuesto_minimo, generar_plan


def fila(producto="Leche Fluida Entera", unidad="$/Caja de 1 Litro", precio="1234,560000", region="13"):
    return {
        "Producto": producto, "Unidad": unidad, "Precio promedio": precio,
        "ID region": region, "Fecha inicio": "2026-11-09",
    }


def ejemplo(region="13", precio="1234,560000"):
    return preparar_datos([fila(precio=precio, region=region)], region, "2026-11-09", "recurso-prueba")


class ConversionODEPATests(SimpleTestCase):
    def test_convierte_envases_y_promedia_sin_mezclar_unidades(self):
        datos = preparar_datos([
            fila(),
            fila("Huevo blanco grande (primera)", "$/bandeja 12 unidades", "1200"),
            fila("Huevo blanco grande (primera)", "$/bandeja 30 unidades", "6000"),
            fila("Spaghetti N�5", "$/envase 400 gramos", "800"),
            fila("Cebolla|Sin especificar|Primera", "$/kilo", "1500"),
            fila("Cebolla|Sin especificar|Primera", "$/unidad", "99999"),
        ], "13", "2026-11-09", "recurso")
        catalogo = datos["catalogo"]
        self.assertEqual(catalogo["leche"]["precio"], "1.23")
        self.assertEqual(catalogo["huevo"]["precio"], "150.00")
        self.assertEqual(catalogo["fideos"]["precio"], "2.00")
        self.assertEqual(catalogo["cebolla"]["precio"], "1.50")
        self.assertEqual(catalogo["atun"]["precio"], 1200)
        self.assertIn("Ejemplo", catalogo["atun"]["fuente"])
        self.assertEqual(INGREDIENTES["leche"]["precio"], 1)
        self.assertNotIn("fuente", INGREDIENTES["leche"])

    def test_no_confunde_pollo_ganso_con_pollo_ni_aceite_con_otro_producto(self):
        datos = preparar_datos([
            fila("Pollo Ganso", "$/kilo", "9000"),
            fila("Aceite de oliva", "$/litro", "10000"),
        ], "13", "2026-11-09", "recurso")
        self.assertIn("Ejemplo", datos["catalogo"]["pollo"]["fuente"])
        self.assertIn("Ejemplo", datos["catalogo"]["aceite"]["fuente"])

    def test_ignora_precios_invalidos_y_rechaza_un_conjunto_vacio(self):
        filas = []
        for precio in ["", None, "NaN", "Infinity", "-1", "0", "abc"]:
            filas.append(fila(precio=precio))
        with self.assertRaises(ErrorODEPA):
            preparar_datos(filas, "13", "2026-11-09", "recurso")
        filas.append(fila(precio="1500,50"))
        self.assertEqual(ejemplo(precio="1500,50")["catalogo"]["leche"]["precio"], "1.50")

    def test_decimales_mantienen_presupuesto_costos_y_compras_consistentes(self):
        catalogo = ejemplo()["catalogo"]
        minimo = calcular_presupuesto_minimo(catalogo)
        self.assertIsNone(generar_plan(minimo - Decimal("0.01"), catalogo))
        for presupuesto in [minimo, minimo + Decimal("0.01"), Decimal("25000.50")]:
            plan = generar_plan(presupuesto, catalogo)
            total_comidas = Decimal("0")
            cantidad = 0
            for dia in plan["menu"]:
                for comida in dia["comidas"]:
                    total_comidas += Decimal(str(comida["costo"]))
                    cantidad += 1
            total_compras = Decimal("0")
            for compra in plan["compras"]:
                subtotal = Decimal(str(compra["precio_unitario"])) * compra["cantidad"]
                self.assertEqual(subtotal, Decimal(str(compra["subtotal"])))
                total_compras += subtotal
            self.assertEqual(cantidad, 21)
            self.assertEqual(total_comidas, total_compras)
            self.assertEqual(total_compras, Decimal(str(plan["costo_total"])))
            self.assertLessEqual(total_compras, presupuesto)
            self.assertEqual(Decimal(plan["saldo"]), presupuesto - total_compras)
            json.dumps(plan)  # El plan completo puede guardarse en JSONField.

    def test_api_detecta_error_de_red_y_respuesta_invalida(self):
        with patch("web.odepa.urlopen", side_effect=URLError("sin conexión")):
            with self.assertRaises(ErrorODEPA):
                consultar_api("package_show", {})
        for contenido in [b'{"success":false}', b'not json', b'{"success":true,"result":[]}']:
            with patch("web.odepa.urlopen", return_value=BytesIO(contenido)):
                with self.assertRaises(ErrorODEPA):
                    consultar_api("package_show", {})

    def test_descarga_todas_las_paginas_de_la_region_y_semana(self):
        paquete = {"resources": [{"name": f"Precios {date.today().year}", "id": "recurso", "datastore_active": True}]}
        with patch("web.odepa.consultar_api", side_effect=[
            paquete, {"records": [fila()]},
            {"records": [fila(precio="1000")], "total": 2},
            {"records": [fila(precio="2000")], "total": 2},
        ]) as api:
            datos = descargar_region("13")
        self.assertEqual(datos["catalogo"]["leche"]["precio"], "1.50")
        self.assertEqual(api.call_count, 4)
        parametros = api.call_args_list[-1].args[1]
        self.assertEqual(parametros["offset"], 1)
        self.assertEqual(json.loads(parametros["filters"]), {"ID region": "13", "Fecha inicio": "2026-11-09"})

    def test_no_acepta_datos_de_otra_region_o_descarga_incompleta(self):
        paquete = {"resources": [{"name": f"Precios {date.today().year}", "id": "recurso", "datastore_active": True}]}
        for pagina in [{"records": [fila(region="5")], "total": 1}, {"records": [], "total": 1}]:
            with patch("web.odepa.consultar_api", side_effect=[paquete, {"records": [fila()]}, pagina]):
                with self.assertRaises(ErrorODEPA):
                    descargar_region("13")


class IntegracionODEPATests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(username="prueba")
        self.client.force_login(self.usuario)
        self.copia = PreciosRegion.objects.create(region="13", datos=ejemplo())

    def test_copia_reciente_no_consulta_la_api(self):
        with patch("web.odepa.descargar_region") as descargar:
            catalogo, info, productos = obtener_precios("13")
        descargar.assert_not_called()
        self.assertEqual(catalogo["leche"]["precio"], "1.23")
        self.assertEqual(info["region_id"], "13")

    def test_copia_antigua_se_actualiza_solo_en_su_region(self):
        PreciosRegion.objects.filter(pk=self.copia.pk).update(actualizado=timezone.now() - timedelta(days=2))
        PreciosRegion.objects.create(region="5", datos=ejemplo("5", "2500"))
        with patch("web.odepa.descargar_region", return_value=ejemplo(precio="1800")) as descargar:
            catalogo, info, productos = obtener_precios("13")
        descargar.assert_called_once_with("13")
        self.assertEqual(catalogo["leche"]["precio"], "1.80")
        self.assertEqual(PreciosRegion.objects.get(region="5").datos["catalogo"]["leche"]["precio"], "2.50")

    def test_error_con_copia_conserva_datos_y_fecha_y_lo_informa(self):
        fecha = timezone.now() - timedelta(days=2)
        PreciosRegion.objects.filter(pk=self.copia.pk).update(actualizado=fecha)
        with patch("web.odepa.descargar_region", side_effect=ErrorODEPA("Sin red")):
            catalogo, info, productos = obtener_precios("13")
        self.assertIn("última copia", info["aviso"])
        self.copia.refresh_from_db()
        self.assertEqual(self.copia.actualizado, fecha)
        self.assertEqual(self.copia.datos, ejemplo())

    def test_error_sin_copia_no_inventa_precios_ni_borra_el_plan(self):
        self.client.post("/", {"region": "13", "presupuesto": "25000"})
        anterior = PlanGuardado.objects.get(usuario=self.usuario).datos
        with patch("web.odepa.descargar_region", side_effect=ErrorODEPA("No pudimos conectar con ODEPA.")):
            respuesta = self.client.post("/", {"region": "5", "presupuesto": "25000"})
        self.assertContains(respuesta, "No pudimos conectar con ODEPA")
        self.assertNotContains(respuesta, "No encontramos un plan con ese presupuesto")
        self.assertEqual(PlanGuardado.objects.get(usuario=self.usuario).datos, anterior)
        self.assertFalse(PreciosRegion.objects.filter(region="5").exists())

    def test_region_se_guarda_y_los_precios_del_plan_no_cambian(self):
        PreciosRegion.objects.create(region="5", datos=ejemplo("5", "2500"))
        respuesta = self.client.post("/", {"region": "5", "presupuesto": "25000"}, follow=True)
        self.assertContains(respuesta, "Valparaíso")
        plan = PlanGuardado.objects.get(usuario=self.usuario).datos
        self.assertEqual(plan["precios"]["region_id"], "5")
        PreciosRegion.objects.filter(region="5").update(datos=ejemplo("5", "5000"))
        self.assertEqual(self.client.get("/plan/").context["plan"], plan)
        self.assertEqual(self.client.get("/").context["form"]["region"].value(), "5")

    def test_region_ausente_o_invalida_no_hace_consultas(self):
        with patch("web.views.obtener_precios") as consulta:
            for region in ["", "99", "https://otro.example"]:
                respuesta = self.client.post("/", {"region": region, "presupuesto": "25000"})
                self.assertTrue(respuesta.context["form"].errors.get("region"))
        consulta.assert_not_called()

    def test_buscador_y_aviso_de_precios_de_ejemplo(self):
        respuesta = self.client.get("/precios/", {"region": "13", "busqueda": "leche"})
        self.assertContains(respuesta, "Leche Fluida Entera")
        self.assertContains(respuesta, "precios ODEPA y precios de ejemplo")
        self.assertEqual(len(respuesta.context["productos"]), 1)
        respuesta = self.client.get("/precios/", {"region": "13", "busqueda": "inexistente"})
        self.assertContains(respuesta, "No encontramos productos")
        self.client.logout()
        self.assertRedirects(self.client.get("/precios/"), "/ingresar/?next=/precios/")
