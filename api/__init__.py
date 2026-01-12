"""
API Module - FastAPI REST API

Este módulo contendrá la API REST para exponer los servicios
a clientes externos (web frontend, móvil, etc.)

Estructura planificada:
- main.py: Aplicación FastAPI y configuración
- routes/: Endpoints organizados por dominio
  - portfolio.py: /api/portfolio/*
  - transactions.py: /api/transactions/*
  - reports.py: /api/reports/*
- auth/: Autenticación y autorización
  - jwt.py: Tokens JWT
  - permissions.py: Roles y permisos
- schemas/: Modelos Pydantic para request/response

Nota: Esta API consumirá los MISMOS servicios que Streamlit,
demostrando la escalabilidad de la arquitectura.

Uso futuro:
    uvicorn api.main:app --reload
"""

__all__ = []
