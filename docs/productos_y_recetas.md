# Productos y recetas personales

## Qué cambió

- **Productos publicados** muestra 10 filas por página, con Primera, Anterior,
  Siguiente y Última. La búsqueda y la región se conservan al navegar. Si hay
  201 resultados, son 21 páginas y la última contiene uno.
- El catálogo pasa de 11 a 35 recetas: 11 desayunos, 12 almuerzos y 12 cenas.
  Estas recetas son de EatWell, no vienen de la API de ODEPA.
- Cada cuenta puede crear y editar sus propios productos y recetas.

## Probar el recorrido completo

1. Inicia sesión y abre **Mis productos → Agregar producto**.
2. Ejemplo: nombre “Mi yogur”, unidad gramos, cantidad 500 y precio 1500.
   El sistema calcula $3 por gramo. Puedes añadir propiedades de la etiqueta
   y una foto JPG, PNG o WebP de hasta 3 MB.
3. Abre **Recetas → Crear mi receta**. Elige la región antes de completar los campos.
4. Escribe el nombre y el tipo de comida. En ingredientes, escribe “Mi yogur”
   y selecciona la sugerencia. Usa 150 gramos. Añade 40 gramos de avena en otra fila.
5. Guarda la receta. Aparece en tu catálogo con su costo y sus ingredientes.
6. Genera un plan con presupuesto suficiente. Tu receta se prueba antes que
   las recetas de ejemplo; sus ingredientes se suman a la lista de compras.
7. Inicia sesión con la misma cuenta desde otro navegador del mismo servidor:
   aparecen tus productos, recetas y plan. Otra cuenta no los puede consultar.

Agregar un producto no lo incorpora por sí solo al menú: hay que usarlo en una
receta. Las recetas personales se consideran, pero no se garantiza que todas
aparezcan en cada semana. Siempre debe quedar presupuesto para las otras comidas.

## Cómo son las recetas

Las cantidades son para **una porción** y se ingresan como enteros de gramos,
mililitros o unidades. Hay espacio para hasta 12 ingredientes distintos. Abre
los bloques opcionales si necesitas más. Si repites un ingrediente, suma sus
cantidades en una sola fila. Al editar, puedes marcar Eliminar en una fila para
quitar ese ingrediente; debe quedar al menos uno.

El campo de ingrediente usa `datalist`, una lista de sugerencias nativa de HTML:
escribe y elige una opción. Django valida la selección en el servidor.
No se agregó JavaScript. Las instrucciones de preparación son opcionales.

Puedes usar ingredientes del catálogo base, productos publicados por ODEPA
con una unidad convertible y productos personales. Las equivalencias conocidas
están en `UNIDADES_ODEPA`, en `web/catalogo.py`. No se inventan conversiones
entre unidades y gramos ni se ofrecen sacos de 25 kilos como envases individuales.

Si cambias a una región donde no existe un ingrediente ODEPA de tu receta,
la receta queda guardada, pero se excluye de ese cálculo y se avisa en pantalla.
Puedes editarla desde el desplegable **Editar mis recetas**, cambiar el ingrediente
o elegir nuevamente una región que lo tenga.

## Guardado y precios

Los productos y recetas son privados de cada cuenta. Los precios de productos
personales los ingresa el usuario; se identifican como “Producto personal”,
nunca como precios ODEPA. Las propiedades son notas del usuario, sin validación
nutricional automática.

Editar un precio o una receta afecta los planes nuevos. El plan ya guardado
conserva el menú, las cantidades y los costos originales. Si un producto ya se
usa en una receta, no se puede cambiar su unidad: se crea otro producto para
evitar que 100 gramos se interpreten como 100 unidades.

## Archivos principales

- `web/models.py`: `ProductoPersonal` y `RecetaPersonal`, relacionados con el usuario.
- `web/forms.py`: valida productos, fotos y hasta 12 filas de ingredientes.
- `web/catalogo.py`: reúne los ingredientes de ODEPA, los propios y las recetas disponibles.
- `web/views_catalogo.py`: páginas de productos, recetas y fotos privadas.
- `web/planner.py`: recibe las recetas disponibles y sigue respetando el presupuesto.
- `web/data.py`: las 35 recetas del catálogo de ejemplo.
- `web/templates/web/paginacion.html`: navegación reutilizable, hecha con Django.

Las fotos se guardan en `media/productos/`, carpeta excluida de Git. Se convierten
a JPEG, se reduce su tamaño y se quitan sus metadatos. Se sirven mediante una
vista que verifica el usuario; no se publica la carpeta media completa.
Para conservar toda la información del servidor hay que respaldar tanto su
base de datos como `media/`.

En este computador ya se aplicaron las migraciones. En otras instalaciones:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Para probar automáticamente: `python manage.py test`. Los casos originales con
montos exactos usan una copia de las primeras 11 recetas. Hay pruebas adicionales
para las 35 recetas, la paginación, creación, edición, fotos, privacidad y uso de
productos propios en la planificación.
