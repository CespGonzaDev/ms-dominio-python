# ms-dominio-python — MS2 Dominio (SkillGrow)

Microservicio del **dominio** de SkillGrow: catálogo de áreas y habilidades, servicios de mentoría, descubrimiento, reseñas y reportes/administración.

| | |
|---|---|
| Stack | Python 3.12 · FastAPI · Pydantic v2 · httpx |
| Datos | Azure Cosmos DB (API NoSQL, 5 contenedores) |
| Hosting | Azure App Service (Linux) |
| Entrada pública | Solo vía Azure API Management: `https://skillgrow-org.azure-api.net/dominio/v1/...` |

## Endpoints implementados

Rutas internas; en APIM se publican con el prefijo `/dominio` (ej. `/dominio/v1/services`). Todas (salvo `/health` y `/v1/health`) exigen identidad propagada por APIM (`X-User-Id` y `X-User-Role`).

### Salud y catálogo

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/v1/health` (y `/health`) | Salud del servicio y timestamp `*EpochMs` |
| GET | `/v1/catalog/areas` | Áreas de conocimiento (`14` en seed Fase I) |
| GET | `/v1/catalog/skills` | Habilidades (`?areaId=&search=`) |

### Servicios de mentoría

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/v1/services` | Búsqueda pública (`search, skillId, areaId, mentorId, modality, type, minRating, priceMax, free, day, sort, page, pageSize`) |
| GET | `/v1/me/services` | Servicios del usuario autenticado (`Page[ServiceOut]`, consulta de una sola partición) |
| GET | `/v1/services/{id}` | Detalle del servicio (lo consume también `ms-core` al reservar) |
| POST | `/v1/services` | Crear servicio (`201`). `mentorId` proviene de `X-User-Id` |
| PUT | `/v1/services/{id}` | Reemplazar campos editables (solo dueño, si no `403`) |
| PATCH | `/v1/services/{id}/status` | Cambiar estado `activo \| inactivo` (solo dueño) |
| DELETE | `/v1/services/{id}` | Eliminar servicio (`204`, solo dueño) |

### Descubrimiento

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/v1/mentors` | Directorio de mentores (`search, areaId, skillId, minRating, page, pageSize`) |
| GET | `/v1/feed` | Feed mixto (`service` / `mentor`), excluye servicios propios |
| GET | `/v1/recommendations` | Hasta 10 servicios recomendados usando historial de búsqueda e intereses de `ms-core` |
| POST | `/v1/me/search-history` | Registrar búsqueda del usuario (`204`) |

### Reseñas y calificaciones

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/v1/sessions/{id}/review` | Crear reseña (`201`). Valida participante y estado `completada` en `ms-core` y recalcula el promedio del mentor |
| GET | `/v1/users/{id}/reviews` | Reseñas visibles de un mentor (`?rating=&page=&pageSize=`) |
| GET | `/v1/users/{id}/rating-summary` | Promedio, conteo y distribución `1..5` |

### Reportes y administración

| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| POST | `/v1/reports` | Usuario | Crear reporte sobre `user`, `service` o `review` (`201`) |
| GET | `/v1/admin/services` | Admin | Moderación de servicios (`search, status, reported`) con `reportsCount` |
| PATCH | `/v1/admin/services/{id}/status` | Admin | Activar/desactivar servicio con motivo obligatorio |
| GET | `/v1/admin/reports` | Admin | Bandeja de reportes (`status, targetType, search`) |
| PATCH | `/v1/admin/reports/{id}` | Admin | Actualizar estado/resolución y ejecutar acción (`desactivar_servicio`, `ocultar_resena`, `suspender_usuario`) |
| GET | `/v1/admin/stats` | Admin | Totales de servicios, reseñas y top 5 áreas |

## Arquitectura (capas desacopladas)

```text
routes (app/api/routes) → services (app/services) → repositories (app/repositories)
                             ↑ schemas (Pydantic v2)      ↑ única capa que importa azure.cosmos
clients (app/clients/core_client.py) → llamadas síncronas vía APIM a ms-core
core: config · security (mTLS APIM + headers JWT) · errors (formato estándar)
```

## Cómo correrlo en local

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env        # APIM_CERT_CHECK=false en local
uvicorn app.main:app --reload
```

- Salud: <http://localhost:8000/health>
- Swagger: <http://localhost:8000/docs>

Tests, lint y OpenAPI:

```powershell
pytest -q
ruff check .
python -m scripts.export_openapi   # actualiza docs/openapi.json para importar en APIM
```

Pruebas de integración contra el emulador local de Cosmos DB (Docker):

```powershell
docker run -d --name cosmos-emulator -p 8081:8081 -p 1234:1234 mcr.microsoft.com/cosmosdb/linux/azure-cosmos-emulator:vnext-preview
$env:COSMOS_ENDPOINT="http://localhost:8081"
$env:COSMOS_KEY="C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw=="
$env:COSMOS_DATABASE="skillgrow"
python -m scripts.seed_cosmos --fixtures-dir data/seed/fase1
pytest -q
```

## Variables de entorno

Ver [.env.example](.env.example). Los valores reales viven en **App Service → Configuration** y en **GitHub Secrets**.

| Variable | Uso |
|---|---|
| `COSMOS_ENDPOINT`, `COSMOS_KEY`, `COSMOS_DATABASE` | Conexión a Azure Cosmos DB (`skillgrow`) |
| `APIM_CERT_CHECK` | `true` en Azure; `false` solo en local/tests |
| `APIM_CERT_THUMBPRINT` | Huella SHA-1 del certificado cliente de APIM |
| `CORE_API_URL`, `APIM_SUBSCRIPTION_KEY` | Llamadas síncronas a `ms-core` vía APIM |

## Seguridad

1. **Red:** restricción de acceso en App Service para aceptar únicamente la IP de APIM.
2. **Certificado mutuo (mTLS):** `clientCertMode=Required` + validación de huella SHA-1 de `X-ARR-ClientCert` en [security.py](app/core/security.py) (incluye `/health`; falla cerrado con `403` si falta configuración).
3. **Identidad:** APIM valida el JWT emitido por `ms-core` y propaga `X-User-Id` y `X-User-Role`; el backend nunca decodifica el token ni confía en IDs enviados en el body.

## Modelo de datos y justificación (Cosmos DB NoSQL)

Se eligió **Azure Cosmos DB (API NoSQL)** para MS2 porque el catálogo de mentorías, reseñas, reportes e historial de búsqueda tienen esquemas flexibles/anidados (área, lista de habilidades, precios opcionales, objeto `mentor` desnormalizado) y consultas orientadas a lectura rápida con baja latencia sin joins relacionales.

| Contenedor | Partition key | Justificación de particionamiento |
|---|---|---|
| `catalog` | `/type` | Agrupa áreas (`area`) y habilidades (`skill`) en dos particiones limpias para lectura completa en 1 consulta |
| `services` | `/mentorId` | Todas las operaciones del dueño (`/v1/me/services`, recálculo de rating del mentor) van a una sola partición |
| `reviews` | `/mentorId` | Las reseñas y el resumen de calificación siempre se consultan por mentor en una única partición |
| `reports` | `/status` | La bandeja de moderación filtra por estado (`pendiente`, `en_revision`, `resuelto`, `descartado`). Al cambiar el `status` de un reporte, el repositorio crea el documento en la nueva partición y luego elimina el anterior (`create-before-delete`) porque Cosmos no permite mutar la partition key con `replace_item` |
| `searchHistory` | `/userId` | Aísla las búsquedas recientes por usuario para alimentar `/v1/recommendations` en 1 partición |

## Despliegue y Postman

- Pipeline en [.github/workflows/ci-cd.yml](.github/workflows/ci-cd.yml): `ruff` + `pytest` en cada PR; en push a `main` despliega a `app-skillgrow-dominio-kay` y verifica `/dominio/v1/health` vía APIM.
- Secrets requeridos en GitHub: `AZURE_WEBAPP_PUBLISH_PROFILE`, `APIM_BASE_URL`, `APIM_SUBSCRIPTION_KEY`.
- Comando de arranque en App Service: `gunicorn -k uvicorn.workers.UvicornWorker app.main:app`.
- Colección Postman lista para unir con `unir-colecciones.py`: [docs/postman/03-MS2-Dominio.postman_collection.json](docs/postman/03-MS2-Dominio.postman_collection.json).
