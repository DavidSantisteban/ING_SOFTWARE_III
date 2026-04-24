"""
test_pi_integracion.py — Pruebas de Integración
Nivel: Integración | Técnica: Caja Gris | Tipo: Funcional + Seguridad
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from controllers.auth_controller import ControladorAutenticacion
from controllers.ventas_controller import ControladorVentas
from controllers.inventario_controller import ControladorInventario
from models import modelos

# AUDITORÍA DE ACCESO
class TestAuditoriaDeAcceso:
    def test_login_exitoso_queda_en_tabla_auditoria(self, db, admin):
        ControladorAutenticacion(db).autenticar_usuario(
            "admin@storevision.com", "admin123"
        )

        registro = db.query(modelos.RegistroAuditoria).filter_by(
            usuario_id=admin.id,
            tipo_accion="login_exitoso",
        ).first()

        assert registro is not None, (
            "El login exitoso no dejó rastro en la tabla de auditoría"
        )

# ATOMICIDAD DE VENTAS

class TestAtomicidadDeVentas:
    def test_venta_exitosa_descuenta_stock_y_crea_movimiento(self, db, cajero, sucursal, producto):
        stock_antes = producto.stock_actual
        ControladorVentas(db).registrar_venta(
            {"items": [{"producto_id": producto.id, "cantidad": 5}]},
            cajero.id,
        )
        db.refresh(producto)

        # Verificar que el stock bajó
        assert producto.stock_actual == stock_antes - 5, (
            f"Stock esperado: {stock_antes - 5}, actual: {producto.stock_actual}"
        )

        # Verificar que el movimiento de inventario quedó registrado
        movimiento = db.query(modelos.MovimientoInventario).filter_by(
            producto_id=producto.id,
            tipo_movimiento="salida",
        ).first()

        assert movimiento is not None, "No se creó el movimiento de inventario"
        assert movimiento.cantidad == 5

    def test_venta_con_producto_inexistente_no_deja_registros_parciales(self, db, cajero, sucursal, producto):
        """
        Escenario: primer ítem válido, segundo ítem con ID 99999 (no existe).
        """
        ventas_antes = db.query(modelos.Venta).count()
        movimientos_antes = db.query(modelos.MovimientoInventario).count()

        ControladorVentas(db).registrar_venta(
            {
                "items": [
                    {"producto_id": producto.id, "cantidad": 1},   # válido
                    {"producto_id": 99999, "cantidad": 1},          # no existe → error
                ]
            },
            cajero.id,
        )

        assert db.query(modelos.Venta).count() == ventas_antes, (
            "Se creó una Venta aunque la transacción debió revertirse"
        )
        assert db.query(modelos.MovimientoInventario).count() == movimientos_antes, (
            "Se crearon movimientos de inventario aunque la transacción debió revertirse"
        )

# ANULACIÓN Y RESTAURACIÓN DE STOCK

class TestAnulacionRestaurandoStock:
    """
    Verifica que anular una venta devuelve el stock al valor original,
    sin más ni menos unidades de las que se habían descontado.

    Contexto del negocio: Una anulación incorrecta (ej: restaura el doble)
    generaría un inventario inflado que no corresponde a la realidad física.
    """

    def test_anular_venta_restaura_stock_al_valor_original(
        self, db, admin, sucursal, producto
    ):
        """
        US-04: Después de registrar una venta y luego anularla,
        el stock debe quedar exactamente igual que al principio.
        """
        stock_original = producto.stock_actual

        resultado = ControladorVentas(db).registrar_venta(
            {"items": [{"producto_id": producto.id, "cantidad": 5}]},
            admin.id,
        )
        ControladorVentas(db).anular_venta(
            resultado["venta_id"], admin.id, "Error en digitación"
        )
        db.refresh(producto)

        assert producto.stock_actual == stock_original, (
            f"Stock después de anular: {producto.stock_actual}, "
            f"debería ser el original: {stock_original}"
        )

# ALERTAS REFLEJADAS EN BASE DE DATOS

class TestAlertasTrasMovimiento:
    """
    Verifica que después de un movimiento de salida que deja el stock
    por debajo del mínimo, la función de alertas consulta la BD y
    retorna ese producto como urgente de reabastecer.
    """

    def test_salida_que_supera_minimo_activa_alerta(self, db, admin):
        # Crear producto justo sobre el mínimo
        producto = modelos.Producto(
            codigo="ALT01",
            nombre="Café Sello Rojo 500g",
            categoria="Bebidas",
            precio_venta=12500,
            costo=8500,
            stock_actual=11,
            stock_minimo=10,
            activo=True,
        )
        db.add(producto)
        db.commit()
        db.refresh(producto)

        # Registrar salida que lo deja bajo el mínimo
        ControladorInventario(db).registrar_movimiento(
            {
                "producto_id": producto.id,
                "tipo_movimiento": "salida",
                "cantidad": 2,
                "motivo": "Venta en caja",
            },
            admin.id,
        )

        alertas = ControladorInventario(db).verificar_alertas_inventario()
        ids_en_alerta = [a["producto_id"] for a in alertas]

        assert producto.id in ids_en_alerta, (
            "El producto bajó del mínimo pero no apareció en las alertas"
        )

# CONTROL DE ACCESO A NIVEL HTTP

class TestControlDeAccesoHTTP:
    """
    Verifica que las restricciones de rol funcionan a nivel de API,
    no solo en la interfaz visual.
    """

    def test_peticion_sin_sesion_retorna_401(self, client):
        respuesta = client.post("/api/ventas", json={"items": []})

        assert respuesta.status_code == 401, (
            f"Se esperaba 401 (no autenticado), se recibió: {respuesta.status_code}"
        )

    def test_cajero_no_puede_anular_ventas(self, client, sesion_cajero, producto):
        """
        Un cajero autenticado que intenta anular una venta debe
        recibir HTTP 403 (prohibido), sin importar que la venta exista.
        """
        # El cajero registra la venta (esto sí puede hacerlo)
        respuesta_venta = client.post(
            "/api/ventas",
            json={"items": [{"producto_id": producto.id, "cantidad": 1}]},
            headers=sesion_cajero,
        )
        venta_id = respuesta_venta.json()["venta_id"]

        # El cajero intenta anularla (esto NO puede hacerlo)
        respuesta_anulacion = client.patch(
            f"/api/ventas/{venta_id}",
            json={"motivo": "Intento no autorizado"},
            headers=sesion_cajero,
        )

        assert respuesta_anulacion.status_code == 403, (
            "El cajero pudo anular una venta cuando no debería tener ese permiso"
        )