# EatWell

Proyecto en Django que genera un menú de 7 días para una persona, con
desayuno, almuerzo y cena, según su presupuesto semanal.

Para ejecutarlo en Windows, desde la carpeta del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Abrir http://127.0.0.1:8000/. Si el entorno y las dependencias ya están listos,
basta con el último comando.

Las recetas y los precios están en `web/data.py`. El cálculo está en
`web/planner.py`. Los precios son de ejemplo y corresponden a las cantidades
usadas, no a envases completos. Se permite repetir comidas.

Casos para probar con los datos actuales:

- **25000:** genera 21 comidas y la lista de compras. El costo es $16.979 y
  sobran $8.021. Al pulsar Confirmar plan, aparece el plan confirmado.
- **5000:** informa que no alcanza y pide ajustar el monto. El mínimo es
  $11.004. Al cambiar a 25000, permite generar el plan.

Para ejecutar las pruebas automáticas:

```powershell
.\.venv\Scripts\python.exe manage.py test
```

El logo se puede guardar en `web/static/web/images/`.
