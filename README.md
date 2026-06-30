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

## Verificación segura de WhatsApp

El CRM incluye una sección **Verificar WhatsApp** para identificar si un prospecto con teléfono abre chat en WhatsApp Web. Esta función **solo verifica disponibilidad**: no escribe textos, no envía mensajes y no debe usarse para envíos masivos.

### Uso recomendado

1. Instala Playwright y Chromium si aún no lo hiciste:

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

2. Abre WhatsApp Web una vez e inicia sesión escaneando el QR cuando el sistema lo solicite.
3. Verifica pocos prospectos por sesión. Se recomienda revisar máximo **20-50 números por sesión**.
4. No uses esta función para spam ni para envíos masivos.

### Desde consola

Ejecuta:

```bash
python main.py
```

Luego entra a **Verificar WhatsApp**. Las opciones disponibles son:

1. Verificar un prospecto por ID.
2. Verificar próximos 20 prospectos de prioridad Alta.
3. Verificar prospectos seleccionados por IDs.
4. Ver resultados de WhatsApp.

No existe una opción para verificar todos los prospectos.

### Desde Streamlit

Ejecuta:

```bash
streamlit run app.py
```

Abre la sección **Verificar WhatsApp** para ver métricas de pendientes, WhatsApp Sí, WhatsApp No y errores. También puedes verificar los próximos 20 prospectos de prioridad Alta o ingresar IDs específicos.

### Columnas de Excel

La verificación agrega y actualiza estas columnas en `prospectos_restaurantes.xlsx`:

- `WhatsApp`: `Pendiente`, `Sí`, `No` o `Error`.
- `Fecha_Verificacion_WhatsApp`: fecha y hora de la última verificación.
- `Error_WhatsApp`: detalle del error cuando no se puede determinar el resultado.

### Reglas de seguridad aplicadas

- Solo verifica prospectos con teléfono.
- No vuelve a verificar prospectos ya marcados como `Sí` o `No`, salvo confirmación/selección explícita.
- Procesa máximo 20 verificaciones por corrida por defecto.
- Espera entre 4 y 9 segundos aleatorios entre verificaciones.
- Cada 10 verificaciones realiza una pausa larga de 30 a 60 segundos.
- Guarda el Excel después de cada verificación.
- Si ocurre un error, lo guarda en `Error_WhatsApp` y continúa con el siguiente prospecto.
