# 🌾 Estrategias de Cobertura - Espartina S.A.

Dashboard completo para análisis de coberturas, FAS teórico y crushing de granos.

![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)

---

## 📋 Características

✅ **Scraping automático** de precios FOB desde Bolsa de Cereales  
✅ **Integración con Google Sheets** para datos A3  
✅ **Cálculos automáticos** de FAS teórico, retenciones y crushing  
✅ **Selectores dinámicos** de posiciones y cultivos  
✅ **Cache inteligente** para optimizar performance  
✅ **Diseño profesional** respetando estética de Espartina  
✅ **Deploy gratuito** en Streamlit Cloud  

---

## 🚀 Instalación Local

### Paso 1: Clonar o descargar los archivos

Asegúrate de tener todos estos archivos en una carpeta:

```
estrategias-cobertura/
├── app.py                  # Aplicación principal
├── scraper.py             # Scraper de Bolsa de Cereales
├── calculadora.py         # Cálculos financieros
├── google_sheets.py       # Integración Google Sheets
├── requirements.txt       # Dependencias
├── test_app.py           # Tests
└── README.md             # Esta documentación
```

### Paso 2: Instalar Python

**Verifica** si ya tienes Python instalado:

```bash
python --version
```

Si no lo tienes, descárgalo desde: https://www.python.org/downloads/

**Versión recomendada:** Python 3.9 o superior

### Paso 3: Crear entorno virtual (recomendado)

```bash
# En Windows
python -m venv venv
venv\Scripts\activate

# En Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### Paso 4: Instalar dependencias

```bash
pip install -r requirements.txt
```

Esto instalará:
- ✅ Streamlit (framework web)
- ✅ Pandas (manipulación de datos)
- ✅ Selenium (scraping)
- ✅ BeautifulSoup (parsing HTML)
- ✅ Requests (HTTP requests)
- ✅ WebDriver Manager (drivers Chrome)

### Paso 5: Ejecutar tests

**IMPORTANTE:** Antes de ejecutar la app, verifica que todo funcione:

```bash
python test_app.py
```

Deberías ver algo como:

```
═══════════════════════════════════════════════════
   TESTS DE FUNCIONALIDAD - ESTRATEGIAS DE COBERTURA
═══════════════════════════════════════════════════

═══ TEST 1: IMPORTS ═══
✓ Streamlit → v1.31.0
✓ Pandas → v2.2.0
✓ Selenium → OK
✓ BeautifulSoup → OK
✓ Requests → OK

═══ TEST 2: MÓDULOS LOCALES ═══
✓ scraper.py → 3 meses cargados
✓ calculadora.py → FAS = $312.52
✓ google_sheets.py → 3 filas

...

═══ RESUMEN ═══
✓ Imports
✓ Módulos locales
✓ Cálculos financieros
✓ Datos Bolsa
✓ Google Sheets
✓ Casos extremos

═══════════════════════════════════════════════════
✓ TODOS LOS TESTS PASARON (6/6)
```

### Paso 6: Ejecutar la aplicación

```bash
streamlit run app.py
```

Se abrirá automáticamente en tu navegador en: **http://localhost:8501**

---

## 📱 Uso de la Aplicación

### 1️⃣ **Actualizar precios FOB**

1. En el **sidebar** (izquierda), presiona **"🌾 Actualizar FOB"**
2. Espera unos segundos mientras scrappea la Bolsa de Cereales
3. Verás un ✓ con la hora de actualización cuando termine

### 2️⃣ **Seleccionar parámetros**

- **Cultivo:** Soja, Maíz, Trigo o Girasol
- **Posición:** Mes de la Bolsa (ABR 2026, MAY 2026, etc.)
- **Precio FAS manual:** Opcional, para comparar con objetivo

### 3️⃣ **Ver cálculos**

Ve a la pestaña **"🧮 Retenciones & FAS Teórico"**

Verás automáticamente:

**Exportación grano:**
- FOB índice
- Retención (24% para soja, 12% para maíz/trigo)
- Fobbing
- **FAS Teórico (CTP)**

**Crushing (solo soja):**
- FOB Aceite × Coef.
- FOB Harina × Coef.
- Retenciones subproductos
- Fobbing subproductos
- Gasto industrial
- **FAS Crushing**
- **Spread** (Crushing vs Teórico)

### 4️⃣ **Sincronizar Google Sheets**

Presiona **"📡 Sincronizar A3"** para obtener datos de tu planilla.

---

## ⚙️ Configuración

### Google Sheets

Para conectar tu propia planilla de Google Sheets:

1. Abre `google_sheets.py`
2. Encuentra esta línea:

```python
SHEET_ID = "2PACX-1vTYR1G5tN0wEOnBhbHOEElP5gF0UWctmCSOSLmjb8_Zw38dLkGMfTTOW51iCQqwROmkUOLsMShcLwnn"
```

3. Reemplázala con el ID de tu sheet (lo encuentras en la URL):

```
https://docs.google.com/spreadsheets/d/e/[ESTE_ES_EL_ID]/pub?output=csv
```

4. Asegúrate de que tu sheet esté **publicado como web**:
   - Archivo → Compartir → Publicar en la web
   - Formato: CSV

---

## 🌐 Deploy en Streamlit Cloud (GRATIS)

### Paso 1: Crear repositorio en GitHub

1. Ve a https://github.com y crea una cuenta (si no tienes)
2. Crea un nuevo repositorio: **estrategias-cobertura**
3. Sube todos los archivos del proyecto

### Paso 2: Deploy en Streamlit Cloud

1. Ve a https://streamlit.io/cloud
2. Inicia sesión con tu cuenta de GitHub
3. Click en **"New app"**
4. Selecciona:
   - **Repository:** tu repositorio
   - **Branch:** main
   - **Main file path:** app.py
5. Click en **"Deploy!"**

🎉 **¡Listo!** Tu app estará online en: `https://tu-usuario-estrategias.streamlit.app`

### Paso 3: Compartir con tu equipo

Simplemente comparte la URL. Cualquiera puede acceder sin instalar nada.

---

## 🧪 Tests

### Ejecutar todos los tests

```bash
python test_app.py
```

### Tests individuales

Puedes ejecutar tests específicos editando `test_app.py`:

```python
# Solo test de cálculos
test_calculos()

# Solo test de scraper
test_datos_bolsa()
```

### Coverage de tests

Los tests cubren:

- ✅ Imports y dependencias
- ✅ Módulos locales (scraper, calculadora, google_sheets)
- ✅ Cálculos financieros (FAS, retenciones, crushing)
- ✅ Estructura de datos de la Bolsa
- ✅ Integración Google Sheets
- ✅ Casos extremos y validaciones

---

## 🎨 Personalización

### Colores y estilo

Los colores de Espartina están definidos en `app.py`:

```python
:root {
    --es-green: #1a5430;    # Verde Espartina
    --es-gold: #c9a961;     # Dorado Espartina
    --bg-primary: #f8f9fa;
    --text-primary: #2d3748;
}
```

Puedes cambiarlos editando el bloque `st.markdown(""" <style> ... </style> """)`

### Parámetros de cálculo

En `calculadora.py` puedes ajustar:

```python
parametros = {
    'soja': {'retencion_pct': 24.0, 'fobbing': 12.0},
    'maiz': {'retencion_pct': 12.0, 'fobbing': 12.0},
    'trigo': {'retencion_pct': 12.0, 'fobbing': 12.0},
    'girasol': {'retencion_pct': 7.0, 'fobbing': 12.0}
}
```

---

## 🐛 Troubleshooting

### Error: "ModuleNotFoundError"

```bash
pip install -r requirements.txt
```

### Error: "ChromeDriver not found"

El ChromeDriver se descarga automáticamente. Si falla:

```bash
pip install --upgrade webdriver-manager
```

### Error de CORS con Google Sheets

Asegúrate de que tu Google Sheet esté **publicado en la web**:
- Archivo → Compartir → Publicar en la web

### La app no carga datos de la Bolsa

1. Verifica tu conexión a internet
2. Comprueba que https://preciosfob.bolsadecereales.com esté online
3. Prueba con datos mock editando `app.py`:

```python
from scraper import obtener_datos_bolsa_mock as obtener_datos_bolsa
```

---

## 📊 Estructura de Datos

### Formato de datos de la Bolsa

```python
{
    'ABR 2026': {
        'soja': 427.0,
        'maiz': 215.0,
        'trigo': 224.0,
        'harina': 357.0,
        'aceite': 1191.0,
        'aceiteGirasol': 1303.0
    },
    'MAY 2026': { ... },
    ...
}
```

### Formato de resultado de cálculo

```python
{
    'fob_indice': 427.0,
    'retencion_pct': 24.0,
    'retencion_valor': 102.48,
    'fobbing': 12.0,
    'fas_teorico': 312.52,
    'precio_fas_manual': None,
    'spread': None
}
```

---

## 🤝 Contribuir

Para agregar funcionalidades:

1. Edita los módulos correspondientes
2. Agrega tests en `test_app.py`
3. Ejecuta `python test_app.py` para verificar
4. Documenta los cambios

---

## 📝 Licencia

Uso interno de Espartina S.A.

---

## 📞 Soporte

Para dudas o problemas:
- Revisa la sección **Troubleshooting**
- Ejecuta `python test_app.py` para diagnosticar
- Verifica los logs en la consola de Streamlit

---

## 🎯 Próximas Funcionalidades

- [ ] Simulador completo de estrategias de cobertura
- [ ] Exportación a PDF
- [ ] Histórico de precios y gráficos
- [ ] Alertas de precios
- [ ] Comparación de estrategias

---

**Desarrollado para Espartina S.A. 🌾**
