from sqlalchemy.orm import Session
from sqlalchemy import and_
from models.modelos import Venta, ItemVenta, Producto, MovimientoInventario, RegistroAuditoria
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class ControladorVentas:
    def __init__(self, db: Session):
        self.db = db
    
    def registrar_venta(self, datos_venta: dict, usuario_id: int):
        try:
            # Validar datos obligatorios
            if not datos_venta.get('items'):
                return {"error": "Debe agregar productos a la venta"}
            
            # Usar sucursal por defecto (ID 1) ya que solo hay una
            sucursal_id = 1
            
            # Validar stock y calcular total
            total_venta = 0
            items_validados = []
            
            for item in datos_venta['items']:
                producto = self.db.query(Producto).filter(Producto.id == item['producto_id']).first()
                if not producto:
                    return {"error": f"Producto {item['producto_id']} no encontrado"}
                
                if producto.stock_actual < item['cantidad']:
                    return {"error": f"Stock insuficiente para {producto.nombre}. Stock actual: {producto.stock_actual}"}
                
                subtotal = item['cantidad'] * producto.precio_venta
                total_venta += subtotal
                
                items_validados.append({
                    'producto': producto,
                    'cantidad': item['cantidad'],
                    'precio_unitario': producto.precio_venta,
                    'subtotal': subtotal
                })
            
            # Crear venta con sucursal por defecto
            nueva_venta = Venta(
                sucursal_id=sucursal_id,  # Siempre sucursal 1
                usuario_id=usuario_id,
                total=total_venta
            )
            self.db.add(nueva_venta)
            self.db.flush()  # Para obtener el ID
            
            # Crear items de venta y actualizar inventario
            for item in items_validados:
                nuevo_item = ItemVenta(
                    venta_id=nueva_venta.id,
                    producto_id=item['producto'].id,
                    cantidad=item['cantidad'],
                    precio_unitario=item['precio_unitario'],
                    subtotal=item['subtotal']
                )
                self.db.add(nuevo_item)
                
                # Actualizar inventario
                stock_anterior = item['producto'].stock_actual
                stock_nuevo = stock_anterior - item['cantidad']
                item['producto'].stock_actual = stock_nuevo
                
                # Registrar movimiento de inventario
                movimiento = MovimientoInventario(
                    producto_id=item['producto'].id,
                    tipo_movimiento="salida",
                    cantidad=item['cantidad'],
                    stock_anterior=stock_anterior,
                    stock_nuevo=stock_nuevo,
                    motivo="Venta",
                    usuario_id=usuario_id
                )
                self.db.add(movimiento)
            
            # Registrar en auditoría
            auditoria = RegistroAuditoria(
                usuario_id=usuario_id,
                tipo_accion="venta",
                descripcion=f"Venta registrada ID: {nueva_venta.id}, Total: ${total_venta}",
                fecha_accion=datetime.now(timezone.utc)

            )
            self.db.add(auditoria)
            
            self.db.commit()
            
            logger.info(f"Venta {nueva_venta.id} registrada exitosamente")
            return {"mensaje": "Venta registrada exitosamente", "venta_id": nueva_venta.id}
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error registrando venta: {str(e)}")
            return {"error": f"Error al registrar venta: {str(e)}"}
    
    def anular_venta(self, venta_id: int, usuario_id: int, motivo: str):
        try:
            venta = self.db.query(Venta).filter(Venta.id == venta_id).first()
            if not venta:
                return {"error": "Venta no encontrada"}
            
            if venta.estado == "anulada":
                return {"error": "La venta ya está anulada"}
            
            # Restaurar inventario
            for item in venta.items:
                producto = item.producto
                stock_anterior = producto.stock_actual
                stock_nuevo = stock_anterior + item.cantidad
                producto.stock_actual = stock_nuevo
                
                # Registrar movimiento de inventario
                movimiento = MovimientoInventario(
                    producto_id=producto.id,
                    tipo_movimiento="entrada",
                    cantidad=item.cantidad,
                    stock_anterior=stock_anterior,
                    stock_nuevo=stock_nuevo,
                    motivo=f"Anulación venta {venta_id}",
                    usuario_id=usuario_id
                )
                self.db.add(movimiento)
            
            # Anular venta
            venta.estado = "anulada"
            
            # Registrar en auditoría
            auditoria = RegistroAuditoria(
                usuario_id=usuario_id,
                tipo_accion="anulacion",
                descripcion=f"Venta anulada ID: {venta_id}. Motivo: {motivo}",
                fecha_accion=datetime.now(timezone.utc)
            )
            self.db.add(auditoria)
            
            self.db.commit()
            return {"mensaje": "Venta anulada exitosamente"}
            
        except Exception as e:
            self.db.rollback()
            return {"error": f"Error al anular venta: {str(e)}"}
    
    def obtener_ventas_por_periodo(self, fecha_inicio: datetime, fecha_fin: datetime):
        try:
            ventas = self.db.query(Venta).filter(
                and_(
                    Venta.fecha_venta >= fecha_inicio,
                    Venta.fecha_venta <= fecha_fin,
                    Venta.estado == "completada"
                )
            ).order_by(Venta.fecha_venta.desc()).all()
            
            return ventas
            
        except Exception as e:
            return {"error": f"Error obteniendo ventas: {str(e)}"}
    
    def consolidar_ventas_diarias(self):
        try:
            hoy = datetime.now(timezone.utc).date()
            fecha_inicio = datetime.combine(hoy, datetime.min.time())
            fecha_fin = datetime.combine(hoy, datetime.max.time())
            
            ventas_hoy = self.db.query(Venta).filter(
                and_(
                    Venta.fecha_venta >= fecha_inicio,
                    Venta.fecha_venta <= fecha_fin,
                    Venta.estado == "completada"
                )
            ).all()
            
            consolidado = {
                'fecha': hoy,
                'total_ventas': len(ventas_hoy),
                'monto_total': sum(venta.total for venta in ventas_hoy),
                'sucursal': 'Tienda StoreVision'
            }
            
            return consolidado
            
        except Exception as e:
            return {"error": f"Error consolidando ventas: {str(e)}"}
    
    def obtener_venta_por_id(self, venta_id: int):
        try:
            venta = self.db.query(Venta).filter(Venta.id == venta_id).first()
            return venta
        except Exception as e:
            return {"error": f"Error obteniendo venta: {str(e)}"}