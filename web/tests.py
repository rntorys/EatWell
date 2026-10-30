# Las pruebas son código que ejecuta acciones y compara el resultado con lo
# esperado. No las ejecuta cada visitante: se lanzan con "manage.py test".
# Si una comprobación falla, Django señala qué prueba y qué resultado fallaron.

# Decimal permite comparar montos y saldos decimales con precisión decimal.
from decimal import Decimal
# patch es una herramienta de pruebas de Python: reemplaza temporalmente
# un valor para simular una condición, sin editar el archivo que lo define.
from unittest.mock import patch

# SimpleTestCase aporta comprobaciones para pruebas que no necesitan BD.
# TestCase añade aislamiento con una BD de pruebas. La necesitamos para que
# las vistas puedan usar las sesiones sin tocar los datos reales de la app.
from django.test import SimpleTestCase, TestCase
# reverse convierte un nombre de ruta en su dirección: reverse("home") -> "/".
# Así no repetimos rutas escritas a mano si luego cambia web/urls.py.
from django.urls import reverse

# Importamos las constantes y funciones propias que vamos a comprobar.
from .planner import DIAS, TIPOS_COMIDA, calcular_presupuesto_minimo, generar_plan


# Esta clase agrupa las pruebas del cálculo, sin peticiones HTTP ni sesiones.
# Los paréntesis indican herencia: recibimos las herramientas de SimpleTestCase.
# Django descubre automáticamente los métodos cuyo nombre empieza por test_.
# self representa esta instancia de la clase y permite usar sus herramientas.
# Algunos métodos de comprobación (assert significa "comprobar que"):
# - assertEqual(a, b): a y b deben ser iguales.
# - assertIsNone(a): a debe ser None.
# - assertLessEqual(a, b): a debe ser menor o igual que b.
# - assertGreater(a, b): a debe ser mayor que b.
# - assertTrue(a) / assertFalse(a): comprueban si a es verdadero o falso.
# - assertNotIn(a, b): a no debe estar dentro de b.
class PlanificadorTests(SimpleTestCase):
    def test_minimo_exacto_cubre_la_semana_y_agrupa_ingredientes(self):
        # Costo calculado a mano: 7 x (520 + 506 + 546).
        self.assertEqual(calcular_presupuesto_minimo(), 11004)
        plan = generar_plan(11004)
        self.assertEqual(plan["costo_total"], 11004)
        # El plan guarda saldo como texto para la sesión: lo convertimos a número.
        self.assertEqual(Decimal(plan["saldo"]), 0)
        # [expresión for elemento in lista] crea una lista por comprensión.
        # Aquí extrae los nombres de los días y compara su contenido y orden.
        self.assertEqual([dia["dia"] for dia in plan["menu"]], list(DIAS))
        for dia in plan["menu"]:
            self.assertEqual([comida["tipo"] for comida in dia["comidas"]], list(TIPOS_COMIDA))

        # Cantidades esperadas al repetir siete veces las opciones más baratas.
        # Creamos un diccionario nombre -> cantidad para comprobar cada total.
        cantidades = {compra["nombre"]: compra["cantidad"] for compra in plan["compras"]}
        self.assertEqual(cantidades, {
            "Avena": 420, "Leche": 1400, "Plátano": 700,
            "Lentejas": 630, "Arroz": 420, "Zanahorias": 1120,
            "Cebollas": 630, "Aceite": 70, "Sal": 14,
            "Papas": 1400, "Pan integral": 420,
        })

    def test_un_centavo_bajo_el_minimo_no_permite_un_plan(self):
        # Prueba del límite: no se debe redondear hacia arriba el presupuesto.
        self.assertIsNone(generar_plan(Decimal("11003.99")))

    def test_varios_presupuestos_cubren_21_comidas_sin_exceder_el_monto(self):
        for presupuesto in (11004, 11005, 11100, 12000, 13000, 15000, 16979, 25000):
            # subTest identifica qué presupuesto falló y permite continuar con
            # las demás iteraciones si falla una comprobación de esta iteración.
            with self.subTest(presupuesto=presupuesto):
                plan = generar_plan(presupuesto)
                # Los dos for aplanan días -> comidas en una sola lista de 21.
                comidas = [comida for dia in plan["menu"] for comida in dia["comidas"]]
                self.assertEqual(len(comidas), 21)
                self.assertLessEqual(plan["costo_total"], presupuesto)
                self.assertEqual(sum(comida["costo"] for comida in comidas), plan["costo_total"])
                self.assertEqual(sum(compra["subtotal"] for compra in plan["compras"]), plan["costo_total"])
                self.assertEqual(Decimal(plan["saldo"]), presupuesto - plan["costo_total"])
                # {...} sin pares clave:valor crea un conjunto (set), que elimina
                # repetidos. Igual longitud implica una sola fila por ingrediente.
                self.assertEqual(len(plan["compras"]), len({c["nombre"] for c in plan["compras"]}))
                for compra in plan["compras"]:
                    self.assertEqual(compra["subtotal"], compra["cantidad"] * compra["precio_unitario"])

    def test_un_presupuesto_holgado_permite_variedad(self):
        # Con dinero suficiente, cada tipo debe tener más de una receta distinta.
        plan = generar_plan(25000)
        for tipo in TIPOS_COMIDA:
            nombres = {
                comida["nombre"] for dia in plan["menu"]
                for comida in dia["comidas"] if comida["tipo"] == tipo
            }
            self.assertGreater(len(nombres), 1)

    def test_catalogo_incompleto_no_genera_un_plan_parcial(self):
        # Durante este bloque, RECETAS será [] dentro del módulo planner.
        # Al salir del with, patch restaura el valor original, incluso si falla
        # la prueba. La lista en data.py no se borra ni se reescribe.
        with patch("web.planner.RECETAS", []):
            self.assertIsNone(generar_plan(25000))
            self.assertIsNone(calcular_presupuesto_minimo())


# Estas pruebas recorren las vistas y el HTML usando el cliente de Django.
# self.client simula solicitudes y conserva cookies entre ellas; no abre un
# navegador real ni ejecuta CSS o JavaScript. Tampoco necesita runserver.
# Cada prueba comienza aislada de los cambios de las otras pruebas.
class FlujoEatWellTests(TestCase):
    def test_escenario_principal_generar_y_confirmar(self):
        # post(ruta, datos) simula enviar el formulario.
        # follow=True sigue las redirecciones y entrega la respuesta final.
        respuesta = self.client.post(reverse("home"), {"presupuesto": "25000"}, follow=True)
        # Comprueba que la vista nos envió a la ruta esperada.
        self.assertRedirects(respuesta, reverse("plan"))
        # assertContains comprueba el texto del HTML y, por defecto, estado 200.
        self.assertContains(respuesta, "Lista de compras")
        self.assertContains(respuesta, "16.979")
        # context contiene las variables que la vista entregó a la plantilla;
        # así examinamos el plan sin tener que extraerlo del HTML.
        plan = respuesta.context["plan"]
        self.assertEqual(len(plan["menu"]), 7)
        self.assertEqual(sum(len(dia["comidas"]) for dia in plan["menu"]), 21)
        self.assertEqual(plan["costo_total"], 16979)
        self.assertEqual(Decimal(plan["saldo"]), 8021)
        self.assertFalse(plan["confirmado"])

        # Simulamos ahora la pulsación del botón Confirmar plan.
        respuesta = self.client.post(reverse("plan"), {
            "accion": "confirmar", "plan_id": plan["id"],
            # Los valores enviados desde el navegador no reemplazan el cálculo.
            "costo_total": "1", "presupuesto": "999999",
        }, follow=True)
        self.assertContains(respuesta, "Plan confirmado")
        # self.client.session permite inspeccionar el estado de esa sesión.
        self.assertTrue(self.client.session["plan"]["confirmado"])
        self.assertEqual(self.client.session["plan"]["costo_total"], 16979)
        self.assertEqual(self.client.session["plan"]["presupuesto"], "25000")
        self.assertContains(self.client.get(reverse("plan")), "Plan confirmado")

    def test_escenario_alternativo_monto_insuficiente_y_reintento(self):
        # El presupuesto es numérico y positivo, pero no cubre las 21 comidas.
        respuesta = self.client.post(reverse("home"), {"presupuesto": "5000"})
        self.assertContains(respuesta, "No encontramos un plan con ese presupuesto")
        self.assertContains(respuesta, "Ajusta el monto")
        self.assertContains(respuesta, "11.004")
        self.assertNotIn("plan", self.client.session)
        # .value() devuelve lo que conserva el campo para mostrar al usuario.
        self.assertEqual(respuesta.context["form"]["presupuesto"].value(), "5000")

        # Mismo visitante: corrige el monto y esta vez debe obtener un resultado.
        respuesta = self.client.post(reverse("home"), {"presupuesto": "25000"}, follow=True)
        self.assertRedirects(respuesta, reverse("plan"))
        self.assertLessEqual(respuesta.context["plan"]["costo_total"], 25000)

    def test_presupuestos_invalidos_muestran_error(self):
        # Enviamos datos directamente, incluso los que bloquearía el navegador,
        # para comprobar que la validación también existe en el servidor.
        for monto in ("", "0", "-100", "hola", "NaN", "Infinity", "25000.123", "1000000000000"):
            with self.subTest(monto=monto):
                respuesta = self.client.post(reverse("home"), {"presupuesto": monto})
                # 200 significa que la página se entregó correctamente. Puede
                # contener errores del formulario; no significa "monto válido".
                self.assertEqual(respuesta.status_code, 200)
                # Una lista de errores no vacía se considera verdadera.
                self.assertTrue(respuesta.context["form"].errors.get("presupuesto"))
                self.assertNotIn("plan", self.client.session)

    def test_presupuesto_decimal_se_conserva_sin_redondear(self):
        # Verifica tanto el cálculo con decimales como su presentación en HTML.
        respuesta = self.client.post(reverse("home"), {"presupuesto": "25000.50"}, follow=True)
        self.assertEqual(Decimal(respuesta.context["plan"]["presupuesto"]), Decimal("25000.50"))
        self.assertEqual(Decimal(respuesta.context["plan"]["saldo"]), Decimal("8021.50"))
        self.assertContains(respuesta, "8.021,50")

    def test_ajustar_regresa_al_formulario_y_descarta_el_plan(self):
        # Genera un plan, pulsa Ajustar y comprueba que solo se conserva el monto.
        self.client.post(reverse("home"), {"presupuesto": "25000"})
        plan_id = self.client.session["plan"]["id"]
        respuesta = self.client.post(reverse("plan"), {
            "accion": "ajustar", "plan_id": plan_id,
        }, follow=True)
        self.assertRedirects(respuesta, reverse("home"))
        self.assertNotIn("plan", self.client.session)
        self.assertEqual(respuesta.context["form"]["presupuesto"].value(), "25000")

    def test_acceso_sin_plan_vuelve_al_formulario(self):
        # Una visita directa o una confirmación sin generar no deben fallar.
        self.assertRedirects(self.client.get(reverse("plan")), reverse("home"))
        self.assertRedirects(self.client.post(reverse("plan"), {"accion": "confirmar"}), reverse("home"))

    def test_ver_el_resultado_no_confirma_el_plan(self):
        # Enviar accion=confirmar por GET no debe aceptar el plan: requiere POST.
        self.client.post(reverse("home"), {"presupuesto": "25000"})
        self.client.get(reverse("plan"), {"accion": "confirmar"})
        self.assertFalse(self.client.session["plan"]["confirmado"])

    def test_no_confirma_un_plan_desde_una_pestana_antigua(self):
        # Generamos dos planes en la misma sesión y enviamos el ID del primero.
        # Representa confirmar desde una pestaña que aún muestra el plan viejo.
        self.client.post(reverse("home"), {"presupuesto": "25000"})
        id_anterior = self.client.session["plan"]["id"]
        self.client.post(reverse("home"), {"presupuesto": "12000"})
        respuesta = self.client.post(reverse("plan"), {
            "accion": "confirmar", "plan_id": id_anterior,
        }, follow=True)
        self.assertContains(respuesta, "La planificación cambió")
        self.assertFalse(self.client.session["plan"]["confirmado"])

    def test_solicitud_nueva_fallida_no_deja_un_plan_anterior_confirmable(self):
        # Después de generar, se intenta de nuevo con un monto insuficiente o
        # inválido. El plan anterior no debe seguir disponible para confirmar.
        for monto in ("5000", "hola"):
            with self.subTest(monto=monto):
                self.client.post(reverse("home"), {"presupuesto": "25000"})
                self.client.post(reverse("home"), {"presupuesto": monto})
                self.assertNotIn("plan", self.client.session)
                self.assertRedirects(self.client.get(reverse("plan")), reverse("home"))
