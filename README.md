# 🎬 CINEMAX – Aplicación de Cine

Aplicación web tipo Royal Films con estética neón oscura. Compra tiquetes, escoge horarios, tipo de asiento (Normal/VIP/Ultra) y paga con efectivo o tarjeta.

---

## 🚀 Instalación Local

### 1. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 2. Configurar variables de entorno
```bash
cp .env.example .env
# Edita .env con tus credenciales
```

### 3. Ejecutar
```bash
python run.py
```
Abre: http://localhost:5000

---

## 🗄️ MySQL Local

1. Crea la base de datos:
```sql
CREATE DATABASE cinemax CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. En `.env`, cambia:
```
DATABASE_URL=mysql+pymysql://root:tu_password@localhost/cinemax
```

3. Ejecuta `python run.py` — crea las tablas automáticamente.

---

## ☁️ Deploy en Railway

1. Crea cuenta en [railway.app](https://railway.app)
2. Sube el proyecto a GitHub
3. En Railway: **New Project → Deploy from GitHub**
4. Agrega un plugin **MySQL** o **PostgreSQL**
5. Railway configura `DATABASE_URL` automáticamente
6. Agrega variable: `SECRET_KEY=tu-clave-secreta`
7. Configura: `NIXPACKS_PYTHON_VERSION=3.11`
8. ¡Listo! Railway detecta el `Procfile` y despliega.

---

## ☁️ Deploy en Render

1. Crea cuenta en [render.com](https://render.com)
2. **New → Web Service → conecta GitHub**
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Agrega **PostgreSQL** desde el dashboard de Render
6. Render te da la URL de conexión — agrégala como `DATABASE_URL`

---

## 🎭 Funcionalidades

| Característica | Detalle |
|---|---|
| 🎬 Cartelera | 11 películas con póster, género, rating |
| 🕐 Horarios | Múltiples horarios hasta las 9:30 PM |
| 💺 Asientos | Normal ($18k), VIP ($28k), Ultra ($38k) |
| 💳 Tarjetas | Crear, guardar y usar tarjetas de crédito |
| 💵 Efectivo | Pago en efectivo disponible |
| 🎟️ Tiquetes | Código único por compra, historial disponible |
| 🌃 UI Neón | Estética oscura con efectos neón y scanlines |
| 🏙️ Ciudades | Selector de ciudad (18 ciudades colombianas) |

---

## 📁 Estructura

```
cinemax/
├── app.py          ← Aplicación Flask + API + Modelos
├── run.py          ← Script de inicio local
├── requirements.txt
├── Procfile        ← Para Railway/Render
├── .env.example    ← Plantilla de variables de entorno
└── templates/
    └── index.html  ← Frontend completo (HTML + CSS + JS)
```
