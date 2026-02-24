from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Base de datos SQLite para desarrollo
DATABASE_URL = "sqlite:///./storevision.db"

motor = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SesionLocal = sessionmaker(autocommit=False, autoflush=False, bind=motor)
Base = declarative_base()

def obtener_db():
    db = SesionLocal()
    try:
        yield db
    finally:
        db.close()

def crear_tablas():
    Base.metadata.create_all(bind=motor)