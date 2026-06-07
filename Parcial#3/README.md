# StreamVault 🎬

Plataforma de streaming completa con gestión de usuarios, contenido, suscripciones y DRM básico.

## Tecnologías

- **Backend**: Python 3.10+ con Flask
- **Frontend**: HTML5 + CSS3 + JavaScript vanilla
- **Base de datos**: SQLite (incluida) / PostgreSQL / MySQL (configurable)
- **Reproductor**: HTML5 Video Player nativo

## Instalación

```bash
# 1. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Iniciar la aplicación
python app.py
```

La app estará disponible en: http://localhost:5000

## Usuarios Demo

Visita `/api/seed` para crear usuarios de prueba:

| Email | Contraseña | Plan |
|-------|-----------|------|
| admin@streamvault.com | admin123 | Admin |
| demo@streamvault.com | demo123 | Premium |

## Cambiar a PostgreSQL/MySQL

En `app.py`, modifica la línea:
```python
# SQLite (por defecto)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///streamvault.db'

# PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:password@localhost/streamvault'

# MySQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://user:password@localhost/streamvault'
```

Instala el driver correspondiente:
```bash
pip install psycopg2-binary  # PostgreSQL
pip install PyMySQL           # MySQL
```

## Funcionalidades

### Gestión de Usuarios
- ✅ Registro con validación
- ✅ Inicio de sesión seguro (bcrypt)
- ✅ Perfil editable
- ✅ Historial de reproducción

### Gestión de Contenido
- ✅ Subir videos (MP4, WebM, MKV)
- ✅ Clasificación por categorías
- ✅ Thumbnails personalizados
- ✅ Editar y eliminar videos propios

### Suscripciones
- ✅ Plan Gratuito (acceso limitado)
- ✅ Plan Premium (acceso total + 720p)
- ✅ Gate de contenido premium

### Recomendaciones
- ✅ Basadas en categorías favoritas del usuario
- ✅ Videos más vistos
- ✅ Sidebar en reproductor

### Streaming Adaptativo
- ✅ 480p y 720p
- ✅ Selección manual de calidad
- ✅ Range requests (seeking eficiente)

### DRM Básico
- ✅ No hay descarga directa (`nodownload`)
- ✅ Sin clic derecho en el video
- ✅ Acceso solo para autenticados
- ✅ Archivos servidos via endpoint seguro (no URL directa)
- ✅ Cache-Control: no-store

## Estructura del Proyecto

```
streamvault/
├── app.py              # Aplicación principal Flask
├── requirements.txt    # Dependencias
├── README.md
├── static/
│   ├── css/
│   │   └── main.css    # Estilos completos
│   ├── js/
│   │   └── main.js     # JavaScript
│   └── uploads/        # Videos y thumbnails
└── templates/
    ├── base.html        # Layout base con navbar
    ├── index.html       # Página de inicio
    ├── auth.html        # Login / Registro
    ├── browse.html      # Catálogo con búsqueda
    ├── watch.html       # Reproductor
    ├── upload.html      # Subir video
    ├── profile.html     # Perfil de usuario
    ├── dashboard.html   # Mis videos
    ├── pricing.html     # Planes y precios
    └── upgrade.html     # Gate premium
```

## API Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/register` | Registro de usuario |
| POST | `/api/login` | Inicio de sesión |
| GET | `/api/logout` | Cerrar sesión |
| POST | `/api/upload` | Subir video |
| PUT | `/api/video/<id>` | Editar video |
| DELETE | `/api/video/<id>` | Eliminar video |
| GET | `/api/stream/<id>/<quality>` | Streaming seguro |
| GET | `/api/recommendations` | Recomendaciones personalizadas |
| POST | `/api/upgrade` | Cambiar plan |
| PUT | `/api/profile` | Actualizar perfil |
