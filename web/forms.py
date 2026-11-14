from decimal import Decimal
from django import forms
from django.core.files.base import ContentFile
from io import BytesIO
from uuid import uuid4
from PIL import Image

from .odepa import REGIONES
from .models import ProductoPersonal, RecetaPersonal
from .catalogo import opciones_ingredientes


class RegionForm(forms.Form):
    region = forms.ChoiceField(label="Región de los precios", choices=REGIONES, initial="13")


class PreciosForm(RegionForm):
    busqueda = forms.CharField(label="Buscar producto", required=False, max_length=100)
    favoritos = forms.BooleanField(label="★ Solo favoritos", required=False)


# Django revisa el número y prepara los errores del formulario.
class PresupuestoForm(RegionForm):
    presupuesto = forms.DecimalField(
        label="Presupuesto para todos los días seleccionados (CLP)",
        # Decimal permite trabajar con dinero sin usar float.
        min_value=Decimal("0.01"),
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            "placeholder": "Ejemplo: 25000",
            "step": "0.01",
            "aria-describedby": "ayuda-presupuesto",
        }),
        error_messages={
            "required": "Ingresa el presupuesto para el período.",
            "invalid": "Ingresa un número válido para el presupuesto.",
            "min_value": "El presupuesto debe ser mayor que 0.",
            "max_decimal_places": "Usa como máximo dos decimales.",
        },
    )


class ProductoForm(forms.ModelForm):
    class Meta:
        model = ProductoPersonal
        fields = ["nombre", "unidad", "cantidad_referencia", "precio_referencia", "propiedades", "foto"]
        labels = {
            "cantidad_referencia": "Cantidad del envase o compra",
            "precio_referencia": "Precio de esa cantidad (CLP)",
            "propiedades": "Propiedades o notas (opcional)", "foto": "Foto (opcional)",
        }
        help_texts = {
            "cantidad_referencia": "Ejemplo: 500 si compras una bolsa de 500 gramos. Usa cantidades enteras.",
            "precio_referencia": "Ejemplo: 1500 si esa bolsa cuesta $1.500. El precio por g, ml o unidad se calcula a dos decimales.",
            "propiedades": "Puedes anotar marca, alérgenos o información de la etiqueta. Son datos ingresados por ti.",
            "foto": "JPG, PNG o WebP, máximo 3 MB. Solo tú puedes consultar esta foto.",
        }
        widgets = {"propiedades": forms.Textarea(attrs={"rows": 3}), "foto": forms.FileInput()}

    def clean(self):
        datos = super().clean()
        precio = datos.get("precio_referencia")
        cantidad = datos.get("cantidad_referencia")
        if precio and cantidad and precio / cantidad < Decimal("0.01"):
            self.add_error("precio_referencia", "El precio por g, ml o unidad debe ser al menos $0,01.")
        if self.instance.pk and datos.get("unidad") != self.instance.unidad:
            clave = "personal_" + str(self.instance.pk)
            if RecetaPersonal.objects.filter(usuario=self.instance.usuario, ingredientes__has_key=clave).exists():
                self.add_error("unidad", "El producto ya se usa en una receta. Crea otro producto si necesitas otra unidad.")
        return datos

    def clean_foto(self):
        foto = self.cleaned_data.get("foto")
        if not foto or not hasattr(foto, "content_type"):
            return foto
        if foto.size > 3 * 1024 * 1024:
            raise forms.ValidationError("La foto no puede superar los 3 MB.")
        foto.seek(0)
        with Image.open(foto) as imagen:
            if imagen.format not in ["JPEG", "PNG", "WEBP"]:
                raise forms.ValidationError("Usa una imagen JPG, PNG o WebP.")
            # Creamos una imagen nueva sin metadatos ni el nombre original del archivo.
            imagen = imagen.convert("RGB")
            imagen.thumbnail((1000, 1000))
            salida = BytesIO()
            imagen.save(salida, format="JPEG", quality=85)
        return ContentFile(salida.getvalue(), name=uuid4().hex + ".jpg")


class RecetaForm(forms.ModelForm):
    class Meta:
        model = RecetaPersonal
        fields = ["nombre", "tipo", "instrucciones"]
        widgets = {"instrucciones": forms.Textarea(attrs={"rows": 4})}


class IngredienteRecetaForm(forms.Form):
    ingrediente = forms.CharField(max_length=300, widget=forms.TextInput(attrs={
        "list": "ingredientes-disponibles", "placeholder": "Escribe para buscar y elige una opción",
        "autocomplete": "off",
    }))
    cantidad = forms.IntegerField(min_value=1, max_value=100000, label="Cantidad para una porción")

    def __init__(self, *args, catalogo, **kwargs):
        super().__init__(*args, **kwargs)
        self.opciones = opciones_ingredientes(catalogo)

    def clean_ingrediente(self):
        etiqueta = self.cleaned_data["ingrediente"]
        if etiqueta not in self.opciones:
            raise forms.ValidationError("Selecciona un ingrediente disponible de la lista.")
        return self.opciones[etiqueta]


class IngredientesBaseFormSet(forms.BaseFormSet):
    def clean(self):
        if any(self.errors):
            return
        usados = set()
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue
            clave = form.cleaned_data["ingrediente"]
            if clave in usados:
                raise forms.ValidationError("No repitas ingredientes: suma su cantidad en una sola fila.")
            usados.add(clave)


IngredientesFormSet = forms.formset_factory(
    IngredienteRecetaForm, formset=IngredientesBaseFormSet,
    extra=11, min_num=1, validate_min=True, max_num=12, validate_max=True, absolute_max=12,
    can_delete=True,
)
