# Guía visual · sigmoGPS

Documento de referencia del sistema de diseño. Vive en `docs/guia-visual.md`.
Las secciones marcadas con **→ README** se trasladan a la sección «Decisiones de diseño» del README de la entrega.

---

## 1. Direcciones elegidas

| Superficie | Dirección | Carácter |
|---|---|---|
| Landing pública `/` | **A · Editorial** | Clara, centrada, aireada. El mapa es el protagonista del hero. |
| Login `/ingresar` | **C · Formulario sobre mapa** | Panel anclado a la izquierda sobre un mapa a sangre. |
| Panel `/app/*` | **B · Consola** | Oscura y densa. Riel de iconos + contenido + mapa. |

La landing y el login viven en superficie clara; el panel vive en superficie oscura. No es modo oscuro: es una decisión de contexto. La landing persuade a la luz del día, el panel se mira ocho horas seguidas.

---

## 2. Paleta y roles **→ README**

La prueba entrega cinco colores sin decir qué hace cada uno. El reparto se decidió midiendo contraste, no por gusto.

### Superficie clara (landing y login)

| Color | Rol | Contraste sobre `#FFFFFF` | Veredicto |
|---|---|---|---|
| `#A81A2B` | Primario de marca: acciones, enlaces, logotipo, selección | 7.35:1 | AA y AAA |
| `#EB162C` | Acento y crítico: hover del primario, «sin señal», destructivo | 4.47:1 | **Falla AA en texto normal** |
| `#1E8C93` | Positivo: «en movimiento», selección en mapa | 4.02:1 | **Falla AA en texto normal** |
| `#6B6B6B` | Texto secundario, bordes fuertes, «detenido» | 5.30:1 | AA |
| `#EEE8F2` | Lienzo de la aplicación bajo las tarjetas blancas | — | Solo superficie |

**Regla que se deriva de la tabla:** `#EB162C` y `#1E8C93` nunca son color de texto en superficie clara. Son relleno, icono y punto de estado. Esta es la decisión central del sistema y la respuesta directa a lo que pide la sección 8.1 del enunciado.

### Superficie oscura (panel)

Sobre `#17141C`, el rojo vivo vuelve a caer por debajo del umbral, así que se aclara.

| Token | Valor | Contraste sobre `#17141C` |
|---|---|---|
| Texto principal | `#EEE8F2` | 15.4:1 |
| Rojo de texto y acento | `#FF6274` | 6.36:1 |
| Teal de estado | `#4FC3C9` | 8.81:1 |
| Texto secundario | `#9A94A3` | 6.1:1 |

### Derivados

| Color | Origen | Para qué | Contraste |
|---|---|---|---|
| `#15666B` | `#1E8C93` oscurecido | Escribir «En movimiento» sobre fondo claro | 6.68:1 |
| `#17141C` | Negro corrido al matiz lila de `#EEE8F2` | Tinta y fondo del panel | 16.9:1 |
| `#8A5A00` | **Único color añadido** | Advertencia | 5.93:1 |

**Justificación del color añadido → README:** advertencia y error no pueden compartir el rojo. Si lo comparten, el operador deja de distinguir «revisar esto» de «esto está caído», que es precisamente la decisión que tiene que tomar rápido. El enunciado permite colores adicionales justificados; este es el único.

### No confiar en el color solo

Cada estado lleva además punto, icono o texto. Un operador con daltonismo rojo-verde tiene que distinguir «detenido» de «sin señal» igual que cualquier otro (UX-03).

---

## 3. Tokens

```css
:root{
  /* tinta y papel — superficie clara */
  --ink:#17141C;
  --ink-2:#44404D;
  --muted:#6B6B6B;
  --paper:#FFFFFF;
  --wash:#EEE8F2;
  --wash-2:#F7F4FA;
  --line:#DCD4E2;
  --line-strong:#C3B9CC;

  /* marca y estado — superficie clara */
  --brand:#A81A2B;
  --brand-hi:#EB162C;
  --brand-soft:#FBE7E9;
  --teal:#1E8C93;
  --teal-ink:#15666B;
  --teal-soft:#E2F2F3;
  --ochre:#8A5A00;
  --ochre-soft:#F6EEDC;

  /* consola — superficie oscura del panel */
  --console:#17141C;
  --console-2:#211D29;
  --console-3:#111016;
  --console-line:#352F3F;
  --console-ink:#EEE8F2;
  --console-muted:#9A94A3;
  --console-brand:#FF6274;
  --console-teal:#4FC3C9;

  /* radios */
  --r-sm:6px; --r-md:10px; --r-lg:16px; --r-xl:24px; --r-pill:999px;

  /* sombras — reservadas a lo que flota sobre el mapa */
  --shadow-sm:0 1px 2px rgba(23,20,28,.06), 0 1px 3px rgba(23,20,28,.04);
  --shadow-md:0 4px 16px rgba(23,20,28,.08), 0 1px 3px rgba(23,20,28,.05);
  --shadow-lg:0 18px 48px rgba(23,20,28,.16), 0 2px 8px rgba(23,20,28,.07);

  /* tipografía */
  --display:"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --body:"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --mono:"IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
}
```

---

## 4. Tipografía

| Rol | Familia | Uso |
|---|---|---|
| Display | Inter 600 / 700, tracking `-0.02em` | Titulares, nombres de unidad, KPIs |
| Cuerpo | Inter 400 / 500 / 600 | Todo el texto corrido y la interfaz |
| Dato | IBM Plex Mono 400 / 500 con `tabular-nums` | Placas, coordenadas, velocidades, horas, IDs |

La monoespaciada no es decorativa: placas, coordenadas y velocidades se leen en columna dentro de tablas y listas, y tienen que alinearse dígito con dígito. Es el detalle que delata si alguien pensó en el operador o solo en la captura de pantalla.

Las etiquetas en versalitas llevan `letter-spacing: .13em` y peso 600. Los titulares llevan `text-wrap: balance`.

---

## 5. Espaciado y forma

Escala de 4: **4 · 8 · 12 · 16 · 24 · 32 · 48 · 64**.

| Valor | Uso |
|---|---|
| 4 px | Separación interna de un chip |
| 8 px | Elementos de una misma fila |
| 12 px | Interior de tarjeta compacta (panel) |
| 16 px | Gutter mínimo en móvil, nunca menos |
| 24 px | Interior de tarjeta estándar |
| 48 px | Entre secciones de la landing |

Radios por rol, no por costumbre: `6px` controles densos del panel, `10px` tarjetas y botones cuadrados, `16px` tarjetas de la landing, `24px` contenedores destacados, pill para botones de acción y chips.

Las sombras se reservan a lo que literalmente flota sobre el mapa. Si todo lleva sombra, nada flota.

---

## 6. Estado derivado del vehículo **→ README**

| Estado | Regla | Color claro | Color oscuro |
|---|---|---|---|
| En movimiento | último mensaje < 10 min **y** velocidad > 3 km/h | `#1E8C93` / texto `#15666B` | `#4FC3C9` |
| Detenido | último mensaje < 10 min **y** velocidad ≤ 3 km/h | `#6B6B6B` | `#9A94A3` |
| Sin señal | último mensaje ≥ 10 min, **o** sin posición conocida | `#EB162C` | `#FF6274` |

Los dos umbrales (10 min y 3 km/h) viven como constantes configurables del backend, en un solo módulo, no repartidos por el código. El umbral de 3 km/h existe porque el GPS reporta deriva de uno o dos km/h con el vehículo parado.

**Pendiente:** ambos valores son provisionales hasta ver la antigüedad real de los mensajes de `demoApps`. Si la cuenta demo tiene unidades con mensajes de hace meses, el umbral de «sin señal» hay que subirlo o el tablero sale en un solo estado.

---

## 7. Estructura de rutas

| Ruta | Layout | Acceso |
|---|---|---|
| `/` | público | Cualquiera. Con sesión activa, el botón de login se reemplaza por acceso al panel |
| `/ingresar` | auth | Cualquiera |
| `/cambiar-clave` | auth | Obligatorio en el primer ingreso |
| `/app/mapa` | app | Los tres roles |
| `/app/vehiculos` | app | Los tres roles · tabla |
| `/app/vehiculos/:id` | app | Ver: los tres · editar campos: Admin y Operador |
| `/app/conductores` | app | Ver: los tres · CRUD: Admin y Operador |
| `/app/pasajeros` | app | Ver: los tres · CRUD: Admin y Operador |
| `/app/tablero` | app | Los tres roles |
| `/app/usuarios` | app | Solo Admin |
| `/app/auditoria` | app | Solo Admin |

El menú, los guards de ruta y los botones deshabilitados se construyen **filtrando esta misma tabla** contra los permisos que devuelve `GET /api/v1/me`. Un solo origen de verdad.

Ocultar no es proteger: el backend valida el permiso en cada endpoint aunque la interfaz ya lo haya escondido (SEG-01).

---

## 8. Inventario de componentes

Esto es lo que hace que el frontend se arme solo. Construir en este orden.

### Base (se construyen primero, los usa todo lo demás)

| Componente | Notas |
|---|---|
| `AppButton` | Variantes: primary, ghost, danger. Formas: pill, square. Estado de carga incluido |
| `AppInput` / `AppSelect` | Label, mensaje de error, `aria-describedby`, estado inválido |
| `StatusChip` | Recibe el estado derivado. Punto + texto, nunca color solo |
| `DataTable` | Ordenar, paginar servidor, estado vacío con guía de acción, scroll horizontal propio |
| `EmptyState` | Icono, frase y acción. Nunca una pantalla en blanco (ARQ-12) |
| `LoadingSkeleton` | Variantes fila, tarjeta y mapa |
| `ErrorState` | Mensaje útil + botón reintentar |
| `ConfirmDialog` | Obligatorio en toda acción destructiva (UX-04) |
| `ToastHost` | Éxito, error y advertencia. Usa el ocre, no el rojo, para advertencia |

### Mapa

| Componente | Notas |
|---|---|
| `FleetMap` | Leaflet, carga diferida sin SSR, atribución OSM visible |
| `VehicleMarker` | Icono por estado, resalta al seleccionar desde la lista |
| `MarkerCluster` | Agrupación cuando hay marcadores cercanos (RF-11) |
| `MapPopupCard` | Datos clave + enlace al detalle |

### Panel

| Componente | Notas |
|---|---|
| `ConsoleRail` | Riel de iconos. En móvil se convierte en barra inferior |
| `VehicleListCard` | Tarjeta densa con placa, estado, conductor y última lectura |
| `DetailSheet` | Hoja flotante sobre el mapa con pestañas |
| `CustomFieldsEditor` | Reutilizado por vehículos y pasajeros. Estados: guardando, éxito, fallo con reintento |
| `RoleNav` | Renderiza el menú filtrando por permisos |

### Landing

`LandingHero`, `StatBand`, `BentoGrid`, `StepList`, `CtaBlock`, `SiteFooter`. Sin estado, sin peticiones: es lo que mantiene el Lighthouse arriba.

---

## 9. Comportamiento responsive **→ README**

El panel es la parte cara. Reglas explícitas, no `flex-wrap` improvisado.

### Panel, de escritorio a 360 px

| Elemento | ≥ 1024 px | 768 – 1023 px | < 768 px |
|---|---|---|---|
| Riel de navegación | Columna de iconos a la izquierda | Igual, colapsado | **Barra inferior de pestañas** |
| Lista de unidades | Columna de 332 px | Columna de 280 px | Ancho completo, es la vista por defecto |
| Mapa | Resto del ancho | Resto del ancho | **Hoja deslizable desde abajo**, se abre al tocar una unidad |
| Hoja de detalle | Flotante sobre el mapa | Flotante | Pantalla completa con botón de volver |

### Tablas en móvil

Por debajo de 768 px la tabla deja de ser tabla: cada fila se convierte en una tarjeta con la placa como título y el resto como pares etiqueta/valor. Una tabla con scroll horizontal en un celular no es responsive, es una tabla rota con scroll.

### Mapa en móvil

Altura máxima del 60 % de la ventana cuando comparte pantalla. Los controles de zoom se mueven al lado derecho, fuera del alcance del pulgar izquierdo.

---

## 10. Accesibilidad **→ README**

- Contraste verificado en ambas superficies; las cifras están en la sección 2.
- Foco visible en todo elemento interactivo: `outline: 2px solid var(--brand); outline-offset: 2px`.
- Todo formulario con `label` asociado y errores anunciados con `aria-describedby`.
- HTML semántico: `nav`, `main`, `aside`, `table` reales. No `div` con `onclick`.
- Toda imagen con `alt`; las decorativas con `alt=""`.
- Animaciones bajo `prefers-reduced-motion`.
- La navegación por teclado alcanza el mapa: los marcadores son enfocables y se abren con Enter.

---

## 11. Pendientes de esta guía

- Umbrales de estado derivado, a confirmar con los datos reales de `demoApps`.
- Logotipo definitivo. El del prototipo es un pin con el hueco en negativo, suficiente para la entrega.
- Favicon y `og:image` de la landing.
