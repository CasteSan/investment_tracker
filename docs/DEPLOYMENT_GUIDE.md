# Guia de Deployment: Investment Tracker en la Nube

Esta guia explica como desplegar Investment Tracker en Streamlit Cloud con Supabase PostgreSQL.

## Indice

1. [Requisitos Previos](#1-requisitos-previos)
2. [Configurar Supabase](#2-configurar-supabase)
3. [Migrar Datos Locales](#3-migrar-datos-locales)
4. [Configurar Usuarios](#4-configurar-usuarios)
5. [Deploy en Streamlit Cloud](#5-deploy-en-streamlit-cloud)
6. [Verificacion](#6-verificacion)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Requisitos Previos

### Cuentas necesarias (gratuitas)

- [x] Cuenta en GitHub con el repositorio
- [ ] Cuenta en [Supabase](https://supabase.com) (Free Tier)
- [ ] Cuenta en [Streamlit Cloud](https://streamlit.io/cloud) (Free Tier)

### Herramientas locales

```bash
# Verificar Python
python --version  # 3.10+

# Verificar dependencias
pip install -r requirements.txt
```

---

## 2. Configurar Supabase

### 2.1. Crear proyecto

1. Ve a [supabase.com](https://supabase.com) y crea una cuenta
2. Click en "New Project"
3. Configura:
   - **Name:** `investment-tracker` (o el nombre que prefieras)
   - **Database Password:** Genera uno seguro y GUARDALO
   - **Region:** Elige la mas cercana (ej: Frankfurt para Europa)
4. Click "Create new project" y espera ~2 minutos

### 2.2. Obtener DATABASE_URL

1. En el Dashboard de Supabase, ve a **Settings** (icono engranaje)
2. Click en **Database** en el menu lateral
3. En la seccion "Connection string", selecciona **URI**
4. Copia la URL. Tendra este formato:

```
postgresql://postgres:[TU_PASSWORD]@db.xxxxx.supabase.co:5432/postgres
```

5. Reemplaza `[TU_PASSWORD]` con el password que creaste

### 2.3. Guardar credenciales

Crea un archivo `.env` local (NO commitear):

```bash
# .env (solo para pruebas locales)
DATABASE_URL=postgresql://postgres:TU_PASSWORD@db.xxxxx.supabase.co:5432/postgres
```

---

## 3. Migrar Datos Locales

### 3.1. Verificar datos locales

```bash
# Ver que carteras tienes
ls data/portfolios/

# Ejemplo de salida:
# Cartera Jorge.db
# Cartera Raul.db
# Principal.db
```

### 3.2. Ejecutar migracion en modo prueba

```bash
# Cargar DATABASE_URL
export DATABASE_URL="postgresql://postgres:TU_PASSWORD@db.xxxxx.supabase.co:5432/postgres"

# Windows PowerShell:
# $env:DATABASE_URL = "postgresql://..."

# Modo dry-run (solo muestra que haria)
python scripts/migrate_to_cloud.py --dry-run
```

Deberia mostrar algo como:

```
============================================================
MIGRACION SQLite -> PostgreSQL
============================================================
Modo: DRY-RUN (sin cambios)

Archivos SQLite encontrados: 3
  - Cartera Jorge.db
  - Cartera Raul.db
  - Principal.db

Procesando: Cartera Jorge
    Transacciones: 4
    Dividendos: 0
    [DRY-RUN] Se crearia portfolio 'Cartera Jorge'
...
```

### 3.3. Ejecutar migracion real

```bash
# Ejecutar migracion REAL
python scripts/migrate_to_cloud.py --execute
```

### 3.4. Verificar en Supabase

1. Ve al Dashboard de Supabase
2. Click en **Table Editor** en el menu lateral
3. Deberias ver las tablas:
   - `portfolios` - Con tus carteras
   - `transactions` - Con tus transacciones
   - `dividends` - Con tus dividendos

---

## 4. Configurar Usuarios

### 4.1. Decidir usuarios y carteras

| Usuario | Password | Portfolio ID | Cartera |
|---------|----------|--------------|---------|
| juan | mi_password_seguro | 1 | Principal |
| maria | otro_password | 2 | Cartera Jorge |

### 4.2. Generar hashes de passwords

```bash
python -c "
from src.services.auth_service import AuthService

# Generar hash para cada usuario
print('juan:', AuthService.generate_password_hash('mi_password_seguro'))
print('maria:', AuthService.generate_password_hash('otro_password'))
"
```

Guarda los hashes generados.

### 4.3. Obtener portfolio_id de Supabase

En Supabase Table Editor, mira la tabla `portfolios`:

| id | name |
|----|------|
| 1 | Principal |
| 2 | Cartera Jorge |
| 3 | Cartera Raul |

### 4.4. Preparar secrets.toml

Crea el contenido para Streamlit Cloud:

```toml
# Conexion a PostgreSQL
DATABASE_URL = "postgresql://postgres:TU_PASSWORD@db.xxxxx.supabase.co:5432/postgres"

[auth.users.juan]
password = "5e884898da28047d9171b..."  # Hash generado
portfolio_id = 1
portfolio_name = "Principal"

[auth.users.maria]
password = "ef92b778bafe771e8924..."  # Hash generado
portfolio_id = 2
portfolio_name = "Cartera Jorge"
```

---

## 5. Deploy en Streamlit Cloud

### 5.1. Preparar repositorio

1. Asegurate de que tu repo esta actualizado en GitHub:

```bash
git push origin main
```

2. Verifica que `.gitignore` incluye:
   - `data/*.db`
   - `.env`
   - `.streamlit/secrets.toml`

### 5.2. Crear app en Streamlit Cloud

1. Ve a [share.streamlit.io](https://share.streamlit.io)
2. Click "New app"
3. Configura:
   - **Repository:** tu-usuario/investment-tracker
   - **Branch:** main
   - **Main file path:** app/main.py
4. Click "Advanced settings"

### 5.3. Configurar Secrets

En "Advanced settings" > "Secrets":

1. Pega el contenido de tu `secrets.toml`:

```toml
DATABASE_URL = "postgresql://postgres:TU_PASSWORD@db.xxxxx.supabase.co:5432/postgres"

[auth.users.juan]
password = "5e884898da28047d9171b..."
portfolio_id = 1
portfolio_name = "Principal"

[auth.users.maria]
password = "ef92b778bafe771e8924..."
portfolio_id = 2
portfolio_name = "Cartera Jorge"
```

2. Click "Save"

### 5.4. Deploy

1. Click "Deploy!"
2. Espera 2-5 minutos mientras se construye
3. La app estara disponible en: `https://tu-usuario-investment-tracker.streamlit.app`

---

## 6. Verificacion

### 6.1. Probar login

1. Abre la URL de tu app
2. Deberia mostrar la pagina de login
3. Introduce usuario y password
4. Deberia cargar el dashboard con tu cartera

### 6.2. Verificar datos

- [ ] Las transacciones aparecen correctamente
- [ ] El valor de la cartera es correcto
- [ ] Los graficos se muestran
- [ ] No aparece el selector de carteras (modo cloud)

### 6.3. Probar logout

1. Click en "Cerrar Sesion" en el sidebar
2. Deberia volver a la pagina de login

---

## 7. Troubleshooting

### Error: "No se pudo conectar a PostgreSQL"

**Causa:** DATABASE_URL incorrecta o password mal copiado

**Solucion:**
1. Verifica el password en Supabase (Settings > Database)
2. Asegurate de que no hay espacios extra en la URL
3. Verifica que el proyecto de Supabase esta activo

### Error: "Usuario o password incorrectos"

**Causa:** Hash del password incorrecto

**Solucion:**
1. Regenera el hash con `AuthService.generate_password_hash('tu_password')`
2. Actualiza el hash en Streamlit Cloud Secrets
3. Reinicia la app (Manage app > Reboot)

### Error: "portfolio_id no encontrado"

**Causa:** El usuario no tiene portfolio_id en secrets

**Solucion:**
1. Verifica que el ID existe en la tabla `portfolios` de Supabase
2. Anade `portfolio_id` al usuario en secrets

### La app no carga (spinner infinito)

**Causa:** Error en el codigo o dependencias

**Solucion:**
1. Ve a Streamlit Cloud > Manage app > Logs
2. Busca el error especifico
3. Comun: falta dependencia en `requirements.txt`

### Los datos no aparecen

**Causa:** La migracion no se ejecuto o portfolio_id incorrecto

**Solucion:**
1. Verifica en Supabase que hay datos en las tablas
2. Verifica que el `portfolio_id` del usuario coincide con los datos

---

## Resumen de URLs

| Servicio | URL |
|----------|-----|
| Tu App | `https://tu-usuario-investment-tracker.streamlit.app` |
| Streamlit Cloud Dashboard | `https://share.streamlit.io` |
| Supabase Dashboard | `https://supabase.com/dashboard` |

---

## Mantenimiento

### Actualizar la app

```bash
# Hacer cambios localmente
git add .
git commit -m "fix: descripcion del cambio"
git push origin main

# Streamlit Cloud detecta el push y redeploya automaticamente
```

### Anadir nuevo usuario

1. Genera hash del password
2. Obtiene portfolio_id de Supabase
3. Edita secrets en Streamlit Cloud Dashboard
4. La app se reinicia automaticamente

### Backup de datos

```sql
-- En Supabase SQL Editor
-- Exportar transacciones
SELECT * FROM transactions;

-- Exportar dividendos
SELECT * FROM dividends;
```

---

## Arquitectura Final

```
┌─────────────────────────────────────────────────────────────┐
│                    USUARIO                                   │
│                      │                                       │
│                      ▼                                       │
│         ┌───────────────────────┐                           │
│         │   Streamlit Cloud     │                           │
│         │   (Frontend + Auth)   │                           │
│         └───────────┬───────────┘                           │
│                     │                                        │
│                     ▼                                        │
│         ┌───────────────────────┐                           │
│         │   Supabase PostgreSQL │                           │
│         │   (Base de datos)     │                           │
│         └───────────────────────┘                           │
└─────────────────────────────────────────────────────────────┘

Modo Local (desarrollo):
┌─────────────────┐     ┌─────────────────┐
│  streamlit run  │────▶│  SQLite local   │
│  app/main.py    │     │  data/*.db      │
└─────────────────┘     └─────────────────┘
```
