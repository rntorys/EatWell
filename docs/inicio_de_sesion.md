# Cuentas de EatWell

## Cómo funciona

1. Abres EatWell. Si no has iniciado sesión, aparece el formulario de ingreso.
2. Puedes crear una cuenta con nombre de usuario y contraseña repetida.
3. Django valida los datos, guarda un hash de la contraseña e inicia tu sesión.
4. Generas un plan con tu presupuesto. Ahora se guarda en la base de datos,
   relacionado con tu usuario. También se guarda si todavía no lo confirmas.
5. Al confirmar, se actualiza ese mismo plan.
6. Cerrar sesión termina el acceso desde ese navegador, pero no borra el plan.
7. Al ingresar desde otro navegador al mismo servidor, recuperas el plan.

Guardamos un solo plan actual por usuario. Generar otro válido lo reemplaza.
Volver al formulario o enviar un monto que no alcanza conserva el plan anterior.
Cada navegador muestra los cambios del otro cuando vuelves a cargar la página;
no hay actualización automática en tiempo real.

Los planes de las antiguas sesiones anónimas no se asocian automáticamente a
una cuenta. El guardado por usuario se aplica a los planes generados desde ahora.

## Qué hace cada parte

- `web/urls.py`: conecta ingresar, registrarse y salir con sus vistas.
- `LoginView`: vista incluida en Django que comprueba usuario y contraseña.
- `LogoutView`: vista de Django que cierra la sesión mediante un formulario POST.
- `registro()` en `web/views.py`: utiliza `UserCreationForm` para validar y crear
  la cuenta. `login(request, usuario)` inicia su sesión después del registro.
- `@login_required`: antes de ejecutar una vista, comprueba que haya un usuario
  identificado. Si no lo hay, envía al formulario de ingreso.
- `request.user`: el usuario que Django identifica por la sesión del navegador.
- `PlanGuardado` en `web/models.py`: tabla que relaciona una cuenta con su plan.
  `OneToOneField` significa que cada usuario tiene como máximo un registro aquí.
  `JSONField` permite guardar el diccionario que ya devuelve el planificador.
- `update_or_create()`: guarda por primera vez o reemplaza el plan de esa cuenta.
- `uuid4()`: crea una etiqueta única para cada nueva planificación. Así, una
  pestaña antigua no puede confirmar por accidente un plan diferente.
- `login.html` y `registro.html`: muestran los formularios. `form.as_p` genera
  campos, etiquetas, ayudas y errores. `{% csrf_token %}` protege los formularios.
- `0001_initial.py`: migración con las instrucciones para crear la tabla nueva.

La sesión identifica quién está entrando. La base de datos conserva su plan.
Las contraseñas se gestionan con las herramientas de Django, no con comparaciones
manuales ni guardándolas como texto. Esta versión no incluye recuperación por correo.

## Prueba rápida en el computador

1. Ejecuta `python manage.py migrate` y `python manage.py runserver` con el entorno activo.
2. Crea una cuenta y genera un plan con `25000`.
3. Abre una ventana privada y entra a la misma dirección con esa cuenta.
4. En **Mi plan**, verás el mismo menú, costo y lista de compras.
5. Confirma desde una ventana y recarga la otra: aparecerá confirmado.
6. Cierra sesión y vuelve a ingresar: el plan sigue guardado.
7. Crea otra cuenta: empieza sin plan y no ve el de la primera.

## Probar desde el celular en la misma red Wi-Fi

El servidor se ejecuta en el computador. El celular entra a ese servidor;
no debe usar `localhost`, porque en el celular eso apunta al propio teléfono.

1. Ejecuta `ipconfig` y busca la dirección IPv4 de tu conexión Wi-Fi.
2. Detén el servidor y, en PowerShell, ejecuta lo siguiente reemplazando la IP
   del ejemplo por la de tu computador:

```powershell
$env:EATWELL_ALLOWED_HOSTS = "localhost,127.0.0.1,192.168.1.50"
.\.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
```

3. En el celular abre `http://192.168.1.50:8000/`, usando tu IP real.
4. Inicia sesión con la misma cuenta. El computador debe seguir encendido y
   ejecutando el servidor. Si Windows solicita acceso de red, usa la red privada.

Esto es una prueba local en una red de confianza. Para acceder desde cualquier
lugar hace falta publicar Django en un servidor con HTTPS; GitHub Pages no ejecuta
este backend. Dos computadores con copias distintas de `db.sqlite3` no comparten
usuarios ni planes por tener el mismo código.

`db.sqlite3` contiene ahora cuentas y planes personales. No la uses para compartir
cuentas por Git: cada instalación crea sus tablas con `migrate`. Si ya estaba
rastreada en Git, seguirá apareciendo en `git status` cuando cambien los datos.

Para ejecutar las pruebas: `python manage.py test`.
