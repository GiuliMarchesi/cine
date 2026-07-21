"""Configuración pública del monitor.

Las credenciales se leen exclusivamente de variables de entorno para que este
archivo pueda subirse a un repositorio público sin exponer datos privados.
"""

import os


# --- Datos privados (GitHub Secrets / variables de entorno locales) ---
USUARIO_EMAIL = os.getenv("SHOWCASE_USUARIO", "")
USUARIO_PASSWORD = os.getenv("SHOWCASE_PASSWORD", "")
WHATSAPP_TELEFONO = os.getenv("WHATSAPP_TELEFONO", "")
CALLMEBOT_APIKEY = os.getenv("CALLMEBOT_APIKEY", "")

# --- Qué querés ver ---
FILM_URL = "https://entradas.todoshowcase.com/showcase/pelicula?filmid=5875&house_id=3250"
CINE = "IMAX Theatre (Norcenter)"
PELICULA = "La Odisea"
FECHA = "2026-08-05"
HORARIO_DESEADO = "19:00"
FILA_DESEADA = "C"  # Se usa si ASIENTOS_DESEADOS está vacío
ASIENTOS_DESEADOS = ["C-11", "C-12"]
TIPO_ENTRADA = "General"
CANTIDAD_ENTRADAS = 2

# --- Ejecución local continua ---
INTERVALO_MINUTOS = 10

# En GitHub siempre se ejecuta sin ventana. Localmente podés usar HEADLESS=false.
HEADLESS = os.getenv("HEADLESS", "true").lower() not in {"0", "false", "no"}
URL_LOGIN = "https://entradas.todoshowcase.com/showcase/ingresar.aspx"


def variables_privadas_faltantes():
    """Devuelve los nombres de las variables privadas que no están definidas."""
    requeridas = {
        "SHOWCASE_USUARIO": USUARIO_EMAIL,
        "SHOWCASE_PASSWORD": USUARIO_PASSWORD,
        "WHATSAPP_TELEFONO": WHATSAPP_TELEFONO,
        "CALLMEBOT_APIKEY": CALLMEBOT_APIKEY,
    }
    return [nombre for nombre, valor in requeridas.items() if not valor]
