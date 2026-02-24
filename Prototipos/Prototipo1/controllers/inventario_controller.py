from sqlalchemy.orm import Session
from sqlalchemy import and_
from models.modelos import Producto, MovimientoInventario, RegistroAuditoria
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)

class ControladorInventario:
    def __init__(self, db: Session):
        self.db = db
    
    def registrar_movimiento(self, datos_movimiento: dict, usuario_id: int):
        try:
            producto = self.db.query(Producto).filter(Producto.id == datos_movimiento['producto_id']).first()
            if not producto:
                return {"error": "Producto no encontrado"}
            
            stock_anterior = producto.stock_actual
            
            if datos_movimiento['tipo_movimiento'] == 'entrada':
                stock_nuevo = stock_anterior + datos_movimiento['cantidad']
            else:  # salida
                if stock_anterior < datos_movimiento['cantidad']:
                    return {"error": "Stock insuficiente"}
                stock_nuevo = stock_anterior - datos_movimiento['cantidad']
            
            # Actualizar stock
            producto.stock_actual = stock_nuevo
            
            # Registrar movimiento
            movimiento = MovimientoInventario(
                producto_id=datos_movimiento['producto_id'],
                tipo_movimiento=datos_movimiento['tipo_movimiento'],
                cantidad=datos_movimiento['cantidad'],
                stock_anterior=stock_anterior,
                stock_nuevo=stock_nuevo,
                motivo=datos_movimiento.get('motivo', 'Ajuste manual'),
                usuario_id=usuario_id
            )
            self.db.add(movimiento)
            
            # Registrar en auditoría
            auditoria = RegistroAuditoria(
                usuario_id=usuario_id,
                tipo_accion="movimiento_inventario",
                descripcion=f"Movimiento de {datos_movimiento['tipo_movimiento']} - Producto: {producto.nombre}, Cantidad: {datos_movimiento['cantidad']}",
                fecha_accion=datetime.now(timezone(timedelta(hours=-5)))
            )
            self.db.add(auditoria)
            
            self.db.commit()
            return {"mensaje": "Movimiento registrado exitosamente"}
            
        except Exception as e:
            self.db.rollback()
            return {"error": f"Error registrando movimiento: {str(e)}"}
    
    def verificar_alertas_inventario(self):
        try:
            productos_bajos = self.db.query(Producto).filter(
                Producto.stock_actual <= Producto.stock_minimo
            ).all()
            
            alertas = []
            for producto in productos_bajos:
                alertas.append({
                    'producto_id': producto.id,
                    'nombre': producto.nombre,
                    'stock_actual': producto.stock_actual,
                    'stock_minimo': producto.stock_minimo,
                    'diferencia': producto.stock_minimo - producto.stock_actual
                })
            
            return alertas
            
        except Exception as e:
            return {"error": f"Error verificando alertas: {str(e)}"}
    
    def obtener_historial_movimientos(self, producto_id: int = None, fecha_inicio: datetime = None, fecha_fin: datetime = None):
        try:
            query = self.db.query(MovimientoInventario)
            
            if producto_id:
                query = query.filter(MovimientoInventario.producto_id == producto_id)
            
            if fecha_inicio and fecha_fin:
                query = query.filter(and_(
                    MovimientoInventario.fecha_movimiento >= fecha_inicio,
                    MovimientoInventario.fecha_movimiento <= fecha_fin
                ))
            
            movimientos = query.order_by(MovimientoInventario.fecha_movimiento.desc()).all()
            return movimientos
            
        except Exception as e:
            return {"error": f"Error obteniendo historial: {str(e)}"}
    
    def obtener_productos_mas_vendidos(self, limite: int = 10, dias: int = 7):
        try:
            from sqlalchemy import func
            from models.modelos import ItemVenta, Venta
            
            fecha_limite = datetime.utcnow() - timedelta(days=dias)
            
            productos_vendidos = (self.db.query(
                    ItemVenta.producto_id,
                    Producto.nombre,
                    func.sum(ItemVenta.cantidad).label('total_vendido')
                )
                .join(Producto)
                .join(Venta)
                .filter(Venta.fecha_venta >= fecha_limite)
                .filter(Venta.estado == 'completada')
                .group_by(ItemVenta.producto_id, Producto.nombre)
                .order_by(func.sum(ItemVenta.cantidad).desc())
                .limit(limite)
                .all())
            
            return productos_vendidos
            
        except Exception as e:
            return {"error": f"Error obteniendo productos más vendidos: {str(e)}"}
        
        
    def obtener_producto_por_id(self, producto_id: int):
        try:
            producto = self.db.query(Producto).filter(Producto.id == producto_id).first()
            return producto
        except Exception as e:
            return {"error": f"Error obteniendo producto: {str(e)}"}