import json
from decimal import Decimal
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, SimpleTestCase, TestCase, override_settings
from PIL import Image

from .catalogo import ingredientes_disponibles, opciones_ingredientes, recetas_disponibles
from .data import INGREDIENTES, RECETAS
from .models import PlanGuardado, PreciosRegion, ProductoPersonal, RecetaPersonal
from .planner import calcular_presupuesto_minimo, generar_plan
from .test_odepa import ejemplo


class RecetasAmpliadasTests(SimpleTestCase):
    def test_recetas_validas_y_con_variedad_en_cada_tipo(self):
        # Permite ampliar el catálogo conservando al menos las 35 recetas iniciales.
        self.assertGreaterEqual(len(RECETAS), 35)
        nombres = set()
        for tipo in ["desayuno", "almuerzo", "cena"]:
            cantidad = 0
            for receta in RECETAS:
                if receta["tipo"] == tipo:
                    cantidad += 1
            self.assertGreaterEqual(cantidad, 10)
        for receta in RECETAS:
            self.assertNotIn(receta["nombre"], nombres)
            nombres.add(receta["nombre"])
            self.assertEqual(receta["porciones"], 1)
            for ingrediente, cantidad in receta["ingredientes"].items():
                self.assertIn(ingrediente, INGREDIENTES)
                self.assertGreater(cantidad, 0)

    def test_catalogo_ampliado_respeta_minimo_y_costo_de_compras(self):
        minimo = calcular_presupuesto_minimo()
        self.assertIsNone(generar_plan(minimo - Decimal("0.01")))
        for monto in [minimo, minimo + Decimal("0.01"), 25000]:
            plan = generar_plan(monto)
            total = sum(Decimal(str(compra["subtotal"])) for compra in plan["compras"])
            self.assertEqual(total, Decimal(str(plan["costo_total"])))
            self.assertLessEqual(total, monto)
            self.assertEqual(sum(len(dia["comidas"]) for dia in plan["menu"]), 21)


class CatalogoPersonalTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(username="ana")
        self.otro = get_user_model().objects.create_user(username="diego")
        self.client.force_login(self.usuario)
        datos = ejemplo()
        for numero in range(25):
            datos["productos"].append({
                "nombre": f"Producto {numero:02d}", "unidad": "$/kilo", "precio": "1500.00",
            })
        self.copia = PreciosRegion.objects.create(region="13", datos=datos)

    def catalogo(self):
        return ingredientes_disponibles(self.usuario, self.copia.datos["catalogo"], self.copia.datos["productos"])

    def etiqueta(self, clave):
        for etiqueta, identificador in opciones_ingredientes(self.catalogo()).items():
            if identificador == clave:
                return etiqueta
        self.fail("No existe la opción de ingrediente")

    def datos_receta(self, filas=None):
        if filas is None:
            filas = [("avena", 60), ("leche", 200)]
        datos = {
            "region": "13", "nombre": "Mi desayuno", "tipo": "desayuno",
            "instrucciones": "Mezclar y cocinar.",
            "ingredientes-TOTAL_FORMS": str(len(filas)),
            "ingredientes-INITIAL_FORMS": "0",
        }
        for indice, (clave, cantidad) in enumerate(filas):
            datos[f"ingredientes-{indice}-ingrediente"] = self.etiqueta(clave)
            datos[f"ingredientes-{indice}-cantidad"] = str(cantidad)
        return datos

    def crear_producto(self, **cambios):
        datos = {
            "usuario": self.usuario, "nombre": "Mi yogur", "unidad": "g",
            "cantidad_referencia": 500, "precio_referencia": Decimal("1500"),
            "propiedades": "Información escrita por el usuario.",
        }
        datos.update(cambios)
        return ProductoPersonal.objects.create(**datos)

    def test_paginacion_de_diez_conserva_busqueda_y_region(self):
        primera = self.client.get("/precios/", {"region": "13", "busqueda": "Producto"})
        pagina = primera.context["pagina"]
        self.assertEqual(len(pagina), 10)
        self.assertEqual(pagina.paginator.count, 25)
        self.assertEqual(pagina.paginator.num_pages, 3)
        self.assertContains(primera, 'region=13&amp;busqueda=Producto&amp;favoritos=&amp;pagina=2')
        segunda = self.client.get("/precios/", {"region": "13", "busqueda": "Producto", "pagina": "2"})
        self.assertNotEqual(primera.context["productos"][0], segunda.context["productos"][0])
        ultima = self.client.get("/precios/", {"region": "13", "busqueda": "Producto", "pagina": "3"})
        self.assertEqual(len(ultima.context["pagina"]), 5)
        for numero in ["abc", "0", "999"]:
            respuesta = self.client.get("/precios/", {"region": "13", "pagina": numero})
            self.assertEqual(respuesta.status_code, 200)
            self.assertLessEqual(len(respuesta.context["pagina"]), 10)

    def test_crear_producto_normaliza_precio_y_no_permite_elegir_dueno(self):
        respuesta = self.client.post("/productos/nuevo/", {
            "nombre": "Mi yogur", "unidad": "g", "cantidad_referencia": "500",
            "precio_referencia": "1500", "propiedades": "Sin azúcar añadida",
            "usuario": self.otro.pk,
        })
        self.assertRedirects(respuesta, "/productos/")
        producto = ProductoPersonal.objects.get()
        self.assertEqual(producto.usuario, self.usuario)
        self.assertEqual(self.catalogo()[f"personal_{producto.pk}"]["precio"], "3.00")
        self.assertContains(self.client.get("/productos/"), "Sin azúcar añadida")

    def test_precio_o_cantidad_invalida_no_crea_producto(self):
        base = {"nombre": "Producto", "unidad": "g", "cantidad_referencia": "500", "precio_referencia": "1500"}
        for campo, valor in [("precio_referencia", "-1"), ("cantidad_referencia", "0"),
                             ("cantidad_referencia", "1.5"), ("precio_referencia", "NaN"),
                             ("precio_referencia", "0.01"), ("unidad", "inventada")]:
            datos = base.copy()
            datos[campo] = valor
            respuesta = self.client.post("/productos/nuevo/", datos)
            self.assertEqual(respuesta.status_code, 200)
            self.assertTrue(respuesta.context["form"].errors)
        self.assertFalse(ProductoPersonal.objects.exists())

    def test_crear_receta_con_producto_personal_y_existente_la_incluye_en_plan(self):
        producto = self.crear_producto()
        datos = self.datos_receta([(f"personal_{producto.pk}", 150), ("avena", 40)])
        respuesta = self.client.post("/recetas/nueva/", datos)
        self.assertRedirects(respuesta, "/recetas/?region=13")
        receta = RecetaPersonal.objects.get()
        self.assertEqual(receta.usuario, self.usuario)
        respuesta = self.client.post("/", {"region": "13", "presupuesto": "25000"}, follow=True)
        plan = respuesta.context["plan"]
        self.assertEqual(plan["menu"][0]["comidas"][0]["nombre"], "Mi desayuno")
        compra = next(c for c in plan["compras"] if c["nombre"] == "Mi yogur")
        self.assertEqual(compra["precio_unitario"], 3)
        self.assertEqual(compra["fuente"], "Producto personal")
        self.assertLessEqual(Decimal(str(plan["costo_total"])), 25000)
        json.dumps(plan)

    def test_producto_odepa_se_puede_usar_en_receta_y_cambiar_region_lo_omite(self):
        clave = next(clave for clave in self.catalogo() if clave.startswith("odepa_"))
        self.client.post("/recetas/nueva/", self.datos_receta([(clave, 200)]))
        receta = RecetaPersonal.objects.get()
        self.assertIn(clave, receta.ingredientes)
        PreciosRegion.objects.create(region="5", datos=ejemplo("5"))
        # La primera opción publicada es leche, disponible también en Valparaíso.
        # Usamos ahora un producto ficticio que solo está en nuestra copia de Metropolitana.
        clave = next(k for k,v in self.catalogo().items() if v["nombre"] == "Producto 00")
        receta.ingredientes = {clave: 100}
        receta.save()
        respuesta = self.client.post("/", {"region": "5", "presupuesto": "25000"}, follow=True)
        self.assertContains(respuesta, "No se pudieron usar estas recetas propias")
        self.assertEqual(respuesta.context["plan"]["precios"]["recetas_omitidas"], [receta.nombre])
        self.assertTrue(RecetaPersonal.objects.filter(pk=receta.pk).exists())

    def test_receta_sin_ingredientes_repetida_o_cantidad_invalida_no_se_guarda(self):
        casos = [self.datos_receta([]), self.datos_receta([("avena", 20), ("avena", 30)]),
                 self.datos_receta([("avena", 0)]), self.datos_receta([("avena", -1)])]
        for datos in casos:
            respuesta = self.client.post("/recetas/nueva/", datos)
            self.assertEqual(respuesta.status_code, 200)
            self.assertTrue(respuesta.context["filas"].errors or respuesta.context["filas"].non_form_errors())
        self.assertFalse(RecetaPersonal.objects.exists())

    def test_otro_usuario_no_ve_productos_recetas_fotos_ni_puede_usarlos(self):
        producto = self.crear_producto(usuario=self.otro, nombre="Producto privado")
        receta = RecetaPersonal.objects.create(usuario=self.otro, nombre="Receta privada", tipo="cena", ingredientes={"pan": 100})
        for ruta in [f"/productos/{producto.pk}/editar/", f"/productos/{producto.pk}/foto/", f"/recetas/{receta.pk}/editar/"]:
            self.assertEqual(self.client.get(ruta).status_code, 404)
        self.assertNotContains(self.client.get("/productos/"), "Producto privado")
        self.assertNotContains(self.client.get("/recetas/"), "Receta privada")
        self.assertNotIn(f"personal_{producto.pk}", self.catalogo())
        datos = self.datos_receta()
        datos["ingredientes-0-ingrediente"] = f"Producto privado (g) — personal_{producto.pk}"
        respuesta = self.client.post("/recetas/nueva/", datos)
        self.assertTrue(respuesta.context["filas"].errors)
        self.assertFalse(RecetaPersonal.objects.filter(usuario=self.usuario).exists())

    def test_editar_producto_o_receta_no_modifica_plan_guardado(self):
        producto = self.crear_producto()
        self.client.post("/recetas/nueva/", self.datos_receta([(f"personal_{producto.pk}", 100)]))
        receta = RecetaPersonal.objects.get()
        self.client.post("/", {"region": "13", "presupuesto": "25000"})
        anterior = PlanGuardado.objects.get(usuario=self.usuario).datos
        respuesta = self.client.post(f"/productos/{producto.pk}/editar/", {
            "nombre": "Yogur nuevo", "unidad": "g", "cantidad_referencia": "500", "precio_referencia": "2000",
        })
        self.assertEqual(respuesta.status_code, 302)
        datos = self.datos_receta([("pan", 100)])
        datos["nombre"] = "Mi tostada"
        self.assertEqual(self.client.post(f"/recetas/{receta.pk}/editar/", datos).status_code, 302)
        self.assertEqual(PlanGuardado.objects.get(usuario=self.usuario).datos, anterior)
        self.client.post("/", {"region": "13", "presupuesto": "25000"})
        self.assertEqual(PlanGuardado.objects.get(usuario=self.usuario).datos["menu"][0]["comidas"][0]["nombre"], "Mi tostada")

    def test_foto_real_se_guarda_privada_y_archivo_falso_se_rechaza(self):
        with TemporaryDirectory() as carpeta, override_settings(MEDIA_ROOT=carpeta):
            imagen = BytesIO()
            Image.new("RGB", (20, 20), "green").save(imagen, "PNG")
            datos = {"nombre": "Foto", "unidad": "unidad", "cantidad_referencia": "1", "precio_referencia": "100"}
            datos["foto"] = SimpleUploadedFile("foto.png", imagen.getvalue(), content_type="image/png")
            self.assertEqual(self.client.post("/productos/nuevo/", datos).status_code, 302)
            producto = ProductoPersonal.objects.get()
            respuesta = self.client.get(f"/productos/{producto.pk}/foto/")
            self.assertEqual(respuesta.status_code, 200)
            contenido = b"".join(respuesta.streaming_content)
            respuesta.close()
            with Image.open(BytesIO(contenido)) as foto:
                self.assertEqual(foto.format, "JPEG")
            otro = Client()
            otro.force_login(self.otro)
            self.assertEqual(otro.get(f"/productos/{producto.pk}/foto/").status_code, 404)
            datos["foto"] = SimpleUploadedFile("falso.png", b"<script>bad</script>", content_type="image/png")
            respuesta = self.client.post("/productos/nuevo/", datos)
            self.assertIn("foto", respuesta.context["form"].errors)
            self.assertEqual(ProductoPersonal.objects.count(), 1)

    def test_formularios_tienen_buscador_y_pantallas_exigen_sesion(self):
        respuesta = self.client.get("/recetas/nueva/")
        self.assertContains(respuesta, 'list="ingredientes-disponibles"')
        self.assertContains(respuesta, 'name="ingredientes-TOTAL_FORMS"')
        self.assertEqual(respuesta.context["filas"].total_form_count(), 12)
        self.assertEqual(self.client.get("/recetas/").context["pagina"].paginator.count, len(RECETAS))
        self.client.logout()
        for ruta in ["/productos/", "/productos/nuevo/", "/recetas/", "/recetas/nueva/"]:
            self.assertEqual(self.client.get(ruta).status_code, 302)

    def test_no_cambia_unidad_de_producto_usado_en_receta(self):
        producto = self.crear_producto()
        self.client.post("/recetas/nueva/", self.datos_receta([(f"personal_{producto.pk}", 100)]))
        respuesta = self.client.post(f"/productos/{producto.pk}/editar/", {
            "nombre": producto.nombre, "unidad": "unidad", "cantidad_referencia": "1", "precio_referencia": "1500",
        })
        self.assertIn("unidad", respuesta.context["form"].errors)
        producto.refresh_from_db()
        self.assertEqual(producto.unidad, "g")

    def test_editar_receta_permite_quitar_una_fila(self):
        self.client.post("/recetas/nueva/", self.datos_receta())
        receta = RecetaPersonal.objects.get()
        datos = self.datos_receta()
        datos["ingredientes-INITIAL_FORMS"] = "2"
        datos["ingredientes-0-DELETE"] = "on"
        respuesta = self.client.post(f"/recetas/{receta.pk}/editar/", datos)
        self.assertEqual(respuesta.status_code, 302)
        receta.refresh_from_db()
        self.assertEqual(receta.ingredientes, {"leche": 200})

    def test_una_receta_personal_muy_cara_no_rompe_el_presupuesto(self):
        producto = self.crear_producto(precio_referencia=Decimal("999999"), cantidad_referencia=1)
        self.client.post("/recetas/nueva/", self.datos_receta([(f"personal_{producto.pk}", 1)]))
        respuesta = self.client.post("/", {"region": "13", "presupuesto": "25000"}, follow=True)
        plan = respuesta.context["plan"]
        self.assertLessEqual(Decimal(str(plan["costo_total"])), 25000)
        for dia in plan["menu"]:
            self.assertNotEqual(dia["comidas"][0]["nombre"], "Mi desayuno")

    def test_crear_y_editar_exige_csrf_y_no_accede_a_otro_dueno(self):
        producto = self.crear_producto(usuario=self.otro)
        receta = RecetaPersonal.objects.create(usuario=self.otro, nombre="Privada", tipo="cena", ingredientes={"pan": 100})
        for ruta in [f"/productos/{producto.pk}/editar/", f"/recetas/{receta.pk}/editar/"]:
            self.assertEqual(self.client.post(ruta, {}).status_code, 404)
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.usuario)
        for ruta in ["/productos/nuevo/", "/recetas/nueva/"]:
            self.assertEqual(cliente.post(ruta, {}).status_code, 403)

    def test_foto_grande_y_exceso_de_ingredientes_se_rechazan(self):
        imagen = BytesIO()
        Image.new("RGB", (20, 20), "green").save(imagen, "PNG")
        foto = SimpleUploadedFile("foto.png", imagen.getvalue() + b"\x00" * (3 * 1024 * 1024), content_type="image/png")
        respuesta = self.client.post("/productos/nuevo/", {
            "nombre": "Grande", "unidad": "unidad", "cantidad_referencia": "1", "precio_referencia": "100", "foto": foto,
        })
        self.assertIn("foto", respuesta.context["form"].errors)
        datos = self.datos_receta()
        datos["ingredientes-TOTAL_FORMS"] = "5000"
        respuesta = self.client.post("/recetas/nueva/", datos)
        self.assertTrue(respuesta.context["filas"].non_form_errors())
        self.assertEqual(len(respuesta.context["filas"].forms), 12)
        self.assertFalse(RecetaPersonal.objects.exists())
