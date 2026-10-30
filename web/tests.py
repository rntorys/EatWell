from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from .planner import DIAS, TIPOS_COMIDA, calcular_presupuesto_minimo, generar_plan


# assertEqual comprueba que dos valores sean iguales.
# SimpleTestCase sirve aquí porque el cálculo no necesita base de datos.
class PlanificadorTests(SimpleTestCase):
    def test_minimo_exacto_cubre_la_semana_y_agrupa_ingredientes(self):
        # Mínimo calculado a mano: 7 x (520 + 506 + 546).
        self.assertEqual(calcular_presupuesto_minimo(), 11004)
        plan = generar_plan(11004)
        self.assertEqual(plan["costo_total"], 11004)
        self.assertEqual(Decimal(plan["saldo"]), 0)

        dias = []
        for dia in plan["menu"]:
            dias.append(dia["dia"])
            tipos = []
            for comida in dia["comidas"]:
                tipos.append(comida["tipo"])
            self.assertEqual(tipos, list(TIPOS_COMIDA))
        self.assertEqual(dias, list(DIAS))

        cantidades = {}
        for compra in plan["compras"]:
            cantidades[compra["nombre"]] = compra["cantidad"]
        self.assertEqual(cantidades, {
            "Avena": 420, "Leche": 1400, "Plátano": 700,
            "Lentejas": 630, "Arroz": 420, "Zanahorias": 1120,
            "Cebollas": 630, "Aceite": 70, "Sal": 14,
            "Papas": 1400, "Pan integral": 420,
        })

    def test_un_centavo_bajo_el_minimo_no_permite_un_plan(self):
        self.assertIsNone(generar_plan(Decimal("11003.99")))

    def test_varios_presupuestos_cubren_21_comidas_sin_exceder_el_monto(self):
        for presupuesto in [11004, 11005, 11100, 12000, 13000, 15000, 16979, 25000]:
            plan = generar_plan(presupuesto)
            cantidad_comidas = 0
            costo_comidas = 0
            for dia in plan["menu"]:
                for comida in dia["comidas"]:
                    cantidad_comidas += 1
                    costo_comidas += comida["costo"]

            costo_compras = 0
            nombres = []
            for compra in plan["compras"]:
                self.assertNotIn(compra["nombre"], nombres)
                nombres.append(compra["nombre"])
                subtotal = compra["cantidad"] * compra["precio_unitario"]
                self.assertEqual(compra["subtotal"], subtotal)
                costo_compras += compra["subtotal"]

            self.assertEqual(cantidad_comidas, 21)
            self.assertLessEqual(plan["costo_total"], presupuesto)
            self.assertEqual(costo_comidas, plan["costo_total"])
            self.assertEqual(costo_compras, plan["costo_total"])
            self.assertEqual(Decimal(plan["saldo"]), presupuesto - plan["costo_total"])

    def test_un_presupuesto_holgado_permite_variedad(self):
        plan = generar_plan(25000)
        for tipo in TIPOS_COMIDA:
            nombres = []
            for dia in plan["menu"]:
                for comida in dia["comidas"]:
                    if comida["tipo"] == tipo and comida["nombre"] not in nombres:
                        nombres.append(comida["nombre"])
            self.assertGreater(len(nombres), 1)

    def test_catalogo_incompleto_no_genera_un_plan_parcial(self):
        # patch simula un catálogo vacío solo durante esta prueba.
        with patch("web.planner.RECETAS", []):
            self.assertIsNone(generar_plan(25000))
            self.assertIsNone(calcular_presupuesto_minimo())


# TestCase usa una base de datos de prueba para las sesiones.
# self.client simula el navegador; follow=True sigue las redirecciones.
class FlujoEatWellTests(TestCase):
    def test_escenario_principal_generar_y_confirmar(self):
        respuesta = self.client.post("/", {"presupuesto": "25000"}, follow=True)
        self.assertRedirects(respuesta, "/plan/")
        self.assertContains(respuesta, "Lista de compras")
        self.assertContains(respuesta, "16.979")

        # context contiene los datos que la vista entregó al HTML.
        plan = respuesta.context["plan"]
        self.assertEqual(len(plan["menu"]), 7)
        for dia in plan["menu"]:
            self.assertEqual(len(dia["comidas"]), 3)
        self.assertEqual(plan["costo_total"], 16979)
        self.assertEqual(Decimal(plan["saldo"]), 8021)
        self.assertFalse(plan["confirmado"])

        respuesta = self.client.post("/plan/", {
            "accion": "confirmar",
            "plan_id": plan["id"],
            # Cambiar estos campos no debe alterar el cálculo del servidor.
            "costo_total": "1",
            "presupuesto": "999999",
        }, follow=True)
        self.assertContains(respuesta, "Plan confirmado")
        self.assertTrue(self.client.session["plan"]["confirmado"])
        self.assertEqual(self.client.session["plan"]["costo_total"], 16979)
        self.assertEqual(self.client.session["plan"]["presupuesto"], "25000")
        self.assertContains(self.client.get("/plan/"), "Plan confirmado")

    def test_escenario_alternativo_monto_insuficiente_y_reintento(self):
        respuesta = self.client.post("/", {"presupuesto": "5000"})
        self.assertContains(respuesta, "No encontramos un plan con ese presupuesto")
        self.assertContains(respuesta, "Ajusta el monto")
        self.assertContains(respuesta, "11.004")
        self.assertNotIn("plan", self.client.session)
        self.assertEqual(respuesta.context["form"]["presupuesto"].value(), "5000")

        respuesta = self.client.post("/", {"presupuesto": "25000"}, follow=True)
        self.assertRedirects(respuesta, "/plan/")
        self.assertLessEqual(respuesta.context["plan"]["costo_total"], 25000)

    def test_presupuestos_invalidos_muestran_error(self):
        montos = ["", "0", "-100", "hola", "NaN", "Infinity", "25000.123", "1000000000000"]
        for monto in montos:
            respuesta = self.client.post("/", {"presupuesto": monto})
            self.assertEqual(respuesta.status_code, 200)
            self.assertTrue(respuesta.context["form"].errors.get("presupuesto"))
            self.assertNotIn("plan", self.client.session)

    def test_presupuesto_decimal_se_conserva_sin_redondear(self):
        respuesta = self.client.post("/", {"presupuesto": "25000.50"}, follow=True)
        plan = respuesta.context["plan"]
        self.assertEqual(Decimal(plan["presupuesto"]), Decimal("25000.50"))
        self.assertEqual(Decimal(plan["saldo"]), Decimal("8021.50"))
        self.assertContains(respuesta, "8.021,50")

    def test_ajustar_regresa_al_formulario_y_descarta_el_plan(self):
        self.client.post("/", {"presupuesto": "25000"})
        plan_id = self.client.session["plan"]["id"]
        respuesta = self.client.post("/plan/", {
            "accion": "ajustar", "plan_id": plan_id,
        }, follow=True)
        self.assertRedirects(respuesta, "/")
        self.assertNotIn("plan", self.client.session)
        self.assertEqual(respuesta.context["form"]["presupuesto"].value(), "25000")

    def test_acceso_sin_plan_vuelve_al_formulario(self):
        self.assertRedirects(self.client.get("/plan/"), "/")
        respuesta = self.client.post("/plan/", {"accion": "confirmar"})
        self.assertRedirects(respuesta, "/")

    def test_ver_el_resultado_no_confirma_el_plan(self):
        self.client.post("/", {"presupuesto": "25000"})
        self.client.get("/plan/", {"accion": "confirmar"})
        self.assertFalse(self.client.session["plan"]["confirmado"])

    def test_no_confirma_un_plan_desde_una_pestana_antigua(self):
        self.client.post("/", {"presupuesto": "25000"})
        id_anterior = self.client.session["plan"]["id"]
        self.client.post("/", {"presupuesto": "12000"})
        respuesta = self.client.post("/plan/", {
            "accion": "confirmar", "plan_id": id_anterior,
        }, follow=True)
        self.assertContains(respuesta, "La planificación cambió")
        self.assertFalse(self.client.session["plan"]["confirmado"])

    def test_solicitud_nueva_fallida_no_deja_un_plan_anterior_confirmable(self):
        for monto in ["5000", "hola"]:
            self.client.post("/", {"presupuesto": "25000"})
            self.client.post("/", {"presupuesto": monto})
            self.assertNotIn("plan", self.client.session)
            self.assertRedirects(self.client.get("/plan/"), "/")
