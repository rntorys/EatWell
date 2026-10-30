# Una vista recibe una solicitud del navegador (request) y devuelve una
# respuesta: por ejemplo, una página HTML o una redirección a otra dirección.

# uuid es parte de Python. uuid4() crea un identificador aleatorio que usamos
# para distinguir un plan de otro. No es el usuario ni el precio del plan.
from uuid import uuid4

# messages es el sistema de avisos temporales de Django. Un aviso puede
# sobrevivir a una redirección y mostrarse en la siguiente página.
# Nuestro base.html recorre "messages" para presentar esos textos.
from django.contrib import messages

# Son dos funciones de ayuda de Django:
# render(request, plantilla, datos) combina un HTML con los datos y responde.
# redirect("nombre_ruta") pide al navegador que visite la ruta con ese nombre.
# Los nombres "home" y "plan" se declararon con name=... en web/urls.py.
from django.shortcuts import redirect, render

# Importamos una función que construye un decorador para limitar los métodos
# HTTP permitidos. La explicación de @ está justo antes de home().
from django.views.decorators.http import require_http_methods

# El punto indica una importación desde nuestro mismo paquete (web).
# Esta clase es la que definimos en web/forms.py; no es el módulo django.forms.
from .forms import PresupuestoForm
# Estas funciones propias realizan los cálculos en web/planner.py.
from .planner import calcular_presupuesto_minimo, generar_plan


# @ aplica un DECORADOR a la función que viene inmediatamente después.
# Un decorador añade comportamiento alrededor de una función.
# Aquí Django comprueba el método antes de ejecutar home():
# - GET: se usa en este flujo para visitar la página y ver el formulario.
# - POST: se usa para enviar el formulario.
# Otros métodos (como PUT o DELETE) reciben una respuesta 405: no permitido.
# Sin la sintaxis @, sería equivalente a escribir, después de definir home:
# home = require_http_methods(["GET", "POST"])(home)
@require_http_methods(["GET", "POST"])
def home(request):
    # Django entrega request: contiene método, datos enviados, sesión, etc.
    # Esta bandera controla el mensaje de presupuesto válido pero insuficiente.
    sin_plan = False
    if request.method == "POST":
        # Una nueva solicitud reemplaza el plan anterior, incluso si es inválida.
        # session se usa como un diccionario asociado a este navegador.
        # En este proyecto Django guarda sus datos en SQLite y el navegador
        # conserva una cookie que identifica la sesión. No exige iniciar sesión.
        # pop("plan", None) quita el plan; si no existe, devuelve None sin fallar.
        request.session.pop("plan", None)
        # request.POST contiene los campos enviados, inicialmente como texto.
        # Crear el formulario enlaza esos datos con las reglas de forms.py.
        form = PresupuestoForm(request.POST)
        # is_valid() ejecuta las reglas. Si falla, form.errors contiene mensajes
        # y seguimos hasta el render final para mostrar el mismo formulario.
        if form.is_valid():
            # cleaned_data contiene valores ya validados y convertidos:
            # en este caso presupuesto es Decimal, no el texto original.
            presupuesto = form.cleaned_data["presupuesto"]
            # Recordamos el monto para precargarlo si el usuario quiere ajustar.
            request.session["ultimo_presupuesto"] = str(presupuesto)
            plan = generar_plan(presupuesto)
            # None significa que no se encontró un plan completo con ese monto.
            if plan is not None:
                # .hex representa el identificador como 32 caracteres de texto.
                plan["id"] = uuid4().hex
                # El plan generado todavía no ha sido aceptado por el usuario.
                plan["confirmado"] = False
                request.session["plan"] = plan
                # 0 solicita una cookie de sesión, sin fecha fija de caducidad
                # en el navegador. No significa eliminar ahora el plan de SQLite.
                request.session.set_expiry(0)
                # Termina esta vista y manda al navegador a GET /plan/.
                # Así actualizar la página del resultado no reenvía este POST.
                return redirect("plan")
            sin_plan = True
    else:
        # Al visitar con GET, initial precarga el monto anterior sin validarlo
        # todavía. .get(..., "") usa texto vacío cuando no hay monto guardado.
        form = PresupuestoForm(initial={
            "presupuesto": request.session.get("ultimo_presupuesto", ""),
        })

    # El tercer argumento es el contexto: un diccionario de variables que
    # home.html puede usar, por ejemplo {{ form.presupuesto }}.
    return render(request, "web/home.html", {
        "form": form,
        "sin_plan": sin_plan,
        "presupuesto_minimo": calcular_presupuesto_minimo(),
    })


@require_http_methods(["GET", "POST"])
def ver_plan(request):
    # Mismo decorador: permite consultar (GET) y enviar una decisión (POST).
    # Recuperamos el resultado guardado, sin volver a calcularlo en cada visita.
    plan = request.session.get("plan")
    if plan is None:
        # Si alguien entra directamente a /plan/, primero debe generar uno.
        return redirect("home")

    if request.method == "POST":
        # Evita confirmar otro plan desde una pestaña que quedó desactualizada.
        # plan.html envía plan_id en un input oculto. Lo comparamos con el plan
        # actual de la sesión; no confiamos en costos enviados por el navegador.
        if request.POST.get("plan_id") != plan["id"]:
            # Registra el aviso. redirect no lo muestra por sí mismo:
            # lo presentará base.html al cargar la página siguiente.
            messages.error(request, "La planificación cambió. Revisa el plan actual.")
            return redirect("plan")

        # El botón pulsado manda name="accion" y su value: ajustar o confirmar.
        accion = request.POST.get("accion")
        if accion == "ajustar":
            # Quitamos el plan, pero conservamos ultimo_presupuesto para editarlo.
            request.session.pop("plan")
            return redirect("home")
        if accion == "confirmar":
            plan["confirmado"] = True
            # Reasignamos el diccionario para que Django detecte el cambio en
            # la sesión. Modificar solo una clave interna puede no marcarla.
            request.session["plan"] = plan
            return redirect("plan")

        # Si llegó una acción desconocida, no confirmamos y damos una indicación.
        messages.error(request, "Selecciona confirmar o ajustar el presupuesto.")
        return redirect("plan")

    # En GET mostramos el mismo plan, con el estado confirmado o pendiente.
    return render(request, "web/plan.html", {"plan": plan})
