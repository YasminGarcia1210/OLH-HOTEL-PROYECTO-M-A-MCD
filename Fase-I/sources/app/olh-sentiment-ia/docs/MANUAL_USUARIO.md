# Manual de usuario — Sentiment AI (Hoteles OLH)

**Versión:** 1.0  
**Aplicación:** Sentiment AI · Intelligence Suite  
**Audiencia:** usuarios finales (consulta de métricas, reseñas y carga de datos) y administradores del sistema.

---

## 1. ¿Qué es Sentiment AI?

Sentiment AI es la interfaz web de **Hoteles OLH** para analizar reseñas de huéspedes con inteligencia artificial. Permite:

- Ver **indicadores ejecutivos** de sentimiento y riesgo reputacional.
- **Explorar reseñas** filtradas por fecha, sentimiento y tópicos.
- **Subir archivos** con reseñas y seguir su procesamiento.
- **Iniciar análisis** sobre archivos pendientes.
- (Solo administradores) **Gestionar usuarios**, umbrales de alerta y recálculo de métricas.

Tras iniciar sesión, la pantalla principal es el **Dashboard**. El menú lateral (escritorio) o la barra inferior (móvil) conecta el resto de secciones.

---

## 2. Requisitos y acceso

### 2.1 Requisitos

- Navegador actualizado (Chrome, Edge, Firefox o Safari).
- Conexión a internet estable.
- **Usuario y contraseña** entregados por el administrador del sistema.

### 2.2 URL de acceso

Abra la dirección que le haya proporcionado su organización (por ejemplo, el despliegue en Azure Container Apps). Si no está autenticado, la aplicación le redirigirá automáticamente a **Iniciar sesión**.

### 2.3 Roles de usuario


| Rol        | Descripción                    | Acceso                                                  |
| ---------- | ------------------------------ | ------------------------------------------------------- |
| **Viewer** | Consulta de métricas y reseñas | Dashboard, Reviews, Upload. No ve **Settings**.         |
| **Admin**  | Gestión del sistema            | Todo lo anterior más **Settings** (usuarios y tópicos). |


Los datos mostrados corresponden al **hotel asignado** a su cuenta (o al hotel configurado en el despliegue). Los administradores con acceso **global** pueden asociar usuarios a distintos hoteles.

---

## 3. Iniciar y cerrar sesión

### 3.1 Iniciar sesión

1. En la pantalla **Iniciar sesión**, escriba su **Usuario**.
2. Escriba su **Contraseña** (puede usar el icono del ojo para mostrarla u ocultarla).
3. Pulse **Ingresar**.

Si las credenciales son incorrectas, verá un mensaje de error en rojo. Si son correctas, entrará al **Dashboard**.

### 3.2 Sesión expirada

Si el token de sesión caduca, la aplicación le llevará de nuevo a **Iniciar sesión** con un mensaje de cierre de sesión. Vuelva a identificarse.

### 3.3 Cerrar sesión

Puede cerrar sesión de dos formas:

- **Barra superior:** clic en el avatar (inicial de su usuario) → **Cerrar sesión**.
- **Menú lateral (escritorio):** botón **Logout** en la parte inferior.

---

## 4. Navegación general

### 4.1 Menú principal


| Sección       | Ruta                  | Icono         | Función                            |
| ------------- | --------------------- | ------------- | ---------------------------------- |
| **DASHBOARD** | Panel principal       | dashboard     | KPIs, tendencias y alertas         |
| **REVIEWS**   | Explorador de reseñas | manage_search | Listado detallado de reseñas       |
| **UPLOAD**    | Carga de archivos     | cloud_upload  | Subir datos y ver historial        |
| **SETTINGS**  | Administración        | settings      | Solo **admin**: usuarios y tópicos |


En **móvil**, las mismas opciones aparecen en la barra inferior. Los usuarios **viewer** que pulsen Settings serán redirigidos al Dashboard (no tienen permiso).

### 4.2 Acción global: New Analysis

En el menú lateral (escritorio), el botón dorado **New Analysis** abre el asistente para **lanzar el procesamiento** de un archivo ya subido pero aún pendiente. Se describe en la sección 7.

### 4.3 Barra superior

Muestra la marca **Hoteles OLH** y el menú de perfil (usuario y cierre de sesión).

---

## 5. Dashboard — Panel ejecutivo

El Dashboard resume el estado del sentimiento del hotel en el período elegido.

### 5.1 Seleccionar período

En la parte superior, use las pestañas:

- **Último mes**
- **Último trimestre**
- **Último semestre** (valor por defecto al entrar)

Al cambiar el período, **todas las secciones** del dashboard se actualizan. Mientras cargan, verá esqueletos animados; si hay error de red, aparecerá un aviso en rojo indicando qué bloque no pudo cargarse.

### 5.2 Bloques del dashboard (de arriba a abajo)

#### Sentimiento general · Core del modelo

- **Puntuación principal de sentimiento** (%): visión global del período.
- Texto explicativo y **badge de variación** (comparación respecto al período anterior).
- Tres tarjetas complementarias con métricas secundarias del modelo (volumen, confianza, etc., según datos del servidor).

#### Tendencia del sentimiento · Serie temporal

Gráfico de evolución **mes a mes** del sentimiento. Si no hay datos en el rango, verá un mensaje informativo (no es un error).

#### Data Strength · Volumen y confiabilidad

Cuatro indicadores sobre la base de datos analizada, por ejemplo:

- Reviews analizadas
- Cobertura temporal
- Confiabilidad del modelo
- Otros ratios de calidad de datos

#### Riesgo reputacional · Alertas

- Contadores de alertas por severidad.
- Listado de **tópicos en riesgo** que superan umbrales configurados.
- Gráfico tipo dona con distribución del riesgo.

#### Categorías / tópicos por categoría

Cuadrícula con **puntuaciones por categoría** de tópicos (limpieza, servicio, ubicación, etc.) para el mes ancla del período.

#### Top Insights

Dos columnas:

- **Fortalezas:** tópicos con mejor desempeño.
- **Pain points:** tópicos con peor desempeño.

#### Pain Points Index

Tarjetas con los puntos de dolor más relevantes y su impacto en el período.

#### Resumen ejecutivo

KPIs tabulares para lectura rápida por dirección (totales, medias, variaciones).

#### Métricas avanzadas

Bloque adicional con indicadores técnicos del análisis (referencia para usuarios avanzados).

Al pie puede aparecer una nota aclaratoria sobre el origen de los datos o la versión del modelo.

### 5.3 Cómo interpretar el dashboard

1. Empiece por el **período** acorde a su reunión (mes operativo vs. visión estratégica trimestral/semestral).
2. Revise **sentimiento general** y la **tendencia**: ¿mejora o empeora?
3. Consulte **riesgo reputacional** para priorizar acciones urgentes.
4. Use **Top Insights** y **Pain Points** para planes de mejora por área.
5. Baje al **Explorador de reseñas** (sección 6) para leer textos concretos.

---

## 6. Reviews — Explorador de reseñas

Permite leer reseñas individuales con el análisis de IA ya aplicado.

### 6.1 Vista general

Cada reseña se muestra en una tarjeta con:

- **Título / identificador** y **fecha**
- **Fuente** (Booking, TripAdvisor, Google, etc.)
- **Badge de sentimiento** (positivo, neutro, negativo o etiquetas como “excelente” / “crítico”)
- **Texto completo** de la reseña
- **Chips de tópicos** detectados (colores según tono positivo/negativo/neutro)

El borde izquierdo de la tarjeta usa color según el sentimiento dominante.

### 6.2 Filtros

#### Rango de fechas

- Muestra el rango activo en texto.
- Use los campos **Desde** y **Hasta** (selector de calendario) para acotar el análisis.
- Si “Desde” queda después de “Hasta”, la aplicación ajusta automáticamente las fechas.

#### Sentimiento

Chips para filtrar:

- **Todos** (sin filtro de sentimiento)
- **Positivo**
- **Neutro**
- **Negativo**

Pulsar un chip activo lo **desactiva** y vuelve a “todos”.

#### Tópicos

Lista de tópicos frecuentes en el resultado actual. Pulse un tópico para filtrar solo reseñas que lo mencionan; pulse de nuevo para quitar el filtro. Algunos chips son solo informativos (“más temas”) y no son clicables.

### 6.3 Paginación

- **20 reseñas por página**.
- Use **Anterior** y **Siguiente** al pie del listado.
- Indicador: “Página X de Y”.

### 6.4 Sin resultados

Si no hay reseñas para los filtros elegidos, verá: *“No hay reseñas para los filtros seleccionados.”* Amplíe fechas o quite filtros.

### 6.5 Errores de carga

Si falla la conexión con el servidor de datos, aparece un panel **Error al cargar reseñas** con el detalle. Contacte al administrador si persiste.

---

## 7. Flujo completo: desde la carga hasta el análisis

Este es el ciclo de trabajo típico para incorporar nuevas reseñas.

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│   UPLOAD    │ ──► │  Pendientes  │ ──► │  New Analysis   │ ──► │  Pipeline    │
│  (subir)    │     │  (almacén)   │     │  (iniciar IA)   │     │  (proceso)   │
└─────────────┘     └──────────────┘     └─────────────────┘     └──────────────┘
                                                                              │
                                                                              ▼
                                                                    Dashboard / Reviews
```

### Paso 1 — Subir archivo (Upload)

Véase sección 8.

### Paso 2 — Archivo pendiente

Tras subir, el archivo aparece en la tabla **Pendientes** (blobs en almacenamiento aún no procesados por el pipeline).

### Paso 3 — Iniciar análisis (New Analysis)

1. En el menú lateral, pulse **New Analysis**.
2. En el cuadro de diálogo:
  - **Archivo pendiente:** elija el archivo de la lista (nombre y tamaño).
  - **Plataforma:** indique el origen — Booking, TripAdvisor, Google u **Otro**.
3. Pulse **Iniciar**.

**Importante:**

- La operación puede tardar **varios minutos**. Recibirá un aviso en pantalla y, según configuración, **notificación por correo** cuando termine.
- Un mismo archivo no puede enviarse dos veces en la **misma sesión del navegador** (aparecerá como “ya enviado”).
- Si no hay archivos pendientes, el selector estará vacío: primero suba un archivo en Upload.

### Paso 4 — Seguimiento en Pipeline

En Upload, la sección **Historial / Pipeline** muestra el estado de cada archivo procesado:


| Tipo de estado                  | Significado habitual                         |
| ------------------------------- | -------------------------------------------- |
| En curso (animación)            | Procesamiento activo                         |
| Completado / cleaned / topicado | Finalizado correctamente                     |
| Error                           | Falló; revise el mensaje de error en la fila |


Cuando el pipeline termina, las métricas del **Dashboard** y las reseñas en **Reviews** reflejan los nuevos datos (puede requerir refrescar la página o esperar al recálculo programado).

---

## 8. Upload — Carga de archivos

### 8.1 Zona de subida

- **Arrastre y suelte** un archivo sobre la zona punteada, o
- Pulse **Browse files** para elegirlo en el explorador.

**Formatos aceptados:** CSV  
**Formato recomendado para el análisis:** **CSV** con la estructura descrita abajo.  
**Tamaño máximo:** 50 MB.

### 8.2 Formato esperado del archivo

El pipeline de verificación y limpieza espera un **CSV** con encabezados en la primera fila. Cada fila representa **una reseña**.

#### Columnas


| Columna       | Obligatoria | Descripción                                                                                                                                             |
| ------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `review`      | **Sí**      | Texto de la reseña del huésped. No puede ir vacío en la mayoría de filas (si más del 50 % están vacías, el archivo se rechaza).                         |
| `fecha`       | **Sí**      | Fecha de la reseña en formato **ISO 8601**: `AAAA-MM-DD` (ej. `2025-11-15`) o con hora `AAAA-MM-DDTHH:MM:SS`. Todas las filas deben tener fecha válida. |
| `sentimiento` | No          | Etiqueta previa (`positivo`, `negativo`, `neutro`, etc.). Se conserva si existe; el sistema puede recalcular sentimiento con IA.                        |
| `idioma`      | No          | Código de idioma (ej. `es`, `en`). Si no se envía, el pipeline puede detectarlo automáticamente.                                                        |


**Nota:** El origen de las reseñas (**Booking**, **TripAdvisor**, **Google**, etc.) **no va en el CSV**. Se elige al pulsar **New Analysis** → **Plataforma**.

#### Reglas rápidas

- Use **coma** como separador y comillas dobles si el texto lleva comas o saltos de línea.
- Codificación recomendada: **UTF-8**.
- No incluya filas de encabezado repetidas ni columnas sin nombre.
- Puede añadir otras columnas (hotel, puntuación, etc.); se ignoran en el procesamiento salvo las listadas arriba.

#### Ejemplo de archivo válido

Nombre sugerido: `reviews_booking_nov2025.csv`

```csv
review,fecha,sentimiento,idioma
"El hotel fue excelente, muy limpio y la cama muy cómoda.",2025-11-02,positivo,es
"Pésimo servicio en recepción y habitación con olor a humedad.",2025-11-05,negativo,es
"Buena ubicación; el desayuno podría mejorar.",2025-11-08,neutro,es
"El wifi funcionaba bien en todo el edificio.",2025-11-10,,es
```

Versión mínima (solo columnas obligatorias):

```csv
review,fecha
"Tuvimos problemas con el aire acondicionado.",2026-01-17
"El wifi funcionaba perfectamente en todo el hotel.",2026-01-27
"Volvería sin dudarlo, una gran experiencia.",2026-01-17
```

#### Errores frecuentes al preparar el archivo


| Problema                                     | Qué ocurre                                               |
| -------------------------------------------- | -------------------------------------------------------- |
| Faltan columnas `review` o `fecha`           | Rechazo con error de estructura (`ESTRUCTURA_INVALIDA`). |
| Fechas en formato `15/11/2025` o texto libre | Rechazo: deben ser ISO (`2025-11-15`).                   |
| Muchas filas sin texto en `review`           | Rechazo si más del 50 % de filas están vacías.           |
| Archivo sin filas de datos                   | Rechazo (`CSV_SIN_DATOS`).                               |


Si exporta desde Excel, guarde como **CSV UTF-8** y revise que los encabezados se llamen exactamente `review` y `fecha` (minúsculas).

### 8.3 Resultado de la subida

- **Éxito:** mensaje con ruta del blob y huella SHA-256 (referencia técnica).
- **Error:** mensajes habituales:
  - Archivo demasiado grande
  - Archivo ya subido anteriormente (`ARCHIVO_YA_SUBIDO`)
  - Otros errores del servidor (texto en pantalla)

Tras una subida exitosa, la sección **Subidas recientes** se actualiza automáticamente.

### 8.4 Subidas recientes

Dos tablas paginadas (20 registros por página):

#### Pendientes

Archivos en almacenamiento **sin iniciar** el pipeline de análisis:


| Columna             | Descripción        |
| ------------------- | ------------------ |
| Archivo             | Nombre del fichero |
| Tamaño              | Peso del archivo   |
| Última modificación | Fecha/hora         |


#### Pipeline / historial

Archivos ya registrados en el proceso:


| Columna   | Descripción                                |
| --------- | ------------------------------------------ |
| Archivo   | Nombre original                            |
| Recepción | Cuándo entró al sistema                    |
| Estado    | Fase actual del procesamiento              |
| Registros | Cantidad de reseñas detectadas (si aplica) |


Use **Anterior** / **Siguiente** en cada tabla para paginar.

---

## 9. Settings — Administración (solo Admin)

Visible solo para rol **admin** en el menú lateral. Incluye **gestión de usuarios** y **umbrales de alerta**.

### 9.1 Gestión de usuarios

#### Listado

Tabla con: ID, nombre, username, hotel, rol, estado (activo/inactivo), fecha de creación y acciones.

- Su propia fila lleva la etiqueta **Tú**.
- No puede **desactivarse ni eliminarse** a usted mismo.

#### Crear usuario

1. Pulse **Nuevo usuario**.
2. Complete:
  - **Nombre completo**
  - **Username** (único)
  - **Contraseña** (mínimo 8 caracteres)
  - **Hotel** (si es admin global; opción “Sin hotel — acceso global”)
  - **Rol:** Admin o Viewer
3. Guarde.

Los administradores **ligados a un hotel** crean usuarios solo para ese hotel (el campo hotel viene prefijado).

#### Editar usuario

- Icono **lápiz**: modificar nombre, username, contraseña (opcional en edición), hotel y rol.
- No puede cambiar su propio rol desde aquí (protección del sistema).

#### Activar / desactivar

- Icono **toggle**: alterna estado activo. Usuarios inactivos no deberían poder iniciar sesión.

#### Eliminar

- Icono **papelera**: pide confirmación antes de borrar (no disponible en su propia cuenta).

#### Paginación

15 usuarios por página; flechas al pie de la tabla.

### 9.2 Umbrales de alerta (tópicos)

Define el **porcentaje mínimo de score negativo** para que un tópico genere alerta en el Dashboard.

- Tópicos **clave** y **adicionales** en tablas separadas.
- Para cambiar un umbral: pase el ratón sobre el valor → icono **editar** → número entre **0 y 100** → ✓ guardar o ✗ cancelar (también **Enter** / **Escape** en teclado).

#### Recalcular semestre

Botón **Recalcular semestre**:

- Recalcula métricas de los **últimos 6 meses naturales** (incluido el mes actual) para el hotel del contexto.
- Operación **lenta**; sobrescribe métricas existentes.
- Confirme en el diálogo. Al terminar, verá notificación de éxito o de fallos parciales.

---

## 10. Consejos y buenas prácticas

1. **Periodicidad:** use “último mes” para operación diaria; “semestre” para comités de dirección.
2. **Investigación:** combine Dashboard (qué pasa) con Reviews (qué dijo el huésped).
3. **Cargas:** un archivo por plataforma/origen facilita el análisis; indique la plataforma correcta en New Analysis.
4. **Duplicados:** si el sistema rechaza un archivo ya subido, no lo vuelva a cargar; revise Pendientes/Pipeline.
5. **Sesión:** si varias personas usan el mismo equipo, cierre sesión al terminar.
6. **Errores persistentes:** anote el mensaje exacto y el código (si aparece) para soporte técnico.

---

## 11. Preguntas frecuentes

**¿Olvidé mi contraseña?**  
Contacte al administrador. La aplicación no incluye recuperación automática en pantalla.

**¿Por qué no veo Settings?**  
Su cuenta es **viewer**. Solo los **admin** acceden a administración.

**¿Por qué el Dashboard está vacío o con errores?**  
Puede no haber reseñas procesadas aún, fallo temporal del servidor o período sin datos. Compruebe Upload/Pipeline y reintente más tarde.

**¿Puedo exportar datos desde la app?**  
La interfaz actual está orientada a consulta en pantalla. Exportaciones, si existen, serían vía procesos externos acordados con TI.

**¿New Analysis no hace nada?**  
Verifique que hay archivos en **Pendientes**, que no los marcó ya como enviados en esta sesión, y que exista conectividad con el servicio de análisis (configuración del entorno).

**¿Cuánto tardan los análisis?**  
Varios minutos u horas según volumen; espere el correo de notificación o revise el estado en Pipeline.

---

## 12. Glosario breve


| Término              | Significado                                                |
| -------------------- | ---------------------------------------------------------- |
| **Sentimiento**      | Clasificación IA: positivo, negativo o neutro              |
| **Tópico**           | Tema detectado en la reseña (ej. limpieza, desayuno)       |
| **Pain point**       | Aspecto recurrente con impacto negativo                    |
| **Pipeline**         | Cadena de procesamiento automático del archivo             |
| **Blob**             | Archivo almacenado en la nube antes/durante el proceso     |
| **KPI**              | Indicador clave de rendimiento                             |
| **Umbral de alerta** | Porcentaje a partir del cual un tópico se considera riesgo |


---

## 13. Soporte

Para incidencias (acceso, errores de carga, datos incorrectos o permisos), contacte al **administrador de Sentiment AI** de su organización con:

- Su **username**
- **Hotel** asignado
- **Pantalla** y acción realizada
- **Captura** del mensaje de error, si es posible
- **Fecha y hora** aproximada

---

*Documento generado para la aplicación web Sentiment AI (Next.js) del proyecto OLH. Actualice este manual cuando se incorporen nuevas pantallas o flujos.*