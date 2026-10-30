# EatWell: planificación semanal

Prototipo en Django para una persona, con desayuno, almuerzo y cena durante
siete días. El usuario ingresa un presupuesto en pesos chilenos, revisa el menú,
su lista de compras y su costo estimado, y confirma el plan o ajusta el monto.
Toda la lógica funciona en Python; no se necesita JavaScript.

## Ejecutar en Windows (PowerShell)

Desde la carpeta del proyecto, usando el entorno virtual que ya existe:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Abrir http://127.0.0.1:8000/ en el navegador. Para detener el servidor, usar
`Ctrl+C` en la terminal. `migrate` prepara las tablas internas de Django y no
necesita ejecutarse otra vez si ya están actualizadas.

En otro equipo, primero crear el entorno e instalar las dependencias:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Dónde está cada parte

| Archivo | Responsabilidad |
| --- | --- |
| `web/data.py` | Los 16 ingredientes con sus precios ficticios y las 11 recetas. |
| `web/forms.py` | Validar que el presupuesto sea numérico, positivo y tenga hasta dos decimales. |
| `web/planner.py` | Calcular costos, elegir 21 comidas y agrupar la lista de compras. |
| `web/views.py` | Recibir el formulario, generar el resultado y gestionar la confirmación o el ajuste. |
| `web/urls.py` | Conectar `/` con el formulario y `/plan/` con el resultado. |
| `web/templates/web/base.html` | Estructura compartida, cabecera y enlace al CSS. |
| `web/templates/web/home.html` | Formulario y mensajes de validación o presupuesto insuficiente. |
| `web/templates/web/plan.html` | Menú, compras, costo, saldo y botones de confirmación. |
| `web/static/web/css/styles.css` | Estilos básicos para continuar el diseño. |
| `web/static/web/images/` | Carpeta preparada para el logo y otras imágenes. |
| `web/tests.py` | Pruebas del cálculo y del flujo completo con Django. |

## Datos y cálculo

Para esta entrega, las listas y diccionarios de `web/data.py` funcionan como
catálogo precargado. No hace falta crear modelos ni tablas propias. SQLite ya
existía en el proyecto y Django lo usa para conservar la sesión del navegador:
allí se mantiene el plan actual y si fue confirmado. No hay historial de planes,
cuentas de usuario ni un guardado permanente propio de EatWell.

Los precios son inventados para demostrar el funcionamiento. Cada ingrediente
tiene un precio entero en CLP por **un gramo, mililitro o unidad**, según indique
su campo `unidad`. Cada receta rinde **una porción**; al agregar recetas, mantener
sus cantidades para una persona y `porciones: 1`. Arroz, fideos y lentejas se
pesan en seco. El costo de la receta se calcula desde sus ingredientes, evitando
guardar un precio duplicado que pudiera quedar desactualizado.

Ejemplo: 60 g de avena a $2/g, 200 ml de leche a $1/ml y 100 g de plátano a $2/g
dan un desayuno de $520.

El algoritmo:

1. Busca la receta más económica de cada tipo de comida.
2. Calcula el mínimo semanal: siete veces la suma de esos tres costos.
3. Si no alcanza el presupuesto, devuelve que no existe un plan posible.
4. Si alcanza, recorre los siete días y sus tres comidas. Rota las recetas para
   dar variedad, pero solo elige una si deja dinero suficiente para cubrir el
   mínimo de todas las comidas pendientes.
5. Suma las cantidades de los ingredientes repetidos y calcula sus subtotales.
   La suma de la lista de compras coincide con el costo de las 21 comidas.

Se permite repetir recetas: por eso el mínimo es alcanzable y un presupuesto
igual o superior siempre permite completar el menú con este catálogo. La
variedad es una preferencia, no una condición que pueda dejar días sin comida.
No se intenta gastar todo el presupuesto: el dinero sobrante se muestra como saldo.

**Alcance de la estimación:** se cobra la cantidad utilizada, sin redondear a
paquetes de supermercado. Por ejemplo, 360 g de arroz cuestan $720 con estos
datos aunque una tienda pudiera vender solamente bolsas de 1 kg. La página
explica esta limitación; no representa una cotización real ni incluye una
evaluación nutricional.

## Dos casos para presentar

Los resultados siguientes corresponden al catálogo incluido; si cambian las
recetas o los precios, también cambiarán los totales.

### 1. Escenario principal: presupuesto suficiente

1. Entrar a la página inicial e ingresar `25000`.
2. Pulsar **Generar planificación**.
3. Verificar siete días, cada uno con desayuno, almuerzo y cena: 21 comidas.
4. Verificar la lista agrupada de compras, un costo de **$16.979 CLP** y un saldo
   de **$8.021 CLP**. El costo es menor que el presupuesto de $25.000.
5. Pulsar **Confirmar plan**: aparece **Plan confirmado** y se mantiene el menú.

### 2. Escenario alternativo: presupuesto insuficiente

1. Volver al formulario e ingresar `5000`.
2. Pulsar **Generar planificación**.
3. Verificar el mensaje de que no existe un plan con ese presupuesto y la
   solicitud de ajustar el monto. No se muestra un menú incompleto ni más caro.
4. Verificar que se informa un mínimo de **$11.004 CLP** con las recetas actuales.
5. Cambiar el monto a `25000` y volver a generar: ahora se obtiene un plan.

También se puede comprobar el límite: `11004` genera un plan exacto con saldo
cero, mientras que `11003.99` no alcanza. Los valores vacíos, cero, negativos
o no numéricos producen errores de validación. El navegador ya impide varias
entradas inválidas y Django vuelve a validarlas en el servidor.

Para rechazar un plan, pulsar **Ajustar presupuesto**: regresa al formulario con
el monto anterior disponible para editar. Una vez confirmado, **Generar otro
plan** permite comenzar otra vez.

## Pruebas automatizadas

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
```

Las pruebas usan una base de datos temporal. Comprueban los dos escenarios,
los límites del presupuesto, los subtotales, la variedad, los datos inválidos,
los decimales, el ajuste y la confirmación del plan correcto.

## Agregar el logo después

Guardar la imagen, por ejemplo, en `web/static/web/images/logo.png`. En
`web/templates/web/base.html`, que ya carga la etiqueta `static`, se podrá usar:

```html
<img src="{% static 'web/images/logo.png' %}" alt="EatWell">
```

El archivo `.gitkeep` permite conservar la carpeta de imágenes en Git mientras
está vacía.
