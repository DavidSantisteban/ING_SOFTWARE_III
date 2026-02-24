from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
from datetime import datetime, timezone, timedelta

class Usuario(Base):
    __tablename__ = "usuarios"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, index=True, nullable=False)
    nombre = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    rol = Column(String(20), nullable=False)  # administradora, cajero
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone(timedelta(hours=-5)))
    )

class Producto(Base):
    __tablename__ = "productos"
    
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True, index=True)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(String(255))
    precio_venta = Column(Float, nullable=False)
    costo = Column(Float, nullable=False)
    stock_actual = Column(Integer, default=0)
    stock_minimo = Column(Integer, default=5)
    categoria = Column(String(50))
    activo = Column(Boolean, default=True)

class Sucursal(Base):
    __tablename__ = "sucursales"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    direccion = Column(String(255))
    telefono = Column(String(20))
    activa = Column(Boolean, default=True)

class Venta(Base):
    __tablename__ = "ventas"
    
    id = Column(Integer, primary_key=True, index=True)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    total = Column(Float, nullable=False)

    fecha_venta = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone(timedelta(hours=-5)))
    )

    estado = Column(String(20), default="completada")  # completada, anulada
    
    sucursal = relationship("Sucursal")
    usuario = relationship("Usuario")
    items = relationship("ItemVenta", back_populates="venta")


class ItemVenta(Base):
    __tablename__ = "items_venta"
    
    id = Column(Integer, primary_key=True, index=True)
    venta_id = Column(Integer, ForeignKey("ventas.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)
    
    venta = relationship("Venta", back_populates="items")
    producto = relationship("Producto")

class MovimientoInventario(Base):
    __tablename__ = "movimientos_inventario"
    
    id = Column(Integer, primary_key=True, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    tipo_movimiento = Column(String(20), nullable=False)  # entrada, salida
    cantidad = Column(Integer, nullable=False)
    stock_anterior = Column(Integer, nullable=False)
    stock_nuevo = Column(Integer, nullable=False)
    motivo = Column(String(100))
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)

    fecha_movimiento = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone(timedelta(hours=-5)))
    )
    
    producto = relationship("Producto")
    usuario = relationship("Usuario")

class RegistroAuditoria(Base):
    __tablename__ = "registros_auditoria"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    tipo_accion = Column(String(50), nullable=False)
    descripcion = Column(Text, nullable=False)

    fecha_accion = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone(timedelta(hours=-5)))
    )

    ip_address = Column(String(45))
    
    usuario = relationship("Usuario")