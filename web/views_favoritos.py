from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme

from .catalogo import clave_producto_odepa, clave_receta
from .data import INGREDIENTES, RECETAS
from .models import Favorito, PreciosRegion, ProductoPersonal, RecetaPersonal


@login_required
def favorito(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    tipo = request.POST.get("tipo")
    clave = request.POST.get("clave", "")
    accion = request.POST.get("accion")
    if accion not in ["agregar", "quitar"]:
        return HttpResponseBadRequest("Acción inválida.")
    valido = False
    if tipo == "producto":
        if clave in INGREDIENTES:
            valido = True
        elif clave.startswith("personal_") and clave[9:].isdigit():
            valido = ProductoPersonal.objects.filter(usuario=request.user, pk=clave[9:]).exists()
        elif clave.startswith("odepa_"):
            copia = PreciosRegion.objects.filter(region=request.POST.get("region", "13")).first()
            if copia is not None:
                valido = any(clave_producto_odepa(p) == clave for p in copia.datos["productos"])
    elif tipo == "receta":
        if clave.startswith("receta_") and clave[7:].isdigit():
            valido = RecetaPersonal.objects.filter(usuario=request.user, pk=clave[7:]).exists()
        else:
            valido = any(clave_receta(receta) == clave for receta in RECETAS)
    # Permite quitar un favorito ODEPA aunque ya no esté disponible esta semana.
    if accion == "quitar" and Favorito.objects.filter(usuario=request.user, tipo=tipo, clave=clave).exists():
        valido = True
    if not valido:
        return HttpResponseBadRequest("El producto o receta no está disponible para tu cuenta.")
    if accion == "agregar":
        Favorito.objects.get_or_create(usuario=request.user, tipo=tipo, clave=clave)
    else:
        Favorito.objects.filter(usuario=request.user, tipo=tipo, clave=clave).delete()
    if request.headers.get("Accept") == "application/json":
        return JsonResponse({"favorito": accion == "agregar", "clave": clave, "tipo": tipo})
    destino = request.POST.get("volver", "/")
    if not url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        destino = "/"
    return redirect(destino)
