// Solo prepara el calendario de la pantalla. Python valida las fechas y calcula el plan.
const planificador = document.getElementById('planificador');
const modo = document.getElementById('id_modo');
const inicio = document.getElementById('id_inicio');
const mes = document.getElementById('id_mes');
const sinFines = document.getElementById('id_sin_fines');
const diasPlan = document.getElementById('dias-plan');
const errorCalendario = document.getElementById('error-calendario');
const generar = document.getElementById('generar-plan');
const formatoFecha = new Intl.DateTimeFormat('es-CL', {
    weekday: 'long', day: '2-digit', month: '2-digit', year: 'numeric', timeZone: 'UTC',
});

function mostrarCampoFecha() {
    const porMes = modo.value === 'mes';
    document.getElementById('campo-inicio').hidden = porMes;
    document.getElementById('campo-mes').hidden = !porMes;
    inicio.disabled = porMes;
    mes.disabled = !porMes;
}

function mostrarResumen() {
    const marcados = Array.from(diasPlan.querySelectorAll('input:checked'));
    const cantidad = marcados.length;
    document.getElementById('resumen-dias').textContent =
        `${cantidad} ${cantidad === 1 ? 'día' : 'días'} · ${cantidad * 3} comidas`;
    document.getElementById('resumen-fechas').textContent = cantidad ?
        `Del ${formatoFecha.format(new Date(marcados[0].value))} al ${formatoFecha.format(new Date(marcados[cantidad - 1].value))}` : '';
    errorCalendario.hidden = cantidad > 0;
    errorCalendario.textContent = cantidad ? '' : 'Selecciona una fecha válida y al menos un día para tu plan.';
    generar.disabled = cantidad === 0;
}

function actualizarCalendario() {
    mostrarCampoFecha();
    const valor = modo.value === 'mes' ? mes.value + '-01' : inicio.value;
    const fecha = new Date(valor + 'T00:00:00Z');
    diasPlan.replaceChildren();
    if (!Number.isNaN(fecha.getTime()) && fecha.getUTCFullYear() >= 2000 && fecha.getUTCFullYear() <= 2100) {
        const cantidad = modo.value === 'mes' ?
            new Date(Date.UTC(fecha.getUTCFullYear(), fecha.getUTCMonth() + 1, 0)).getUTCDate() : Number(modo.value);
        for (let numero = 0; numero < cantidad; numero++) {
            const dia = new Date(fecha);
            dia.setUTCDate(fecha.getUTCDate() + numero);
            if (sinFines.checked && [0, 6].includes(dia.getUTCDay())) continue;
            const etiqueta = document.createElement('label');
            etiqueta.className = 'calendar-day';
            const casilla = document.createElement('input');
            casilla.type = 'checkbox';
            casilla.name = 'dias';
            casilla.className = 'calendar-checkbox';
            casilla.value = dia.toISOString().slice(0, 10);
            casilla.checked = true;
            const texto = document.createElement('span');
            texto.textContent = formatoFecha.format(dia);
            etiqueta.append(casilla, texto);
            diasPlan.append(etiqueta);
        }
    }
    mostrarResumen();
}

for (const campo of [modo, inicio, mes, sinFines]) {
    campo.addEventListener('change', actualizarCalendario);
}
diasPlan.addEventListener('change', mostrarResumen);
planificador.addEventListener('submit', evento => {
    if (generar.disabled) evento.preventDefault();
});
// Conserva las fechas elegidas al volver o al corregir un presupuesto inválido.
mostrarCampoFecha();
mostrarResumen();
