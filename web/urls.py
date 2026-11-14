from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path
from . import views
from . import views_catalogo
from . import views_favoritos
from . import views_plan

urlpatterns = [
    path("favoritos/", views_favoritos.favorito, name="favorito"),
    # Django ya incluye la comprobación de contraseñas y el cierre de sesión.
    path("ingresar/", LoginView.as_view(template_name="web/login.html"), name="login"),
    path("registro/", views.registro, name="registro"),
    path("salir/", LogoutView.as_view(), name="logout"),
    path("", views.home, name="home"),
    path("plan/", views.ver_plan, name="plan"),
    path("plan/comida/<int:dia>/<int:comida>/", views_plan.editar_comida, name="editar_comida"),
    path("plan/producto/<str:clave>/", views_plan.editar_producto_plan, name="editar_producto_plan"),
    path("plan/presupuesto/", views_plan.presupuesto_plan, name="presupuesto_plan"),
    path("precios/", views.precios, name="precios"),
    path("productos/", views_catalogo.productos, name="productos"),
    path("productos/nuevo/", views_catalogo.producto_formulario, name="producto_nuevo"),
    path("productos/<int:pk>/editar/", views_catalogo.producto_formulario, name="producto_editar"),
    path("productos/<int:pk>/foto/", views_catalogo.producto_foto, name="producto_foto"),
    path("recetas/", views_catalogo.recetas, name="recetas"),
    path("recetas/nueva/", views_catalogo.receta_formulario, name="receta_nueva"),
    path("recetas/<int:pk>/editar/", views_catalogo.receta_formulario, name="receta_editar"),
]
