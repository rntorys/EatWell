"""Pantallas para los productos y recetas privados de cada usuario."""
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import FileResponse, Http404, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render

from .catalogo import ingredientes_disponibles, opciones_ingredientes, recetas_disponibles, selector_productos
from .forms import IngredientesFormSet, PreciosForm, ProductoForm, RecetaForm, RegionForm
from .models import Favorito, PlanGuardado, ProductoPersonal, RecetaPersonal
from .odepa import ErrorODEPA, obtener_precios
from .planner import calcular_costo_receta


def region_inicial(usuario):
    plan = PlanGuardado.objects.filter(usuario=usuario).first()
    if plan is not None:
        return plan.datos.get("precios", {}).get("region_id", "13")
    return "13"


@login_required
def productos(request):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    propios = list(ProductoPersonal.objects.filter(usuario=request.user).order_by("-id"))
    claves = set(Favorito.objects.filter(usuario=request.user, tipo="producto").values_list("clave", flat=True))
    favoritos = []
    otros = []
    for producto in propios:
        producto.clave = "personal_" + str(producto.pk)
        producto.favorito = producto.clave in claves
        if producto.favorito:
            favoritos.append(producto)
        else:
            otros.append(producto)
    propios = favoritos if request.GET.get("favoritos") else favoritos + otros
    pagina = Paginator(propios, 10).get_page(request.GET.get("pagina"))
    return render(request, "web/productos.html", {"pagina": pagina, "filtros": urlencode({"favoritos": request.GET.get("favoritos", "")})})


@login_required
def producto_formulario(request, pk=None):
    if request.method not in ["GET", "POST"]:
        return HttpResponseNotAllowed(["GET", "POST"])
    producto = None
    if pk is not None:
        producto = get_object_or_404(ProductoPersonal, pk=pk, usuario=request.user)
    if request.method == "POST":
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            producto = form.save(commit=False)
            producto.usuario = request.user
            producto.save()
            return redirect("productos")
    else:
        form = ProductoForm(instance=producto)
    return render(request, "web/producto_form.html", {"form": form, "producto": producto})


@login_required
def producto_foto(request, pk):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    producto = get_object_or_404(ProductoPersonal, pk=pk, usuario=request.user)
    if not producto.foto:
        raise Http404
    try:
        archivo = producto.foto.open("rb")
    except FileNotFoundError:
        raise Http404
    respuesta = FileResponse(archivo, content_type="image/jpeg")
    respuesta["Cache-Control"] = "private, no-store"
    return respuesta


@login_required
def recetas(request):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    datos = request.GET if request.GET else {"region": region_inicial(request.user)}
    filtro = PreciosForm(datos)
    lista = []
    omitidas = []
    error = ""
    info = None
    if filtro.is_valid():
        try:
            base, info, publicados = obtener_precios(filtro.cleaned_data["region"])
        except ErrorODEPA as problema:
            error = str(problema)
        else:
            catalogo = ingredientes_disponibles(request.user, base, publicados)
            disponibles, omitidas = recetas_disponibles(request.user, catalogo)
            for receta in disponibles:
                if filtro.cleaned_data["favoritos"] and not receta["favorito"]:
                    continue
                if filtro.cleaned_data["busqueda"].casefold() not in receta["nombre"].casefold():
                    continue
                ficha = receta.copy()
                ficha["costo"] = calcular_costo_receta(receta, catalogo)
                detalle = []
                for clave, cantidad in receta["ingredientes"].items():
                    ingrediente = catalogo[clave]
                    detalle.append({"nombre": ingrediente["nombre"], "cantidad": cantidad, "unidad": ingrediente["unidad"]})
                ficha["detalle"] = detalle
                lista.append(ficha)
    pagina = Paginator(lista, 10).get_page(request.GET.get("pagina"))
    filtros = urlencode({"region": filtro["region"].value() or "13", "busqueda": filtro["busqueda"].value() or "", "favoritos": "on" if filtro["favoritos"].value() else ""})
    # También ofrecemos editar las recetas no disponibles en esta región.
    propias = RecetaPersonal.objects.filter(usuario=request.user).order_by("-id")
    return render(request, "web/recetas.html", {
        "form": filtro, "pagina": pagina, "filtros": filtros, "error": error,
        "info_precios": info, "omitidas": omitidas, "propias": propias,
    })


@login_required
def receta_formulario(request, pk=None):
    if request.method not in ["GET", "POST"]:
        return HttpResponseNotAllowed(["GET", "POST"])
    receta = None
    if pk is not None:
        receta = get_object_or_404(RecetaPersonal, pk=pk, usuario=request.user)
    datos_region = request.POST if request.method == "POST" else {
        "region": request.GET.get("region", region_inicial(request.user)),
    }
    region_form = RegionForm(datos_region)
    catalogo = {}
    info = None
    error = ""
    if region_form.is_valid():
        try:
            base, info, publicados = obtener_precios(region_form.cleaned_data["region"])
        except ErrorODEPA as problema:
            error = str(problema)
        else:
            catalogo = ingredientes_disponibles(request.user, base, publicados)
    opciones = opciones_ingredientes(catalogo)
    inicial = []
    faltantes = []
    if receta is not None:
        etiquetas = {}
        for etiqueta, clave in opciones.items():
            etiquetas[clave] = etiqueta
        for clave, cantidad in receta.ingredientes.items():
            if clave not in etiquetas:
                faltantes.append(clave)
            inicial.append({"ingrediente": etiquetas.get(clave, clave), "cantidad": cantidad})
    if request.method == "POST":
        form = RecetaForm(request.POST, instance=receta)
        filas = IngredientesFormSet(request.POST, form_kwargs={"catalogo": catalogo}, prefix="ingredientes")
        # Ambos se validan para mostrar todos los errores sin perder lo escrito.
        receta_valida = form.is_valid()
        filas_validas = filas.is_valid()
        if region_form.is_valid() and not error and receta_valida and filas_validas:
            ingredientes = {}
            for fila in filas:
                if fila.cleaned_data and not fila.cleaned_data.get("DELETE"):
                    ingredientes[fila.cleaned_data["ingrediente"]] = fila.cleaned_data["cantidad"]
            receta = form.save(commit=False)
            receta.usuario = request.user
            receta.ingredientes = ingredientes
            receta.save()
            return redirect("/recetas/?" + urlencode({"region": region_form.cleaned_data["region"]}))
    else:
        form = RecetaForm(instance=receta)
        filas = IngredientesFormSet(initial=inicial, form_kwargs={"catalogo": catalogo}, prefix="ingredientes")
    return render(request, "web/receta_form.html", {
        "form": form, "filas": filas, "region_form": region_form,
        "opciones": opciones, "receta": receta, "error": error,
        "info_precios": info, "faltantes": faltantes,
        "selector_productos": selector_productos(catalogo),
    })
