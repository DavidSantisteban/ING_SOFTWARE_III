from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
from models.database import crear_tablas, motor
from models import modelos
from views import api_views
import uvicorn
from sqlalchemy.orm import sessionmaker
from controllers.auth_controller import ControladorAutenticacion
from datetime import timezone, timedelta

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Crear tablas y datos de ejemplo
    print("Iniciando StoreVision...")
    crear_tablas()
    await inicializar_datos_ejemplo()
    yield
    # Shutdown: Limpiar recursos si es necesario
    print("Cerrando StoreVision...")

# Crear aplicación FastAPI con lifespan
app = FastAPI(
    title="StoreVision API",
    description="Sistema de gestión para tiendas colombianas",
    version="1.0.0",
    lifespan=lifespan
)

# Montar archivos estáticos y templates
# app.mount("/static", StaticFiles(directory="static"), name="static")

# Incluir rutas
app.include_router(api_views.router)

async def inicializar_datos_ejemplo():

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=motor)
    db = SessionLocal()
    
    try:
        # Verificar si ya existen usuarios
        usuario_existente = db.query(modelos.Usuario).first()
        if not usuario_existente:
            controlador_auth = ControladorAutenticacion(db)
            
            # Crear usuario administradora
            usuario_admin = modelos.Usuario(
                email='admin@storevision.com',
                nombre='María González',
                hashed_password=controlador_auth.obtener_hash_password('admin123'),
                rol='administradora'
            )
            db.add(usuario_admin)
            
            # Crear usuario cajero
            usuario_cajero = modelos.Usuario(
                email='cajero@storevision.com',
                nombre='Carlos Rodríguez',
                hashed_password=controlador_auth.obtener_hash_password('cajero123'),
                rol='cajero'
            )
            db.add(usuario_cajero)
            
            # CREAR SOLO UNA SUCURSAL
            sucursal_principal = modelos.Sucursal(
                nombre="Tienda StoreVision",
                direccion="Carrera 15 # 45-60, Bogotá",
                telefono="+57 601 1234567"
            )
            db.add(sucursal_principal)
            
            # Crear productos típicos colombianos
            productos_colombianos = [
                # Lácteos y Huevos
                {"codigo": "LAC001", "nombre": "Leche Entera Alpina 1L", "precio_venta": 3800, "costo": 2800, "stock_actual": 50, "stock_minimo": 10, "categoria": "Lácteos"},
                {"codigo": "LAC002", "nombre": "Queso Campesino 500g", "precio_venta": 12500, "costo": 8500, "stock_actual": 20, "stock_minimo": 5, "categoria": "Lácteos"},
                {"codigo": "LAC003", "nombre": "Huevos AA x30", "precio_venta": 18500, "costo": 14500, "stock_actual": 30, "stock_minimo": 8, "categoria": "Lácteos"},
                
                # Granos y Enlatados
                {"codigo": "GRA001", "nombre": "Arroz Diana 1kg", "precio_venta": 4500, "costo": 3200, "stock_actual": 40, "stock_minimo": 12, "categoria": "Granos"},
                {"codigo": "GRA002", "nombre": "Fríol Cargamanto 1kg", "precio_venta": 6800, "costo": 4800, "stock_actual": 35, "stock_minimo": 10, "categoria": "Granos"},
                {"codigo": "GRA003", "nombre": "Atún Van Camps 170g", "precio_venta": 5800, "costo": 4200, "stock_actual": 45, "stock_minimo": 15, "categoria": "Enlatados"},
                
                # Aseo y Limpieza
                {"codigo": "ASE001", "nombre": "Jabón Rey 3 unidades", "precio_venta": 7500, "costo": 5200, "stock_actual": 60, "stock_minimo": 20, "categoria": "Aseo"},
                {"codigo": "ASE002", "nombre": "Detergente Líquido 1L", "precio_venta": 12800, "costo": 8900, "stock_actual": 25, "stock_minimo": 8, "categoria": "Aseo"},
                
                # Bebidas
                {"codigo": "BEB001", "nombre": "Coca-Cola 1.5L", "precio_venta": 5800, "costo": 4200, "stock_actual": 65, "stock_minimo": 20, "categoria": "Bebidas"},
                {"codigo": "BEB002", "nombre": "Café Sello Rojo 500g", "precio_venta": 12500, "costo": 8500, "stock_actual": 30, "stock_minimo": 10, "categoria": "Bebidas"},
                
                # Snacks y Dulces
                {"codigo": "SNK001", "nombre": "Papas Margarita 60g", "precio_venta": 2200, "costo": 1500, "stock_actual": 80, "stock_minimo": 25, "categoria": "Snacks"},
                {"codigo": "SNK002", "nombre": "Chocolatina Jet", "precio_venta": 1200, "costo": 800, "stock_actual": 120, "stock_minimo": 40, "categoria": "Snacks"},
            ]
            
            for prod in productos_colombianos:
                producto = modelos.Producto(**prod)
                db.add(producto)
            
            db.commit()
            print("Datos de ejemplo creados exitosamente")
            print("Usuarios de prueba:")
            print("- admin@storevision.com / admin123 (Administradora)")
            print("- cajero@storevision.com / cajero123 (Cajero)")
            print("Productos colombianos creados: 12 productos") 
            print("Sucursal creada: Tienda StoreVision")
        else:
            print("ℹ️  La base de datos ya contiene datos, omitiendo creación de ejemplos")
            
    except Exception as e:
        print(f"Error creando datos de ejemplo: {e}")
        db.rollback()
    finally:
        db.close()

@app.get("/")
async def root():
    return RedirectResponse(url="/")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "message": "StoreVision API está funcionando correctamente",
        "timestamp": modelos.datetime.now(timezone(timedelta(hours=-5))).isoformat()
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)