# sigmoGPS

Plataforma web de monitoreo de flota conectada a la API remota de Wialon.

**Prueba técnica · GPS Control · Ingeniero Fullstack Junior · noviembre de 2026**

---

## 1. Descripción

sigmoGPS consume la API remota de Wialon y presenta la flota en una interfaz
operativa con control de acceso por roles. No replica el panel de Wialon: lo
traduce. Wialon entrega identificadores internos, marcas de tiempo en segundos
UNIX y campos sin unidad declarada; la aplicación entrega placas, horas locales,
kilómetros por hora y estados derivados.

**Qué hace**

| Módulo | Capacidad |
|---|---|
| Mapa | 65 unidades con agrupamiento de marcadores, estado derivado y refresco cada 10 s |
| Tablero | KPIs de la flota, composición por estado, cobertura de conductor y las unidades que exigen atención |
| Detalle de vehículo | última lectura convertida, conductor vinculado, pasajeros asignados, campos personalizados editables |
| Conductores | CRUD completo sobre Wialon y vínculo con vehículo |
| Pasajeros | CRUD sobre 101 registros reales con campos personalizados y asignación a unidad |
| Usuarios | CRUD, cambio de rol, restablecimiento de credenciales, activación |
| Auditoría | registro consultable de quién hizo qué, con filtros y paginación |
| Exportación | CSV de vehículos, conductores y pasajeros |

**Stack**

| Capa | Tecnología |
|---|---|
| Backend | FastAPI · Python 3.14 · SQLAlchemy 2 async · Alembic · PyJWT · argon2-cffi · structlog |
| Frontend | Nuxt 4 · Vue 3.5 · TypeScript estricto · Tailwind v4 · TanStack Query · Leaflet |
| Base de datos | PostgreSQL (Neon) |
| Despliegue | Render (API) · Vercel (interfaz) · Neon (base de datos) — los tres en plan gratuito |

### Capturas

> Pendiente de adjuntar: mapa, tablero, detalle de vehículo, conductores,
> pasajeros, usuarios y auditoría.

---

## 2. Enlaces

| Recurso | URL |
|---|---|
| Aplicación | https://sigmogps.vercel.app |
| API | https://sigmogps.vercel.app/api/v1 |
| Repositorio | https://github.com/davecoude/sigmogps |

La interfaz consume el API **desde su propio origen**. Nuxt reenvía `/api/**` al
backend mediante `routeRules`, así que las cookies de sesión son de primera
parte. Esto no es un detalle estético: Safari y Brave bloquean cookies de
terceros por defecto, y con CORS la sesión simplemente no persistía en esos
navegadores.

**Swagger está deshabilitado en producción a propósito** (SEG-05).
`docs_url` y `openapi_url` devuelven `None` cuando `APP_ENV=production`: la
documentación interactiva expone el inventario completo de endpoints y esquemas,
que es reconocimiento gratuito para un atacante. Para revisarla, levantar el
proyecto en local y abrir http://localhost:8000/docs.

### Credenciales de evaluación

Se entregan por separado en el correo de entrega, no en el repositorio.

---

## 3. Ejecución local

**Requisitos:** Python 3.14, Node 20 o superior, y una base PostgreSQL
accesible. Hace falta un token de la API de Wialon y su host.

### Backend

```bash
cd backend
python -m venv .venv

# Linux / macOS
source .venv/bin/activate
# Windows (Git Bash)
source .venv/Scripts/activate

pip install -r requirements.lock.txt
pip install -e ".[dev]"

cp ../.env.example .env     # completar DATABASE_URL, WIALON_TOKEN, SECRET_KEY, ADMIN_*

alembic upgrade head        # crea el esquema
python seed.py              # siembra roles, permisos y el Admin inicial

python run.py               # http://localhost:8000
```

`run.py` en vez de `uvicorn` directo por una razón concreta: Windows usa
`ProactorEventLoop` por defecto y psycopg no funciona sobre él. `run.py` fija
`WindowsSelectorEventLoopPolicy` **antes** de importar uvicorn y fuera del guard
`__main__`, para que el proceso hijo del recargador también la herede. En Render
corre Linux y se usa `uvicorn` directamente.

### Frontend

```bash
cd frontend
npm install
npm run dev                 # http://localhost:3000
```

### Pruebas

```bash
cd backend
pytest
```

---

## 4. Arquitectura

### Diagrama de componentes

```
┌─────────────────────────────────────────────────────────────────┐
│  NAVEGADOR                                                      │
│  Nuxt 4 · Vue 3 · TanStack Query · Leaflet                      │
│  Cookies HttpOnly de sesión + cookie CSRF legible               │
└───────────────────────────┬─────────────────────────────────────┘
                            │ mismo origen: /api/** → routeRules
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  VERCEL · proxy de Nuxt                                         │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTPS
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  RENDER · FastAPI                                               │
│                                                                 │
│   api/          traduce HTTP a casos de uso y de vuelta         │
│     │           deps.py: sesión, usuario, permisos, CSRF        │
│     ▼                                                           │
│   services/     casos de uso. Importan solo domain              │
│     │                                                           │
│     ▼                                                           │
│   domain/  ◄──  infrastructure/                                 │
│   modelos,      db/      → PostgreSQL                           │
│   puertos,      wialon/  → API remota de Wialon                 │
│   permisos,                                                     │
│   excepciones                                                   │
│                                                                 │
│   core/         transversal: config, logging, errores RFC 7807  │
└──────────┬──────────────────────────────────┬───────────────────┘
           │                                  │
           ▼                                  ▼
┌────────────────────────┐        ┌──────────────────────────────┐
│  NEON · PostgreSQL     │        │  WIALON · API remota         │
│  usuarios, roles,      │        │  unidades, conductores,      │
│  permisos, auditoría   │        │  pasajeros (tags), vínculos  │
└────────────────────────┘        └──────────────────────────────┘
```

**La regla de dependencia apunta hacia adentro:**

```
api → services → domain ← infrastructure
```

- `domain/` no importa nada de las otras capas. Contiene modelos propios,
  excepciones de negocio, el catálogo de permisos y los puertos (`Protocol`).
- `services/` importa solo `domain`. Son los casos de uso.
- `infrastructure/` implementa lo que el dominio declara: base de datos y Wialon.
- `api/` traduce HTTP a casos de uso y de vuelta.
- `core/` es transversal: configuración, logging y formato de errores.

Sin esa regla serían carpetas decorativas. El pago concreto está en las pruebas:
como los servicios dependen de interfaces y no de clases concretas, simular
Wialon es una clase de diez líneas en vez de parchear HTTP.

**Se descartó** la estructura plana por recurso (`users.py`, `vehicles.py`)
porque mezcla reglas de negocio con detalles de transporte y hace imposible
probar sin levantar la aplicación entera.

### Modelo de datos

La base de datos guarda **solo lo que es nuestro**: identidad, autorización y
auditoría. Vehículos, conductores y pasajeros viven en Wialon y no se replican
(ver sección 9).

```
┌──────────────────┐        ┌────────────────────┐        ┌───────────────┐
│ users            │        │ role_permissions   │        │ permissions   │
├──────────────────┤        ├────────────────────┤        ├───────────────┤
│ id          UUID │◄──┐    │ role_id         FK │───────►│ id        int │
│ email     unique │   │    │ permission_id   FK │        │ code   unique │
│ password_hash    │   │    └────────────────────┘        │ description   │
│ full_name        │   │               ▲                  └───────────────┘
│ role_id       FK │───┼───────────────┘
│ is_active        │   │    ┌────────────────────┐
│ must_change_pass │   │    │ roles              │
│ token_version    │   │    ├────────────────────┤
│ failed_attempts  │   └───►│ id             int │
│ locked_until     │        │ name        unique │
│ last_login_at    │        │ description        │
│ created_at       │        └────────────────────┘
│ updated_at       │
└────────┬─────────┘
         │
         ▼
┌──────────────────────┐
│ audit_log            │
├──────────────────────┤
│ id              UUID │
│ user_id       FK NUL │  nulo a propósito: un intento de ingreso
│ user_email           │  fallido no tiene usuario autenticado
│ action         index │
│ entity_type          │
│ entity_id            │
│ success              │
│ detail         JSONB │
│ ip_address           │
│ user_agent           │
│ created_at     index │
└──────────────────────┘
```

**Por qué UUID en `users` y entero en `roles`.** El identificador de usuario
viaja en la URL. Con enteros secuenciales, cualquiera recorre `/users/1`,
`/users/2` y descubre cuántos usuarios hay y en qué orden se crearon. Con UUID no
hay nada que recorrer. `roles` y `permissions` son datos de referencia que
siembra el código: no se exponen por id y el entero es más barato de indexar en
la tabla puente.

**Por qué la convención de nombres en `base.py`.** Sin ella PostgreSQL inventa
los nombres de las *constraints* y Alembic genera migraciones de bajada que
fallan porque no encuentran el nombre que esperan. Con la convención, el nombre
es determinista.

---

## 5. Decisiones de arquitectura

### Principios SOLID aplicados

| Principio | Dónde | Cómo |
|---|---|---|
| Responsabilidad única | `core/security.py` | Solo hashea y valida política de contraseñas. No sabe de usuarios ni de sesiones |
| Abierto/cerrado | `domain/permissions.py` | Agregar un permiso es añadir una línea al enum y correr el seed. Ningún condicional cambia |
| Sustitución de Liskov | `domain/exceptions.py` | Todas las excepciones heredan de `DomainError` y el manejador global las trata igual |
| Segregación de interfaces | `api/deps.py` | `CurrentUser`, `VerifiedUser` y `require_permission` son tres contratos distintos; cada endpoint pide solo el que necesita |
| Inversión de dependencias | `domain/ports.py` + `api/deps.py` | Los servicios dependen de `Protocol`, no de clases concretas. La sesión de base de datos se inyecta, no se construye |

### Patrones de diseño

| Patrón | Dónde | Para qué |
|---|---|---|
| Repository | `infrastructure/wialon/repository.py` | Encapsula las llamadas a Wialon detrás de métodos con nombre de negocio |
| Adapter / Gateway | `infrastructure/wialon/client.py` | Traduce el protocolo de Wialon (parámetros JSON en query string, sesión por `sid`) a llamadas Python |
| Mapper | `infrastructure/wialon/mappers.py` | Convierte la respuesta cruda de Wialon en modelos de dominio |
| DTO | `api/v1/schemas/` | Los modelos Pydantic son el contrato del API. Nunca se devuelve un modelo de SQLAlchemy, por eso el hash de contraseña no puede filtrarse por accidente |
| Dependency Injection | `api/deps.py` | El sistema de dependencias de FastAPI resuelve sesión, usuario y permisos |
| Unit of Work | `infrastructure/db/session.py` | `get_session` confirma al terminar bien y revierte al fallar. Un endpoint no puede dejar media escritura aplicada |
| Factory | `main.py` → `create_app()` | Arma la aplicación; permite construir una instancia distinta en las pruebas |

### Otras decisiones

**`assert_production_ready()` al arrancar.** Falla al levantar, no en la primera
petición. Si en Render falta `SECRET_KEY` o `APP_DEBUG` quedó en `true`, el
proceso no arranca y el despliegue se marca como fallido. La alternativa
—descubrirlo cuando un usuario recibe un 500— es peor.

**`get_settings()` con `lru_cache`.** La configuración se lee del entorno una
sola vez por proceso. El caché la vuelve un *singleton* sin usar una variable
global mutable, y en las pruebas se limpia con `get_settings.cache_clear()`.

**Cotas mínimas en `pyproject.toml` y lockfile aparte** (SEG-06).
`pyproject.toml` declara qué se necesita; `requirements.lock.txt` declara qué se
instaló exactamente. El primero es el contrato, el segundo la reproducibilidad.
Render instala del lockfile, así que la versión probada es la que corre.

**`.python-version` con 3.14.** El entorno local y el de Render corren el mismo
intérprete, declarado en un archivo versionado que Render lee. Es paridad entre
desarrollo y producción sin depender de que alguien recuerde configurar una
variable.

**Errores en RFC 7807** (ARQ-04). `application/problem+json` es un estándar: el
frontend parsea `title`, `detail` y `errors` sin contratos inventados. Cada
respuesta incluye un `trace_id` que también viaja en la cabecera
`X-Request-Id`, así que un usuario reporta un error y se encuentra la línea
exacta en los logs.

---

## 6. Seguridad

### Controles por categoría OWASP Top 10 (2021)

| Categoría | Control implementado | Dónde |
|---|---|---|
| **A01 · Control de acceso roto** | RBAC granular con denegación por defecto. `require_permission` se declara en cada endpoint; sin permiso explícito no hay acceso. IDs de usuario en UUID para evitar enumeración. Autoprotección: un Admin no puede desactivarse ni quitarse su propio rol | `api/deps.py`, `domain/permissions.py`, `services/user_service.py` |
| **A02 · Fallas criptográficas** | Argon2id con la configuración primaria de OWASP (19 MiB, t=2, p=1). Cookies `Secure` + `HttpOnly`. Secretos solo por variables de entorno, nunca en el repositorio | `core/security.py`, `core/config.py` |
| **A03 · Inyección** | ORM con consultas parametrizadas en todo el acceso a datos; no hay SQL concatenado. Validación de entrada con Pydantic en cada endpoint. Protección contra inyección de fórmulas en CSV | `services/csv_service.py`, `api/v1/schemas/` |
| **A04 · Diseño inseguro** | Contraseñas temporales de un solo uso: el usuario creado por el Admin no puede operar hasta cambiarla (`VerifiedUser`). Política de contraseñas de 12 caracteres con cuatro clases | `api/deps.py`, `core/security.py` |
| **A05 · Configuración incorrecta** | `assert_production_ready()` aborta el arranque si falta un secreto o si `APP_DEBUG` quedó encendido. Swagger y OpenAPI deshabilitados en producción. Cabeceras de seguridad en toda respuesta | `core/config.py`, `main.py` |
| **A06 · Componentes vulnerables** | Lockfile con versiones exactas en ambos proyectos. `pip-audit` y `npm audit` ejecutados, con resultados y decisiones en la subsección de auditorías | `requirements.lock.txt`, `package-lock.json` |
| **A07 · Fallas de identificación** | Bloqueo tras 5 intentos fallidos durante 15 minutos. Mismo mensaje para correo inexistente y clave incorrecta, con hash desechable para igualar el tiempo de respuesta. `token_version` revoca todas las sesiones de un usuario | `services/auth_service.py` |
| **A08 · Fallas de integridad** | CSRF por doble envío en toda petición que modifica datos. Lectura-modificación-escritura contra Wialon para no perder datos al actualizar parcialmente | `api/deps.py`, `services/driver_service.py` |
| **A09 · Fallas de registro** | Auditoría de toda acción sensible con IP y agente de usuario. Redacción central de datos sensibles en los logs: contraseñas, tokens, cookies y el `sid` de Wialon | `services/audit_service.py`, `core/logging.py` |
| **A10 · SSRF** | El host de Wialon viene de configuración, no de entrada del usuario. No existe ningún endpoint que acepte una URL y la consulte | `core/config.py` |

### Cabeceras de seguridad

`core/http_security.py` añade en **toda** respuesta, incluidos los caminos de
error:

| Cabecera | Valor | Por qué |
|---|---|---|
| `Content-Security-Policy` | `default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'` | El API responde JSON, nunca HTML, así que puede usar la política más restrictiva que existe |
| `X-Content-Type-Options` | `nosniff` | Impide que el navegador adivine el tipo y ejecute como script algo declarado como JSON |
| `Referrer-Policy` | `no-referrer` | Las URLs del API llevan identificadores que no deben viajar a terceros |
| `X-Frame-Options` | `DENY` | Redundante con `frame-ancestors`, pero navegadores viejos solo entienden esta |
| `Permissions-Policy` | `geolocation=(), camera=(), microphone=(), payment=(), usb=()` | El API no necesita ninguna |
| `Cross-Origin-Opener-Policy` | `same-origin` | Aísla el contexto de navegación |
| `Cache-Control` | `no-store` | Las respuestas llevan datos de sesión; no deben quedar en caché de navegador ni de proxy |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | **Solo en producción.** En local no hay HTTPS y fijarlo rompería el acceso a `localhost` durante un año |

La ruta de Swagger recibe una política propia en desarrollo, porque carga su JS
y su CSS desde un CDN. En producción esa ruta no existe.

Las pruebas de `tests/test_http_security.py` verifican lo que de verdad importa:
que un **404 y un 429** salgan con las mismas cabeceras que un 200. Es
exactamente donde este tipo de middleware se suele colar.

### Limitador de peticiones

Dos cubos independientes por IP, en ventana deslizante de 60 segundos:

| Cubo | Límite | Configurable con |
|---|---|---|
| General | 600 por minuto | `RATE_LIMIT_PER_MINUTE` |
| Ingreso | 40 por minuto | `RATE_LIMIT_LOGIN_PER_MINUTE` |

Rechaza con `429` en formato Problem Details y cabecera `Retry-After`.

**Los umbrales son holgados a propósito.** La interfaz llega al API a través del
proxy de Vercel, y no está verificado que ese salto propague la IP del cliente
hasta Render. Si no lo hace, todas las peticiones caen en un mismo cubo: con
umbrales estrechos, el limitador se convierte en una caída de servicio para
usuarios legítimos, que es peor que el abuso que previene. Un umbral que no
puedes atribuir correctamente debe ser generoso.

Tres honestidades sobre este control:

1. **Es un amortiguador, no el control principal.** La IP viene de
   `X-Forwarded-For`, que es falsificable si alguien alcanza el servicio sin
   pasar por el proxy. El control principal contra fuerza bruta sigue siendo el
   bloqueo por usuario de `auth_service`.
2. **El contador vive en memoria del proceso.** Con más de una instancia cada
   una tendría el suyo. Es correcto para una sola instancia, que es lo que el
   plan gratuito ofrece. La solución general requiere Redis.

### Auditoría de dependencias

Ejecutadas el 8 de noviembre de 2026 sobre los lockfiles:

```bash
# Backend
pip-audit -r backend/requirements.lock.txt
# → No known vulnerabilities found

# Frontend
npm audit --package-lock-only
# → 12 vulnerabilidades: 6 bajas, 6 moderadas. Ninguna alta ni crítica.
```

Las 12 del frontend vienen de **tres causas raíz, todas transitivas**, ninguna
declarada en `package.json`:

| Paquete | Severidad | Naturaleza |
|---|---|---|
| `minimatch` | moderada | denegación de servicio por amplificación de patrones |
| `glob` | moderada | cancelación de `AbortSignal` evadible |
| `deepmerge` | baja | contaminación de prototipo en `mergeObject()` |

**Decisión: no se tocaron los lockfiles en la víspera de la entrega.** Son
dependencias de la cadena de herramientas de construcción —`glob` y `minimatch`
hacen recorrido de sistema de archivos, que no existe en un navegador—, no hay
ninguna alta ni crítica, y `npm audit fix --force` implica cambios mayores en
las versiones de Nuxt y Vite. Cambiar eso sin tiempo para volver a probar la
aplicación completa introduce más riesgo que el que elimina.

La remediación correcta, para después de la entrega, es subir Nuxt y Vite a la
versión que ya resuelva las transitivas y volver a correr la suite completa.

### Cómo funciona la protección CSRF

Doble envío. Al iniciar sesión se emiten tres cookies:

| Cookie | HttpOnly | Para qué |
|---|---|---|
| `sigmogps_access` | Sí | JWT de acceso, 15 minutos |
| `sigmogps_refresh` | Sí | JWT de renovación, 7 días |
| `sigmogps_csrf` | **No** | Valor aleatorio que el frontend lee y reenvía |

En cada petición que modifica datos, el frontend lee la cookie CSRF y la manda
también en la cabecera `X-CSRF-Token`. El backend exige que coincidan. Un sitio
atacante puede provocar que el navegador envíe las cookies, pero **no puede
leerlas** para construir la cabecera.

### Por qué cookies y no el token en `localStorage`

Un token en `localStorage` es legible por cualquier script que logre inyectarse:
un XSS se convierte en robo de sesión. Las cookies `HttpOnly` son invisibles al
JavaScript. El costo es tener que resolver CSRF, que es un problema con solución
conocida; el XSS que roba tokens no la tiene.

### Revocación de sesiones

Un JWT no se puede revocar por sí solo. La tabla `users` tiene `token_version`, y
cada *refresh* lleva dentro la versión con la que fue emitido. Al cerrar sesión,
cambiar la contraseña, cambiar de rol o desactivar al usuario, la versión sube en
uno y **todos** los refresh emitidos antes dejan de servir, en todos los
dispositivos.

**Se descartó** una tabla de tokens revocados porque exige limpieza periódica y
una consulta extra por petición, para el mismo resultado.

### Inyección de fórmulas en CSV

Una celda que empieza por `=`, `+`, `-`, `@`, tabulador o retorno de carro la
ejecutan Excel, LibreOffice y Google Sheets como fórmula al abrir el archivo.
`services/csv_service.py` antepone una comilla simple, que los tres programas
tratan como marca de texto y no muestran al usuario. El archivo sale con BOM
UTF-8 y delimitador `;` para que Excel en español lo abra en columnas sin
pedir importación.

### Modelado de amenazas

| Amenaza | Vector | Mitigación | Riesgo residual |
|---|---|---|---|
| Robo de sesión | XSS que lee el token | Cookies `HttpOnly`; el token nunca está en JavaScript | Un XSS aún puede actuar *en nombre* del usuario mientras la pestaña está abierta. Mitigado parcialmente con CSP |
| Petición forjada | Sitio de terceros que provoca una escritura | CSRF por doble envío + `SameSite` | Bajo |
| Fuerza bruta de credenciales | Intentos repetidos sobre un correo | Bloqueo de 15 min tras 5 fallos; auditoría de cada intento | **El bloqueo es por usuario, no por IP.** Un atacante con muchos correos no se frena |
| Enumeración de usuarios | Diferencia de mensaje o de tiempo entre correo inexistente y clave errónea | Mismo mensaje y hash desechable para igualar el tiempo | Bajo |
| Escalación de privilegios | Llamar un endpoint que la interfaz oculta | Denegación por defecto en el backend; ocultar un botón no es seguridad | Bajo |
| Admin se deja fuera del sistema | Quitarse el rol o desactivarse a sí mismo | Autoprotección explícita en `user_service` | No cubre el caso de dos Admin que se desactivan mutuamente |
| Fuga de datos por logs | Hash o token volcado al stdout | Redacción central en `core/logging.py`; eco de SQL desactivado | Bajo |
| Pérdida de datos del cliente en Wialon | Actualización parcial que borra campos no enviados | Lectura-modificación-escritura antes de cada escritura | Bajo |

---

## 7. Decisiones de diseño

La guía visual completa, con razones y relaciones de contraste medidas, está en
[`docs/guia-visual.md`](docs/guia-visual.md).

**Dos superficies, no un tema claro con variantes.** La página pública y el
ingreso son claros; el panel operativo es oscuro. No es decoración: un operador
mira el mapa durante horas y el fondo oscuro reduce el deslumbramiento, mientras
que la página pública se ve a plena luz. Los tokens semánticos
(`--surface`, `--on-surface`, `--border`, `--action`, `--danger`) se redefinen
bajo `.surface-light` y `.surface-dark`, y los componentes leen el token, no el
color literal.

Esto resolvió un problema real: los campos de formulario escritos para la
superficie clara quedaban ilegibles al reutilizarlos en modales oscuros. La
solución no fue agregar variantes a cada componente, sino que el componente
dejara de conocer su color.

**El color nunca viaja solo.** Cada chip de estado lleva punto, color y texto.
Un operador con deuteranopía distingue «En movimiento» de «Sin señal» por la
palabra, no por el verde y el rojo.

**Las tablas se ajustan a la ventana, sin desplazamiento de página.**
`useFilasQueCaben` mide el contenedor con `ResizeObserver` y deriva cuántas filas
caben; la paginación es numerada con elipsis. Al cambiar el tamaño de página se
recalcula a qué página pertenece el primer registro visible, para que la fila que
el usuario estaba mirando no se pierda.

**Tipografía Inter**, por su altura de x generosa y sus números tabulares, que
mantienen las columnas de velocidad y coordenadas alineadas.

---

## 8. Transformación de datos

Esta es la parte del trabajo que no se ve en una captura. Wialon entrega datos
crudos; la aplicación entrega información.

| Dato de Wialon | Forma cruda | Qué entrega la aplicación |
|---|---|---|
| `pos.t` | segundos UNIX (`1762549800`) | ISO-8601 UTC en el API; hora de `America/Bogota` más antigüedad relativa en la interfaz |
| `pos.s` | número sin unidad | `km/h`, rotulado |
| `pos.c` | grados, 0 a 359 | grados + punto cardinal + palabra («NE, nororiente») |
| `nm` | identificador interno (`957.`, `863238077731893`) | la placa, tomada del campo personalizado `PLACA`; cae al nombre de la unidad cuando no existe |
| `flds` | diccionario con claves numéricas | lista de nombre y valor, con el nombre original preservado |
| `bu` del conductor | id de unidad o `0` | nombre del vehículo vinculado, o estado vacío explícito |
| estado | no existe en Wialon | derivado: `en_movimiento`, `detenido`, `sin_senal` |

### El estado derivado

Wialon no dice si un vehículo está detenido. Se deriva de dos umbrales
configurables:

- `sin_senal` — el último mensaje tiene más de `VEHICLE_STALE_MINUTES` (10 min).
- `en_movimiento` — reporta hace menos de 10 min y su velocidad supera
  `VEHICLE_MOVING_MIN_KMH` (3 km/h).
- `detenido` — reporta hace menos de 10 min por debajo de ese umbral.

El umbral de 3 km/h no es arbitrario: el GPS reporta velocidades de 1 y 2 km/h
en vehículos parados por deriva de la señal. Con umbral en cero, media flota
aparecía «en movimiento» en un parqueadero.

### Hallazgos sobre los datos reales

Lo que se encontró al integrar la cuenta real, y que la aplicación tiene que
tolerar:

1. **El nombre de la unidad no es la placa.** La placa vive en un campo
   personalizado `PLACA`, presente solo en 15 de 65 unidades.
2. **Los nombres de campos personalizados traen erratas del cliente:** `LINEA` y
   `LÍNEA`, `COLOR` y `COLORE`, `PROPIETARIO` y `PROPOIETARIO`. Se normaliza
   acento y caja **para buscar**, pero al escribir se reenvía el nombre
   original: renombrarle un campo al cliente en silencio sería corromper su dato.
3. **Posiciones inválidas.** Algunas unidades reportan `(0, 0)` o coordenadas
   fuera de rango. El *mapper* las rechaza en vez de dibujar un marcador en el
   golfo de Guinea.
4. **Los vínculos existentes apuntan a unidades invisibles.** Los cuatro
   conductores que la cuenta trae vinculados apuntan a unidades que este token no
   puede ver. Con los datos de origen, RF-13 no se puede demostrar; se demuestra
   vinculando un conductor desde la interfaz a una unidad visible, que es
   justamente lo que el requisito pide poder hacer.
5. **La sesión de Wialon expira por inactividad** (~5 min). El *gateway* detecta
   el código de error, renueva la sesión bajo un `asyncio.Lock` para que varias
   peticiones concurrentes no disparen varios logins, y reintenta la petición
   original de forma transparente.

### La latencia de propagación de Wialon

El hallazgo más costoso de la integración, y el que mejor ilustra por qué hay que
medir antes de teorizar.

`resource/bind_unit_driver` responde de inmediato, pero Wialon tarda alrededor de
**2,3 segundos** en exponer el cambio en el campo `bu` del conductor. Eso no está
documentado; se midió.

El síntoma era que el usuario vinculaba un conductor y no veía el cambio hasta
recargar varias veces. La causa real **no era el caché viejo, sino el que se
guardaba después**: al escribir se limpiaba el caché correctamente, pero la
lectura siguiente llegaba antes de la propagación, traía el valor anterior y lo
dejaba fijado los 15 segundos completos del TTL.

Dos correcciones:

1. **Cuarentena de lecturas.** Durante seis segundos después de cualquier
   escritura, las lecturas van directo a Wialon: ni se sirven ni se guardan en
   caché. Protege a toda escritura, no solo al vínculo.
2. **Confirmación antes de responder.** `bind` y `unbind` sondean hasta que
   Wialon expone el cambio, con límite de seis segundos. Cuando el endpoint
   devuelve `204`, el cambio ya es visible: el cliente puede confiar en la
   respuesta en vez de adivinar cuándo releer.

**Resultado medido: de 17 s a 0,56 s.** Cubierto por
`backend/tests/test_wialon_cache.py`, donde la tercera prueba es exactamente la
que habría atrapado el error.

El diagnóstico se hizo con dos sondas, no leyendo código. La primera medía contra
el API y separaba frontend de backend. La segunda leía con y sin caché para
separar la propagación de Wialon del retraso propio: **2,35 s sin caché contra
15,84 s con caché**. Esa diferencia era la parte que aportaba nuestro código.

---

## 9. Supuestos y decisiones ante ambigüedades

**Wialon es la fuente de verdad de la flota; no se replica en PostgreSQL.**
Vehículos, conductores y pasajeros se leen y escriben siempre contra Wialon. Una
copia local tendría que sincronizarse, y una copia desincronizada es peor que no
tenerla: el operador vería datos que ya no existen. La base de datos guarda solo
lo que es nuestro —identidad, autorización, auditoría—, que es lo que Wialon no
puede guardar.

**Los pasajeros se modelan como *tags* de Wialon.** El enunciado habla de
pasajeros, pero la API de Wialon no tiene esa entidad. Los *tags* del recurso son
el objeto que la cuenta real usa para eso: 101 registros con nombre, código y
campos personalizados, vinculables a una unidad. La bandera correcta del recurso
para leerlos es `0x200000` (2097153 con la base); `0x100000` devuelve grupos de
geocercas, que fue un error que costó una tarde de diagnóstico.

**Los campos personalizados se reemplazan como conjunto completo** (RF-27).
Enviar un subconjunto borraría los demás. El endpoint recibe el conjunto completo
y la operación es idempotente.

**Las credenciales iniciales del Admin se entregan funcionando.** El Admin
sembrado tiene `must_change_password` en `false`: sus credenciales se entregan al
evaluador y deben servir tal cual. Los usuarios que ese Admin cree sí deben
cambiar la contraseña en el primer ingreso (RF-06).

**El bloqueo de ingreso es por usuario y no por IP.** Es la decisión que el
plan gratuito permite sin una capa de almacenamiento adicional. Está declarada
como limitación en la sección 11, no omitida.

---

## 10. Declaración de uso de IA

Se usó Claude (Anthropic) como asistente durante todo el desarrollo, de forma
intensiva y declarada.

**En qué se usó:** generación de código a partir de decisiones ya tomadas,
redacción de documentación, revisión de implementaciones, búsqueda de errores y
verificación de referencias de la API de Wialon contra la documentación oficial.

**Qué no delegué:** las decisiones de arquitectura, el modelo de datos, el
alcance, la guía visual y los criterios de seguridad. Cada medición reportada en
este documento —la latencia de propagación de Wialon, las relaciones de contraste,
los tiempos de login— se ejecutó y se verificó en este proyecto, no se tomó de
una recomendación general.

**Cómo lo verifiqué:** todo el código fue leído y probado antes de integrarse.
Varios de los hallazgos de la sección 8 surgieron precisamente de que la primera
implementación propuesta estaba equivocada: la bandera de *tags*, los parámetros
de Argon2 por defecto y el diagnóstico inicial de la latencia del vínculo se
corrigieron después de medir.

Estoy en capacidad de explicar cualquier línea de este repositorio y las razones
detrás de ella. `docs/defensa-tecnica.md` recoge esas razones en formato de
pregunta y respuesta.

---

## 11. Limitaciones conocidas y mejoras futuras

Lo que falta, dicho explícitamente. Preferí entregar menos alcance bien resuelto
que más alcance a medias.

### Fuera de alcance en esta entrega

| Requisito | Estado | Por qué |
|---|---|---|
| RF-24 · Historial de recorridos | No implementado | Requiere `messages/load_interval` de Wialon con manejo de intervalos y paginación de mensajes. Es un módulo completo, no un endpoint; no alcanzaba sin recortar calidad en lo demás |
| Gráficas de serie temporal | KPIs numéricos y composición | Una gráfica de evolución necesita series temporales, que dependen del historial de arriba |
| TST-03 · Pruebas de frontend | No implementadas | Las 42 pruebas de backend cubren la lógica de negocio, la integración con Wialon y la autorización, que es donde está el riesgo. Las de frontend quedaron priorizadas por debajo |

### Pruebas

42 pruebas, todas en el backend:

| Archivo | Qué fija |
|---|---|
| `test_wialon_cache.py` | El caché y su cuarentena tras escribir. La tercera es la regresión del error de propagación medido |
| `test_http_security.py` | Que las cabeceras envuelvan también un 404 y un 429, y que los dos cubos del limitador sean independientes |
| `test_vehicle_custom_fields.py` | Que se escriba solo el campo que cambió y que no se renombren los campos del cliente |
| `test_authorization.py` | Barrido de toda la superficie: ninguna ruta sin permiso, ninguna escritura sin CSRF |

Las de autorización no revisan endpoint por endpoint: recorren el árbol de
rutas. Si alguien agrega un endpoint sin `require_permission` o sin
`verify_csrf`, fallan solas. Incluyen tres guardas contra la forma en que este
tipo de prueba se degrada en silencio: que el barrido encuentre al menos 25
rutas, que no queden excepciones apuntando a rutas inexistentes, y que no haya
permisos en el catálogo que ninguna ruta exija.

### Limitaciones de lo que sí está implementado

- **El bloqueo por intentos fallidos es por usuario, no por IP.** Un atacante
  que rote correos no se frena. La solución correcta es un limitador por IP con
  almacenamiento compartido, que el plan gratuito no ofrece sin agregar Redis.
- **`token_version` invalida todos los *refresh* de un usuario a la vez.** No
  permite cerrar un solo dispositivo. La alternativa —una tabla de sesiones—
  agrega una consulta por petición.
- **Arranque en frío.** El plan gratuito de Render suspende el servicio tras
  15 minutos de inactividad. La primera petición después de eso puede tardar
  cerca de un minuto. No es un defecto del código.
- **El caché de Wialon es en memoria del proceso.** Con más de una instancia,
  cada una tendría el suyo. Para una sola instancia es correcto y suficiente.
- **La autoprotección del Admin no cubre dos administradores que se desactiven
  mutuamente.** Cubre el caso realista, que es dejarse fuera a uno mismo.

### Mejoras priorizadas

1. Historial de recorridos y reproducción sobre el mapa (RF-24).
2. Limitador de peticiones por IP con almacenamiento compartido.
3. Pruebas de interfaz sobre los flujos críticos: ingreso, vínculo, creación de
   usuario.
4. Sesiones individuales revocables, en lugar de revocación por usuario.
5. WebSocket o SSE en lugar de sondeo cada 10 segundos para las posiciones.
