# Defensa técnica · sigmoGPS

Notas para la sesión en vivo. Cada entrada responde a una pregunta que me pueden
hacer sobre mi propio código.

Formato: **qué decidí · por qué · qué alternativa descarté.**

---

## Integración con Wialon

### ¿Qué fue lo más difícil de integrar?

El vínculo conductor-vehículo. Wialon acepta `resource/bind_unit_driver` y
responde de inmediato, pero tarda alrededor de **2,3 segundos** en exponer el
cambio en el campo `bu` del conductor. Eso no está documentado; lo medí.

El efecto era que el usuario vinculaba un conductor y no veía el cambio hasta
recargar varias veces. La causa real no era el caché viejo sino el que
guardábamos después: al escribir se limpiaba el caché correctamente, pero la
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

Resultado medido: de 17 segundos a 0,56 segundos. Cubierto por
`tests/test_wialon_cache.py`, donde la tercera prueba es exactamente la que
habría atrapado el error.

### ¿Cómo lo diagnosticaste?

Con dos sondas, no leyendo código. La primera medía contra el API y separaba
frontend de backend. La segunda leía con y sin caché para separar la
propagación de Wialon de nuestro propio retraso: 2,35 s sin caché contra
15,84 s con caché. Esa diferencia era la parte que aportábamos nosotros.

### ¿Por qué el nombre visible del vehículo no es `nm`?

Porque en la cuenta real `nm` es un identificador interno (`957.`,
`863238077731893`) y la placa vive en un campo personalizado llamado `PLACA`,
presente solo en 15 de 65 unidades. La interfaz muestra la placa cuando existe
y cae al nombre de la unidad cuando no.

Los nombres de campos personalizados vienen con erratas del cliente
(`LINEA` y `LÍNEA`, `COLOR` y `COLORE`, `PROPIETARIO` y `PROPOIETARIO`). Se
normaliza acento y caja **para buscar**, pero al escribir se reenvía el nombre
original: renombrarle un campo al cliente en silencio sería corromper su dato.

### ¿Por qué ningún vehículo muestra conductor al entrar?

Los cuatro conductores que la cuenta demo trae vinculados apuntan a unidades
que este token no puede ver. Con los datos de origen, RF-13 no se puede
demostrar. Se demuestra vinculando un conductor desde la interfaz (RF-17) a una
unidad visible, que es justamente lo que el requerimiento pide poder hacer.

---

## Arquitectura y capas

### ¿Por qué estas cinco carpetas y no un solo archivo por recurso?

Arquitectura por capas con la **regla de dependencia apuntando hacia adentro**:

```
api → services → domain ← infrastructure
```

- `domain/` no importa nada de las otras capas. Contiene modelos propios,
  excepciones de negocio y el catálogo de permisos.
- `services/` importa solo `domain`. Son los casos de uso.
- `infrastructure/` implementa lo que el dominio necesita: base de datos y Wialon.
- `api/` traduce HTTP a casos de uso y de vuelta.
- `core/` es transversal: configuración, logging y formato de errores.

Sin esa regla serían carpetas decorativas. El pago concreto está en los tests:
como los servicios dependen de interfaces y no de clases concretas, simular
Wialon es una clase de diez líneas en vez de parchear HTTP.

**Descarté** la estructura plana por recurso (`users.py`, `vehicles.py`) porque
mezcla reglas de negocio con detalles de transporte y hace imposible testear sin
levantar la aplicación entera.

### ¿Dónde aplicaste SOLID?

| Principio | Dónde | Cómo |
| --- | --- | --- |
| Responsabilidad única | `core/security.py` | Solo hashea y valida política. No sabe de usuarios ni de sesiones |
| Abierto/cerrado | `domain/permissions.py` | Agregar un permiso es añadir una línea al enum y correr el seed. Ningún `if` cambia |
| Sustitución de Liskov | `domain/exceptions.py` | Todas las excepciones heredan de `DomainError` y el manejador global las trata igual |
| Segregación de interfaces | `api/deps.py` | `CurrentUser`, `VerifiedUser` y `require_permission` son tres contratos distintos; un endpoint pide solo el que necesita |
| Inversión de dependencias | `api/deps.py` → `get_session` | Los endpoints reciben la sesión inyectada, no la construyen |

### ¿Qué patrones usaste?

- **Dependency Injection** — el sistema de dependencias de FastAPI en `api/deps.py`.
- **Unit of Work** — `get_session` confirma al terminar bien y revierte al fallar.
  Un endpoint no puede dejar media escritura aplicada.
- **Factory** — `create_app()` en `main.py` arma la aplicación; permite construir
  una instancia distinta en los tests.
- **DTO** — los modelos Pydantic de `api/v1/schemas/` son el contrato del API.
  Nunca se devuelve un modelo de SQLAlchemy directamente, por eso el hash de
  contraseña no puede filtrarse por accidente.

---

## Configuración y arranque

### ¿Por qué `assert_production_ready()`?

Falla al arrancar, no en la primera petición. Si en Render falta `SECRET_KEY` o
`APP_DEBUG` quedó en `true`, el proceso no levanta y el despliegue se marca como
fallido. La alternativa — descubrirlo cuando un usuario recibe un 500 — es peor.

### ¿Por qué `get_settings()` con `lru_cache`?

La configuración se lee del entorno una sola vez por proceso. El caché la vuelve
un singleton sin usar una variable global mutable, y en los tests se puede
limpiar con `get_settings.cache_clear()`.

### ¿Por qué `.python-version` con 3.14?

Mi entorno local y el de Render corren el mismo intérprete, declarado en un
archivo versionado. Render lee ese archivo. Es la respuesta a «¿cómo garantizas
paridad entre desarrollo y producción?» sin depender de que alguien recuerde
configurar una variable.

---

## Logging y errores

### ¿Cómo evitas filtrar datos sensibles a los logs? (SEG-02, SEG-09)

`core/logging.py` tiene un procesador `redactar` que corre en **todos** los
eventos y sustituye el valor de cualquier clave sensible: contraseñas, tokens,
cookies, cabeceras de autorización y el identificador de sesión de Wialon.

Es una última línea de defensa, no la primera: la primera es no pasar esos datos
al logger. Pero un procesador central me protege del descuido de un día apurado.

También desactivé el eco de SQL de SQLAlchemy, que volcaba los hashes de
contraseña al stdout.

### ¿Por qué RFC 7807 y no un JSON propio? (ARQ-04)

`application/problem+json` es un estándar: el frontend parsea `title`, `detail`
y `errors` sin que yo invente un contrato. Cada respuesta incluye un `trace_id`
que también viaja en la cabecera `X-Request-Id`, así que un usuario puede
reportar un error y yo encuentro la línea exacta en los logs.

### ¿Qué pasa con una excepción no prevista? (SEG-10)

El manejador de `Exception` registra el stack trace completo del lado del
servidor y devuelve al cliente un 500 genérico con el `trace_id`. **Nunca** se
expone un stack trace, una consulta SQL ni un nombre de archivo interno.

---

## Autenticación

### ¿Por qué Argon2 y no bcrypt? (SEG-02)

Argon2id ganó la Password Hashing Competition y es la primera recomendación de
OWASP. A diferencia de bcrypt, es resistente a ataques con GPU porque consume
memoria además de CPU.

Los parámetros **no** son los predeterminados de `argon2-cffi`. Los
predeterminados (64 MiB, 3 iteraciones, 4 hilos) asumen una máquina con varios
núcleos dedicados; en el plan gratuito de Render, donde el servicio corre sobre
una fracción de vCPU, los 4 hilos compiten entre sí y el login tardaba
**2,3 segundos** medidos. Se cambió a la configuración primaria de la hoja de
OWASP —**19 MiB, t=2, p=1**— que ofrece la misma resistencia con un perfil
pensado para un solo hilo. El login bajó a unos 0,4 s.

Es el ejemplo de por qué «usar los valores por defecto» no es una decisión: hay
que saber para qué máquina fueron pensados.

`needs_rehash()` permite subir el costo en el futuro: el hash se regenera en el
siguiente login exitoso, sin pedirle nada al usuario.

**Descarté** `passlib` porque lleva años sin mantenimiento activo y choca con
bcrypt 4.x.

### ¿Por qué cookies y no el token en localStorage? (SEG-02)

Un token en `localStorage` es legible por cualquier script que logre inyectarse:
un XSS se convierte en robo de sesión. Las cookies `HttpOnly` son invisibles al
JavaScript. El costo es tener que resolver CSRF, que es un problema con solución
conocida; el XSS que roba tokens no la tiene.

### ¿Cómo funciona la protección CSRF? (SEG-11)

Doble envío. Al iniciar sesión se emiten tres cookies:

| Cookie | HttpOnly | Para qué |
| --- | --- | --- |
| `sigmogps_access` | Sí | JWT de acceso, 15 minutos |
| `sigmogps_refresh` | Sí | JWT de renovación, 7 días |
| `sigmogps_csrf` | **No** | Valor aleatorio que el frontend lee y reenvía |

En cada petición que modifica datos, el frontend lee la cookie CSRF y la manda
también en la cabecera `X-CSRF-Token`. El backend exige que coincidan. Un sitio
atacante puede provocar que el navegador envíe las cookies, pero no puede
leerlas para construir la cabecera.

### ¿Cómo invalidas una sesión al cerrarla? (SEG-07)

Un JWT no se puede revocar por sí solo. La tabla `users` tiene `token_version`,
y cada refresh lleva dentro la versión con la que fue emitido. Al cerrar sesión
o cambiar la contraseña, la versión sube en uno y **todos** los refresh emitidos
antes dejan de servir, en todos los dispositivos.

**Descarté** una tabla de tokens revocados porque exige limpieza periódica y una
consulta extra por petición, para el mismo resultado.

### ¿Por qué el mismo mensaje para correo inexistente y clave incorrecta?

Para no permitir enumeración de usuarios. Si el mensaje distinguiera, un atacante
podría averiguar qué correos están registrados.

Hay un detalle menos obvio: cuando el correo no existe se calcula igualmente un
hash desechable. Sin eso, la respuesta sería notablemente más rápida y el tiempo
delataría lo que el mensaje oculta.

### ¿Cómo frenas la fuerza bruta? (SEG-07)

`failed_login_attempts` sube con cada fallo. Al llegar a `LOGIN_MAX_ATTEMPTS`, se
fija `locked_until` a quince minutos en el futuro y el contador se reinicia.
Durante el bloqueo, ni siquiera una contraseña correcta entra. Un login exitoso
limpia ambos campos.

Todos los intentos, exitosos y fallidos, quedan en el registro de auditoría con
IP y agente de usuario.

---

## RBAC

### ¿Por qué permisos granulares y no `if role == "admin"`?

El enunciado lo pide explícitamente y la razón es práctica: con permisos
granulares, agregar un rol es insertar filas, no buscar condicionales por todo
el código.

El flujo tiene una sola fuente de verdad, `domain/permissions.py`:

1. El seed escribe el catálogo y la matriz en la base.
2. `require_permission` los exige en cada endpoint.
3. `/auth/me` los devuelve y el frontend arma su menú con eso.

Agregar un permiso es una línea en el enum más una corrida del seed. No hay un
cuarto lugar donde actualizar.

### ¿Por qué el frontend también los recibe, si el backend ya valida?

Son dos cosas distintas. El backend **protege**: deniega por defecto y rechaza
aunque alguien llame el endpoint a mano. El frontend **ordena la interfaz**: no
muestra un botón que va a fallar.

Ocultar un botón no es seguridad. Por eso los tests de autorización verifican lo
contrario de lo habitual: que cada rol **no pueda** hacer lo que no le toca.

### ¿Por qué `VerifiedUser` además de `CurrentUser`?

`CurrentUser` solo confirma que la sesión es válida. `VerifiedUser` además exige
que el usuario ya haya cambiado su contraseña inicial. Un usuario recién creado
por el Admin tiene sesión válida pero no puede tocar nada hasta cambiarla
(RF-06). Separarlos deja que `/auth/change-password` funcione con el primero
mientras el resto de la aplicación exige el segundo.

---

## Base de datos

### ¿Por qué UUID en `users` y entero en `roles`?

El identificador de usuario viaja en la URL. Con enteros secuenciales, cualquiera
puede recorrer `/users/1`, `/users/2` y descubrir cuántos usuarios hay y en qué
orden se crearon. Con UUID no hay nada que recorrer.

`roles` y `permissions` son datos de referencia que siembra el código: no se
exponen por id y el entero es más barato de indexar en la tabla puente.

### ¿Por qué la convención de nombres en `base.py`?

Sin ella, PostgreSQL inventa los nombres de las constraints y Alembic genera
migraciones de bajada que fallan porque no encuentra el nombre que espera. Con
la convención, el nombre es determinista.

### ¿Por qué el seed es idempotente?

Se ejecuta en cada despliegue. Debe poder correr diez veces sin duplicar nada y
sin pisar la contraseña del Admin si ya existe. Además reemplaza la lista
completa de permisos de cada rol, así que quitar un permiso del catálogo lo
quita del rol en la siguiente corrida.

### ¿Por qué `pool_pre_ping` y `pool_recycle`?

Neon cierra las conexiones ociosas. Sin `pool_pre_ping`, la primera petición
después de un rato falla con una conexión muerta del pool. Con él, SQLAlchemy la
verifica y la reemplaza de forma transparente.

---

## Decisiones de entorno

### ¿Por qué `run.py` en vez de `uvicorn` directo?

Windows usa `ProactorEventLoop` por defecto y psycopg no funciona sobre él.
`run.py` fija `WindowsSelectorEventLoopPolicy` antes de importar uvicorn, fuera
del guard `__main__` para que el proceso hijo del recargador también la herede.

Es un parche de desarrollo: en Render corre Linux y se usa `uvicorn`
directamente. Lo mismo en `alembic/env.py`, pero ahí con `loop_factory`, que es
la forma nativa de Python 3.14.

### ¿Por qué cotas mínimas en `pyproject.toml` y lockfile aparte? (SEG-06)

`pyproject.toml` declara qué necesito; `requirements.lock.txt` declara qué se
instaló exactamente. El primero es el contrato, el segundo la reproducibilidad.
Render instala del lockfile, así que la versión que probé es la que corre.

---

## Limitaciones conocidas

La lista completa, con mejoras priorizadas, está en la sección 11 del README.
Las tres que más probablemente pregunten:

- El bloqueo por intentos fallidos es por usuario, no por IP. Un atacante con
  muchos correos no se frena. El limitador por IP de `core/http_security.py`
  amortigua el volumen, pero la IP viene de `X-Forwarded-For` y es falsificable
  si alguien alcanza el servicio sin pasar por el proxy.
- `token_version` invalida todos los refresh de un usuario a la vez; no permite
  cerrar un solo dispositivo.
- El contador del limitador vive en memoria del proceso. Con más de una
  instancia cada una tendría el suyo; la solución general requiere Redis, que
  el plan gratuito no ofrece.
