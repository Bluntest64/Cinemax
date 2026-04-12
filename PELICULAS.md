# 🎬 Guía: Cómo Agregar y Eliminar Películas

---

## ✅ Agregar una película nueva

### 1. Sube la imagen del póster
Coloca el archivo `.jpg` en `static/posters/`. Nombre sin espacios ni tildes:
```
static/posters/mipelicula.jpg
```

### 2. Llena la plantilla en `app.py`
Busca el bloque con el `display_order` que quieres usar (-2, -3, etc.) y reemplaza los valores:

```python
{
    "title": "Sword Art Online: Ordinal Scale",   # ← nombre exacto (clave única)
    "genre": "Animación / Ciencia Ficción",
    "duration": 119,                              # ← minutos, número entero
    "rating": "PG-13",                            # ← PG / PG-13 / R / NR
    "age_limit": 13,                              # ← 0 / 7 / 13 / 16 / 18
    "age_label": "+13",                           # ← "ATP" / "+7" / "+13" / "+16" / "+18"
    "tags": "Animación,Acción,Videojuegos,Anime", # ← sin espacios tras comas
    "director": "Tomohiko Ito",
    "cast_list": "Yoshitsugu Matsuoka, Haruka Tomatsu",
    "language": "Subtitulada",
    "description": "Kirito y sus amigos se enfrentan...",
    "poster_url": "/static/posters/sao.jpg",      # ← ruta al jpg
    "display_order": -2                           # ← número (más negativo = más arriba)
},
```

### 3. Haz commit y push
```bash
git add .
git commit -m "feat: agrego Sword Art Online"
git push
```
Render redespliega automáticamente y la película aparece con horarios en la web.

---

## ⚠️ Valores de `age_limit` y `age_label` que debes usar juntos

| Clasificación | `age_limit` | `age_label` | Badge color |
|---|---|---|---|
| Para todos | `0` | `"ATP"` | Verde |
| Mayores de 7 | `7` | `"+7"` | Azul |
| Mayores de 13 | `13` | `"+13"` | Amarillo |
| Mayores de 16 | `16` | `"+16"` | Naranja |
| Mayores de 18 | `18` | `"+18"` | Rojo |

---

## ❌ Eliminar una película — Dos opciones

### Opción A: Desactivar (recomendada) — La película desaparece de la web pero sus datos y tiquetes se conservan en la BD

Agrega `"is_active": False` al bloque de la película en `MOVIES_DATA`:

```python
{
    "title": "Película que quiero ocultar",
    # ... resto de campos ...
    "is_active": False,      # ← agrega esta línea
    "display_order": 5
},
```

Luego haz commit y push. La película desaparece de la cartelera.

### Opción B: Borrar del array — Solo funciona completamente si también la borras de la BD

**Sí, puedes borrar el bloque del array** en `app.py`. Eso evita que se vuelva a crear en futuros despliegues. **Pero si ya estaba en la BD de PostgreSQL en Render, sigue apareciendo en la web** porque `seed_db` solo inserta/actualiza — no borra.

Para eliminarla completamente de Render también debes correr esto en el Shell de Render (Render → Web Service → Shell):

```sql
-- Primero ve el ID de la película
SELECT id, title FROM movies WHERE title = 'Nombre Exacto de la Película';

-- Luego bórrala (reemplaza 999 con el ID real)
DELETE FROM showtimes WHERE movie_id = 999;
DELETE FROM movies WHERE id = 999;
```

**Resumen:**

| Acción | ¿Desaparece de la web? | ¿Se borran tiquetes? |
|---|---|---|
| Solo borrar del array | ❌ No (sigue en BD) | No |
| Poner `is_active: False` | ✅ Sí | No |
| Borrar del array + DELETE en BD | ✅ Sí | Sí (si no tiene tiquetes) |

---

## 📐 Sistema de `display_order`

Número más **pequeño** = aparece más a la **izquierda/arriba** en la cartelera.

```
-8  -7  -6  -5  -4  -3  -2  -1  1  2  3  4 ... 24
◄─────────────── más importante ───────────────────────── menos importante ───►
```

Para agregar más películas prioritarias, continúa con -9, -10, -11, etc.
