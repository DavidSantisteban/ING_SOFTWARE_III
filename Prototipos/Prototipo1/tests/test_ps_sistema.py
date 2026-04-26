"""
test_ps_sistema.py — Pruebas de Sistema
Nivel: Sistema | Técnica: Caja Negra | Tipo: Funcional + Seguridad + Rendimiento
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# FLUJO COMPLETO DE VENTA


class TestFlujoDeVenta:
    """
    Simula el flujo real del cajero en caja: selecciona productos,
    confirma la venta y el sistema descuenta el stock automáticamente.
    """

    def test_venta_exitosa_retorna_201(self, client, sesion_cajero, producto):
        """
        Una venta con producto disponible debe retornar HTTP 201
        (recurso creado exitosamente).
        """
        respuesta = client.post(
            "/api/ventas",
            json={"items": [{"producto_id": producto.id, "cantidad": 2}]},
            headers=sesion_cajero,
        )

        assert respuesta.status_code == 201, (
            f"Se esperaba 201, se recibió {respuesta.status_code}. "
            f"Detalle: {respuesta.json()}"
        )

    def test_venta_descuenta_stock_en_base_de_datos(
        self, client, db, sesion_cajero, producto
    ):
        """
        Después de confirmar la venta, el stock en la BD debe
        reflejar las unidades vendidas, sin necesidad de ninguna acción manual.
        """
        stock_antes = producto.stock_actual
        client.post(
            "/api/ventas",
            json={"items": [{"producto_id": producto.id, "cantidad": 3}]},
            headers=sesion_cajero,
        )
        db.refresh(producto)

        assert producto.stock_actual == stock_antes - 3, (
            f"Stock esperado: {stock_antes - 3}, actual: {producto.stock_actual}"
        )


# ANULACIÓN DE VENTAS CON CONTROL DE ROLES


class TestAnulacionDeVentas:
    """
    Verifica el flujo de anulación y que los permisos funcionan
    correctamente a nivel HTTP.
    """

    def test_administradora_puede_anular_venta(
        self, client, sesion_admin, sesion_cajero, producto
    ):
        # El cajero registra la venta
        respuesta_venta = client.post(
            "/api/ventas",
            json={"items": [{"producto_id": producto.id, "cantidad": 1}]},
            headers=sesion_cajero,
        )
        venta_id = respuesta_venta.json()["venta_id"]

        # La administradora la anula
        respuesta_anulacion = client.patch(
            f"/api/ventas/{venta_id}",
            json={"motivo": "Error en digitación del cajero"},
            headers=sesion_admin,
        )

        assert respuesta_anulacion.status_code == 200, (
            f"La administradora no pudo anular la venta. "
            f"Código: {respuesta_anulacion.status_code}"
        )

    def test_cajero_no_puede_anular_ventas(self, client, sesion_cajero, producto):
        respuesta_venta = client.post(
            "/api/ventas",
            json={"items": [{"producto_id": producto.id, "cantidad": 1}]},
            headers=sesion_cajero,
        )
        venta_id = respuesta_venta.json()["venta_id"]

        respuesta_anulacion = client.patch(
            f"/api/ventas/{venta_id}",
            json={"motivo": "Intento no autorizado"},
            headers=sesion_cajero,
        )

        assert respuesta_anulacion.status_code == 403, (
            "El cajero pudo anular una venta, lo cual representa un riesgo de fraude"
        )


# ALERTAS DE INVENTARIO


class TestAlertasDeInventario:
    """
    Verifica que el endpoint de alertas retorna los productos correctos.
    """

    def test_producto_bajo_minimo_aparece_en_alertas(self, client, producto_en_limite):
        """
        Un producto con stock en el límite mínimo debe aparecer
        en el listado de alertas del endpoint /api/inventario/alertas.
        """

        respuesta = client.get("/api/inventario/alertas")

        assert respuesta.status_code == 200
        ids_en_alerta = [a["producto_id"] for a in respuesta.json()]
        assert producto_en_limite.id in ids_en_alerta, (
            "El producto bajo mínimo no aparece en las alertas del sistema"
        )

    def test_producto_con_stock_normal_no_genera_alerta_falsa(self, client, producto):
        ids_en_alerta = [
            a["producto_id"] for a in client.get("/api/inventario/alertas").json()
        ]

        assert producto.id not in ids_en_alerta, (
            "Un producto con stock normal apareció en alertas (falsa alarma)"
        )


# CONTROL DE ROLES EN LA API


class TestControlDeRoles:
    """
    Tabla de decisión de acceso a la API:
      Sin sesión          → 401 en cualquier operación
      Cajero, crea prod   → 403 (no tiene ese permiso)
      Admin, crea prod    → 201 (tiene acceso completo)
    """

    def test_sin_sesion_retorna_401(self, client):
        """
        Cualquier operación sin autenticación debe ser rechazada.
        """
        respuesta = client.post("/api/ventas", json={"items": []})

        assert respuesta.status_code == 401

    def test_cajero_no_puede_crear_productos(self, client, sesion_cajero):
        """
        Crear productos es una función exclusiva de la
        administradora. El cajero debe recibir HTTP 403.
        """
        respuesta = client.post(
            "/api/productos",
            json={
                "codigo": "PROD_TEST",
                "nombre": "Producto de prueba",
                "categoria": "Test",
                "precio_venta": 1000,
                "costo": 500,
            },
            headers=sesion_cajero,
        )

        assert respuesta.status_code == 403, (
            "El cajero pudo crear un producto cuando no debería tener ese permiso"
        )

    def test_administradora_puede_crear_productos(self, client, sesion_admin):
        """
        La administradora tiene acceso completo y puede crear
        nuevos productos en el catálogo.
        """
        respuesta = client.post(
            "/api/productos",
            json={
                "codigo": "NUEVO99",
                "nombre": "Producto Nuevo",
                "categoria": "Test",
                "precio_venta": 1000,
                "costo": 500,
                "stock_minimo": 5,
            },
            headers=sesion_admin,
        )

        assert respuesta.status_code == 201, (
            f"La administradora no pudo crear un producto. "
            f"Código: {respuesta.status_code}, detalle: {respuesta.json()}"
        )
