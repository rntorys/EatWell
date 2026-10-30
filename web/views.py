from django.http import HttpResponseNotAllowed
from django.shortcuts import redirect, render

from .forms import PresupuestoForm
from .planner import calcular_presupuesto_minimo, generar_plan


def home(request):
    # GET muestra la página y POST envía el formulario.
    if request.method not in ["GET", "POST"]:
        return HttpResponseNotAllowed(["GET", "POST"])

    sin_plan = False
    if request.method == "POST":
        if "plan" in request.session:
            del request.session["plan"]

        form = PresupuestoForm(request.POST)
        if form.is_valid():
            presupuesto = form.cleaned_data["presupuesto"]
            request.session["ultimo_presupuesto"] = str(presupuesto)
            plan = generar_plan(presupuesto)

            if plan is not None:
                # Numeramos los planes para distinguir uno nuevo de uno anterior.
                numero = request.session.get("numero_plan", 0) + 1
                request.session["numero_plan"] = numero
                plan["id"] = str(numero)
                plan["confirmado"] = False
                # La sesión recuerda el plan entre una página y otra.
                request.session["plan"] = plan
                request.session.set_expiry(0)
                return redirect("plan")

            sin_plan = True
    else:
        form = PresupuestoForm(initial={
            "presupuesto": request.session.get("ultimo_presupuesto", ""),
        })

    return render(request, "web/home.html", {
        "form": form,
        "sin_plan": sin_plan,
        "presupuesto_minimo": calcular_presupuesto_minimo(),
    })


def ver_plan(request):
    if request.method not in ["GET", "POST"]:
        return HttpResponseNotAllowed(["GET", "POST"])

    plan = request.session.get("plan")
    if plan is None:
        return redirect("home")

    error = ""
    if request.method == "POST":
        accion = request.POST.get("accion")

        # Una pestaña antigua no puede confirmar el plan nuevo.
        if request.POST.get("plan_id") != plan["id"]:
            error = "La planificación cambió. Revisa el plan actual."
        elif accion == "ajustar":
            del request.session["plan"]
            return redirect("home")
        elif accion == "confirmar":
            plan["confirmado"] = True
            request.session["plan"] = plan
            return redirect("plan")
        else:
            error = "Selecciona confirmar o ajustar el presupuesto."

    return render(request, "web/plan.html", {"plan": plan, "error": error})
