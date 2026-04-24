# StoreVision

![image](https://subir-imagen.com/images/2026/04/24/Screenshot-from-2026-04-24-06-53-42.png)

Sistema web de gestión de ventas e inventario para tiendas colombianas, desarrollado como proyecto académico en el curso de Ingeniería de Software III — Universidad Libre.

Construido sobre **FastAPI**, un framework moderno de Python para APIs REST de alto rendimiento. FastAPI se encarga de recibir las peticiones HTTP del navegador, validar los datos de entrada y enrutar cada solicitud al controlador correspondiente. Su sistema de dependencias permite inyectar la sesión de base de datos en cada endpoint de forma automática, lo que facilita el aislamiento entre pruebas y el manejo limpio de transacciones.

---

## Tabla de contenido

- [¿Qué hace StoreVision?](#qué-hace-storevision)
- [Arquitectura del proyecto](#arquitectura-del-proyecto)
- [Tecnologías utilizadas](#tecnologías-utilizadas)
- [Requisitos previos](#requisitos-previos)
- [Instalación y puesta en marcha](#instalación-y-puesta-en-marcha)
- [Cómo usar la tienda](#cómo-usar-la-tienda)
- [Pruebas automatizadas](#pruebas-automatizadas)
- [Estructura de carpetas](#estructura-de-carpetas)

---

## ¿Qué hace StoreVision?

StoreVision digitaliza los procesos manuales de una tienda de barrio. Desde una sola interfaz web puedes:

- Registrar ventas en caja y descontar el stock automáticamente.
- Controlar entradas y salidas de inventario con trazabilidad completa.
- Recibir alertas cuando un producto baja del stock mínimo configurado.
- Consultar reportes de ventas, ranking de productos y balance económico.
- Gestionar usuarios con roles diferenciados: **administradora** y **cajero**.

---

## Arquitectura del proyecto

El proyecto sigue el patrón **Modelo — Vista — Controlador (MVC)**:

```
models/
  database.py          → Conexión y sesión de base de datos (SQLAlchemy)
  modelos.py           → Definición de tablas: Usuario, Producto, Venta, etc.

controllers/
  auth_controller.py   → Lógica de autenticación y gestión de usuarios
  ventas_controller.py → Lógica de registro y anulación de ventas
  inventario_controller.py → Lógica de movimientos y alertas de stock
  reportes_controller.py   → Lógica de balance económico e indicadores

views/
  api_views.py         → Rutas HTTP (FastAPI): recibe peticiones, llama al
                         controlador correspondiente y retorna la respuesta

templates/
  index.html           → Interfaz web (SPA en HTML + JS vanilla)
```

**Flujo de una petición:**

```
Navegador → api_views.py (Vista) → controlador (Controlador) → modelos.py (Modelo) → SQLite
```

La Vista no contiene lógica de negocio. El Controlador no sabe nada de HTTP. El Modelo solo define la estructura de datos.

---

## Tecnologías utilizadas

| Componente | Tecnología |
|---|---|
| Framework web | FastAPI 0.134 |
| ORM | SQLAlchemy 2.0 |
| Base de datos | SQLite (archivo local `storevision.db`) |
| Autenticación | Passlib + bcrypt |
| Plantillas HTML | Jinja2 |
| Servidor | Uvicorn |
| Pruebas | pytest + httpx |

---

## Requisitos previos

Antes de empezar necesitas tener instalado:

- **Python 3.12 (versiones superiores de alguna manera generan incompatibilidad con las dependencias)** — verificar con `python --version` o `python3 --version`
- **Git** — verificar con `git --version`

---

## Instalación y puesta en marcha

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/storevision.git
cd storevision
```

### 2. Crear el entorno virtual

Un entorno virtual aísla las dependencias del proyecto para que no interfieran con otros proyectos de Python en tu máquina.

**En macOS / Linux:**
```bash
python3.12 -m venv .venv
```

**En Windows:**
```bash
python3.12 -m venv .venv
```

### 3. Activar el entorno virtual

Este paso debes repetirlo cada vez que abras una terminal nueva para trabajar con el proyecto.

**En macOS / Linux:**
```bash
source .venv/bin/activate
```

**En Windows (PowerShell):**
```bash
.venv\Scripts\Activate.ps1
```

**En Windows (CMD):**
```bash
.venv\Scripts\activate.bat
```

Cuando el entorno esté activo, verás `(.venv)` al inicio de la línea de tu terminal.

### 4. Instalar dependencias

```bash
pip install -r requirements.txt
```

Esto instala FastAPI, SQLAlchemy, bcrypt, pytest y el resto de librerías necesarias.

### 5. Ejecutar la aplicación

```bash
python main.py
```
Importante estar en la carpeta Prototipo1.

La primera vez que arranques, el sistema crea automáticamente la base de datos con dos usuarios de prueba y 12 productos colombianos de ejemplo. Verás en consola:

```
Iniciando StoreVision...
Datos de ejemplo creados exitosamente
Usuarios de prueba:
- admin@storevision.com / admin123 (Administradora)
- cajero@storevision.com / cajero123 (Cajero)
```

### 6. Abrir en el navegador

Ve a [http://localhost:8000](http://localhost:8000)

---

## Cómo usar la tienda

### Inicio de sesión

Al abrir la aplicación verás el formulario de login. Usa una de las dos cuentas de prueba:

| Rol | Email | Contraseña | Acceso |
|---|---|---|---|
| Administradora | admin@storevision.com | admin123 | Completo |
| Cajero | cajero@storevision.com | cajero123 | Solo ventas e inventario básico |

### Dashboard

Muestra un resumen del día: número de ventas, monto total y alertas de inventario activas. Haz clic en **Actualizar** para refrescar los datos.

### Registrar una venta (cajero o admin)

1. Haz clic en **Ventas** en el menú superior.
2. En la sección *Nueva Venta*, selecciona un producto del desplegable.
3. Ingresa la cantidad deseada.
4. Si necesitas agregar más productos a la misma venta, haz clic en **+ Agregar producto**.
5. Haz clic en **Confirmar Venta**.

El stock se descuenta automáticamente. 

### Anular una venta (solo administradora)

1. Ve a la pestaña **Ventas**.
2. En la tabla de ventas del día, haz clic en **Anular** junto a la venta que quieres revertir.
3. Ingresa el motivo de la anulación.
4. Haz clic en **Confirmar Anulación**.

El stock de los productos de esa venta se restaura automáticamente.

### Gestionar inventario

1. Ve a la pestaña **Inventario**.
2. En *Alertas de Stock Bajo* verás los productos que necesitan reabastecimiento.
3. Para registrar una entrada (llega mercancía) o salida (pérdida, ajuste): selecciona el producto, el tipo de movimiento, la cantidad y el motivo, luego haz clic en **Registrar**.
4. Para crear un producto nuevo (solo administradora): completa el formulario en la sección *Nuevo Producto*.

### Reportes (solo administradora)

1. Ve a la pestaña **Reportes**.
2. Selecciona el rango de fechas que quieres analizar.
3. Haz clic en **Generar**.

Verás el balance económico (ventas, costos, utilidad y margen), los indicadores comparativos con el periodo anterior, y el ranking de productos más vendidos.

---

## Pruebas automatizadas

### Estructura de las pruebas

Las pruebas están organizadas en tres niveles, cada uno con un enfoque distinto:

| Archivo | Nivel | Técnica | Qué verifica |
|---|---|---|---|
| `tests/test_pu_unitarias.py` | Unitario | Caja blanca | Cada función de los controladores de forma aislada, sin HTTP ni BD real |
| `tests/test_pi_integracion.py` | Integración | Caja gris | Que las capas funcionan juntas: el controlador escribe en BD y los datos persisten correctamente |
| `tests/test_ps_sistema.py` | Sistema | Caja negra | Flujos HTTP completos de extremo a extremo, como los usaría un usuario real |

Las *fixtures* compartidas (usuarios, productos, sesiones de prueba) están en `tests/conftest.py`.

Una *fixture* define un contexto reutilizable para múltiples pruebas:

- Inicializa recursos (datos, conexiones, archivos, objetos)
- Los entrega a la prueba
- Opcionalmente libera o limpia esos recursos

### Ejecutar todas las pruebas

Con el entorno virtual activo:

```bash
pytest tests/ -v
```

La flag `-v` muestra el nombre de cada test y si pasó o falló.

### Ejecutar solo un nivel

```bash
# Solo unitarias
pytest tests/test_pu_unitarias.py -v

# Solo integración
pytest tests/test_pi_integracion.py -v

# Solo sistema
pytest tests/test_ps_sistema.py -v
```

### Ejecutar un test específico

```bash
pytest tests/test_pu_unitarias.py::TestAlertasStock::test_stock_igual_al_minimo_genera_alerta -v
```

### Ver cobertura de código

```bash
pip install pytest-cov
pytest tests/ --cov=controllers --cov-report=term-missing
```

El reporte muestra qué líneas de los controladores se ejecutaron durante las pruebas y cuáles no.

### Verificar que los tests realmente detectan errores

Para confirmar que un test no es un falso positivo, puedes introducir un bug deliberado y comprobar que el test lo detecta. Por ejemplo, en `controllers/inventario_controller.py` cambia:

```python
# Original
Producto.stock_actual <= Producto.stock_minimo

# Mutación temporal
Producto.stock_actual < Producto.stock_minimo
```

Luego ejecuta:

```bash
pytest tests/test_pu_unitarias.py::TestAlertasStock -v
```

El test `test_stock_igual_al_minimo_genera_alerta` debe **fallar**. Revierte el cambio y vuelve a correr: debe **pasar**. Eso confirma que el test estaba verificando esa lógica específica.

## Estructura de carpetas

```
storevision/
│
├── controllers/
│   ├── auth_controller.py
│   ├── ventas_controller.py
│   ├── inventario_controller.py
│   └── reportes_controller.py
│
├── models/
│   ├── database.py
│   └── modelos.py
│
├── views/
│   └── api_views.py
│
├── templates/
│   └── index.html
│
├── tests/
│   ├── conftest.py
│   ├── test_pu_unitarias.py
│   ├── test_pi_integracion.py
│   └── test_ps_sistema.py
│
├── main.py
├── requirements.txt
└── README.md
```
