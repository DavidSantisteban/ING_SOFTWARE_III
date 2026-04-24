"""
conftest.py — Fixtures compartidas para las pruebas de StoreVision
Cada fixture representa un estado del mundo real del Autoservicio Don Julián:
  - Un cajero que registra ventas en caja
  - Una administradora que gestiona productos, anula ventas y revisa reportes
  - Productos con distintos niveles de stock para probar alertas y límites

Base de datos: SQLite en memoria, se crea limpia antes de cada test y se
destruye al terminar, garantizando que los tests no se afecten entre sí.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import Base, obtener_db
from models import modelos
from controllers.auth_controller import ControladorAutenticacion


# BASE DE DATOS DE PRUEBA

engine_prueba = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SesionPrueba = sessionmaker(autocommit=False, autoflush=False, bind=engine_prueba)


@pytest.fixture(scope="function")
def db():
    """
    Sesión de base de datos limpia por cada test.
    """
    Base.metadata.create_all(bind=engine_prueba)
    sesion = SesionPrueba()
    try:
        yield sesion
    finally:
        sesion.close()
        Base.metadata.drop_all(bind=engine_prueba)


@pytest.fixture(scope="function")
def client(db):
    """
    Cliente HTTP que simula peticiones al servidor sin levantarlo realmente.
    """
    from views.api_views import router, usuarios_activos
    from fastapi import FastAPI

    app_prueba = FastAPI()
    app_prueba.include_router(router)
    app_prueba.dependency_overrides[obtener_db] = lambda: (yield db)
    usuarios_activos.clear()

    with TestClient(app_prueba) as c:
        yield c

# USUARIOS — representan los roles reales del negocio (US-12, US-13)

@pytest.fixture
def admin(db):
    """
    Administradora con acceso completo al sistema.
    """
    ctrl = ControladorAutenticacion(db)
    usuario = modelos.Usuario(
        email="admin@storevision.com",
        nombre="María González",
        hashed_password=ctrl.obtener_hash_password("admin123"),
        rol="administradora",
        activo=True,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario

@pytest.fixture
def cajero(db):
    """
    Cajero con acceso limitado: solo puede registrar ventas.
    """
    ctrl = ControladorAutenticacion(db)
    usuario = modelos.Usuario(
        email="cajero@storevision.com",
        nombre="Carlos Rodríguez",
        hashed_password=ctrl.obtener_hash_password("cajero123"),
        rol="cajero",
        activo=True,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario

# SUCURSAL — requerida como FK en cada venta

@pytest.fixture
def sucursal(db):
    s = modelos.Sucursal(nombre="Tienda StoreVision", direccion="Cra 15 #45-60")
    db.add(s)
    db.commit()
    db.refresh(s)
    return s

# PRODUCTOS — cubren los tres escenarios de stock más importantes (US-06, US-07)

@pytest.fixture
def producto(db):
    """
    Producto con stock suficiente para ventas normales.
    """
    p = modelos.Producto(
        codigo="TEST001",
        nombre="Arroz Diana 1kg",
        categoria="Granos",
        precio_venta=4500.0,
        costo=3200.0,
        stock_actual=100,
        stock_minimo=10,
        activo=True,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@pytest.fixture
def producto_en_limite(db):
    """
    Producto exactamente en el umbral mínimo (stock == mínimo).
    """
    p = modelos.Producto(
        codigo="LOW001",
        nombre="Queso Campesino 500g",
        categoria="Lácteos",
        precio_venta=12500.0,
        costo=8500.0,
        stock_actual=5,
        stock_minimo=5,
        activo=True,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@pytest.fixture
def producto_sin_stock(db):
    """
    Producto completamente agotado.
    """
    p = modelos.Producto(
        codigo="ZERO01",
        nombre="Huevos AA x30",
        categoria="Lácteos",
        precio_venta=18500.0,
        costo=14500.0,
        stock_actual=0,
        stock_minimo=8,
        activo=True,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p

# SESIONES HTTP — simulan un usuario ya autenticado haciendo peticiones

@pytest.fixture
def sesion_admin(client, admin, sucursal):
    """
    Header de sesión activa para la administradora.
    """
    r = client.post(
        "/api/login",
        json={"email": "admin@storevision.com", "password": "admin123"},
    )
    assert r.status_code == 200, "El login de admin falló al preparar la sesión"
    return {"session-id": r.json()["session_id"]}


@pytest.fixture
def sesion_cajero(client, cajero, sucursal):
    """
    Header de sesión activa para el cajero.
    """
    r = client.post(
        "/api/login",
        json={"email": "cajero@storevision.com", "password": "cajero123"},
    )
    assert r.status_code == 200, "El login de cajero falló al preparar la sesión"
    return {"session-id": r.json()["session_id"]}