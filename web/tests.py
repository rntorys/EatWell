from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase

from .models import PlanGuardado
from .data import INGREDIENTES, RECETAS
from .planner import DIAS, TIPOS_COMIDA, calcular_presupuesto_minimo, generar_plan


def precios_de_prueba(region):
    # Estos tests conservan los montos originales sin depender de internet.
    return INGREDIENTES, {
        "region_id": region, "region": "Metropolitana", "semana": "2026-11-09",
        "faltantes": [], "aviso": "Datos simulados de prueba",
    }, []


# assertEqual comprueba que dos valores sean iguales.
# SimpleTestCase sirve aquí porque el cálculo no necesita base de datos.
class PlanificadorTests(SimpleTestCase):
    def setUp(self):
        # Conservamos los 11 ejemplos originales para comprobar sus montos exactos.
        recetas = patch("web.planner.RECETAS", RECETAS[:11])
        recetas.start()
        self.addCleanup(recetas.stop)

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


# TestCase usa una base temporal para usuarios, planes y sesiones.
# self.client simula el navegador; follow=True sigue las redirecciones.
class FlujoEatWellTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(username="estudiante")

    def setUp(self):
        # Aquí probamos el planificador con un usuario ya identificado.
        self.client.force_login(self.usuario)
        consulta = patch("web.views.obtener_precios", side_effect=precios_de_prueba)
        consulta.start()
        self.addCleanup(consulta.stop)
        recetas = patch("web.catalogo.RECETAS", RECETAS[:11])
        recetas.start()
        self.addCleanup(recetas.stop)

    def plan_guardado(self):
        return PlanGuardado.objects.get(usuario=self.usuario).datos

    def test_escenario_principal_generar_y_confirmar(self):
        respuesta = self.client.post("/", {"region": "13", "presupuesto": "25000"}, follow=True)
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
        self.assertTrue(self.plan_guardado()["confirmado"])
        self.assertEqual(self.plan_guardado()["costo_total"], 16979)
        self.assertEqual(self.plan_guardado()["presupuesto"], "25000")
        self.assertContains(self.client.get("/plan/"), "Plan confirmado")

    def test_escenario_alternativo_monto_insuficiente_y_reintento(self):
        respuesta = self.client.post("/", {"region": "13", "presupuesto": "5000"})
        self.assertContains(respuesta, "No encontramos un plan con ese presupuesto")
        self.assertContains(respuesta, "Ajusta el monto")
        self.assertContains(respuesta, "11.004")
        self.assertFalse(PlanGuardado.objects.filter(usuario=self.usuario).exists())
        self.assertEqual(respuesta.context["form"]["presupuesto"].value(), "5000")

        respuesta = self.client.post("/", {"region": "13", "presupuesto": "25000"}, follow=True)
        self.assertRedirects(respuesta, "/plan/")
        self.assertLessEqual(respuesta.context["plan"]["costo_total"], 25000)

    def test_presupuestos_invalidos_muestran_error(self):
        montos = ["", "0", "-100", "hola", "NaN", "Infinity", "25000.123", "1000000000000"]
        for monto in montos:
            respuesta = self.client.post("/", {"region": "13", "presupuesto": monto})
            self.assertEqual(respuesta.status_code, 200)
            self.assertTrue(respuesta.context["form"].errors.get("presupuesto"))
            self.assertFalse(PlanGuardado.objects.filter(usuario=self.usuario).exists())

    def test_presupuesto_decimal_se_conserva_sin_redondear(self):
        respuesta = self.client.post("/", {"region": "13", "presupuesto": "25000.50"}, follow=True)
        plan = respuesta.context["plan"]
        self.assertEqual(Decimal(plan["presupuesto"]), Decimal("25000.50"))
        self.assertEqual(Decimal(plan["saldo"]), Decimal("8021.50"))
        self.assertContains(respuesta, "8.021,50")

    def test_ajustar_conserva_el_plan_hasta_generar_otro_valido(self):
        self.client.post("/", {"region": "13", "presupuesto": "25000"})
        plan_id = self.plan_guardado()["id"]
        respuesta = self.client.post("/plan/", {
            "accion": "ajustar", "plan_id": plan_id,
        }, follow=True)
        self.assertRedirects(respuesta, "/")
        self.assertEqual(self.plan_guardado()["id"], plan_id)
        self.assertEqual(respuesta.context["form"]["presupuesto"].value(), "25000")
        self.client.post("/", {"region": "13", "presupuesto": "12000"})
        self.assertNotEqual(self.plan_guardado()["id"], plan_id)
        self.assertEqual(PlanGuardado.objects.filter(usuario=self.usuario).count(), 1)

    def test_acceso_sin_plan_vuelve_al_formulario(self):
        self.assertRedirects(self.client.get("/plan/"), "/")
        respuesta = self.client.post("/plan/", {"accion": "confirmar"})
        self.assertRedirects(respuesta, "/")

    def test_ver_el_resultado_no_confirma_el_plan(self):
        self.client.post("/", {"region": "13", "presupuesto": "25000"})
        self.client.get("/plan/", {"accion": "confirmar"})
        self.assertFalse(self.plan_guardado()["confirmado"])

    def test_no_confirma_un_plan_desde_una_pestana_antigua(self):
        self.client.post("/", {"region": "13", "presupuesto": "25000"})
        id_anterior = self.plan_guardado()["id"]
        self.client.post("/", {"region": "13", "presupuesto": "12000"})
        respuesta = self.client.post("/plan/", {
            "accion": "confirmar", "plan_id": id_anterior,
        }, follow=True)
        self.assertContains(respuesta, "La planificación cambió")
        self.assertFalse(self.plan_guardado()["confirmado"])

    def test_solicitud_fallida_conserva_el_plan_guardado(self):
        for monto in ["5000", "hola"]:
            self.client.post("/", {"region": "13", "presupuesto": "25000"})
            anterior = self.plan_guardado()
            self.client.post("/", {"region": "13", "presupuesto": monto})
            self.assertEqual(self.plan_guardado(), anterior)
            self.assertContains(self.client.get("/"), "Ver mi plan guardado")


class CuentasTests(TestCase):
    def setUp(self):
        consulta = patch("web.views.obtener_precios", side_effect=precios_de_prueba)
        consulta.start()
        self.addCleanup(consulta.stop)
        recetas = patch("web.catalogo.RECETAS", RECETAS[:11])
        recetas.start()
        self.addCleanup(recetas.stop)

    @classmethod
    def setUpTestData(cls):
        cls.clave = "Comidas-Verdes-2026!"
        cls.usuario = get_user_model().objects.create_user(
            username="ana", password=cls.clave,
        )
        cls.otro = get_user_model().objects.create_user(
            username="diego", password=cls.clave,
        )

    def test_las_paginas_del_plan_exigen_iniciar_sesion(self):
        for ruta in ["/", "/plan/"]:
            respuesta = self.client.get(ruta)
            self.assertRedirects(respuesta, "/ingresar/?next=" + ruta)
            respuesta = self.client.post(ruta, {"region": "13", "presupuesto": "25000"})
            self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(PlanGuardado.objects.count(), 0)

    def test_registro_guarda_hash_e_inicia_sesion(self):
        respuesta = self.client.post("/registro/", {
            "username": "nueva", "password1": self.clave, "password2": self.clave,
        }, follow=True)
        self.assertRedirects(respuesta, "/")
        nueva = get_user_model().objects.get(username="nueva")
        self.assertNotEqual(nueva.password, self.clave)
        self.assertTrue(nueva.check_password(self.clave))
        self.assertEqual(int(self.client.session["_auth_user_id"]), nueva.pk)
        self.assertContains(respuesta, "Hola, nueva")

    def test_registro_rechaza_duplicados_claves_distintas_y_clave_debil(self):
        casos = [
            {"username": "ana", "password1": self.clave, "password2": self.clave},
            {"username": "nueva", "password1": self.clave, "password2": "Otra-clave!"},
            {"username": "nueva", "password1": "123", "password2": "123"},
        ]
        for datos in casos:
            respuesta = self.client.post("/registro/", datos)
            self.assertEqual(respuesta.status_code, 200)
            self.assertTrue(respuesta.context["form"].errors)
            self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(get_user_model().objects.count(), 2)

    def test_login_correcto_e_incorrecto(self):
        respuesta = self.client.post("/ingresar/", {
            "username": "ana", "password": "incorrecta",
        })
        self.assertTrue(respuesta.context["form"].errors)
        self.assertNotIn("_auth_user_id", self.client.session)
        respuesta = self.client.post("/ingresar/", {
            "username": "ana", "password": self.clave,
        }, follow=True)
        # Sin plan guardado, el login lleva finalmente al formulario inicial.
        self.assertEqual(respuesta.request["PATH_INFO"], "/")
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.usuario.pk)

    def test_login_no_redirige_a_un_sitio_externo(self):
        respuesta = self.client.post("/ingresar/", {
            "username": "ana", "password": self.clave,
            "next": "https://otro-sitio.example/",
        })
        self.assertRedirects(respuesta, "/plan/", fetch_redirect_response=False)

    def test_cuenta_inactiva_no_puede_ingresar(self):
        self.usuario.is_active = False
        self.usuario.save()
        respuesta = self.client.post("/ingresar/", {
            "username": "ana", "password": self.clave,
        })
        self.assertTrue(respuesta.context["form"].errors)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_dos_dispositivos_comparten_plan_y_confirmacion(self):
        # Cada Client tiene sus propias cookies, como celular y computador.
        celular = Client()
        self.client.post("/ingresar/", {"username": "ana", "password": self.clave})
        self.client.post("/", {"region": "13", "presupuesto": "25000"})
        celular.post("/ingresar/", {"username": "ana", "password": self.clave})
        plan = celular.get("/plan/").context["plan"]
        self.assertEqual(plan["costo_total"], 16979)
        celular.post("/plan/", {"accion": "confirmar", "plan_id": plan["id"]})
        self.assertContains(self.client.get("/plan/"), "Plan confirmado")
        self.client.post("/salir/")
        self.assertContains(celular.get("/plan/"), "Plan confirmado")
        self.client.post("/ingresar/", {"username": "ana", "password": self.clave})
        self.assertEqual(self.client.get("/plan/").context["plan"]["id"], plan["id"])

    def test_usuarios_distintos_no_comparten_ni_modifican_sus_planes(self):
        self.client.force_login(self.usuario)
        self.client.post("/", {"region": "13", "presupuesto": "25000"})
        plan_ana = PlanGuardado.objects.get(usuario=self.usuario).datos
        otro_cliente = Client()
        otro_cliente.force_login(self.otro)
        self.assertRedirects(otro_cliente.get("/plan/"), "/")
        otro_cliente.post("/", {"region": "13", "presupuesto": "12000", "usuario": self.usuario.pk})
        respuesta = otro_cliente.post("/plan/", {
            "accion": "confirmar", "plan_id": plan_ana["id"], "usuario": self.usuario.pk,
        })
        self.assertContains(respuesta, "La planificación cambió")
        self.assertEqual(PlanGuardado.objects.get(usuario=self.usuario).datos, plan_ana)
        self.assertEqual(PlanGuardado.objects.get(usuario=self.otro).datos["presupuesto"], "12000")

    def test_plan_antiguo_en_otro_dispositivo_no_sobrescribe_el_nuevo(self):
        self.client.force_login(self.usuario)
        celular = Client()
        celular.force_login(self.usuario)
        self.client.post("/", {"region": "13", "presupuesto": "25000"})
        anterior = self.client.get("/plan/").context["plan"]
        celular.post("/", {"region": "13", "presupuesto": "12000"})
        respuesta = self.client.post("/plan/", {
            "accion": "confirmar", "plan_id": anterior["id"],
        })
        self.assertContains(respuesta, "La planificación cambió")
        actual = PlanGuardado.objects.get(usuario=self.usuario).datos
        self.assertEqual(actual["presupuesto"], "12000")
        self.assertFalse(actual["confirmado"])

    def test_salir_requiere_post_y_no_borra_el_plan(self):
        self.client.force_login(self.usuario)
        self.client.post("/", {"region": "13", "presupuesto": "25000"})
        self.assertEqual(self.client.get("/salir/").status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)
        self.assertRedirects(self.client.post("/salir/"), "/ingresar/")
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertTrue(PlanGuardado.objects.filter(usuario=self.usuario).exists())
        self.assertRedirects(self.client.get("/plan/"), "/ingresar/?next=/plan/")

    def test_formularios_exigen_csrf(self):
        navegador = Client(enforce_csrf_checks=True)
        for ruta in ["/registro/", "/ingresar/"]:
            self.assertEqual(navegador.post(ruta, {}).status_code, 403)
        navegador.force_login(self.usuario)
        for ruta in ["/salir/", "/", "/plan/"]:
            self.assertEqual(navegador.post(ruta, {}).status_code, 403)
        # Con el token que entrega el formulario, el POST sí funciona.
        navegador.get("/")
        token = navegador.cookies["csrftoken"].value
        respuesta = navegador.post("/", {
            "region": "13", "presupuesto": "25000", "csrfmiddlewaretoken": token,
        })
        self.assertRedirects(respuesta, "/plan/")
