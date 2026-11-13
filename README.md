# ms-dominio-python — MS2 Dominio (SkillGrow)

Microservicio del **dominio** de SkillGrow: catálogo de áreas y habilidades, servicios de mentoría, descubrimiento, reseñas y reportes/administración.

| | |
|---|---|
| Stack | Python 3.12 · FastAPI · Pydantic v2 |
| Datos | Azure Cosmos DB (API NoSQL) |
| Hosting | Azure App Service (Linux) |
| Entrada pública | Solo vía Azure API Management: `https://skillgrow-org.azure-api.net/dominio/v1/...` |

> Estado: **Fase B** (catálogo + CRUD y búsqueda de servicios). Descubrimiento, reseñas y reportes se agregan en la fase C.

## Endpoints

Rutas internas; en APIM se publican con el prefijo `/dominio` (ej. `/dominio/v1/services`). Todas (salvo `health`) exigen `X-User-Id`, que APIM extrae del JWT.

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/v1/health` (y `/health`) | Salud |
| GET | `/v1/catalog/areas` | Áreas |
| GET | `/v1/catalog/skills?areaId=` | Habilidades |
| GET | `/v1/services` | Búsqueda: `search, skillId, areaId, modality, type, minRating, priceMax, free, day, sort (recent\|rating\|priceAsc\|priceDesc), page, pageSize`. Solo servicios `active`. Respuesta `{ totalRecords, page, pageSize, items }` |
| GET | `/v1/services/{id}` | Detalle (cualquier estado; lo usa MS1 al reservar) |
| GET | `/v1/me/services` | Servicios del usuario |
| POST | `/v1/services` | Crear (201). El mentor sale de `X-User-Id`, nunca del body |
| PUT | `/v1/services/{id}` | Reemplazar campos editables (solo el dueño, si no 403) |
| PATCH | `/v1/services/{id}/status` | `active \| paused \| inactive` (solo el dueño) |
| DELETE | `/v1/services/{id}` | 204 (solo el dueño) |

### Supuestos que hay que confirmar contra la Fase I

La forma de un servicio (campos, valores de `type`/`modality`, formato de `availableDays`, valores de `sort`) se dedujo del reparto; el contrato real de la Fase I no estaba disponible. Ver [app/schemas/service.py](app/schemas/service.py).

## Arquitectura (capas simples)

```
routes (app/api) → services (lógica) → repositories (Cosmos)
                       ↑ schemas (Pydantic)      ↑ única capa que importa azure.cosmos
core: config · security (mTLS APIM) · errors (formato estándar)
```

## Cómo correrlo en local

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env        # completar valores; APIM_CERT_CHECK=false en local
uvicorn app.main:app --reload
```

- Salud: <http://localhost:8000/health>
- Swagger: <http://localhost:8000/docs>

Tests y lint:

```powershell
pytest -q
ruff check .
python -m scripts.export_openapi   # genera docs/openapi.json para importar en APIM
```

Pruebas de integración contra el emulador local de Cosmos DB (Docker):

```powershell
docker run -d --name cosmos-emulator -p 8081:8081 -p 1234:1234 mcr.microsoft.com/cosmosdb/linux/azure-cosmos-emulator:vnext-preview
$env:COSMOS_ENDPOINT="http://localhost:8081"
$env:COSMOS_KEY="C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw=="
$env:COSMOS_DATABASE="skillgrow"
python -m scripts.seed_cosmos --fixtures-dir data/seed/sample
pytest -q
```

## Variables de entorno

Ver [.env.example](.env.example). Los valores reales viven en **App Service → Configuration** (o Key Vault) y en **GitHub Secrets**; nunca en el repo.

| Variable | Uso |
|---|---|
| `COSMOS_ENDPOINT`, `COSMOS_KEY`, `COSMOS_DATABASE` | Conexión a Cosmos DB |
| `APIM_CERT_CHECK` | `true` en Azure; `false` solo en local/tests |
| `APIM_CERT_THUMBPRINT` | Huella SHA-1 del certificado de cliente de APIM |
| `CORE_API_URL`, `APIM_SUBSCRIPTION_KEY` | Llamada a MS1 al crear reseñas |

## Seguridad

1. **Red:** access restriction en App Service, solo la IP de APIM.
2. **Certificado:** `clientCertMode=Required` + este servicio compara la huella SHA-1 de `X-ARR-ClientCert` con `APIM_CERT_THUMBPRINT` ([security.py](app/core/security.py)). Aplica a **todas** las rutas, `/health` incluido; si falta configuración falla cerrado (403).
3. **Identidad:** APIM valida el JWT y envía `X-User-Id` (y `X-User-Role`); el backend no decodifica el token.

## Convenciones (doc 03)

- JSON en camelCase; fechas siempre como **epoch en milisegundos** (`*EpochMs`, `int`); IDs UUID v4.
- Errores: `{ code, message, details[], timestampEpochMs, path }` — nunca se devuelve el stack trace.

## Modelo de datos (Cosmos DB)

| Contenedor | Partition key | Motivo |
|---|---|---|
| `catalog` | `/type` | Leer todas las áreas o habilidades en una partición |
| `services` | `/mentorId` | Gestión por dueño agrupada |
| `reviews` | `/mentorId` | Reseñas y resumen siempre por mentor |
| `reports` | `/status` | Bandeja de moderación por estado |
| `searchHistory` | `/userId` | Historial aislado por usuario |

Crear la estructura y cargar datos: `python -m scripts.seed_cosmos --fixtures-dir data/seed/sample` (requiere credenciales en `.env`). `data/seed/sample` son datos de **ejemplo**; los fixtures reales de la Fase I se exportan a JSON con el mismo formato.

## Despliegue

Pipeline en [.github/workflows/ci-cd.yml](.github/workflows/ci-cd.yml): lint + tests en cada PR; en push a `main` despliega a App Service y hace *smoke test* de `/dominio/v1/health` **vía APIM**.

Secrets del repo: `AZURE_WEBAPP_PUBLISH_PROFILE`, `APIM_BASE_URL`, `APIM_SUBSCRIPTION_KEY`.
Comando de arranque en App Service: `gunicorn -k uvicorn.workers.UvicornWorker app.main:app`.

## Flujo de trabajo

`main` protegida; ramas `feat/*`, `fix/*`, `docs/*`; commits convencionales; PRs pequeños con la [plantilla](.github/pull_request_template.md).
