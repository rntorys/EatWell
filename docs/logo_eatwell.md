# Logo de EatWell

El símbolo representa un plato con hojas y una semilla. Se generó con la herramienta
integrada **imagegen**, con fondo transparente, para acompañar el nombre de la app.

Archivo: `web/static/web/img/eatwell-logo.png`.
Se usa en el encabezado y como icono de la pestaña del navegador.

El tamaño visible y el fondo del recuadro se ajustan en las clases `brand-mark`
y `brand-logo` de `styles.css`.

Para compartir el diseño, incluye la imagen y los cambios de las plantillas
`base.html` y `plan.html` en la base común del proyecto. Después se puede aplicar
la versión del CSS copiando su contenido completo en `styles.css`.

Prompt usado:

```text
Use case: logo-brand. Create one finished standalone logo symbol for EatWell, a student meal planning and grocery budgeting web app. A minimal, distinctive rounded dinner plate or bowl combined with two fresh leaves growing from its center; a small warm gold accent can suggest a seed. Bold clean geometric flat shapes, friendly and contemporary, simple enough to read at 40 pixels. Deep forest green #183f31 and fresh leaf green #70ad78, warm gold #e8bd76. Square composition, tightly centered with modest clear padding. Transparent background, no text or letters, no mockup, no gradients, no shadows, no watermark, no surrounding scenery. This is the actual small website brand mark, not a presentation sheet of variants.
```
