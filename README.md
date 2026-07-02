# CRM local para prospectar restaurantes y generar demos

Herramienta en Python para buscar restaurantes en Google Maps, guardarlos en Excel sin duplicados, clasificarlos por prioridad y crear carpetas de demo web usando una plantilla React + Vite existente.

## Instalación

### Dependencias Python

```bash
pip install -r requirements.txt
```

### Playwright

```bash
python -m playwright install chromium
```

### GitHub CLI

Instala GitHub CLI desde:

```text
https://cli.github.com/
```

Inicia sesión una vez:

```bash
gh auth login
```

### Vercel CLI

```bash
npm i -g vercel
```

Inicia sesión una vez:

```bash
vercel login
```

## Ejecutar CRM

### Interfaz gráfica (Streamlit)

```bash
streamlit run app.py
```

### Consola

```bash
python main.py
```

Menú disponible:

1. Buscar nuevos prospectos
2. Ver prospectos
3. Ver prospectos de prioridad alta
4. Cambiar estado
5. Agregar link de demo
6. Generar demo completa
7. Generar demos en lote
8. Exportar lista filtrada
9. Salir

## Interfaz gráfica con Streamlit

La nueva interfaz web mantiene la consola intacta y permite operar el CRM desde el navegador. Incluye:

- Buscar prospectos por nichos, zonas y máximo por búsqueda.
- Ver `prospectos_restaurantes.xlsx` en una tabla interactiva con filtros por prioridad, estado, web y nicho.
- Gestionar **Prospectos con WhatsApp** y **Prospectos sin WhatsApp** en secciones separadas con métricas, filtros, acciones rápidas y guardado inmediato en Excel.
- Revisar métricas de total de prospectos, prioridad alta, sin página web, contactados, interesados y cerrados.
- Generar demo completa para un prospecto seleccionado por ID o nombre.
- Exportar Excel de todos los prospectos, prioridad alta, sin página web o contactados.
- Guardar configuración local en `config.json` para plantilla React, carpeta Clientes, GitHub y Vercel.

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Generar demo completa

Desde `python main.py`, elige **6. Generar demo completa**. El CRM muestra los prospectos disponibles, pide un único ID y coordina automáticamente:

1. Crear carpeta local del cliente copiando la plantilla React + Vite.
2. Crear `restaurant.json`, `prompt_codex.txt` y `codex_task.md`.
3. Inicializar Git, crear el primer commit y subir a GitHub con GitHub CLI.
4. Si el repositorio ya existe, usar un nombre alternativo como `nombre-web-2` o `nombre-web-3`.
5. Publicar la demo con Vercel CLI usando `vercel --prod --yes`.
6. Guardar en Excel `Demo`, `Repositorio_GitHub`, `Vercel_URL`, `Vercel_Project_Name`, `Codex_Task`, `Restaurant_JSON`, `Estado` y `Notas`.
7. Cambiar el estado a `Demo publicada` cuando el deploy de Vercel finaliza correctamente.
8. Copiar `codex_task.md` al portapapeles con `pyperclip`.
9. Abrir `https://chatgpt.com/codex`.
10. Abrir la carpeta local en VS Code con `code .` / `code <carpeta>`.
11. Mostrar un resumen final con carpeta local, repositorio GitHub, URL de Vercel y archivos de prompt.

Si Vercel falla, el flujo no se detiene: el error se guarda en `Notas` y se muestra un mensaje claro.

## Excel de trabajo

El archivo principal es:

```text
prospectos_restaurantes.xlsx
```

Columnas principales:

- ID
- Nombre
- Nicho
- Telefono
- Tiene_web
- Sitio_web
- Rating
- Resenas
- Direccion
- Horario
- Categoria
- Google_Maps
- Prioridad
- Estado
- Demo
- Repositorio_GitHub
- Vercel_URL
- Vercel_Project_Name
- Codex_Task
- Restaurant_JSON
- Notas
- Fecha_busqueda

## Notas importantes

- No automatiza WhatsApp.
- Prueba manual de reseñas en Google Maps: agrega negocios con reseñas visibles como `123 reseñas`, `123 opiniones`, `(1,234)`, `1.234 opiniones` o `123 reviews` y verifica que la columna `Resenas` de `prospectos_restaurantes.xlsx` y de `export_prospectos.xlsx` se llene con enteros (`123`, `1234`, etc.).
- No usa APIs pagadas.
- No usa Apify.
- No usa Claude.
- No usa Tailwind.
- Mantiene React + Vite.

## Dashboard visual de ventas

La pantalla **Dashboard** de Streamlit es ahora la vista principal para administrar cientos de prospectos sin depender solamente de una tabla.

### Cómo usar el dashboard

1. Ejecuta:

```bash
streamlit run app.py
```

2. Abre la sección **Dashboard** en la barra lateral.
3. Revisa las métricas superiores: total de prospectos, nuevos, contactados, respondieron, interesados, demo enviada, negociación, clientes, perdidos, demos creadas, repositorios y deploys.
4. Usa el **Pipeline visual** para ver el embudo comercial por estado. Cada columna muestra el conteo y tarjetas resumidas de prospectos.
5. Usa la tabla inferior como vista secundaria para revisar o auditar la base filtrada.

### Cómo cambiar estados

En cada tarjeta puedes cambiar el estado con acciones rápidas:

- Contactado
- Respondió
- Interesado
- Demo enviada
- Negociación
- Cliente
- Perdido

También puedes abrir **Más acciones**, elegir cualquier estado del pipeline y presionar **Guardar estado**. Los cambios se guardan inmediatamente en `prospectos_restaurantes.xlsx`.

### Cómo programar seguimientos

Desde cada tarjeta puedes usar:

- **+3 días** para programar el próximo seguimiento a tres días.
- **+7 días** para programarlo a una semana.

En la **Vista detalle** también puedes editar manualmente `Fecha último contacto`, `Fecha próximo seguimiento`, `Persona de contacto`, `Canal`, `Probabilidad de cierre`, `Valor estimado` y notas. Todo se persiste inmediatamente en `prospectos_restaurantes.xlsx`.

### Cómo usar “Hoy qué hago”

La sección **Hoy qué hago** aparece arriba del dashboard y ordena acciones prioritarias del día:

1. Seguimientos vencidos o con fecha de hoy.
2. Interesados sin próximo seguimiento.
3. Demos creadas sin enviar.
4. Prospectos que respondieron pero no tienen siguiente paso.
5. Negociaciones abiertas.

Abre cada acción para ver la tarjeta del prospecto, contactar por WhatsApp, abrir Google Maps, actualizar estado, agregar notas o programar el siguiente seguimiento.

### Filtros disponibles

El dashboard incluye filtros por estado, prioridad, nicho, si tiene web, demo creada, repositorio, deploy, seguimiento vencido, rango de rating y rango de reseñas.

## Gestión comercial por WhatsApp

La interfaz de Streamlit agrega dos secciones específicas para separar el trabajo comercial según la columna `WhatsApp` de `prospectos_restaurantes.xlsx`:

### Prospectos con WhatsApp

Muestra únicamente registros con `WhatsApp = Sí`. Incluye métricas de total con WhatsApp, pendientes, contactados, interesados, demos enviadas y clientes. La tabla muestra teléfono limpio, estado, prioridad, reseñas, links de Google Maps, demo, repositorio, Vercel, fechas de seguimiento y notas.

Desde esta sección puedes:

- Filtrar por `Estado`, `Prioridad`, `Demo`, `Nicho`, nombre y reseñas mínimas.
- Cambiar `Estado` con estados comerciales como `Pendiente`, `Contactado`, `Respondió`, `Interesado`, `Demo enviada`, `Cotización enviada`, `Negociación`, `Cliente`, `Perdido` y `Pospuesto`.
- Editar `Notas`, `Ultimo_Contacto`, `Proximo_Seguimiento`, `Persona_Contacto`, `Probabilidad_Cierre` y `Valor_Estimado`.
- Abrir Google Maps, WhatsApp y demo cuando existan enlaces disponibles.
- Guardar cada cambio inmediatamente en `prospectos_restaurantes.xlsx` usando el `ID` como referencia principal.

### Prospectos sin WhatsApp

Muestra únicamente registros con `WhatsApp = No`. Está pensada para canales alternativos como llamada telefónica, Instagram, Facebook, correo, visita o revisión posterior. Incluye métricas de total sin WhatsApp, alta prioridad sin WhatsApp, para llamar, pospuestos y contactados por otro canal.

Desde esta sección puedes:

- Filtrar por `Prioridad`, `Estado`, `Nicho`, `Demo`, nombre y reseñas mínimas.
- Cambiar `Estado` con opciones como `Sin WhatsApp`, `Llamar`, `Buscar Instagram`, `Buscar Facebook`, `Buscar correo`, `Contactado por llamada`, `Contactado por redes`, `No interesado` y `Pospuesto`.
- Abrir Google Maps, copiar visualmente el teléfono limpio, abrir sitio web si existe, marcar para llamada o marcar pospuesto.
- Editar notas y datos de seguimiento comercial con guardado inmediato en `prospectos_restaurantes.xlsx`.

Si faltan columnas comerciales (`Ultimo_Contacto`, `Proximo_Seguimiento`, `Persona_Contacto`, `Probabilidad_Cierre`, `Valor_Estimado`, `Canal` o `Historial_Comercial`), la app las crea automáticamente al cargar y guardar el Excel.

## Verificación manual de WhatsApp

El CRM no automatiza WhatsApp Web con Playwright para validar números. La revisión queda como un flujo manual asistido: la app solo genera enlaces `https://wa.me/52XXXXXXXXXX`, muestra el teléfono normalizado para copiarlo y guarda cambios únicamente cuando una persona presiona un botón de decisión.

Columnas usadas:

- `WhatsApp`: `Pendiente`, `Sí` o `No`.
- `Fecha_Verificacion_WhatsApp`: fecha y hora en que se registró manualmente la revisión.
- `Estado`: se actualiza a `WhatsApp verificado` o `Sin WhatsApp` solo cuando se confirma manualmente.
- `Notas`: agrega `Revisar WhatsApp después` cuando se elige revisar luego.

Abre la sección **Verificar WhatsApp**, que muestra el encabezado **Verificación manual de WhatsApp**. Desde ahí puedes:

1. Ver solo prospectos con `WhatsApp = Pendiente`.
2. Ver solo prospectos que tienen teléfono capturado.
3. Filtrar por `Prioridad`, `Estado` y `Nicho`.
4. Definir la `Cantidad a mostrar`.
5. Abrir el enlace `https://wa.me/52XXXXXXXXXX` con **Abrir WhatsApp**.
6. Copiar manualmente el número normalizado o el enlace mostrado si el navegador no abre WhatsApp.
7. Registrar la decisión con **Sí tiene WhatsApp**, **No tiene WhatsApp** o **Revisar después**.

Al pulsar **Sí tiene WhatsApp**, la app guarda inmediatamente el Excel con:

- `WhatsApp = Sí`
- `Fecha_Verificacion_WhatsApp = fecha actual`
- `Estado = WhatsApp verificado`

Al pulsar **No tiene WhatsApp**, la app guarda inmediatamente el Excel con:

- `WhatsApp = No`
- `Fecha_Verificacion_WhatsApp = fecha actual`
- `Estado = Sin WhatsApp`

Al pulsar **Revisar después**, la app mantiene `WhatsApp = Pendiente`, agrega `Revisar WhatsApp después` en `Notas` y guarda el Excel.

Reglas de seguridad del flujo:

- No envía mensajes automáticamente.
- No intenta detectar WhatsApp automáticamente.
- No usa Playwright para verificar WhatsApp.
- No actualiza el estado hasta que presionas un botón de decisión.
- Solo abre enlaces `https://wa.me/...` para revisión humana.
