from sqlalchemy.orm import Session
from models.modelos import Usuario, RegistroAuditoria
from passlib.context import CryptContext
from datetime import datetime, timezone, timedelta

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class ControladorAutenticacion:
    def __init__(self, db: Session):
        self.db = db
    
    def verificar_password(self, password_plano: str, password_hashed: str):
        return pwd_context.verify(password_plano, password_hashed)
    
    def obtener_hash_password(self, password: str):
        return pwd_context.hash(password)
    
    def autenticar_usuario(self, email: str, password: str, ip_address: str = None):
        try:
            usuario = self.db.query(Usuario).filter(Usuario.email == email).first()
            if not usuario or not self.verificar_password(password, usuario.hashed_password):
                auditoria = RegistroAuditoria(
                    tipo_accion="login_fallido",
                    descripcion=f"Intento de login fallido para email: {email}",
                    fecha_accion=datetime.now(timezone(timedelta(hours=-5))),
                    ip_address=ip_address
                )
                self.db.add(auditoria)
                self.db.commit()
                return None
            
            if not usuario.activo:
                return None
            
            auditoria = RegistroAuditoria(
                usuario_id=usuario.id,
                tipo_accion="login_exitoso",
                descripcion=f"Login exitoso para usuario: {usuario.nombre}",
                fecha_accion=datetime.now(timezone(timedelta(hours=-5))),
                ip_address=ip_address
            )
            self.db.add(auditoria)
            self.db.commit()
            
            return usuario
            
        except Exception:
            self.db.rollback()
            return None
    
    def crear_usuario(self, datos_usuario: dict, usuario_creador_id: int):
        try:
            usuario_existente = self.db.query(Usuario).filter(
                Usuario.email == datos_usuario['email']
            ).first()
            if usuario_existente:
                return {"error": "El email ya está registrado"}
            
            nuevo_usuario = Usuario(
                email=datos_usuario['email'],
                nombre=datos_usuario['nombre'],
                hashed_password=self.obtener_hash_password(datos_usuario['password']),
                rol=datos_usuario['rol']
            )
            
            self.db.add(nuevo_usuario)
            
            auditoria = RegistroAuditoria(
                usuario_id=usuario_creador_id,
                tipo_accion="creacion_usuario",
                descripcion=(
                    f"Usuario creado: {datos_usuario['nombre']} "
                    f"({datos_usuario['email']}) con rol: {datos_usuario['rol']}"
                ),
                fecha_accion=datetime.now(timezone(timedelta(hours=-5)))
            )
            self.db.add(auditoria)
            
            self.db.commit()
            return {"mensaje": "Usuario creado exitosamente"}
            
        except Exception as e:
            self.db.rollback()
            return {"error": f"Error creando usuario: {str(e)}"}
