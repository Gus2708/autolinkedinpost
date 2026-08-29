# Ejecución programada confiable

## El problema

El evento `schedule` de GitHub Actions es **best-effort**. La documentación de GitHub
advierte que los disparos pueden retrasarse o descartarse cuando la plataforma está
bajo carga, y no ofrece garantía de ejecución.

Medición real en este repositorio, entre el 24 y el 28 de agosto de 2026 con el cron
configurado a diario:

| Día | Disparo automático |
|-----|--------------------|
| 24 ago | ✅ con 16 min de retraso |
| 25 ago | ✅ con 15 min de retraso |
| 26 ago | ❌ descartado |
| 27 ago | ⚠️ más de 3 horas de retraso |
| 28 ago | ❌ descartado |

**Tres disparos sobre cinco esperados.** Mover el cron fuera del minuto 0 (de `0 21` a
`20 21`) no corrigió el problema: el primer disparo con el horario nuevo también se perdió.

## La solución

Invertir quién decide el momento. Un scheduler externo con garantías reales invoca
`workflow_dispatch` por API, y GitHub Actions queda sólo como ejecutor.

El cron de GitHub se mantiene como respaldo. El step `Evitar ejecuciones duplicadas`
del workflow impide que ambas fuentes publiquen dos veces el mismo día.

```
┌──────────────────┐   POST /dispatches   ┌─────────────────┐
│ Scheduler externo├─────────────────────►│ GitHub Actions  │
│ (garantiza hora) │                      │  (sólo ejecuta) │
└──────────────────┘                      └─────────────────┘
         ▲
         │  el cron de GitHub sigue activo como respaldo,
         └─ el guard de duplicados evita la doble publicación
```

## Configuración

### 1. Crear el token

En [Fine-grained tokens](https://github.com/settings/personal-access-tokens/new):

- **Repository access**: sólo este repositorio.
- **Permissions → Actions**: `Read and write`.
- **Expiration**: la que prefieras, con recordatorio de renovación.

Copiá el token: no se vuelve a mostrar.

> El token permite disparar workflows en este repositorio. Guardalo como secreto en el
> scheduler, nunca en el código.

### 2. Configurar el disparo

Cualquier servicio que haga un POST HTTP sirve. Ejemplo con
[cron-job.org](https://cron-job.org) (gratuito, sin tarjeta):

| Campo | Valor exacto |
|-------|--------------|
| **Title** | `AutoLinkedInPost diario` |
| **URL** | `https://api.github.com/repos/Gus2708/autolinkedinpost/actions/workflows/daily_linkedin_post.yml/dispatches` |
| **Schedule** | Every day at `18:20` (ajustá a tu huso; el cron de respaldo dispara 21:20 UTC) |
| **Request method** | `POST` |

En la pestaña **Advanced → Headers**, tres entradas:

| Key | Value |
|-----|-------|
| `Authorization` | `Bearer TU_TOKEN` |
| `Accept` | `application/vnd.github+json` |
| `X-GitHub-Api-Version` | `2022-11-28` |

En **Request body**:

```json
{"ref":"main","inputs":{"days":"1"}}
```

`dry_run` y `force` quedan en su valor por defecto (`false`), que es lo que querés para
la corrida diaria: publica de verdad y respeta el guard de duplicados.

Activá **"Save responses in job history"** para poder auditar los disparos.

Una respuesta **HTTP 204** sin cuerpo significa que el disparo fue aceptado. cron-job.org
puede marcarlo como fallo por no traer contenido: si te deja elegir, tratá 204 como éxito.

### 3. Verificar

El repositorio incluye un script equivalente para probar el disparo desde tu máquina o
desde cualquier runner:

```bash
GH_PAT=ghp_tu_token REPO=tu_usuario/autolinkedinpost ./scripts/trigger_daily_run.sh
```

Confirmá que el disparo llegó:

```bash
gh run list --workflow=daily_linkedin_post.yml --limit 3
```

## Alternativas

| Servicio | Costo | Nota |
|----------|-------|------|
| [cron-job.org](https://cron-job.org) | Gratis | POST con headers custom, historial de ejecuciones |
| [Google Cloud Scheduler](https://cloud.google.com/scheduler) | 3 jobs gratis | Requiere proyecto de GCP |
| Render Cron Job | Pago | Útil si ya desplegás el bot ahí |
| Runner propio (`crontab`) | Gratis | Depende de que tu máquina esté encendida |

## El guard de duplicados

El workflow verifica, antes de hacer cualquier trabajo, si ya hubo una ejecución exitosa
en las últimas 11 horas. Si la hubo, sale sin publicar.

La ventana es de 11 horas para que dos ejecuciones diarias separadas por 24 horas nunca
se bloqueen entre sí, mientras que un disparo duplicado dentro del mismo día sí se corta.

Para publicar igual, ignorando el guard:

```bash
gh workflow run daily_linkedin_post.yml -f force=true
```

## Verificación posterior

Una vez configurado el disparador, confirmá que funciona:

```bash
gh run list --workflow=daily_linkedin_post.yml --limit 5
```

Buscá una fila con `workflow_dispatch` a la hora que programaste. Si no aparece:

| Síntoma | Causa probable |
|---------|----------------|
| HTTP 401 | Token vencido o mal copiado (debe incluir el prefijo `Bearer `) |
| HTTP 403 | Al token le falta el permiso `Actions: Read and write` |
| HTTP 404 | El repositorio no está en el alcance del token, o el nombre del workflow cambió |
| HTTP 422 | El body no es JSON válido, o `ref` apunta a una rama inexistente |
| 204 pero no aparece el run | El guard de duplicados lo cortó: ya hubo una corrida exitosa en las últimas 11 horas |

Para descartar el guard, mirá el log del run más reciente: el step
`Evitar ejecuciones duplicadas` dice explícitamente si omitió la corrida y por qué.
