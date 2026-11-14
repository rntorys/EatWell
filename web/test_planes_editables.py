from copy import deepcopy
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.http import QueryDict
from django.test import Client, SimpleTestCase, TestCase

from .calendario import PeriodoForm, seleccionar_fechas
from .catalogo import clave_producto_odepa, clave_receta, opciones_ingredientes
from .data import RECETAS
from .edicion import catalogo_del_plan
from .models import Favorito, PlanGuardado, PreciosRegion, ProductoPersonal, RecetaPersonal
from .test_odepa import ejemplo


class CalendarioTests(SimpleTestCase):
    def test_febrero_bisiesto_y_meses_de_30_y_31_dias(self):
        for mes, cantidad in [("2028-02", 29), ("2026-02", 28), ("2026-11", 30), ("2026-12", 31)]:
            form = PeriodoForm({"modo": "mes", "mes": mes})
            self.assertTrue(form.is_valid(), form.errors)
            calendario, dias = seleccionar_fechas(form)
            self.assertEqual(len(dias), cantidad)
            self.assertEqual(dias[0]["fecha"], mes + "-01")

    def test_periodos_y_cambio_de_anio(self):
        for cantidad in [7, 28, 30, 31]:
            form = PeriodoForm({"modo": str(cantidad), "inicio": "2026-12-30"})
            calendario, dias = seleccionar_fechas(form)
            self.assertEqual(len(dias), cantidad)
            self.assertTrue(dias[-1]["fecha"].startswith("2027"))

    def test_excluir_fines_de_semana_y_elegir_dias_concretos(self):
        form = PeriodoForm({"modo": "mes", "mes": "2026-02", "sin_fines": "on"})
        calendario, dias = seleccionar_fechas(form)
        self.assertEqual(len(dias), 20)
        self.assertTrue(all(date.fromisoformat(d["fecha"]).weekday() < 5 for d in dias))
        datos = QueryDict("calendario_presentado=1", mutable=True)
        datos.setlist("dias", ["2026-02-02", "2026-02-06"])
        calendario, dias = seleccionar_fechas(form, datos)
        self.assertEqual([d["fecha"] for d in dias], ["2026-02-02", "2026-02-06"])

    def test_fechas_invalidas_no_permiten_generar(self):
        for datos in [{"modo": "mes", "mes": "2026-99"}, {"modo": "7", "inicio": "2026-02-30"},
                      {"modo": "10000", "inicio": "2026-11-01"}, {"modo": "mes", "mes": "9999-12"}]:
            self.assertFalse(PeriodoForm(datos).is_valid())
        for valores in [[], ["2026-03-01"], ["2026-02-01"]]:
            form = PeriodoForm({"modo": "mes", "mes": "2026-02", "sin_fines": "on"})
            datos = QueryDict("calendario_presentado=1", mutable=True)
            datos.setlist("dias", valores)
            seleccionar_fechas(form, datos)
            self.assertFalse(form.is_valid())


class PlanEditableTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(username="ana")
        self.otro = get_user_model().objects.create_user(username="diego")
        self.client.force_login(self.usuario)
        PreciosRegion.objects.create(region="13", datos=ejemplo())
        self.client.post("/", {"region": "13", "presupuesto": "25000"})

    def plan(self):
        return PlanGuardado.objects.get(usuario=self.usuario).datos

    def manual(self, ingredientes, nombre="Mi comida editada"):
        opciones = opciones_ingredientes(catalogo_del_plan(self.usuario, self.plan()))
        etiquetas = {clave: etiqueta for etiqueta, clave in opciones.items()}
        datos = {"plan_id": self.plan()["id"], "accion": "editar", "nombre": nombre,
                 "ingredientes-TOTAL_FORMS": str(len(ingredientes)), "ingredientes-INITIAL_FORMS": "0"}
        for numero, (clave, cantidad) in enumerate(ingredientes.items()):
            datos[f"ingredientes-{numero}-ingrediente"] = etiquetas[clave]
            datos[f"ingredientes-{numero}-cantidad"] = str(cantidad)
        return datos

    def comprobar_totales(self):
        plan = self.plan()
        comidas = sum(Decimal(str(c["costo"])) for d in plan["menu"] for c in d["comidas"])
        compras = sum(Decimal(str(c["subtotal"])) for c in plan["compras"])
        self.assertEqual(comidas, compras)
        self.assertEqual(compras, Decimal(str(plan["costo_total"])))
        self.assertEqual(Decimal(plan["saldo"]), Decimal(plan["presupuesto"]) - compras)
        self.assertLessEqual(compras, Decimal(plan["presupuesto"]))

    def test_generar_un_mes_y_solo_dias_elegidos(self):
        for mes, dias in [("2028-02", 29), ("2026-11", 30), ("2026-12", 31)]:
            respuesta = self.client.post("/", {"region": "13", "presupuesto": "100000", "modo": "mes", "mes": mes}, follow=True)
            self.assertEqual(respuesta.status_code, 200)
            self.assertEqual(self.plan()["cantidad_dias"], dias)
            self.assertEqual(self.plan()["cantidad_comidas"], dias * 3)
            self.comprobar_totales()
        respuesta = self.client.post("/", {"region": "13", "presupuesto": "10000", "modo": "mes", "mes": "2026-02",
            "sin_fines": "on", "calendario_presentado": "1", "dias": ["2026-02-02", "2026-02-06"]}, follow=True)
        self.assertEqual(self.plan()["cantidad_comidas"], 6)
        self.assertContains(respuesta, "6 comidas")
        calendario = self.client.get("/").context["calendario"]
        self.assertEqual(sum(d["marcado"] for d in calendario), 2)
        self.comprobar_totales()

    def test_seleccion_vacia_o_monto_insuficiente_no_borra_plan_anterior(self):
        anterior = self.plan()
        self.client.post("/", {"region": "13", "presupuesto": "100000", "modo": "mes", "mes": "2026-11", "calendario_presentado": "1"})
        self.assertEqual(self.plan(), anterior)
        respuesta = self.client.post("/", {"region": "13", "presupuesto": "5000", "modo": "mes", "mes": "2026-11"})
        self.assertTrue(respuesta.context["sin_plan"])
        self.assertEqual(respuesta.context["cantidad_comidas"], 90)
        self.assertEqual(self.plan(), anterior)

    def test_calendario_get_no_modifica_plan_y_muestra_checkboxes(self):
        anterior = self.plan()
        respuesta = self.client.get("/", {"modo": "mes", "mes": "2028-02"})
        self.assertEqual(len(respuesta.context["calendario"]), 29)
        self.assertContains(respuesta, 'value="2028-02-29"')
        self.assertEqual(self.plan(), anterior)

    def test_revisar_dias_sin_javascript_conserva_presupuesto_y_plan(self):
        anterior = self.plan()
        respuesta = self.client.post("/", {
            "accion": "revisar_dias", "modo": "mes", "mes": "2028-02", "sin_fines": "on",
            "region": "13", "presupuesto": "45000", "calendario_presentado": "1",
            "dias": ["2026-01-01"],
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["cantidad_dias"], 21)
        self.assertEqual(respuesta.context["cantidad_comidas"], 63)
        self.assertEqual(respuesta.context["form"]["presupuesto"].value(), "45000")
        self.assertEqual(respuesta.context["form"]["region"].value(), "13")
        self.assertFalse(respuesta.context["form"].errors)
        self.assertEqual(self.plan(), anterior)

    def test_revisar_dias_invalidos_muestra_error_sin_modificar_plan(self):
        anterior = self.plan()
        respuesta = self.client.post("/", {"accion": "revisar_dias", "modo": "mes", "mes": "2028-99", "presupuesto": "45000"})
        self.assertTrue(respuesta.context["periodo_form"].errors)
        self.assertEqual(respuesta.context["cantidad_dias"], 0)
        self.assertEqual(self.plan(), anterior)

    def test_editar_una_comida_no_cambia_las_otras_ni_receta_original(self):
        antes = self.plan()
        self.client.post("/plan/", {"accion": "confirmar", "plan_id": antes["id"]})
        respuesta = self.client.post("/plan/comida/0/0/", self.manual({"pan": 100, "huevo": 2}))
        self.assertRedirects(respuesta, "/plan/")
        despues = self.plan()
        self.assertEqual(despues["menu"][0]["comidas"][0]["ingredientes"], {"pan": 100, "huevo": 2})
        self.assertEqual(despues["menu"][1:], antes["menu"][1:])
        self.assertEqual(despues["menu"][0]["comidas"][1:], antes["menu"][0]["comidas"][1:])
        self.assertFalse(despues["confirmado"])
        self.assertNotEqual(despues["id"], antes["id"])
        self.assertEqual(RECETAS[0]["ingredientes"], {"avena": 60, "leche": 200, "platano": 100})
        self.comprobar_totales()

    def test_reemplazar_comida_y_quitarla_y_restaurarla(self):
        clave = clave_receta(RECETAS[-1])
        respuesta = self.client.post("/plan/comida/0/0/", {"plan_id": self.plan()["id"], "accion": "reemplazar", "receta": clave})
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self.plan()["menu"][0]["comidas"][0]["nombre"], RECETAS[-1]["nombre"])
        self.assertEqual(self.plan()["menu"][0]["comidas"][0]["tipo"], "desayuno")
        self.client.post("/plan/comida/0/0/", {"plan_id": self.plan()["id"], "accion": "quitar"})
        self.assertEqual(self.plan()["cantidad_comidas"], 20)
        self.assertEqual(self.plan()["menu"][0]["comidas"][0]["costo"], 0)
        self.client.post("/plan/comida/0/0/", self.manual({"leche": 200}))
        self.assertEqual(self.plan()["cantidad_comidas"], 21)
        self.comprobar_totales()

    def test_producto_global_se_reemplaza_sumando_cantidades_existentes(self):
        antes = self.plan()
        totales = {c["clave"]: c["cantidad"] for c in antes["compras"]}
        opciones = opciones_ingredientes(catalogo_del_plan(self.usuario, antes))
        arroz = next(etiqueta for etiqueta, clave in opciones.items() if clave == "arroz")
        respuesta = self.client.post("/plan/producto/avena/", {"plan_id": antes["id"], "accion": "reemplazar", "ingrediente": arroz})
        self.assertEqual(respuesta.status_code, 302)
        compras = {c["clave"]: c["cantidad"] for c in self.plan()["compras"]}
        self.assertNotIn("avena", compras)
        self.assertEqual(compras["arroz"], totales["arroz"] + totales["avena"])
        self.comprobar_totales()

    def test_cambio_de_unidad_exige_cantidad_y_quitar_producto_recalcula(self):
        antes = self.plan()
        opciones = opciones_ingredientes(catalogo_del_plan(self.usuario, antes))
        huevo = next(etiqueta for etiqueta, clave in opciones.items() if clave == "huevo")
        datos = {"plan_id": antes["id"], "accion": "reemplazar", "ingrediente": huevo}
        respuesta = self.client.post("/plan/producto/avena/", datos)
        self.assertTrue(respuesta.context["form"].errors)
        self.assertEqual(self.plan(), antes)
        datos["cantidad"] = "1"
        self.assertEqual(self.client.post("/plan/producto/avena/", datos).status_code, 302)
        self.client.post("/plan/producto/huevo/", {"plan_id": self.plan()["id"], "accion": "quitar"})
        self.assertFalse(any("huevo" in c["ingredientes"] for d in self.plan()["menu"] for c in d["comidas"]))
        self.comprobar_totales()

    def test_edicion_cara_se_rechaza_y_presupuesto_puede_ajustarse_sin_regenerar(self):
        antes = self.plan()
        respuesta = self.client.post("/plan/comida/0/0/", self.manual({"huevo": 100000}))
        self.assertIn("supera tu presupuesto", respuesta.context["error"])
        self.assertEqual(self.plan(), antes)
        self.client.post("/plan/presupuesto/", {"plan_id": antes["id"], "presupuesto": "50000"})
        self.assertEqual(self.plan()["presupuesto"], "50000")
        self.assertEqual(self.plan()["menu"], antes["menu"])
        actual = self.plan()
        self.client.post("/plan/presupuesto/", {"plan_id": actual["id"], "presupuesto": "1"})
        self.assertEqual(self.plan(), actual)

    def test_no_acepta_pestana_antigua_producto_ajeno_o_receta_ajena(self):
        datos = self.manual({"pan": 100})
        self.client.post("/plan/comida/0/0/", datos)
        actual = self.plan()
        respuesta = self.client.post("/plan/comida/0/0/", datos)
        self.assertIn("cambió", respuesta.context["error"])
        self.assertEqual(self.plan(), actual)
        receta = RecetaPersonal.objects.create(usuario=self.otro, nombre="Ajena", tipo="desayuno", ingredientes={"pan": 100})
        self.client.post("/plan/comida/0/0/", {"plan_id": actual["id"], "accion": "reemplazar", "receta": f"receta_{receta.pk}"})
        self.assertEqual(self.plan(), actual)
        self.assertEqual(self.client.get("/plan/comida/100/0/").status_code, 404)
        otro = Client()
        otro.force_login(self.otro)
        self.assertEqual(otro.get("/plan/comida/0/0/").status_code, 404)

    def test_edicion_recupera_precios_de_un_plan_antiguo(self):
        antes = self.plan()
        viejo = deepcopy(antes)
        del viejo["catalogo"]
        for compra in viejo["compras"]:
            compra.pop("clave")
        PlanGuardado.objects.filter(usuario=self.usuario).update(datos=viejo)
        datos = ejemplo(precio="9000")
        PreciosRegion.objects.filter(region="13").update(datos=datos)
        ingredientes = antes["menu"][0]["comidas"][0]["ingredientes"]
        self.client.post("/plan/comida/0/0/", self.manual(ingredientes))
        self.assertEqual(self.plan()["costo_total"], antes["costo_total"])

    def test_get_y_csrf_no_modifican_el_plan(self):
        antes = self.plan()
        self.assertEqual(self.client.get("/plan/comida/0/0/").status_code, 200)
        self.assertEqual(self.client.get("/plan/producto/avena/").status_code, 200)
        seguro = Client(enforce_csrf_checks=True)
        seguro.force_login(self.usuario)
        for ruta in ["/plan/comida/0/0/", "/plan/producto/avena/", "/plan/presupuesto/"]:
            self.assertEqual(seguro.post(ruta, {"accion": "quitar", "plan_id": antes["id"]}).status_code, 403)
        self.assertEqual(self.plan(), antes)


class FavoritosTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(username="ana")
        self.otro = get_user_model().objects.create_user(username="diego")
        self.client.force_login(self.usuario)
        self.datos = ejemplo()
        PreciosRegion.objects.create(region="13", datos=self.datos)

    def marcar(self, tipo, clave, accion="agregar"):
        return self.client.post("/favoritos/", {"tipo": tipo, "clave": clave, "accion": accion, "region": "13"}, HTTP_ACCEPT="application/json")

    def test_agregar_quitar_es_idempotente_y_separa_usuarios(self):
        for intento in range(2):
            self.assertTrue(self.marcar("producto", "avena").json()["favorito"])
        self.assertEqual(Favorito.objects.filter(usuario=self.usuario).count(), 1)
        self.assertFalse(Favorito.objects.filter(usuario=self.otro).exists())
        for intento in range(2):
            self.assertFalse(self.marcar("producto", "avena", "quitar").json()["favorito"])
        self.assertFalse(Favorito.objects.exists())

    def test_recetas_favoritas_primero_y_filtro_solo_favoritas(self):
        elegida = RECETAS[-1]
        clave = clave_receta(elegida)
        self.assertEqual(self.marcar("receta", clave).status_code, 200)
        respuesta = self.client.get("/recetas/", {"region": "13", "favoritos": "on"})
        self.assertEqual(respuesta.context["pagina"].paginator.count, 1)
        self.assertEqual(respuesta.context["pagina"][0]["nombre"], elegida["nombre"])
        respuesta = self.client.get("/recetas/", {"region": "13"})
        self.assertEqual(respuesta.context["pagina"][0]["clave"], clave)

    def test_productos_odepa_favoritos_y_selector_de_ingredientes(self):
        clave = clave_producto_odepa(self.datos["productos"][0])
        self.assertEqual(self.marcar("producto", clave).status_code, 200)
        respuesta = self.client.get("/precios/", {"region": "13", "favoritos": "on"})
        self.assertEqual(respuesta.context["pagina"].paginator.count, 1)
        respuesta = self.client.get("/recetas/nueva/", {"region": "13"})
        self.assertEqual(respuesta.context["selector_productos"][0]["clave"], clave)
        self.assertTrue(respuesta.context["selector_productos"][0]["favorito"])

    def test_favoritos_personales_no_permiten_referencias_de_otro_usuario(self):
        producto = ProductoPersonal.objects.create(usuario=self.otro, nombre="Ajeno", unidad="g", cantidad_referencia=100, precio_referencia=100)
        receta = RecetaPersonal.objects.create(usuario=self.otro, nombre="Ajena", tipo="cena", ingredientes={"pan": 100})
        self.assertEqual(self.marcar("producto", f"personal_{producto.pk}").status_code, 400)
        self.assertEqual(self.marcar("receta", f"receta_{receta.pk}").status_code, 400)
        self.assertEqual(self.marcar("producto", "odepa_inventado").status_code, 400)
        self.assertFalse(Favorito.objects.exists())

    def test_favoritos_requieren_post_csrf_y_redireccion_local(self):
        self.assertEqual(self.client.get("/favoritos/").status_code, 405)
        seguro = Client(enforce_csrf_checks=True)
        seguro.force_login(self.usuario)
        self.assertEqual(seguro.post("/favoritos/", {}).status_code, 403)
        respuesta = self.client.post("/favoritos/", {"tipo": "producto", "clave": "avena", "accion": "agregar", "volver": "https://ajeno.example"})
        self.assertRedirects(respuesta, "/")

    def test_nombres_duplicados_no_cambian_de_identidad_al_marcar_favoritos(self):
        for precio in [100, 200]:
            ProductoPersonal.objects.create(usuario=self.usuario, nombre="Mismo nombre", unidad="g", cantidad_referencia=100, precio_referencia=precio)
        antes = self.client.get("/recetas/nueva/", {"region": "13"}).context["opciones"]
        ultimo = ProductoPersonal.objects.filter(usuario=self.usuario).last()
        self.marcar("producto", f"personal_{ultimo.pk}")
        despues = self.client.get("/recetas/nueva/", {"region": "13"}).context["opciones"]
        self.assertEqual(dict(antes), dict(despues))
        self.assertEqual(next(iter(despues.values())), f"personal_{ultimo.pk}")

    def test_favoritos_se_recuperan_en_otro_navegador(self):
        self.marcar("producto", "avena")
        otro = Client()
        otro.force_login(self.usuario)
        respuesta = otro.get("/recetas/nueva/", {"region": "13"})
        self.assertEqual(respuesta.context["selector_productos"][0]["clave"], "avena")
        self.assertTrue(respuesta.context["selector_productos"][0]["favorito"])
