from sqlalchemy.orm import Session
from sqlalchemy import func, and_, extract
from models.modelos import Venta, ItemVenta, Producto, MovimientoInventario
from datetime import datetime, timedelta
import logging
import traceback

logger = logging.getLogger(__name__)

class ControladorReportes:
    def __init__(self, db: Session):
        self.db = db
    
    def generar_balance_economico(self, fecha_inicio: datetime, fecha_fin: datetime):
        try:
            # Consulta base para ventas - solo sucursal 1
            datos_ventas = self.db.query(
                func.sum(Venta.total).label('total_ventas'),
                func.count(Venta.id).label('cantidad_ventas')
            ).filter(
                and_(
                    Venta.fecha_venta >= fecha_inicio,
                    Venta.fecha_venta <= fecha_fin,
                    Venta.estado == 'completada',
                    Venta.sucursal_id == 1
                )
            ).first()
            
            # Consulta para costos - solo sucursal 1
            datos_costos = self.db.query(
                func.sum(ItemVenta.cantidad * Producto.costo).label('costo_total')
            ).join(Producto).join(Venta).filter(
                and_(
                    Venta.fecha_venta >= fecha_inicio,
                    Venta.fecha_venta <= fecha_fin,
                    Venta.estado == 'completada',
                    Venta.sucursal_id == 1
                )
            ).first()
            
            total_ventas = datos_ventas.total_ventas or 0
            costo_ventas = datos_costos.costo_total or 0
            utilidad_bruta = total_ventas - costo_ventas
            margen_utilidad = (utilidad_bruta / total_ventas * 100) if total_ventas > 0 else 0
            
            balance = {
                'periodo': {
                    'fecha_inicio': fecha_inicio,
                    'fecha_fin': fecha_fin
                },
                'resumen_ventas': {
                    'total_ventas': round(total_ventas, 2),
                    'cantidad_ventas': datos_ventas.cantidad_ventas or 0,
                    'ticket_promedio': round(total_ventas / (datos_ventas.cantidad_ventas or 1), 2)
                },
                'rentabilidad': {
                    'costo_ventas': round(costo_ventas, 2),
                    'utilidad_bruta': round(utilidad_bruta, 2),
                    'margen_utilidad': round(margen_utilidad, 2)
                }
            }
            
            return balance
            
        except Exception as e:
            logger.error(f"Error generando balance económico: {str(e)}")
            return {"error": f"Error generando balance: {str(e)}"}
    
    def obtener_indicadores_ventas(self, fecha_inicio: datetime = None, fecha_fin: datetime = None):
        try:
            # Si no se proporcionan fechas, usar los últimos 7 días
            if not fecha_inicio or not fecha_fin:
                fecha_fin = datetime.now(timezone(timedelta(hours=-5)))
                fecha_inicio = fecha_fin - timedelta(days=7)
            
            # Ventas del periodo actual
            ventas_periodo_actual = self.db.query(func.sum(Venta.total)).filter(
                and_(
                    Venta.fecha_venta >= fecha_inicio,
                    Venta.fecha_venta <= fecha_fin,
                    Venta.estado == 'completada',
                    Venta.sucursal_id == 1
                )
            ).scalar() or 0
            
            # Ventas del periodo anterior (misma duración)
            duracion = fecha_fin - fecha_inicio
            fecha_inicio_anterior = fecha_inicio - duracion
            fecha_fin_anterior = fecha_inicio
            
            ventas_periodo_anterior = self.db.query(func.sum(Venta.total)).filter(
                and_(
                    Venta.fecha_venta >= fecha_inicio_anterior,
                    Venta.fecha_venta < fecha_fin_anterior,
                    Venta.estado == 'completada',
                    Venta.sucursal_id == 1
                )
            ).scalar() or 0
            
            # Calcular variación
            variacion_ventas = 0
            if ventas_periodo_anterior > 0:
                variacion_ventas = ((ventas_periodo_actual - ventas_periodo_anterior) / ventas_periodo_anterior) * 100
            
            # Alerta si la caída es mayor al 15%
            alerta_caida = variacion_ventas < -15
            
            indicadores = {
                'comparativa': {
                    'periodo_actual': round(ventas_periodo_actual, 2),
                    'periodo_anterior': round(ventas_periodo_anterior, 2),
                    'variacion_porcentaje': round(variacion_ventas, 2),
                    'alerta_caida': alerta_caida
                }
            }
            
            return indicadores
            
        except Exception as e:
            logger.error(f"Error obteniendo indicadores de ventas: {str(e)}")
            return {
                'comparativa': {
                    'periodo_actual': 0,
                    'periodo_anterior': 0,
                    'variacion_porcentaje': 0,
                    'alerta_caida': False
                }
            }
    
    def obtener_productos_mas_vendidos(self, fecha_inicio: datetime = None, fecha_fin: datetime = None):
        try:
            print("🎯 Iniciando obtención de productos más vendidos")
            
            # Si no se proporcionan fechas, usar un rango amplio
            if not fecha_inicio or not fecha_fin:
                fecha_fin = datetime.now(timezone(timedelta(hours=-5)))
                fecha_inicio = fecha_fin - timedelta(days=365)
                print("📅 Usando fechas por defecto (último año)")
            
            print(f"📊 Consultando entre {fecha_inicio} y {fecha_fin}")
            
            # Consulta para productos más vendidos
            productos_vendidos = (self.db.query(
                    ItemVenta.producto_id,
                    Producto.nombre,
                    Producto.codigo,
                    Producto.categoria,
                    func.sum(ItemVenta.cantidad).label('total_vendido'),
                    func.sum(ItemVenta.subtotal).label('total_ingresos')
                )
                .join(Producto, ItemVenta.producto_id == Producto.id)
                .join(Venta, ItemVenta.venta_id == Venta.id)
                .filter(
                    Venta.fecha_venta >= fecha_inicio,
                    Venta.fecha_venta <= fecha_fin,
                    Venta.estado == 'completada'
                )
                .group_by(ItemVenta.producto_id, Producto.nombre, Producto.codigo, Producto.categoria)
                .order_by(func.sum(ItemVenta.cantidad).desc())
                .all())
            
            print(f"✅ Encontrados {len(productos_vendidos)} productos con ventas")
            
            resultado = []
            for p in productos_vendidos:
                item = {
                    'producto_id': p.producto_id,
                    'nombre': p.nombre,
                    'codigo': p.codigo,
                    'categoria': p.categoria,
                    'total_vendido': p.total_vendido or 0,
                    'total_ingresos': float(p.total_ingresos or 0)
                }
                print(f"   - {item['nombre']}: {item['total_vendido']} unidades")
                resultado.append(item)
            
            return resultado
            
        except Exception as e:
            print(f"❌ Error en obtener_productos_mas_vendidos: {str(e)}")
            print(f"📝 Traceback: {traceback.format_exc()}")
            logger.error(f"Error obteniendo productos más vendidos: {str(e)}")
            return []