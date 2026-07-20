# Monitor de asientos de Showcase

Comprueba periódicamente una película, fecha, horario y asientos exactos de
Showcase Cinemas Argentina. Cuando todos están disponibles, envía un WhatsApp.
No selecciona butacas ni inicia una compra.

## Configurar la búsqueda

Los datos no sensibles se editan en `config.py`:

- `FILM_URL`, `PELICULA` y `CINE`.
- `FECHA` y `HORARIO_DESEADO`.
- `ASIENTOS_DESEADOS`, por ejemplo `["J-18", "J-19"]`.
- `TIPO_ENTRADA` y `CANTIDAD_ENTRADAS`.

La cantidad de entradas debe coincidir con la cantidad de asientos exactos.

## Ejecutarlo gratis con GitHub Actions

### 1. Crear el repositorio

Creá un repositorio **público** vacío en GitHub. El código puede ser público
porque las credenciales ya no están guardadas en ningún archivo. No agregues
un README ni `.gitignore` desde GitHub porque este proyecto ya los incluye.

Desde esta carpeta, ejecutá los comandos que GitHub muestra bajo
"push an existing repository from the command line". Normalmente son:

```bash
git init
git add .
git commit -m "Configurar monitor de asientos"
git branch -M main
git remote add origin URL_DE_TU_REPOSITORIO
git push -u origin main
```

La carpeta `venv` y cualquier archivo `.env` están excluidos por `.gitignore`.

### 2. Crear los cuatro secretos

En el repositorio, abrí:

`Settings` → `Secrets and variables` → `Actions` → `New repository secret`

Creá exactamente estos cuatro secretos:

| Nombre | Valor |
|---|---|
| `SHOWCASE_USUARIO` | DNI o email usado para entrar a Showcase |
| `SHOWCASE_PASSWORD` | Contraseña de Showcase |
| `WHATSAPP_TELEFONO` | Número completo, sin `+` ni espacios |
| `CALLMEBOT_APIKEY` | API key entregada por CallMeBot |

Los valores de los secretos no aparecen en el repositorio ni en los logs.

### 3. Probar y activar

1. Abrí la pestaña `Actions` del repositorio.
2. Elegí `Monitor de asientos`.
3. Presioná `Run workflow` para probarlo inmediatamente.
4. Abrí la ejecución para comprobar los mensajes del bot.

Después se ejecutará automáticamente cada diez minutos. Las pruebas iniciadas
con `Run workflow` no desactivan la programación. Cuando una revisión automática
encuentre todos los asientos y envíe el WhatsApp, el workflow se desactivará para
no repetir el mensaje. Para una búsqueda nueva, editá `config.py` y después usá
`Actions` → `Monitor de asientos` → `Enable workflow`.

GitHub puede demorar ocasionalmente una ejecución programada. En repositorios
públicos también desactiva los workflows programados que pasan 60 días sin
actividad en el repositorio.

## Ejecución local opcional

Instalación:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

Antes de ejecutarlo localmente, definí las mismas variables privadas:

```bash
export SHOWCASE_USUARIO="tu_usuario"
export SHOWCASE_PASSWORD="tu_password"
export WHATSAPP_TELEFONO="tu_numero"
export CALLMEBOT_APIKEY="tu_api_key"
```

Una sola revisión:

```bash
python bot.py --once
```

Ejecución continua cada diez minutos:

```bash
python bot.py
```

Para ver el navegador durante una prueba local:

```bash
HEADLESS=false python bot.py --once
```
