from uuid import uuid4
from urllib.parse import urlencode

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponseNotAllowed, QueryDict
from django.core.paginator import Paginator
from django.shortcuts import redirect, render

from .forms import PreciosForm, PresupuestoForm
from .models import PlanGuardado
from .odepa import ErrorODEPA, obtener_precios
from .planner import calcular_presupuesto_minimo, generar_plan
from .catalogo import ingredientes_disponibles, recetas_disponibles, clave_producto_odepa, marcar_favoritos
from .calendario import PeriodoForm, periodo_predeterminado, seleccionar_fechas


def registro(request):
    if request.method not in ["GET", "POST"]:
        return HttpResponseNotAllowed(["GET", "POST"])
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        # Django valida el usuario y las dos contraseñas, y guarda un hash.
        form = UserCreationForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            login(request, usuario)
            return redirect("home")
    else:
        form = UserCreationForm()

    return render(request, "web/registro.html", {"form": form})


# Este decorador envía al login a quien todavía no ha iniciado sesión.
@login_required
def home(request):
    # GET muestra la página y POST envía el formulario.
    if request.method not in ["GET", "POST"]:
        return HttpResponseNotAllowed(["GET", "POST"])

    guardado = PlanGuardado.objects.filter(usuario=request.user).first()
    sin_plan = False
    error = ""
    info_precios = None
    minimo = None
    datos_periodo = periodo_predeterminado()
    if guardado is not None:
        datos_periodo.update(guardado.datos.get("periodo", {}))
    entrada = request.POST if request.method == "POST" else request.GET
    revisar_dias = request.method == "POST" and entrada.get("accion") == "revisar_dias"
    if "modo" in entrada:
        datos_periodo = entrada
    periodo_form = PeriodoForm(datos_periodo)
    seleccion = entrada if request.method == "POST" and not revisar_dias else None
    if request.method == "GET" and "modo" not in entrada and guardado is not None and guardado.datos.get("periodo"):
        seleccion = QueryDict("calendario_presentado=1", mutable=True)
        seleccion.setlist("dias", [dia["fecha"] for dia in guardado.datos["menu"] if "fecha" in dia])
    calendario, dias = seleccionar_fechas(periodo_form, seleccion)
    if revisar_dias:
        # Alternativa sin JavaScript: actualiza el calendario sin generar un plan.
        form = PresupuestoForm(initial={"region": entrada.get("region", "13"), "presupuesto": entrada.get("presupuesto", "")})
    elif request.method == "POST":
        form = PresupuestoForm(request.POST)
        if form.is_valid() and periodo_form.is_valid():
            presupuesto = form.cleaned_data["presupuesto"]
            region = form.cleaned_data["region"]
            try:
                ingredientes, info_precios, productos = obtener_precios(region)
            except ErrorODEPA as problema:
                error = str(problema)
                plan = None
            else:
                ingredientes = ingredientes_disponibles(request.user, ingredientes, productos)
                recetas, omitidas = recetas_disponibles(request.user, ingredientes)
                info_precios["recetas_omitidas"] = omitidas
                minimo = calcular_presupuesto_minimo(ingredientes, recetas, len(dias))
                plan = generar_plan(presupuesto, ingredientes, recetas, dias)
                sin_plan = plan is None

            if plan is not None:
                # Identificador único: distingue planes incluso entre dispositivos.
                plan["id"] = str(uuid4())
                plan["confirmado"] = False
                plan["precios"] = info_precios
                plan["periodo"] = {
                    "modo": periodo_form.cleaned_data["modo"],
                    "inicio": str(periodo_form.cleaned_data.get("inicio") or ""),
                    "mes": periodo_form.cleaned_data.get("mes", ""),
                    "sin_fines": periodo_form.cleaned_data["sin_fines"],
                }
                # El plan pertenece a la cuenta, no a la sesión del navegador.
                PlanGuardado.objects.update_or_create(
                    usuario=request.user, defaults={"datos": plan},
                )
                return redirect("plan")

    else:
        presupuesto = ""
        region = "13"
        if guardado is not None:
            presupuesto = guardado.datos["presupuesto"]
            region = guardado.datos.get("precios", {}).get("region_id", "13")
        form = PresupuestoForm(initial={"presupuesto": presupuesto, "region": region})

    return render(request, "web/home.html", {
        "form": form,
        "sin_plan": sin_plan,
        "presupuesto_minimo": minimo,
        "tiene_plan": guardado is not None,
        "error": error,
        "info_precios": info_precios,
        "periodo_form": periodo_form,
        "calendario": calendario,
        "cantidad_comidas": len(dias) * 3,
        "cantidad_dias": len(dias),
        "revisar_dias": revisar_dias,
        "resumen_desde": dias[0]["dia"] if dias else "",
        "resumen_hasta": dias[-1]["dia"] if dias else "",
    })


@login_required
def ver_plan(request):
    if request.method not in ["GET", "POST"]:
        return HttpResponseNotAllowed(["GET", "POST"])

    # Siempre buscamos por el usuario conectado: no por un usuario enviado en HTML.
    guardado = PlanGuardado.objects.filter(usuario=request.user).first()
    if guardado is None:
        return redirect("home")
    plan = guardado.datos
    plan.setdefault("cantidad_comidas", sum(bool(c["ingredientes"]) for d in plan["menu"] for c in d["comidas"]))
    claves = sorted({clave for d in plan["menu"] for c in d["comidas"] for clave in c["ingredientes"]})
    for clave, compra in zip(claves, plan["compras"]):
        compra.setdefault("clave", clave)

    error = ""
    if request.method == "POST":
        accion = request.POST.get("accion")

        # Una pestaña antigua no puede confirmar el plan nuevo.
        if request.POST.get("plan_id") != plan["id"]:
            error = "La planificación cambió. Revisa el plan actual."
        elif accion == "ajustar":
            # Conservamos el plan hasta que se genere otro válido.
            return redirect("home")
        elif accion == "confirmar":
            plan["confirmado"] = True
            # La condición también evita sobrescribir un plan recién cambiado
            # desde otro dispositivo mientras se procesa esta petición.
            actualizados = PlanGuardado.objects.filter(
                usuario=request.user, datos__id=plan["id"],
            ).update(datos=plan)
            if actualizados:
                return redirect("plan")
            guardado.refresh_from_db()
            plan = guardado.datos
            error = "La planificación cambió. Revisa el plan actual."
        else:
            error = "Selecciona confirmar o ajustar el presupuesto."

    return render(request, "web/plan.html", {"plan": plan, "error": error})


@login_required
def precios(request):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    guardado = PlanGuardado.objects.filter(usuario=request.user).first()
    region = "13"
    if guardado is not None:
        region = guardado.datos.get("precios", {}).get("region_id", "13")
    datos = request.GET if request.GET else {"region": region}
    form = PreciosForm(datos)
    info = None
    productos = []
    ingredientes = {}
    error = ""
    if form.is_valid():
        try:
            ingredientes, info, productos = obtener_precios(form.cleaned_data["region"])
        except ErrorODEPA as problema:
            error = str(problema)
        else:
            busqueda = form.cleaned_data["busqueda"].casefold()
            encontrados = []
            for producto in productos:
                if busqueda in producto["nombre"].casefold():
                    encontrados.append(producto)
            productos = encontrados
            productos = [dict(p, clave=clave_producto_odepa(p)) for p in productos]
            productos = marcar_favoritos(request.user, "producto", productos)
            if form.cleaned_data["favoritos"]:
                productos = [p for p in productos if p["favorito"]]
            ingredientes = ingredientes_disponibles(request.user, ingredientes, [])
    pagina = Paginator(productos, 10).get_page(request.GET.get("pagina"))
    filtros = urlencode({"region": form["region"].value() or region, "busqueda": form["busqueda"].value() or "", "favoritos": "on" if form["favoritos"].value() else ""})
    return render(request, "web/precios.html", {
        "form": form, "info_precios": info, "productos": pagina,
        "pagina": pagina, "filtros": filtros,
        "ingredientes": ingredientes, "error": error,
    })
