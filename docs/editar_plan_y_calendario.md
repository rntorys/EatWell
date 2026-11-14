# Editar planes, favoritos y calendario

## Elegir los días

En Planificar hay dos pasos:

1. Elige 7, 28, 30 o 31 días desde una fecha inicial, o un mes completo.
   Puedes excluir sábados y domingos. Pulsa **Mostrar días del período**.
2. Desmarca las fechas que no necesitas, elige región e ingresa el presupuesto
   total para los días que quedaron seleccionados. Genera la propuesta.

Febrero tiene 28 o 29 días según el año. Los otros meses incluyen sus 30 o 31
días automáticamente. Debes seleccionar al menos un día. La opción de excluir
fines de semana reduce la cantidad de días del período, no los mueve hacia adelante.
Las fechas seleccionadas y la región se conservan con el plan de tu cuenta.

El presupuesto cubre **todo el período**, no cada semana. Por ejemplo, elegir
30 días con $25.000 no significa disponer de $25.000 por semana. El mínimo se
calcula con tres comidas por cada fecha seleccionada.

## Editar la propuesta o el plan confirmado

Cada comida tiene el enlace **Editar o reemplazar**. Allí puedes:

- Reemplazarla por una receta del catálogo o una propia.
- Cambiar su nombre, productos y cantidades.
- Añadir ingredientes en las filas vacías o marcar Eliminar para quitar uno.
- Quitar toda la comida. Queda marcada como omitida y sus ingredientes salen
  de las compras. Puedes volver a editar ese espacio para añadir otra comida.

En la lista de compras, **Quitar o reemplazar en todo el plan** aplica el cambio
a todas las comidas que usen ese ingrediente. Si mantienes la unidad, puedes
conservar las cantidades originales. Si pasas de gramos a unidades, por ejemplo,
debes indicar expresamente la cantidad para cada comida afectada: no se inventa
una equivalencia. Si el reemplazo ya estaba en una comida, las cantidades se suman.

Cada cambio recalcula los costos, las compras y el saldo. Si excede el presupuesto,
se muestra el costo propuesto y no se modifica el plan guardado. Puedes reducir
cantidades, elegir otro producto o cambiar el presupuesto desde **Mi plan**
conservando sus comidas. El presupuesto nuevo no puede ser menor que el costo actual.

Editar un plan confirmado lo deja pendiente de confirmación. Las recetas y los
productos del catálogo no cambian por editar una comida del plan. Un formulario
abierto antes de una modificación en otro dispositivo se rechaza para no borrar
los cambios más recientes.

La cantidad de comidas mostrada se actualiza. Si quitas una comida, ese espacio
queda sin cubrir; EatWell no presenta el plan como si todavía cubriera todas las
comidas originales.

## Precios durante la edición

El plan guarda una copia de los ingredientes disponibles y sus precios al crearse.
La edición utiliza esa copia para no cambiar inesperadamente todos los costos.
Los productos personales creados después se pueden añadir y usan el precio que
tienen al incorporarse. Generar otro plan consulta nuevamente los precios vigentes.

Los planes anteriores a esta función recuperan los precios de su lista de compras.
Para las nuevas opciones se consulta el catálogo disponible, conservando los precios
de los ingredientes que ya tenían.

## Favoritos

Las estrellas ☆ y ★ permiten agregar y quitar favoritos de productos y recetas.
Se guardan en tu cuenta y aparecen al ingresar desde otro dispositivo. Los productos
y recetas personales de otras cuentas nunca se pueden marcar ni consultar.

En las listas puedes activar **★ Solo favoritos**. Los favoritos aparecen primero.
Al crear recetas o editar comidas hay un desplegable para buscar y marcar favoritos:
sus estrellas no borran lo que ya escribiste en el formulario. El mismo filtro
limita las sugerencias de ingredientes o las opciones de receta.

Marcar un producto no lo añade solo a una comida. Las recetas favoritas se ordenan
primero entre las candidatas del planificador, pero siguen sujetas al presupuesto
y a la rotación de opciones. No se garantiza que cada favorita aparezca en cada plan.

Se añadió un archivo pequeño de JavaScript para guardar estrellas sin recargar
la página y filtrar sugerencias. La validación, los cálculos, permisos y guardado
siguen en Python. Sin JavaScript, las estrellas de las listas funcionan mediante
formularios; marcar una mientras editas recarga la página y puede perder el borrador.

## Dónde está el código

- `web/calendario.py`: fechas válidas, duración del mes y selección de días.
- `web/planner.py`: planificación para entre 1 y 31 días seleccionados.
- `web/edicion.py`: cambios y recálculo sin modificar el catálogo original.
- `web/views_plan.py`: formularios para editar comidas, productos y presupuesto.
- `web/models.py`: tabla `Favorito`, única por usuario, tipo y producto o receta.
- `web/views_favoritos.py`: valida y guarda estrellas mediante POST con CSRF.
- `web/static/web/js/favoritos.js`: interacción de estrellas y filtros.
- `web/test_planes_editables.py`: pruebas de meses bisiestos, fechas, edición,
  compras, límites de presupuesto, privacidad, favoritos y formularios antiguos.

En este computador la migración ya está aplicada. En otro: `python manage.py migrate`.
Para ejecutar las pruebas: `python manage.py test`.
