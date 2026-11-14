// Solo interacción: evita perder lo escrito al marcar favoritos.
// La autorización y el guardado siguen ocurriendo en Django.
function filtrarFavoritos(selector) {
    const busqueda = selector.querySelector('.favorite-search').value.toLocaleLowerCase();
    const solo = selector.querySelector('.favorite-only').checked;
    const contenedor = selector.querySelector('.favorite-items');
    const elementos = Array.from(contenedor.children);
    elementos.sort((a, b) => Number(b.dataset.favorito) - Number(a.dataset.favorito));
    for (const elemento of elementos) {
        elemento.hidden = (solo && elemento.dataset.favorito !== '1') ||
            !elemento.querySelector('span').textContent.toLocaleLowerCase().includes(busqueda);
        contenedor.appendChild(elemento);
    }
    const lista = document.getElementById(selector.dataset.lista);
    if (lista) {
        const seleccion = lista.value;
        const opciones = Array.from(lista.children);
        opciones.sort((a, b) => Number(b.dataset.favorito) - Number(a.dataset.favorito));
        for (const opcion of opciones) {
            const texto = (opcion.textContent || opcion.value).toLocaleLowerCase();
            opcion.disabled = (solo && opcion.dataset.favorito !== '1') || !texto.includes(busqueda);
            opcion.hidden = opcion.disabled;
            lista.appendChild(opcion);
        }
        if (lista.tagName === 'SELECT') lista.value = seleccion;
    }
}

document.querySelectorAll('.favorite-picker').forEach(selector => {
    selector.querySelector('.favorite-search').addEventListener('input', () => filtrarFavoritos(selector));
    selector.querySelector('.favorite-only').addEventListener('change', () => filtrarFavoritos(selector));
});

document.querySelectorAll('.favorite-form').forEach(form => {
    form.addEventListener('submit', async evento => {
        evento.preventDefault();
        const boton = form.querySelector('button');
        const estado = form.querySelector('.favorite-status');
        boton.disabled = true;
        try {
            const respuesta = await fetch(form.action, {
                method: 'POST', body: new FormData(form), headers: {'Accept': 'application/json'},
            });
            if (!respuesta.ok) throw new Error('No se pudo guardar');
            const datos = await respuesta.json();
            document.querySelectorAll('.favorite-form').forEach(otro => {
                if (otro.dataset.clave === datos.clave && otro.dataset.tipo === datos.tipo) {
                    otro.querySelector('button').textContent = datos.favorito ? '★' : '☆';
                    otro.querySelector('button').setAttribute('aria-pressed', String(datos.favorito));
                    otro.elements.accion.value = datos.favorito ? 'quitar' : 'agregar';
                }
            });
            document.querySelectorAll('.favorite-item, datalist option, .recipe-option').forEach(elemento => {
                if (elemento.dataset.clave === datos.clave) elemento.dataset.favorito = datos.favorito ? '1' : '0';
            });
            document.querySelectorAll('.favorite-picker').forEach(filtrarFavoritos);
            estado.textContent = datos.favorito ? 'Guardado' : 'Quitado';
        } catch (error) {
            estado.textContent = 'No se guardó. Revisa tu conexión o vuelve a iniciar sesión.';
        } finally {
            boton.disabled = false;
        }
    });
});
