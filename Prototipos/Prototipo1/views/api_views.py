from fastapi import APIRouter, Depends, HTTPException, Request, Header
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from models.database import obtener_db
from models.modelos import Producto, Venta, ItemVenta, MovimientoInventario, RegistroAuditoria
from controllers.ventas_controller import ControladorVentas
from controllers.inventario_controller import ControladorInventario
from controllers.auth_controller import ControladorAutenticacion
from controllers.reportes_controller import ControladorReportes
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Simulación de sesión (en producción usar JWT)
usuarios_activos = {}


# ─────────────────────────────────────────────
# UTILIDAD: verificar sesión
# ─────────────────────────────────────────────
def obtener_usuario_activo(session_id: str):
    if not session_id or session_id not in usuarios_activos:
        raise HTTPException(status_code=401, detail="No autenticado")
    return usuarios_activos[session_id]


# ─────────────────────────────────────────────
# VISTAS HTML
# ─────────────────────────────────────────────
@router.get("/", response_class=HTMLResponse)
@router.get("/ventas", response_class=HTMLResponse)
@router.get("/inventario", response_class=HTMLResponse)
@router.get("/reportes", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ─────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────
@router.post("/api/login", status_code=200)
async def login(request: Request, db: Session = Depends(obtener_db)):
    datos = await request.json()
    controlador_auth = ControladorAutenticacion(db)

    usuario = controlador_auth.autenticar_usuario(
        datos['email'],
        datos['password'],
        request.client.host
    )

    if not usuario:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    session_id = f"session_{usuario.id}_{datetime.utcnow().timestamp()}"
    usuarios_activos[session_id] = {
        'usuario_id': usuario.id,
        'nombre': usuario.nombre,
        'rol': usuario.rol,
        'email': usuario.email
    }

    return {
        "mensaje": "Login exitoso",
        "session_id": session_id,
        "usuario": {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "rol": usuario.rol,
            "email": usuario.email
        }
    }

@router.post("/api/logout", status_code=200)
async def logout(session_id: Optional[str] = Header(None, alias="session-id")):
    if session_id and session_id in usuarios_activos:
        del usuarios_activos[session_id]
    return {"mensaje": "Sesión cerrada exitosamente"}


# ─────────────────────────────────────────────
# PRODUCTOS
# ─────────────────────────────────────────────

# GET /api/productos - listar todos los productos activos
@router.get("/api/productos", status_code=200)
async def obtener_productos(db: Session = Depends(obtener_db)):
    try:
        productos = db.query(Producto).filter(Producto.activo == True).all()
        return [
            {
                "id": p.id,
                "codigo": p.codigo,
                "nombre": p.nombre,
                "categoria": p.categoria,
                "precio_venta": p.precio_venta,
                "stock_actual": p.stock_actual,
                "stock_minimo": p.stock_minimo
            }
            for p in productos
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo productos: {str(e)}")

# GET /api/productos/{id} - obtener un producto por ID
@router.get("/api/productos/{producto_id}", status_code=200)
async def obtener_producto(producto_id: int, db: Session = Depends(obtener_db)):
    producto = db.query(Producto).filter(Producto.id == producto_id, Producto.activo == True).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return {
        "id": producto.id,
        "codigo": producto.codigo,
        "nombre": producto.nombre,
        "descripcion": producto.descripcion,
        "categoria": producto.categoria,
        "precio_venta": producto.precio_venta,
        "costo": producto.costo,
        "stock_actual": producto.stock_actual,
        "stock_minimo": producto.stock_minimo
    }

# POST /api/productos - crear producto (solo administradora)
@router.post("/api/productos", status_code=201)
async def crear_producto(
    request: Request,
    session_id: Optional[str] = Header(None, alias="session-id"),
    db: Session = Depends(obtener_db)
):
    try:
        usuario = obtener_usuario_activo(session_id)

        if usuario['rol'] != 'administradora':
            raise HTTPException(status_code=403, detail="No tiene permisos para crear productos")

        datos = await request.json()

        producto_existente = db.query(Producto).filter(Producto.codigo == datos['codigo']).first()
        if producto_existente:
            raise HTTPException(status_code=409, detail="El código del producto ya existe")

        nuevo_producto = Producto(
            codigo=datos['codigo'],
            nombre=datos['nombre'],
            categoria=datos['categoria'],
            precio_venta=datos['precio_venta'],
            costo=datos['costo'],
            stock_actual=datos.get('stock_actual', 0),
            stock_minimo=datos.get('stock_minimo', 5),
            descripcion=datos.get('descripcion', '')
        )
        db.add(nuevo_producto)

        auditoria = RegistroAuditoria(
            usuario_id=usuario['usuario_id'],
            tipo_accion="creacion_producto",
            descripcion=f"Producto creado: {datos['nombre']} ({datos['codigo']})",
            fecha_accion=datetime.utcnow()
        )
        db.add(auditoria)
        db.commit()

        return {"mensaje": "Producto creado exitosamente", "producto_id": nuevo_producto.id}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creando producto: {str(e)}")

# PUT /api/productos/{id} - actualizar producto completo (solo administradora)
@router.put("/api/productos/{producto_id}", status_code=200)
async def actualizar_producto(
    producto_id: int,
    request: Request,
    session_id: Optional[str] = Header(None, alias="session-id"),
    db: Session = Depends(obtener_db)
):
    try:
        usuario = obtener_usuario_activo(session_id)

        if usuario['rol'] != 'administradora':
            raise HTTPException(status_code=403, detail="No tiene permisos para editar productos")

        producto = db.query(Producto).filter(Producto.id == producto_id).first()
        if not producto:
            raise HTTPException(status_code=404, detail="Producto no encontrado")

        datos = await request.json()

        producto.nombre = datos['nombre']
        producto.categoria = datos['categoria']
        producto.precio_venta = datos['precio_venta']
        producto.costo = datos['costo']
        producto.stock_minimo = datos['stock_minimo']
        producto.descripcion = datos.get('descripcion', '')

        auditoria = RegistroAuditoria(
            usuario_id=usuario['usuario_id'],
            tipo_accion="edicion_producto",
            descripcion=f"Producto actualizado: {producto.nombre} (ID: {producto_id})",
            fecha_accion=datetime.utcnow()
        )
        db.add(auditoria)
        db.commit()

        return {"mensaje": "Producto actualizado exitosamente"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error actualizando producto: {str(e)}")

# DELETE /api/productos/{id} - desactivar producto (solo administradora)
@router.delete("/api/productos/{producto_id}", status_code=200)
async def eliminar_producto(
    producto_id: int,
    session_id: Optional[str] = Header(None, alias="session-id"),
    db: Session = Depends(obtener_db)
):
    try:
        usuario = obtener_usuario_activo(session_id)

        if usuario['rol'] != 'administradora':
            raise HTTPException(status_code=403, detail="No tiene permisos para eliminar productos")

        producto = db.query(Producto).filter(Producto.id == producto_id).first()
        if not producto:
            raise HTTPException(status_code=404, detail="Producto no encontrado")

        # Desactivación lógica para conservar historial
        producto.activo = False

        auditoria = RegistroAuditoria(
            usuario_id=usuario['usuario_id'],
            tipo_accion="eliminacion_producto",
            descripcion=f"Producto desactivado: {producto.nombre} (ID: {producto_id})",
            fecha_accion=datetime.utcnow()
        )
        db.add(auditoria)
        db.commit()

        return {"mensaje": "Producto eliminado exitosamente"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error eliminando producto: {str(e)}")


# ─────────────────────────────────────────────
# VENTAS
# ─────────────────────────────────────────────

# GET /api/ventas - listar ventas por fecha
@router.get("/api/ventas", status_code=200)
async def obtener_ventas(
    fecha: Optional[str] = None,
    db: Session = Depends(obtener_db)
):
    try:
        controlador_ventas = ControladorVentas(db)

        if fecha:
            fecha_inicio = datetime.fromisoformat(fecha)
            fecha_fin = fecha_inicio.replace(hour=23, minute=59, second=59)
        else:
            fecha_inicio = datetime.utcnow().replace(hour=0, minute=0, second=0)
            fecha_fin = datetime.utcnow().replace(hour=23, minute=59, second=59)

        ventas = controlador_ventas.obtener_ventas_por_periodo(fecha_inicio, fecha_fin)

        if isinstance(ventas, dict) and 'error' in ventas:
            raise HTTPException(status_code=400, detail=ventas['error'])

        return [
            {
                "id": v.id,
                "fecha_venta": v.fecha_venta,
                "total": v.total,
                "estado": v.estado,
                "usuario": {"nombre": v.usuario.nombre},
                "items": [
                    {
                        "cantidad": i.cantidad,
                        "producto": {"nombre": i.producto.nombre},
                        "precio_unitario": i.precio_unitario,
                        "subtotal": i.subtotal
                    }
                    for i in v.items
                ]
            }
            for v in ventas
        ]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo ventas: {str(e)}")

# GET /api/ventas/consolidado - consolidado del día
@router.get("/api/ventas/consolidado", status_code=200)
async def obtener_consolidado_ventas(db: Session = Depends(obtener_db)):
    controlador_ventas = ControladorVentas(db)
    return controlador_ventas.consolidar_ventas_diarias()

# GET /api/ventas/{id} - obtener venta por ID
@router.get("/api/ventas/{venta_id}", status_code=200)
async def obtener_venta(venta_id: int, db: Session = Depends(obtener_db)):
    controlador_ventas = ControladorVentas(db)
    venta = controlador_ventas.obtener_venta_por_id(venta_id)
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    return {
        "id": venta.id,
        "fecha_venta": venta.fecha_venta,
        "total": venta.total,
        "estado": venta.estado,
        "usuario": {"nombre": venta.usuario.nombre},
        "items": [
            {
                "cantidad": i.cantidad,
                "producto": {"nombre": i.producto.nombre},
                "precio_unitario": i.precio_unitario,
                "subtotal": i.subtotal
            }
            for i in venta.items
        ]
    }

# POST /api/ventas - registrar nueva venta
@router.post("/api/ventas", status_code=201)
async def crear_venta(
    request: Request,
    session_id: Optional[str] = Header(None, alias="session-id"),
    db: Session = Depends(obtener_db)
):
    usuario = obtener_usuario_activo(session_id)
    datos = await request.json()
    controlador_ventas = ControladorVentas(db)

    resultado = controlador_ventas.registrar_venta(datos, usuario['usuario_id'])

    if 'error' in resultado:
        raise HTTPException(status_code=400, detail=resultado['error'])

    return resultado

# PATCH /api/ventas/{id} - anular venta (solo administradora)
@router.patch("/api/ventas/{venta_id}", status_code=200)
async def anular_venta(
    venta_id: int,
    request: Request,
    session_id: Optional[str] = Header(None, alias="session-id"),
    db: Session = Depends(obtener_db)
):
    try:
        usuario = obtener_usuario_activo(session_id)

        if usuario['rol'] != 'administradora':
            raise HTTPException(status_code=403, detail="No tiene permisos para anular ventas")

        datos = await request.json()
        controlador_ventas = ControladorVentas(db)

        resultado = controlador_ventas.anular_venta(
            venta_id, usuario['usuario_id'], datos.get('motivo', 'Sin motivo especificado')
        )

        if 'error' in resultado:
            raise HTTPException(status_code=400, detail=resultado['error'])

        return resultado

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error anulando venta: {str(e)}")


# ─────────────────────────────────────────────
# INVENTARIO
# ─────────────────────────────────────────────

# GET /api/inventario/productos - listar productos con info de stock
@router.get("/api/inventario/productos", status_code=200)
async def obtener_productos_inventario(db: Session = Depends(obtener_db)):
    try:
        productos = db.query(Producto).filter(Producto.activo == True).all()
        return [
            {
                "id": p.id,
                "codigo": p.codigo,
                "nombre": p.nombre,
                "categoria": p.categoria,
                "stock_actual": p.stock_actual,
                "stock_minimo": p.stock_minimo,
                "precio_venta": p.precio_venta
            }
            for p in productos
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo productos: {str(e)}")

# GET /api/inventario/alertas - productos con stock bajo
@router.get("/api/inventario/alertas", status_code=200)
async def obtener_alertas_inventario(db: Session = Depends(obtener_db)):
    controlador_inventario = ControladorInventario(db)
    return controlador_inventario.verificar_alertas_inventario()

# GET /api/inventario/historial - historial de movimientos
@router.get("/api/inventario/historial", status_code=200)
async def obtener_historial_inventario(
    producto_id: Optional[int] = None,
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    db: Session = Depends(obtener_db)
):
    try:
        controlador_inventario = ControladorInventario(db)

        fecha_inicio_dt = datetime.fromisoformat(fecha_inicio) if fecha_inicio else None
        fecha_fin_dt = datetime.fromisoformat(fecha_fin) if fecha_fin else None

        historial = controlador_inventario.obtener_historial_movimientos(
            producto_id, fecha_inicio_dt, fecha_fin_dt
        )

        if isinstance(historial, dict) and 'error' in historial:
            raise HTTPException(status_code=400, detail=historial['error'])

        return [
            {
                "fecha_movimiento": m.fecha_movimiento,
                "producto": {"nombre": m.producto.nombre},
                "tipo_movimiento": m.tipo_movimiento,
                "cantidad": m.cantidad,
                "stock_anterior": m.stock_anterior,
                "stock_nuevo": m.stock_nuevo,
                "motivo": m.motivo,
                "usuario": {"nombre": m.usuario.nombre}
            }
            for m in historial
        ]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo historial: {str(e)}")

# POST /api/inventario/movimientos - registrar entrada o salida
@router.post("/api/inventario/movimientos", status_code=201)
async def registrar_movimiento_inventario(
    request: Request,
    session_id: Optional[str] = Header(None, alias="session-id"),
    db: Session = Depends(obtener_db)
):
    usuario = obtener_usuario_activo(session_id)
    datos = await request.json()
    controlador_inventario = ControladorInventario(db)

    resultado = controlador_inventario.registrar_movimiento(datos, usuario['usuario_id'])

    if 'error' in resultado:
        raise HTTPException(status_code=400, detail=resultado['error'])

    return resultado


# ─────────────────────────────────────────────
# REPORTES
# ─────────────────────────────────────────────

# GET /api/reportes/balance - balance económico por periodo
@router.get("/api/reportes/balance", status_code=200)
async def obtener_balance_economico(
    fecha_inicio: str,
    fecha_fin: str,
    db: Session = Depends(obtener_db)
):
    try:
        controlador_reportes = ControladorReportes(db)
        balance = controlador_reportes.generar_balance_economico(
            datetime.fromisoformat(fecha_inicio),
            datetime.fromisoformat(fecha_fin)
        )
        return balance
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando balance: {str(e)}")

# GET /api/reportes/indicadores-ventas - comparativa de periodos
@router.get("/api/reportes/indicadores-ventas", status_code=200)
async def obtener_indicadores_ventas(
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    db: Session = Depends(obtener_db)
):
    try:
        controlador_reportes = ControladorReportes(db)
        indicadores = controlador_reportes.obtener_indicadores_ventas(
            datetime.fromisoformat(fecha_inicio) if fecha_inicio else None,
            datetime.fromisoformat(fecha_fin) if fecha_fin else None
        )
        return indicadores
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo indicadores: {str(e)}")

# GET /api/reportes/productos-mas-vendidos - ranking de productos
@router.get("/api/reportes/productos-mas-vendidos", status_code=200)
async def obtener_productos_mas_vendidos(
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    db: Session = Depends(obtener_db)
):
    try:
        controlador_reportes = ControladorReportes(db)
        productos = controlador_reportes.obtener_productos_mas_vendidos(
            datetime.fromisoformat(fecha_inicio) if fecha_inicio else None,
            datetime.fromisoformat(fecha_fin) if fecha_fin else None
        )
        return productos
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo productos más vendidos: {str(e)}")