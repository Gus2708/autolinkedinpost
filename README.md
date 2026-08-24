# 🚀 Auto LinkedIn Post Generator (Daily Project-Segmented Posts)

Sistema automatizado con **GitHub Actions** que revisa diariamente tu actividad técnica en GitHub, detecta si hay cambios relevantes y genera posts independientes para **LinkedIn** segmentados por cada repositorio/proyecto activo usando **Google Gemini** (con prompts anti-clichés de IA y sugerencias visuales), enviándotelos directamente a **Telegram**.

---

## 🏛️ Arquitectura del Flujo Diario

```text
[ GitHub Actions Cron ] (Diario a las 21:00 UTC)
         │
         ▼
[ 1. GitHub API Extractor ] ──► Revisa actividad de las últimas 24 horas
         │                      (Si no hay actividad nueva, finaliza en silencio)
         ▼
[ 2. Gemini 3.6 Flash ]     ──► Genera 1 Post enfocado + Sugerencia Visual por cada proyecto activo
         │
         ▼
[ 3. Telegram Bot Notifier] ──► Envía los borradores individuales a tu chat privado
```

---

## 🤖 Dos Modos de Operación

### 1. Novedades Diarias (GitHub Actions Cron)
- **Objetivo:** Detectar los commits técnicos de las últimas 24 horas y enviar posts independientes por proyecto activo.
- **Ejecución:** Totalmente desatendida en GitHub Actions todos los días a las 21:00 UTC (o manual con `workflow_dispatch`).

### 2. Showcase de Portafolio / Reclutadores (Bot Interactivo de Telegram)
- **Objetivo:** Analizar un repositorio completo (README, arquitectura, archivos clave, stack y trade-offs) para generar un post técnico de alto calibre que demuestre tu nivel como Senior / Tech Lead a reclutadores y Engineering Managers.
- **Cómo usarlo:**
  1. Ejecutá el bot en tu máquina o servidor:
     ```bash
     python bot.py
     ```
  2. En Telegram con `@DinBot`, escribí `/menu` o `/proyectos`.
  3. Tocá el botón interactivo del repositorio que quieras mostrar y recibí el post completo al instante.

---

## ☁️ Deploy 24/7 en Render (100% Gratis)

Para que el menú interactivo de Telegram funcione **siempre desde tu celular** sin tener tu computadora encendida:

1. Subí este repositorio a tu cuenta de GitHub.
2. Entrá a tu dashboard de [Render](https://dashboard.render.com/).
3. Hacé clic en **New +** ➔ **Blueprint** (o **Web Service**) y seleccioná tu repositorio.
4. Render leerá automáticamente el archivo [`render.yaml`](file:///g:/Projects/autolinkedinpost/render.yaml).
5. Completá las variables de entorno (`GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `GH_USERNAME`).
6. ¡Listo! El bot quedará escuchando 24/7 en la nube en el Free Tier de Render.

---

## ⚙️ Configuración Paso a Paso

### 1. Bot de Telegram
- **`TELEGRAM_BOT_TOKEN`**: Obtenido de [@BotFather](https://t.me/BotFather).
- **`TELEGRAM_CHAT_ID`**: Tu ID numérico obtenido de [@userinfobot](https://t.me/userinfobot).

### 2. Google Gemini
- **`GEMINI_API_KEY`**: Clave gratuita de [Google AI Studio](https://aistudio.google.com/).

### 3. Secretos en GitHub Actions
En tu repositorio: **Settings ➔ Secrets and variables ➔ Actions ➔ New repository secret**:

| Nombre del Secreto | Descripción | Obligatorio |
|---|---|:---:|
| `GEMINI_API_KEY` | Tu API Key de Google AI Studio | **Sí** |
| `TELEGRAM_BOT_TOKEN` | Token de tu bot de Telegram | **Sí** |
| `TELEGRAM_CHAT_ID` | Tu ID de chat en Telegram | **Sí** |
| `GH_USERNAME` | Tu nombre de usuario en GitHub | **Sí** |
| `GH_TOKEN` | Personal Access Token (PAT) con permisos `repo` (para repos privados) | Opcional |

---

## 🧪 Pruebas en Local

1. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Revisión del día de hoy:**
   ```bash
   python main.py
   ```

3. **Revisión de los últimos N días:**
   ```bash
   python main.py --days 7
   ```

4. **Prueba simulada con datos mock:**
   ```bash
   python main.py --mock --dry-run
   ```

---

## ⏱️ Programación Diaria

- El cron se ejecuta todos los días a las **21:00 UTC** (18:00 ARG / 15:00 CDMX).
- Si en las últimas 24 horas no hiciste commits relevantes, no te llena el chat de spam; simplemente se apaga.
- Podés forzar la ejecución manual en cualquier momento desde la pestaña **Actions** en GitHub.

---

## 📄 Licencia
MIT
