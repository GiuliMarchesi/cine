import urllib.parse
import requests

from config import WHATSAPP_TELEFONO, CALLMEBOT_APIKEY


def enviar_whatsapp(mensaje: str) -> bool:
    """
    Envía un mensaje de WhatsApp usando la API gratuita de CallMeBot.
    Requiere haber vinculado el número una sola vez (ver instrucciones en config.py).
    """
    texto = urllib.parse.quote(mensaje)
    url = (
        f"https://api.callmebot.com/whatsapp.php?"
        f"phone={WHATSAPP_TELEFONO}&text={texto}&apikey={CALLMEBOT_APIKEY}"
    )
    try:
        resp = requests.get(url, timeout=15)
        print(f"[WhatsApp] status={resp.status_code} resp={resp.text[:200]}")
        return resp.status_code == 200
    except Exception as e:
        print(f"[WhatsApp] Error enviando mensaje: {e}")
        return False
