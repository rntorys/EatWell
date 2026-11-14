# EatWell

Proyecto en Django que genera un menú para una persona, con desayuno, almuerzo
y cena, según el presupuesto total y los días seleccionados.

Para ejecutarlo en Windows, desde la carpeta del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Abrir http://127.0.0.1:8000/ y pulsar **Crear cuenta**. Si ya tienes cuenta,
inicia sesión. Después de actualizar el proyecto, ejecuta `migrate` antes de
`runserver` para crear las tablas nuevas.

Cada cuenta guarda su plan actual, incluso al cerrar sesión. **Mi plan** permite
recuperarlo. Generar otro plan válido reemplaza el anterior; un monto inválido
o insuficiente no lo borra. No hay historial de planes.

Para recuperar el plan desde otro dispositivo, ambos deben conectarse al mismo
servidor con la misma cuenta. El flujo y la prueba desde el celular están en
[docs/inicio_de_sesion.md](docs/inicio_de_sesion.md).

Elige tu región al generar el plan. EatWell consulta los precios públicos de ODEPA
y conserva una copia durante 24 horas. En **Precios por región** puedes buscar
productos y revisar las equivalencias usadas en las recetas.
Los productos publicados se muestran de 10 en 10, conservando la búsqueda y región.

Hay 35 recetas de ejemplo de EatWell. En **Mis productos** puedes guardar nombre,
precio, cantidad del envase, unidad, propiedades y una foto opcional. En **Recetas**
puedes crear y editar recetas para una porción, buscando ingredientes existentes,
productos ODEPA compatibles o productos propios. El planificador prueba primero
tus recetas, si el presupuesto lo permite. Todo queda asociado a tu cuenta.
El recorrido está en [docs/productos_y_recetas.md](docs/productos_y_recetas.md).

Puedes planificar 7, 28, 30 o 31 días, o elegir un mes, excluir fines de semana y
marcar fechas concretas. En **Mi plan** puedes editar cada comida o quitar y
reemplazar un producto en todo el plan. Las compras se recalculan y los cambios
que superan el presupuesto no se guardan. Las estrellas ☆/★ guardan favoritos
privados y permiten encontrarlos primero al buscar.
Más detalles en [docs/editar_plan_y_calendario.md](docs/editar_plan_y_calendario.md).

Las recetas y los precios de respaldo están en `web/data.py`; la conexión a ODEPA,
en `web/odepa.py`; el cálculo, en `web/planner.py`. Los ingredientes sin equivalencia
conservan precios de ejemplo y se identifican en pantalla. Se estiman cantidades
usadas, no envases completos. Se permite repetir comidas.

Casos para comprobar el flujo:

- **25000 para 7 días:** genera 21 comidas dentro del presupuesto y permite confirmar.
- **Monto menor que el mínimo:** informa que no alcanza y permite ajustar el monto.

Los valores cambian según región, semana y recetas personales. Las pruebas automáticas usan datos
simulados y conservan también los dos escenarios del catálogo original.
La integración y actualización manual están explicadas en [docs/odepa.md](docs/odepa.md).

Para ejecutar las pruebas automáticas:

```powershell
.\.venv\Scripts\python.exe manage.py test
```

El logo se puede guardar en `web/static/web/images/`.
