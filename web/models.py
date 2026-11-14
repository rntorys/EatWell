from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


class PlanGuardado(models.Model):
    # OneToOneField permite guardar un solo plan actual por usuario.
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    # JSONField guarda el diccionario completo: menú, compras, saldo y confirmación.
    datos = models.JSONField()


class PreciosRegion(models.Model):
    # Una copia por región evita descargar los mismos datos en cada visita.
    region = models.CharField(max_length=2, unique=True)
    datos = models.JSONField()
    actualizado = models.DateTimeField(auto_now=True)


class ProductoPersonal(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)
    unidad = models.CharField(max_length=6, choices=[("g", "Gramos"), ("ml", "Mililitros"), ("unidad", "Unidades")])
    cantidad_referencia = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(100000)])
    precio_referencia = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    propiedades = models.TextField(blank=True, max_length=1000)
    foto = models.ImageField(upload_to="productos/", blank=True)


class RecetaPersonal(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=10, choices=[("desayuno", "Desayuno"), ("almuerzo", "Almuerzo"), ("cena", "Cena")])
    instrucciones = models.TextField(blank=True, max_length=3000)
    # Igual que en data.py: identificador de ingrediente -> cantidad para una porción.
    ingredientes = models.JSONField(default=dict)


class Favorito(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=10, choices=[("producto", "Producto"), ("receta", "Receta")])
    clave = models.CharField(max_length=100)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["usuario", "tipo", "clave"], name="favorito_unico_por_usuario")]
