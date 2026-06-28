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
