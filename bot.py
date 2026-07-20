"""
Bot de chequeo de asientos - Showcase Cinemas Argentina
=========================================================
Revisa periódicamente si hay asientos libres en la fila deseada,
para la película/cine/fecha configurados en config.py, y avisa
por WhatsApp cuando encuentra disponibilidad.

Puede ejecutarse continuamente en una computadora o una sola vez con
``python bot.py --once`` (modo usado por GitHub Actions).
"""

import time
import sys
from datetime import datetime

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

import config
from notificador import enviar_whatsapp


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def login(page):
    """Inicia sesión con el usuario configurado en ingresar.aspx."""
    log("Iniciando sesión...")
    page.goto(config.URL_LOGIN, wait_until="domcontentloaded")

    # El formulario tiene 2 campos: DNI/mail y contraseña.
    # AJUSTAR SI HACE FALTA: si esto falla, abrí la página con HEADLESS=False,
    # click derecho sobre el campo de "DNI o mail" -> Inspeccionar, y fijate
    # el name/id real del <input> (suele ser algo como
    # "ctl00$Contenido$txtDni" en sitios ASP.NET como este).
    campos_texto = page.locator("input[type='text']")
    page.locator("input[type='password']").wait_for(timeout=10000)

    campos_texto.first.fill(config.USUARIO_EMAIL)
    page.locator("input[type='password']").first.fill(config.USUARIO_PASSWORD)

    # El botón "INGRESAR" es un link que dispara un __doPostBack (ASP.NET).
    page.click("text=INGRESAR")

    page.wait_for_load_state("networkidle")
    log("Sesión iniciada (verificar visualmente la primera vez).")


def buscar_funcion(page):
    """
    Navega directamente a la URL de la película/cine configurada
    (FILM_URL), clickea la pestaña del día correspondiente a config.FECHA,
    y espera a que carguen los horarios disponibles.
    Devuelve True si encontró al menos una función.
    """
    log(f"Abriendo página de '{config.PELICULA}' en '{config.CINE}'...")
    page.goto(config.FILM_URL, wait_until="domcontentloaded")

    # La cartelera se carga por AJAX desde api.voyalcine.net. Esperamos una
    # señal real de que terminó: o aparecen botones de fecha, o el error pasa
    # a estar visible. El nodo de error siempre existe en el HTML, oculto, por
    # eso no alcanza con comprobar count(): daba un falso negativo siempre.
    fechas = page.locator("button.op_day")
    error_visible = page.locator("#op_error:visible")
    try:
        fechas.first.wait_for(state="visible", timeout=15000)
    except PWTimeout:
        if error_visible.count() > 0:
            log("El sitio dice: 'No se encontraron funciones para esta película'.")
        else:
            log("La cartelera no terminó de cargar (posible fallo de la API del sitio).")
        return False

    # Cada botón contiene la fecha ISO completa en value. Esto es más preciso
    # que buscar solo el texto DD/MM y evita coincidencias con otros elementos.
    pestana_fecha = page.locator(f"button.op_day[value='{config.FECHA}']")
    if pestana_fecha.count() == 0:
        disponibles = fechas.evaluate_all("els => els.map(e => e.value)")
        rango = f"{disponibles[0]} a {disponibles[-1]}" if disponibles else "ninguna"
        log(f"No se encontró la fecha {config.FECHA}. Fechas publicadas: {rango}.")
        return False

    pestana_fecha.click()

    if error_visible.count() > 0:
        log("El sitio dice: 'No se encontraron funciones para esta película' ese día.")
        return False

    return True


def elegir_horario(page):
    """
    Dentro de la página de la película, hace click en el horario deseado
    (o en el primero disponible si HORARIO_DESEADO es None) y entra a
    la pantalla de selección de butacas.
    """
    # El sitio muestra cada cine como un acordeón inicialmente cerrado.
    # Aunque el botón de horario ya existe en el DOM, no es clickeable hasta
    # abrir primero el encabezado del cine.
    cine_loc = page.locator("#op_cinemas > h3").filter(has_text=config.CINE)
    if cine_loc.count() == 0:
        log(f"No se encontró el cine '{config.CINE}' para esa fecha.")
        return False
    cine_loc.first.click()

    if config.HORARIO_DESEADO:
        horario_loc = page.locator(
            "button.op_perf:visible, button.op_perf_am:visible"
        ).filter(has_text=config.HORARIO_DESEADO)
    else:
        horario_loc = page.locator("button.op_perf:visible, button.op_perf_am:visible")

    if horario_loc.count() == 0:
        log("No hay horarios disponibles para elegir todavía.")
        return False

    horario_loc.first.click()

    # Elegir una hora abre un modal de confirmación; el cambio de página recién
    # ocurre al confirmar. Esperamos el botón y hacemos ese segundo click.
    confirmar = page.locator("#modalConfirmButton:visible")
    confirmar.wait_for(state="visible", timeout=10000)
    confirmar.click()
    page.wait_for_load_state("domcontentloaded")
    return True


def elegir_entradas(page):
    """Selecciona el tipo/cantidad mínimos necesarios para abrir el mapa."""
    filas_precio = page.locator("#ctl00_Contenido_gridPrices tr")
    fila_precio = filas_precio.filter(has_text=config.TIPO_ENTRADA)

    if fila_precio.count() == 0:
        opciones = filas_precio.locator("select").evaluate_all(
            "els => els.map(e => e.closest('tr').innerText.trim().split('\\n')[0])"
        )
        log(
            f"No se encontró el tipo de entrada '{config.TIPO_ENTRADA}'. "
            f"Opciones: {', '.join(opciones) or 'ninguna'}."
        )
        return False

    cantidad = str(config.CANTIDAD_ENTRADAS)
    selector_cantidad = fila_precio.first.locator("select")
    valores = selector_cantidad.locator("option").evaluate_all(
        "els => els.map(e => e.value)"
    )
    if cantidad not in valores:
        log(f"La cantidad {cantidad} no está disponible para '{config.TIPO_ENTRADA}'.")
        return False

    selector_cantidad.select_option(cantidad)
    continuar = page.locator("#ctl00_Contenido_btnContinue")
    continuar.click()
    page.wait_for_load_state("domcontentloaded")

    if "butacas.aspx" not in page.url:
        log("El sitio no avanzó al mapa de butacas después de elegir la entrada.")
        return False
    return True


def chequear_fila(page) -> bool:
    """
    Ya parado en la pantalla del mapa de butacas, revisa si hay algún
    asiento LIBRE en la fila deseada. Devuelve True si encontró.
    """
    fila = config.FILA_DESEADA
    deseados = getattr(config, "ASIENTOS_DESEADOS", [])

    # Showcase codifica la ubicación en title ("C-16") y el estado en la
    # imagen del input: AvSeat.jpg = disponible; SoldSeat.jpg = vendido.
    # Leemos el mapa completo para que ASIENTOS_DESEADOS sea independiente de
    # FILA_DESEADA y admita incluso asientos de filas distintas.
    asientos_mapa = page.locator("input[type='image'][title]")
    estado_asientos = asientos_mapa.evaluate_all(
        "els => Object.fromEntries(els.map(e => [e.title, "
        "!e.disabled && (e.getAttribute('src') || '')"
        ".toLowerCase().endsWith('/avseat.jpg')]))"
    )
    if deseados:
        faltantes = [asiento for asiento in deseados if asiento not in estado_asientos]
        if faltantes:
            log(f"No existen en el mapa: {', '.join(faltantes)}.")
            return False

        ocupados = [asiento for asiento in deseados if not estado_asientos[asiento]]
        if ocupados:
            log(f"Asientos deseados ocupados: {', '.join(ocupados)}.")
            return False

        log(f"¡Están libres juntos: {', '.join(deseados)}!")
        return True

    estado_fila = {
        asiento: libre
        for asiento, libre in estado_asientos.items()
        if asiento.startswith(f"{fila}-")
    }
    total = len(estado_fila)
    if total == 0:
        log(f"No se encontraron asientos para la fila {fila}.")
        return False

    libres = sum(estado_fila.values())
    log(f"Fila {fila}: {libres} de {total} asientos libres.")
    return libres >= config.CANTIDAD_ENTRADAS


def ciclo_de_chequeo(page) -> bool:
    """Un ciclo completo: buscar función, entrar al mapa, chequear fila."""
    try:
        if not buscar_funcion(page):
            return False
        if not elegir_horario(page):
            return False
        if not elegir_entradas(page):
            return False
        return chequear_fila(page)
    except PWTimeout as e:
        log(f"Timeout esperando un elemento: {e}")
        return False
    except Exception as e:
        log(f"Error inesperado durante el chequeo: {e}")
        return False


def main():
    faltantes = config.variables_privadas_faltantes()
    if faltantes:
        log(f"Faltan variables privadas: {', '.join(faltantes)}")
        return 2

    ejecutar_una_vez = "--once" in sys.argv

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=config.HEADLESS)
        context = browser.new_context()
        page = context.new_page()

        try:
            login(page)
        except Exception as e:
            log(f"No se pudo iniciar sesión: {e}")
            log("Revisá los selectores de la función login() y volvé a intentar.")
            browser.close()
            return 1

        ya_avisado = False

        if ejecutar_una_vez:
            log("Monitor iniciado en modo de una sola revisión.")
        else:
            log(
                f"Bot iniciado. Revisando cada {config.INTERVALO_MINUTOS} minutos. "
                "Ctrl+C para salir."
            )

        while True:
            encontro = ciclo_de_chequeo(page)
            notificacion_enviada = False

            if encontro and not ya_avisado:
                deseados = getattr(config, "ASIENTOS_DESEADOS", [])
                asientos_mensaje = (
                    ", ".join(deseados) if deseados
                    else f"fila {config.FILA_DESEADA}"
                )
                mensaje = (
                    f"🎬 ¡Hay asientos libres!\n"
                    f"Película: {config.PELICULA}\n"
                    f"Cine: {config.CINE}\n"
                    f"Fecha: {config.FECHA}\n"
                    f"Horario: {config.HORARIO_DESEADO or 'cualquiera'}\n"
                    f"Asientos: {asientos_mensaje}"
                )
                if enviar_whatsapp(mensaje):
                    log("Notificación de WhatsApp enviada.")
                    notificacion_enviada = True
                    ya_avisado = True  # evita spamear; sacá esta línea si querés aviso repetido
            elif not encontro:
                log("Todavía sin asientos libres en esa fila. Reintentando más tarde.")

            if ejecutar_una_vez:
                # El código 10 le indica al workflow que hubo aviso y que debe
                # desactivarse para no mandar el mismo WhatsApp cada 10 minutos.
                if encontro and not notificacion_enviada:
                    return 1
                return 10 if notificacion_enviada else 0

            time.sleep(config.INTERVALO_MINUTOS * 60)


if __name__ == "__main__":
    sys.exit(main())
