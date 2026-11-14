from django.core.management.base import BaseCommand, CommandError

from web.odepa import ErrorODEPA, REGIONES, obtener_precios


class Command(BaseCommand):
    help = "Descarga los precios ODEPA de una región sin esperar las 24 horas de caché."

    def add_arguments(self, parser):
        parser.add_argument("--region", required=True, choices=dict(REGIONES))

    def handle(self, *args, **options):
        try:
            catalogo, info, productos = obtener_precios(options["region"], forzar=True)
        except ErrorODEPA as error:
            raise CommandError(str(error)) from error
        if info["aviso"]:
            raise CommandError(info["aviso"])
        self.stdout.write(self.style.SUCCESS(
            f"{info['region']}: semana {info['semana']}, {len(productos)} productos/unidades, "
            f"{info['ingredientes_odepa']} ingredientes con precio ODEPA."
        ))
        self.stdout.write("Con precio de ejemplo: " + ", ".join(info["faltantes"]))
