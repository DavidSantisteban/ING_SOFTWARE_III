"""
test_pu_unitarias.py — Pruebas Unitarias
Nivel: Unitario | Técnica: Caja Blanca | Tipo: Funcional
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime

from controllers.auth_controller import ControladorAutenticacion
from controllers.ventas_controller import ControladorVentas
from controllers.inventario_controller import ControladorInventario
from controllers.reportes_controller import ControladorReportes
from models import modelos


# AUTENTICACIÓN Y CONTROL DE ACCESO

class TestAutenticacion:
    def test_credenciales_correctas_retornan_usuario(self, db, admin):
        resultado = ControladorAutenticacion(db).autenticar_usuario(
            "admin@storevision.com", "admin123"
        )

        assert resultado is not None
        assert resultado.rol == "administradora"

    def test_password_incorrecta_bloquea_acceso(self, db, admin):
        resultado = ControladorAutenticacion(db).autenticar_usuario(
            "admin@storevision.com", "password_incorrecta"
        )

        assert resultado is None

    def test_login_fallido_queda_registrado_en_auditoria(self, db, admin):
        ControladorAutenticacion(db).autenticar_usuario(
            "admin@storevision.com", "password_incorrecta"
        )

        registro = db.query(modelos.RegistroAuditoria).filter_by(
            tipo_accion="login_fallido"
        ).first()

        assert registro is not None, (
            "El intento fallido de login no quedó registrado en auditoría"
        )

    def test_email_duplicado_no_crea_usuario(self, db, admin):
        resultado = ControladorAutenticacion(db).crear_usuario(
            {
                "email": "admin@storevision.com",  # email ya existente
                "nombre": "Otro Usuario",
                "password": "otropass123",
                "rol": "cajero",
            },
            usuario_creador_id=admin.id,
        )

        assert "error" in resultado
        total_admins = db.query(modelos.Usuario).filter_by(
            email="admin@storevision.com"
        ).count()
        assert total_admins == 1, "Se creó un usuario duplicado cuando no debía"

# REGISTRO DE VENTAS

class TestRegistrarVenta:
    def test_venta_valida_genera_id_de_venta(self, db, cajero, sucursal, producto):
        resultado = ControladorVentas(db).registrar_venta(
            {"items": [{"producto_id": producto.id, "cantidad": 3}]},
            cajero.id,
        )
        assert "venta_id" in resultado, (
            f"La venta no retornó un ID. Respuesta recibida: {resultado}"
        )

    def test_total_es_cantidad_por_precio_unitario(self, db, cajero, sucursal, producto):
        cantidad = 3
        resultado = ControladorVentas(db).registrar_venta(
            {"items": [{"producto_id": producto.id, "cantidad": cantidad}]},
            cajero.id,
        )

        venta = db.query(modelos.Venta).filter_by(id=resultado["venta_id"]).first()
        total_esperado = cantidad * producto.precio_venta

        assert abs(venta.total - total_esperado) <= 0.01, (
            f"Total calculado: {venta.total}, esperado: {total_esperado}"
        )

    def test_venta_sin_productos_retorna_error(self, db, cajero, sucursal):
        resultado = ControladorVentas(db).registrar_venta(
            {"items": []},
            cajero.id,
        )

        assert "error" in resultado

    def test_venta_con_stock_insuficiente_no_modifica_inventario(self, db, cajero, sucursal, producto):
        stock_antes = producto.stock_actual
        resultado = ControladorVentas(db).registrar_venta(
            {"items": [{"producto_id": producto.id, "cantidad": 9999}]},
            cajero.id,
        )
        db.refresh(producto)

        assert "error" in resultado
        assert producto.stock_actual == stock_antes, (
            "El stock cambió aunque la venta debió rechazarse por insuficiencia"
        )

    def test_venta_con_producto_agotado_retorna_error(self, db, cajero, sucursal, producto_sin_stock):
        resultado = ControladorVentas(db).registrar_venta(
            {"items": [{"producto_id": producto_sin_stock.id, "cantidad": 1}]},
            cajero.id,
        )

        assert "error" in resultado

# ANULACIÓN DE VENTAS

class TestAnularVenta:
    def test_no_se_puede_anular_una_venta_ya_anulada(self, db, admin, sucursal, producto):
        resultado = ControladorVentas(db).registrar_venta(
            {"items": [{"producto_id": producto.id, "cantidad": 2}]},
            admin.id,
        )
        venta_id = resultado["venta_id"]

        ctrl = ControladorVentas(db)
        ctrl.anular_venta(venta_id, admin.id, "Error en caja - primera vez")
        segunda_anulacion = ctrl.anular_venta(venta_id, admin.id, "Intento duplicado")

        assert "error" in segunda_anulacion, (
            "El sistema permitió anular dos veces la misma venta"
        )

# GESTIÓN DE INVENTARIO — ENTRADAS Y SALIDAS

class TestMovimientosInventario:
    def test_entrada_de_mercancia_incrementa_el_stock(self, db, admin, producto):
        stock_antes = producto.stock_actual
        cantidad_recibida = 20

        ControladorInventario(db).registrar_movimiento(
            {
                "producto_id": producto.id,
                "tipo_movimiento": "entrada",
                "cantidad": cantidad_recibida,
                "motivo": "Compra a proveedor",
            },
            admin.id,
        )
        db.refresh(producto)

        assert producto.stock_actual == stock_antes + cantidad_recibida, (
            f"Stock esperado: {stock_antes + cantidad_recibida}, "
            f"stock actual: {producto.stock_actual}"
        )

    def test_salida_mayor_al_stock_retorna_error(self, db, admin, producto):
        resultado = ControladorInventario(db).registrar_movimiento(
            {
                "producto_id": producto.id,
                "tipo_movimiento": "salida",
                "cantidad": 9999,
                "motivo": "Ajuste",
            },
            admin.id,
        )

        assert "error" in resultado

# ALERTAS DE STOCK MÍNIMO

class TestAlertasStock:
    def test_producto_en_limite_minimo_genera_alerta(self, db, producto_en_limite):
        alertas = ControladorInventario(db).verificar_alertas_inventario()
        ids_en_alerta = [a["producto_id"] for a in alertas]

        assert producto_en_limite.id in ids_en_alerta, (
            "Un producto con stock igual al mínimo no aparece en alertas, "
            "pero debería (condición inclusiva stock <= mínimo)"
        )

    def test_producto_con_stock_suficiente_no_genera_alerta(self, db, producto):
        alertas = ControladorInventario(db).verificar_alertas_inventario()
        ids_en_alerta = [a["producto_id"] for a in alertas]

        assert producto.id not in ids_en_alerta, (
            "Un producto con stock normal apareció en alertas (falsa alarma)"
        )

    def test_producto_agotado_tambien_genera_alerta(self, db, producto_sin_stock):
        alertas = ControladorInventario(db).verificar_alertas_inventario()
        ids_en_alerta = [a["producto_id"] for a in alertas]

        assert producto_sin_stock.id in ids_en_alerta, (
            "Un producto agotado (stock=0) no aparece en alertas"
        )

# BALANCE ECONÓMICO

class TestBalanceEconomico:
    def test_utilidad_bruta_es_ventas_menos_costos(self, db, admin, sucursal, producto):
        """
        US-11: Utilidad bruta = total de ventas − costo de ventas.
        Esta es la métrica financiera fundamental del balance.
        """
        ControladorVentas(db).registrar_venta(
            {"items": [{"producto_id": producto.id, "cantidad": 2}]},
            admin.id,
        )

        balance = ControladorReportes(db).generar_balance_economico(
            datetime(2024, 1, 1),
            datetime(2099, 12, 31),
        )

        utilidad_calculada = balance["rentabilidad"]["utilidad_bruta"]
        utilidad_esperada = (
            balance["resumen_ventas"]["total_ventas"]
            - balance["rentabilidad"]["costo_ventas"]
        )

        assert abs(utilidad_calculada - utilidad_esperada) <= 0.01, (
            f"Utilidad calculada: {utilidad_calculada}, "
            f"esperada (ventas - costos): {utilidad_esperada}"
        )