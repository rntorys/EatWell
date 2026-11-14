# Precios ODEPA en EatWell

La API consultada es pública y no necesitó cuenta, clave ni pago en las consultas
realizadas. Fuente: [Precios al consumidor de ODEPA](https://datos.odepa.gob.cl/dataset/precios-consumidor),
con licencia Creative Commons Attribution (CC BY). La aplicación muestra esa atribución.

## Qué puedes hacer

1. Inicia sesión y elige una región en el formulario de presupuesto.
2. Genera el plan. Se usan precios de la última semana disponible de esa región.
3. Revisa la semana, región y fuente de cada ingrediente en la lista de compras.
4. En **Precios por región**, puedes consultar los productos y buscarlos por nombre.

La región se guarda con el plan de la cuenta y se recuerda al volver al formulario.
La consulta de productos por sí sola no cambia el plan ni añade ingredientes a una
receta. Cada plan conserva los precios y la fecha con los que fue calculado,
incluso si ODEPA publica nuevos precios después.

El conjunto cubre Arica y Parinacota, Coquimbo, Valparaíso, Metropolitana, Maule,
Ñuble, Biobío, La Araucanía y Los Lagos. No usamos otra región como reemplazo de
una región sin cobertura. La lista se encuentra en `REGIONES`, en `web/odepa.py`.

## Cómo funciona el código

- `web/odepa.py`: conecta con la API usando `urllib`, que viene con Python.
  `truststore` permite validar HTTPS con los certificados del sistema; se añadió
  a `requirements.txt` porque la conexión normal de Python fallaba al validar
  la cadena de certificados en este computador. No se desactivó la verificación.
- `package_show`: descubre el recurso anual disponible, sin dejar fijo un ID
  que cambie al pasar de año.
- `datastore_search`: consulta la última semana de la región y descarga sus
  registros en páginas. Los filtros viajan en la URL, no como consultas SQL.
- `preparar_datos()`: interpreta precios con coma decimal, agrupa los productos
  y convierte las unidades que conocemos.
- `PreciosRegion`, en `web/models.py`: almacena la copia local por región.
- `obtener_precios()`: usa la copia durante 24 horas; al vencer, intenta actualizar
  cuando alguien consulta o genera un plan. No hay una tarea en segundo plano.
- `web/planner.py`: recibe el catálogo regional como argumento. Usa `Decimal`
  para sumar los costos sin errores de coma flotante.
- `web/forms.py` y `web/views.py`: validan la región elegida, consultan los precios
  y entregan el catálogo al planificador. No se necesita JavaScript.

Solo se envían a ODEPA identificadores de recursos, región, semana y paginación.
No enviamos cuentas, contraseñas, presupuestos ni planes de los usuarios.

## Cómo interpretamos los precios

ODEPA publica registros por producto, unidad, sector y tipo de comercio.
EatWell calcula una media simple de los precios promedio de esos registros.
Esa media es un cálculo de EatWell, no un promedio oficial regional ponderado.
Puede combinar supermercados, ferias y otros comercios de la región.

Para las recetas convertimos cada registro antes de promediar. Por ejemplo,
una bandeja de 12 huevos a $3.000 equivale a $250 por huevo; un kilo de arroz
a $1.500 equivale a $1,50 por gramo. Redondeamos el precio utilizado por gramo,
ml o unidad a dos decimales; con ese mismo valor calculamos recetas y compras.

Las equivalencias son explícitas en `EQUIVALENCIAS`. Pan integral usa hallulla
integral; pollo usa pechuga deshuesada. No confundimos “Pollo Ganso” (vacuno) con
pollo. En verduras no convertimos precios por unidad a gramos sin un peso conocido.
Los sacos de legumbres de 5 o 25 kg no se usan en las recetas del estudiante.

En la consulta comprobada de Metropolitana y Valparaíso, 13 de los 16 ingredientes
tienen equivalencia. Avena, atún y sal conservan los valores de demostración.
Esto se avisa en pantalla y por ingrediente. Un precio de ejemplo nunca se etiqueta
como ODEPA. La cobertura puede cambiar según la región y la semana.

Los precios son referenciales semanales, no precios de una tienda en tiempo real.
El presupuesto limita el costo estimado de las cantidades utilizadas; comprar
envases completos puede costar más. Este conjunto no incluye fotos ni propiedades
nutricionales. Algunos nombres llegan con caracteres dañados desde ODEPA.

## Si no hay internet o falla ODEPA

Con una copia local, se conserva y se muestra un aviso con su semana.
Sin copia de esa región, se informa el error y no se genera un plan con precios
inventados ni de otra región. Un plan anterior de la cuenta permanece guardado.
Una descarga fallida no reemplaza la copia anterior.

## Instalar en otro computador y actualizar

En este computador ya se instalaron las dependencias y se aplicó la migración.
Tus compañeros deben ejecutar:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

No necesitan registrarse en ODEPA. La primera consulta requiere internet.
Para actualizar manualmente sin esperar las 24 horas:

```powershell
.\.venv\Scripts\python.exe manage.py actualizar_precios --region 13
```

Ejemplos de códigos: 13 Metropolitana, 5 Valparaíso, 8 Biobío, 9 La Araucanía.
La tabla `PreciosRegion` almacena precios públicos; `PlanGuardado` conserva los
planes privados de cada usuario. No hace falta compartir `db.sqlite3` por Git.

## Verificación

`python manage.py test` incluye pruebas de conversión de unidades, decimales,
paginación, filtros de región, copias locales, errores de conexión y planes
guardados. Las pruebas simulan ODEPA: no necesitan internet ni dependen de cambios
de precios. También se hicieron consultas reales para Metropolitana y Valparaíso.

Para estudiar la API: [documentación de DataStore de CKAN](https://docs.ckan.org/en/2.11/maintaining/datastore.html).
