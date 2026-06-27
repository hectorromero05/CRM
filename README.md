# CRM local para prospectar restaurantes y generar demos

Herramienta en Python para buscar restaurantes en Google Maps, guardarlos en Excel sin duplicados, clasificarlos por prioridad y crear carpetas de demo web usando una plantilla React + Vite existente.

## Instalación

```bash
pip install playwright pandas openpyxl
python -m playwright install chromium
```

## Ejecución principal

```bash
python main.py
```

Menú disponible:

1. Buscar nuevos prospectos
2. Ver prospectos
3. Ver prospectos de prioridad alta
4. Cambiar estado
5. Agregar link de demo
6. Generar demo para un prospecto
7. Generar demos en lote
8. Exportar lista filtrada
9. Crear repositorio GitHub
10. Salir

## Buscar prospectos

Desde `python main.py`, elige la opción **1. Buscar nuevos prospectos**. Puedes usar todos los nichos y zonas por defecto o escribir listas separadas por coma.

Nichos incluidos:

- restaurantes
- mariscos
- taquerías
- cafeterías
- desayunos
- hamburguesas
- sushi
- ramen
- pizza

Zonas incluidas:

- Guadalajara
- Zapopan
- Tlaquepaque
- Providencia
- Chapalita
- Americana
- Santa Tere
- Jardines Universidad
- Centro Guadalajara
- Ciudad del Sol

El script genera combinaciones como `mariscos Providencia Guadalajara` o `cafeterías Zapopan`, navega con Playwright en Google Maps e intenta extraer nombre, teléfono, sitio web, rating, reseñas, dirección, horario, categoría y link de Google Maps.

> Nota: Google Maps cambia con frecuencia. El scraper está preparado para no romper todo el proceso si una búsqueda falla, pero puede requerir ajustes de selectores con el tiempo.

## Excel de trabajo

El archivo principal es:

```text
prospectos_restaurantes.xlsx
```

Columnas:

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
- Notas
- Fecha_busqueda
- Repositorio_GitHub

El sistema evita duplicados usando nombre normalizado, teléfono, link de Google Maps y dirección. Si encuentra un registro existente, intenta completar datos faltantes sin crear otra fila.

## Prioridad comercial

La columna `Prioridad` se calcula así:

- **Alta**: no tiene página web, tiene teléfono, rating mayor o igual a 4.3 y más de 80 reseñas.
- **Media**: no tiene página web, tiene teléfono, pero tiene pocas reseñas o menor rating.
- **Baja**: ya tiene página web, no tiene teléfono o tiene poca información.

Estados disponibles:

- Pendiente
- Contactado
- Respondió
- Interesado
- Demo creada
- Demo enviada
- Cotización enviada
- Cerrado
- Perdido

## Generar una demo

Desde `python main.py`, elige **6. Generar demo para un prospecto** y escribe el ID del prospecto.

Por defecto copia la plantilla desde:

```text
C:\Users\carrera\.vscode\codigos\Pagina Web\Plantillas\Restaurante-web
```

Y crea el cliente en:

```text
C:\Users\carrera\.vscode\codigos\Pagina Web\Clientes
```

Ejemplos de carpeta generada:

- `mariscos-el-jarocho-web`
- `quilombo-web`
- `la-patrona-web`

Si ya existe una carpeta, crea una nueva con sufijo, por ejemplo `quilombo-web-2`.

La herramienta intenta reemplazar textos básicos en `index.html`, `App.jsx` y `App.css` cuando existan. También guarda la ruta generada en la columna `Demo` del Excel.

## Generar demos en lote

Desde `python main.py`, elige **7. Generar demos en lote**. El sistema muestra únicamente prospectos que cumplen estas condiciones:

- Prioridad `Alta`
- Estado `Pendiente` o `Contactado`
- Columna `Demo` vacía

La tabla muestra las columnas `ID`, `Nombre`, `Nicho`, `Telefono`, `Rating`, `Resenas` y `Direccion`. Después escribe varios IDs separados por coma, por ejemplo:

```text
201,205,208,214
```

Para cada ID seleccionado, la herramienta:

1. Copia la plantilla base desde:

   ```text
   C:\Users\carrera\.vscode\codigos\Pagina Web\Plantillas\Restaurante-web
   ```

2. Crea la demo dentro de:

   ```text
   C:\Users\carrera\.vscode\codigos\Pagina Web\Clientes
   ```

3. Genera `prompt_codex.txt` personalizado y `restaurant.json` con los datos del negocio.
4. Actualiza inmediatamente el Excel después de cada demo creada, guardando la ruta en `Demo` y cambiando `Estado` a `Demo creada`.
5. Si una carpeta ya existe, no la sobrescribe: crea versiones como `nombre-web-2`, `nombre-web-3`, etc.
6. Si una demo falla, continúa con las demás y muestra el error al final.

Al terminar, muestra un resumen con demos creadas, demos fallidas, ruta de cada carpeta y ruta de cada `prompt_codex.txt`.

Flujo rápido:

```text
python main.py
→ Generar demos en lote
→ escribir IDs separados por coma
```

## prompt_codex.txt

Cada demo incluye un archivo:

```text
prompt_codex.txt
```

Ese prompt contiene:

- Nombre del restaurante
- Teléfono / WhatsApp
- Google Maps
- Dirección
- Nicho
- Estilo sugerido
- Colores sugeridos
- Secciones recomendadas
- Instrucciones para adaptar `App.jsx`, `App.css` e `index.html`
- Rutas sugeridas para imágenes en `public/`
- Texto SEO

Úsalo en Codex para terminar de personalizar la demo visualmente. Las rutas de imagen sugeridas son:

```text
public/hero.jpg
public/logo.png
public/galeria1.jpg
public/galeria2.jpg
public/galeria3.jpg
```

## Crear repositorio GitHub para una demo

Después de generar una demo, puedes subirla automáticamente a un repositorio público nuevo en GitHub desde `python main.py` con la opción **9. Crear repositorio GitHub**.

La opción muestra las columnas `ID`, `Nombre` y `Demo`, pide el ID del prospecto y usa la ruta guardada en `Demo` como carpeta fuente del repositorio. Si la carpeta no existe, si el repositorio ya existe o si hay un problema con Git/GitHub CLI, la operación se cancela mostrando el aviso correspondiente.

### Instalar GitHub CLI

Descarga e instala GitHub CLI desde:

```text
https://cli.github.com/
```

Después inicia sesión una vez:

```bash
gh auth login
```

### Comandos usados

Si la carpeta de la demo todavía no tiene Git, el CRM ejecuta dentro de esa carpeta:

```bash
git init
git add .
git commit -m "Primera versión"
```

Luego configura la rama principal y crea/sube el repositorio público con GitHub CLI:

```bash
git branch -M main
gh repo create NOMBRE_REPO --public --source . --remote origin --push
git push -u origin main
```

El nombre del repositorio se genera a partir del nombre del restaurante: elimina acentos y caracteres especiales, reemplaza espacios por guiones, usa minúsculas y agrega el sufijo `-web`. Ejemplos:

- `Mariscos El Jarocho` → `mariscos-el-jarocho-web`
- `Quilombo` → `quilombo-web`
- `Ruma Café` → `ruma-cafe-web`

Cuando el repositorio se crea correctamente, el CRM actualiza automáticamente el Excel:

- `Estado` = `Repositorio creado`
- `Repositorio_GitHub` = URL del repositorio, por ejemplo `https://github.com/hectorromero05/mariscos-el-jarocho-web`

## Subir después a GitHub y Vercel

1. Abre la carpeta del cliente generada en VS Code.
2. Revisa y adapta la demo con `prompt_codex.txt`.
3. Instala dependencias de la plantilla si hace falta:

```bash
npm install
npm run dev
```

4. Crea un repositorio en GitHub y sube la carpeta:

```bash
git init
git add .
git commit -m "Demo inicial del restaurante"
git branch -M main
git remote add origin URL_DEL_REPO
git push -u origin main
```

5. En Vercel, importa el repositorio y publica la demo.

## Limitaciones intencionales

- No automatiza envío por WhatsApp.
- No intenta saltarse bloqueos de WhatsApp.
- No usa APIs pagadas.
- No usa Apify.
- No usa Claude.
- Solo usa Python, Playwright, pandas, openpyxl y archivos locales.
