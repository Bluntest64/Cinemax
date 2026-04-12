from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import smtplib, ssl, threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Nombres de días y meses en español para formatear fechas
_DIAS_ES   = ['lunes','martes','miércoles','jueves','viernes','sábado','domingo']
_MESES_ES  = ['enero','febrero','marzo','abril','mayo','junio',
               'julio','agosto','septiembre','octubre','noviembre','diciembre']

def fecha_es(dt):
    """Devuelve la fecha en español: 'sábado, 11 de abril de 2026'"""
    if not dt:
        return ''
    dia_semana = _DIAS_ES[dt.weekday()]
    mes        = _MESES_ES[dt.month - 1]
    return f"{dia_semana}, {dt.day} de {mes} de {dt.year}"
import os, uuid, random, hashlib

# ─── CONFIGURACIÓN DE EMAIL ────────────────────────────────────────────────────
MAIL_USER     = os.environ.get('MAIL_USER', '')      # tu@gmail.com
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')  # App Password de Google
APP_URL       = os.environ.get('APP_URL', 'http://localhost:5000')  # URL pública del sitio

def _qr_svg_inline(code: str, size: int = 200) -> str:
    """Genera un SVG de QR pseudoaleatorio determinista para incluir en el email."""
    CELL = 7
    N    = 25
    # Hash determinista del código
    h = int(hashlib.sha256(code.encode()).hexdigest(), 16)
    bits = []
    seed = h
    for _ in range(N * N):
        seed = (seed * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
        bits.append((seed >> 33) & 1)
    # Forzar esquinas de finder patterns
    for r in range(7):
        for c in range(7):
            bits[r*N+c] = 1
            bits[r*N+(N-1-c)] = 1
            bits[(N-1-r)*N+c] = 1
    total = CELL * N + 16
    rects = []
    for r in range(N):
        for c in range(N):
            if bits[r*N+c]:
                x = c * CELL + 8
                y = r * CELL + 8
                rects.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" fill="#0a0d14"/>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{total}" height="{total}">'
           f'<rect width="{total}" height="{total}" fill="white" rx="8"/>'
           + ''.join(rects) + '</svg>')
    return svg

def _send_email_async(to_email: str, subject: str, html_body: str):
    """Envía el email en un hilo aparte para no bloquear la respuesta HTTP."""
    if not MAIL_USER or not MAIL_PASSWORD:
        print(f"[EMAIL] MAIL_USER/MAIL_PASSWORD no configurados — email NO enviado a {to_email}")
        return
    def _send():
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From']    = f'CINEMAX Experience <{MAIL_USER}>'
            msg['To']      = to_email
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=ctx) as s:
                s.login(MAIL_USER, MAIL_PASSWORD)
                s.sendmail(MAIL_USER, to_email, msg.as_string())
            print(f"[EMAIL] Enviado a {to_email}: {subject}")
        except Exception as e:
            print(f"[EMAIL] ERROR enviando a {to_email}: {e}")
    threading.Thread(target=_send, daemon=True).start()

def _build_confirmation_email(user_name: str, ticket_code: str, confirm_url: str,
                               movie_title: str, show_time: str, seats: str,
                               total: int, combo: str, date_str: str) -> str:
    """HTML del email de confirmación con diseño cinematográfico."""
    qr_svg    = _qr_svg_inline(ticket_code)
    total_fmt = f"${total:,.0f}".replace(',', '.')
    combo_row = f"""
        <tr>
          <td style="padding:8px 0;border-bottom:1px solid #1a1f2e;color:#7986cb;font-size:13px;">🍿 Combos</td>
          <td style="padding:8px 0;border-bottom:1px solid #1a1f2e;color:#e8eaf6;font-size:13px;text-align:right;">{combo}</td>
        </tr>""" if combo and combo != 'Sin combos' else ''

    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#030508;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#030508;padding:40px 20px;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#0a0d14;border:1px solid #1a1f2e;border-radius:16px;overflow:hidden;max-width:560px;width:100%;">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#0d1117,#1a0a20);padding:32px;text-align:center;border-bottom:1px solid #1a1f2e;">
            <div style="font-size:32px;font-weight:900;letter-spacing:6px;background:linear-gradient(135deg,#bf00ff,#00d4ff);-webkit-background-clip:text;-webkit-text-fill-color:transparent;color:#bf00ff;">CINEMAX</div>
            <div style="font-size:9px;letter-spacing:5px;color:#7986cb;margin-top:4px;">EXPERIENCE</div>
            <div style="margin-top:20px;font-size:22px;font-weight:700;letter-spacing:2px;color:#ffffff;">🎬 CONFIRMA TU COMPRA</div>
            <div style="font-size:13px;color:#7986cb;margin-top:6px;">Hola, <strong style="color:#e8eaf6;">{user_name}</strong> — revisa los detalles y confirma</div>
          </td>
        </tr>

        <!-- Ticket details -->
        <tr>
          <td style="padding:28px 32px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td colspan="2" style="padding-bottom:16px;">
                  <div style="font-size:20px;font-weight:700;color:#ffffff;letter-spacing:1px;">{movie_title}</div>
                  <div style="font-size:11px;letter-spacing:3px;color:#bf00ff;margin-top:4px;text-transform:uppercase;">Código: {ticket_code}</div>
                </td>
              </tr>
              <tr>
                <td style="padding:8px 0;border-bottom:1px solid #1a1f2e;color:#7986cb;font-size:13px;">📅 Fecha</td>
                <td style="padding:8px 0;border-bottom:1px solid #1a1f2e;color:#e8eaf6;font-size:13px;text-align:right;">{date_str}</td>
              </tr>
              <tr>
                <td style="padding:8px 0;border-bottom:1px solid #1a1f2e;color:#7986cb;font-size:13px;">🕐 Función</td>
                <td style="padding:8px 0;border-bottom:1px solid #1a1f2e;color:#e8eaf6;font-size:13px;text-align:right;">{show_time}</td>
              </tr>
              <tr>
                <td style="padding:8px 0;border-bottom:1px solid #1a1f2e;color:#7986cb;font-size:13px;">💺 Asientos</td>
                <td style="padding:8px 0;border-bottom:1px solid #1a1f2e;color:#e8eaf6;font-size:13px;text-align:right;">{seats}</td>
              </tr>
              {combo_row}
              <tr>
                <td style="padding:12px 0;color:#7986cb;font-size:14px;font-weight:700;">💰 Total</td>
                <td style="padding:12px 0;color:#ffd700;font-size:20px;font-weight:700;text-align:right;">{total_fmt} COP</td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- QR -->
        <tr>
          <td style="padding:0 32px 24px;text-align:center;">
            <div style="background:white;display:inline-block;padding:12px;border-radius:12px;">
              {qr_svg}
            </div>
            <div style="font-size:11px;letter-spacing:4px;color:#bf00ff;margin-top:12px;font-weight:700;">{ticket_code}</div>
            <div style="font-size:11px;color:#7986cb;margin-top:4px;">Presenta este código en taquilla</div>
          </td>
        </tr>

        <!-- CTA Button -->
        <tr>
          <td style="padding:0 32px 32px;text-align:center;">
            <div style="background:#1a1f2e;border:1px solid #2a2f3e;border-radius:10px;padding:16px 24px;margin-bottom:20px;">
              <div style="font-size:12px;color:#7986cb;margin-bottom:8px;">⚠️ Tu tiquete aún NO está confirmado</div>
              <div style="font-size:11px;color:#5a6080;">Haz clic en el botón para confirmar tu compra y activar tu entrada</div>
            </div>
            <a href="{confirm_url}"
               style="display:inline-block;padding:16px 40px;background:linear-gradient(135deg,#bf00ff,#00d4ff);border-radius:8px;color:#ffffff;font-size:16px;font-weight:700;letter-spacing:3px;text-decoration:none;text-transform:uppercase;">
              ✅ CONFIRMAR MI COMPRA
            </a>
            <div style="font-size:11px;color:#5a6080;margin-top:16px;">Este enlace expira en 24 horas</div>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#060810;padding:20px 32px;border-top:1px solid #1a1f2e;text-align:center;">
            <div style="font-size:11px;color:#3a3f50;letter-spacing:1px;">CINEMAX EXPERIENCE · Sistema de gestión de cine</div>
            <div style="font-size:10px;color:#2a2f40;margin-top:4px;">Si no solicitaste esta compra, ignora este correo.</div>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'cinemax-secret-change-in-prod')

# ─── DATABASE ──────────────────────────────────────────────────────────────────
DB_URL = os.environ.get('DATABASE_URL')
if not DB_URL:
    raise RuntimeError(
        "DATABASE_URL no está configurada. "
        "Agrega la variable de entorno en Render → Environment."
    )
# Render a veces entrega postgres:// pero SQLAlchemy necesita postgresql://
if DB_URL.startswith('postgres://'):
    DB_URL = DB_URL.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# ─── MODELS ────────────────────────────────────────────────────────────────────
class User(db.Model):
    __tablename__ = 'users'
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(150), nullable=False)
    email      = db.Column(db.String(200), unique=True, nullable=False)
    password   = db.Column(db.String(255), nullable=False)   # bcrypt hash
    role       = db.Column(db.String(60),  default='Usuario')
    color      = db.Column(db.String(20),  default='#00d4ff')
    initials   = db.Column(db.String(4),   default='??')
    created_at = db.Column(db.DateTime,   default=datetime.utcnow)
    # Relations
    cards      = db.relationship('Card',   backref='user', lazy=True, cascade='all,delete')
    tickets    = db.relationship('Ticket', backref='user', lazy=True, cascade='all,delete')

class Movie(db.Model):
    __tablename__ = 'movies'
    id            = db.Column(db.Integer, primary_key=True)
    title         = db.Column(db.String(200), nullable=False)
    genre         = db.Column(db.String(100))
    duration      = db.Column(db.Integer)
    rating        = db.Column(db.String(10))
    age_limit     = db.Column(db.Integer, default=0)
    age_label     = db.Column(db.String(20), default='ATP')
    tags          = db.Column(db.String(300))
    director      = db.Column(db.String(150))
    cast_list     = db.Column(db.String(300))
    language      = db.Column(db.String(50), default='Subtitulada')
    description   = db.Column(db.Text)
    poster_url    = db.Column(db.String(500))
    is_active     = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=99)

class Showtime(db.Model):
    __tablename__ = 'showtimes'
    id          = db.Column(db.Integer, primary_key=True)
    movie_id    = db.Column(db.Integer, db.ForeignKey('movies.id'))
    hall        = db.Column(db.String(50))
    show_time   = db.Column(db.String(10))
    format_type = db.Column(db.String(20))
    movie       = db.relationship('Movie', backref='showtimes')

class Card(db.Model):
    __tablename__ = 'cards'
    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    card_number   = db.Column(db.String(20))   # last 4 digits only
    holder_name   = db.Column(db.String(150))
    expiry_date   = db.Column(db.String(10))
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

class Ticket(db.Model):
    __tablename__ = 'tickets'
    id             = db.Column(db.Integer, primary_key=True)
    ticket_code    = db.Column(db.String(60), unique=True, nullable=False)
    user_id        = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    movie_title    = db.Column(db.String(200))
    show_time      = db.Column(db.String(20))
    seats          = db.Column(db.Text)          # JSON list of seats
    total          = db.Column(db.Integer, default=0)
    payment_method = db.Column(db.String(30))
    combo_detail   = db.Column(db.Text)
    status         = db.Column(db.String(20), default='pendiente')  # pendiente / activo / usado / cancelado
    confirm_token  = db.Column(db.String(80), unique=True, nullable=True)
    purchased_at   = db.Column(db.DateTime, default=datetime.utcnow)

# ─── LOCATION DATA ─────────────────────────────────────────────────────────────
LOCATION_DATA = {
    "Colombia":  ["Armenia","Barranquilla","Bogotá","Bucaramanga","Buenaventura",
                  "Cali","Cartagena","Cúcuta","Ibagué","Manizales","Medellín",
                  "Montería","Neiva","Pasto","Pereira","Santa Marta","Valledupar","Villavicencio"],
    "México":    ["Ciudad de México","Guadalajara","Monterrey","Puebla","Tijuana",
                  "León","Juárez","Mérida","San Luis Potosí","Querétaro"],
    "Argentina": ["Buenos Aires","Córdoba","Rosario","Mendoza","La Plata",
                  "Tucumán","Mar del Plata","Salta","Santa Fe","San Juan"],
    "Chile":     ["Santiago","Valparaíso","Concepción","La Serena","Antofagasta",
                  "Temuco","Rancagua","Talca","Arica","Chillán"],
    "Perú":      ["Lima","Arequipa","Trujillo","Chiclayo","Piura","Iquitos","Cusco","Huancayo"],
    "Venezuela": ["Caracas","Maracaibo","Valencia","Barquisimeto","Maturín","Maracay"],
    "Ecuador":   ["Quito","Guayaquil","Cuenca","Santo Domingo","Ambato","Manta"],
    "Bolivia":   ["La Paz","Santa Cruz","Cochabamba","Sucre","Oruro","Potosí"],
    "Paraguay":  ["Asunción","Ciudad del Este","San Lorenzo","Luque","Capiatá"],
    "Uruguay":   ["Montevideo","Salto","Paysandú","Las Piedras","Rivera"],
}

# ─── MOVIES ────────────────────────────────────────────────────────────────────
MOVIES_DATA = [
    # ── PELÍCULAS EXISTENTES (títulos corregidos) ──────────────────────────────
    {
        "title": "La Muerte Roja",
        "genre": "Sci-Fi oscuro / Suspenso",
        "duration": 107,
        "rating": "PG-13", "age_limit": 13, "age_label": "+13",
        "tags": "Terror,Psicologico,IA,Tecnologia,Oscuro,Suspenso,Distopia,VocalSynth,Digital,Misterio,Thriller,Anime,Horror,CienciaFiccion",
        "director": "Twindrill",
        "cast_list": "Laura Méndez (Dra. Valeria Torres), Carlos Herrera (Técnico Mateo Ríos), Sofía Navarro (Niña Elena), Andrés Salgado (Investigador Daniel Cruz)",
        "language": "Subtitulada / Doblada",
        "description": "Una inteligencia artificial experimental comienza a enviar señales misteriosas que provocan visiones y paranoia en quienes las reciben. A medida que el fenómeno se expande, aparece una figura conocida como Kasane Teto en todas las pantallas. Mientras un grupo intenta detener la propagación, descubren que la “Muerte Roja” no es solo un error… sino un evento digital imposible de apagar.",
        "poster_url": "/static/posters/LaMuerteRoja.jpg",
        "display_order": -9
    },
    {
        "title": "Five Nights at Freddy's 2",
        "genre": "Terror / Misterio",
        "duration": 110, "rating": "PG-13", "age_limit": 13, "age_label": "+13",
        "tags": "Terror,Suspenso,Animatrónicos,Misterio,Supervivencia,Noche,Videojuego,Adaptación",
        "director": "Emma Tammi","cast_list": "Josh Hutcherson, Matthew Lillard, Elizabeth Lail",
        "language": "Subtitulada / Doblada",
        "description": "Después de los aterradores eventos en Freddy Fazbear's Pizza, nuevas anomalías comienzan a surgir cuando una instalación renovada abre sus puertas con animatrónicos más avanzados. Un nuevo turno nocturno deberá vigilar las cámaras mientras extraños sucesos se intensifican. A medida que la noche avanza, los secretos del pasado resurgen y las nuevas máquinas demuestran que no solo están diseñadas para entretener, sino también para observar… y moverse cuando nadie las mira.",
        "poster_url": "/static/posters/FNAF2.jpg",
        "display_order": -8
    },
    {
        "title": "Five Nights at Freddy's",
        "genre": "Género / Subgénero",
        "duration": 109,
        "rating": "PG-13", "age_limit": 13, "age_label": "+13",
        "tags": "Terror,Suspenso,Animatrónicos,Misterio,Supervivencia,Noche,Videojuego,Adaptación",
        "director": "Emma Tammi",
        "cast_list": "Josh Hutcherson, Matthew Lillard, Elizabeth Lail",
        "language": "Subtitulada / Doblada",
        "description": "Un joven con problemas personales acepta un trabajo como guardia de seguridad nocturno en la abandonada pizzería Freddy Fazbear's Pizza. Lo que parecía una tarea sencilla se convierte en una pesadilla cuando descubre que los animatrónicos cobran vida durante la noche. Mientras intenta sobrevivir hasta el amanecer, comienza a descubrir oscuros secretos relacionados con desapariciones, experimentos y el verdadero origen del lugar.",
        "poster_url": "/static/posters/FNAF.jpg",
        "display_order": -7
    },
    {
        "title": "The Backrooms",
        "genre": "Terror / Fantasía", "duration": 105,
        "rating": "PG-13", "age_limit": 13, "age_label": "+13",
        "tags": "Terror_psicológico,Found_Footage,Misterio,Ciencia_ficción",
        "director": "Kane Parsons",
        "cast_list": "Chiwetel Ejiofor, Renate Reinsve, Mark Duplass",
        "language": "Subtitulada / Doblada",
        "description": "Un joven camarógrafo accidentalmente atraviesa una anomalía y despierta en un laberinto interminable de oficinas amarillas iluminadas por luces fluorescentes. Mientras intenta encontrar una salida, descubre grabaciones, instalaciones abandonadas y evidencias de un experimento que salió terriblemente mal. A medida que avanza, la realidad se vuelve inestable y una presencia desconocida parece observar cada uno de sus movimientos.",
        "poster_url": "/static/posters/TheBackrooms.jpg",
        "display_order": -6
    },
    {
        "title": "Miku No Puede Cantar",
        "genre": "Anime / Musical / Drama / Fantasías",
        "duration": 105,
        "rating": "PG",
        "age_limit": 7,
        "age_label": "+7",
        "tags": "Musical,Drama,Fantasía,Emotiva,Idols,Virtual,Superación,Juvenil",
        "director": "Hiroyuki Hata",
        "cast_list": "Saki Fujita, Ruriko Noguchi, Tomori Kusunoki",
        "language": "Subtitulada",
        "description": "En un mundo donde la música conecta sentimientos, una versión de Hatsune Miku aparece incapaz de cantar, perdiendo aquello que le daba sentido a su existencia. Mientras distintos jóvenes atraviesan sus propias luchas personales, sus emociones comienzan a entrelazarse con esta misteriosa Miku. A través de la amistad, la creatividad y el poder de la música, deberán encontrar la forma de devolverle su voz y descubrir que incluso en los momentos de silencio, los sentimientos pueden resonar con más fuerza que nunca.",
        "poster_url": "/static/posters/MikuNoPuedeCantar.jpg",
        "display_order": -5
    },
    {
        "title": "Friday Night Funkin Triple Trouble",
        "genre": "accion / terror",
        "duration": 60,
        "rating": "PG-13",
        "age_limit": 13,
        "age_label": "+13",
        "tags": "Musical,Ritmo,Crossover,Acción",
        "director": "RightBurstUltrar",
        "cast_list": "Xenophanes/Sonic.EXE: MarStarBro, Tails(voz y gritos): Saster, Knuckles : Saster, Boyfriend: Kawai Sprite",
        "language": "Subtitulada / Doblada",
        "description": "Boyfriend y Girlfriend se ven arrastrados a una dimensión oscura dominada por entidades corruptas inspiradas en el universo de Sonic. A medida que avanzan, deben enfrentarse a múltiples adversarios en intensos duelos musicales donde cada canción se vuelve más peligrosa que la anterior. Con la realidad distorsionándose y el tiempo desmoronándose, la única forma de sobrevivir es mantener el ritmo perfecto. En esta batalla desesperada, la música se convierte en la última defensa contra una amenaza que busca atraparlos para siempre.",
        "poster_url": "/static/posters/FNFTripleTroble.jpg",
        "display_order": -4
    },
    {
        "title": "Rascal Does Not Dream of a Knapsack Kid (2023)",
        "genre": "Romance / Drama",
        "duration": 75, "rating": "PG-13", "age_limit": 13, "age_label": "+13",
        "tags": "Drama,Romance,Sobrenatural,Escolar,Emotiva,Adolescentes",
        "director": "Sōichi Masui",
        "cast_list": "Kaito Ishikawa (Sakuta Azusagawa), Asami Seto (Mai Sakurajima), Yurika Kubo (Kaede Azusagawa)",
        "language": "Subtitulada",
        "description": "Una misteriosa chica con apariencia infantil aparece frente a Sakuta, afirmando ser una versión más joven de Mai. Mientras la fecha de graduación se acerca, Sakuta se ve envuelto nuevamente en fenómenos del 'Síndrome de la Adolescencia', donde los sentimientos reprimidos y los miedos al futuro toman forma. La historia explora el crecimiento, la identidad y el significado de avanzar hacia una nueva etapa de la vida, poniendo a prueba los vínculos entre Sakuta, Mai y quienes los rodean.",
        "poster_url": "/static/posters/RascalDoesNotDreamofaKnapsackKid.jpg",
        "display_order": -3
    },
    {
        "title": "Rascal Does Not Dream of a Sister Venturing Out (2023)",       
        "genre": "Romance / Adolescentes",       # ← ej: "Acción / Aventura"
        "duration": 73, "rating": "PG-13",# ← minutos (número) \ ← PG/PG-13/R/NR/G
        "age_limit": 13, "age_label": "+13", # ←0/7/13/16/18 \← "ATP"/"+7"/"+13"/"+16"/"+18"
        "tags": "Drama,Anime,Adolescentes,Japón,melancólico,superación,familia", # ← sin espacios tras comas
        "director": "Sōichi Masui",                   # ← director
        "cast_list": "Kaito Ishikawa (Sakuta Azusagawa), Asami Seto (Mai Sakurajima), Yurika Kubo (Kaede Azusagawa)",  # ← actores principales
        "language": "Subtitulada",                    # ← idioma
        "description": "Kaede, la hermana menor de Sakuta, decide dar un paso importante: volver a salir al mundo después de haber pasado mucho tiempo aislada. Mientras intenta enfrentarse a sus miedos y recuperar una vida normal, Sakuta la apoya en cada momento, acompañándola en este proceso lleno de emociones, recuerdos y crecimiento personal. La historia se centra en la superación, la familia y el valor necesario para avanzar hacia el futuro.",    # ← descripción corta
        "poster_url": "/static/posters/RascalDoesNotDramofaSisterVenturingOut(2023).jpg",  # ← nombre del jpg en static/posters/
        "display_order": -2                           # ← no toques esto
    },
    {
        "title": "Rascal Does Not Dream of a Dreaming Girl (2019)",
        "genre": "Romance / Drama",
        "duration": 90, "rating": "PG-13", "age_limit": 13, "age_label": "+13",
        "tags": "Romance,Drama,Anime,Adolescentes,Japón,emocional",
        "director": "Souichi Masui",
        "cast_list": "Kaito Ishikawa, Asami Seto, Atsumi Tanezaki",
        "language": "Subtitulada",
        "description": "Sakuta Azusagawa, quien conoce la existencia del Síndrome de la Pubertad, se enfrenta a un nuevo caso: una chica que vive en su interior y en la realidad al mismo tiempo.",
        "poster_url": "/static/posters/RascalDoesNotDramofaDreamingGirl(2019).jpg",
        "display_order": -1
    },
    {
        "title":"Black Panther: Wakanda Forever",
        "genre":"Acción / Superhéroes",
        "duration":161,"rating":"PG-13","age_limit":13,"age_label":"+13",
        "tags":"Acción,Superhéroes,Drama,Marvel,Aventura",
        "director":"Ryan Coogler","cast_list":"Letitia Wright, Angela Bassett, Tenoch Huerta",
        "language":"Subtitulada / Doblada",
        "description":"Los guerreros de Wakanda luchan para proteger su nación tras la pérdida de su rey y enfrentan una amenaza submarina inesperada: Namor y Talokan.",
        "poster_url":"/static/posters/wakanda.jpg","display_order":1
    },
    {
        "title":"Damsel",
        "genre":"Fantasía / Acción",
        "duration":110,"rating":"PG-13","age_limit":13,"age_label":"+13",
        "tags":"Fantasía,Acción,Aventura,Suspenso,Dragones",
        "director":"Juan Carlos Fresnadillo","cast_list":"Millie Bobby Brown, Ray Winstone, Robin Wright",
        "language":"Subtitulada",
        "description":"Una joven damisela descubre que su matrimonio arreglado fue una trampa para sacrificarla a un dragón antiguo. Deberá luchar sola para sobrevivir.",
        "poster_url":"/static/posters/damsel.jpg","display_order":2
    },
    {
        "title":"Alita: Ángel de Combate",
        "genre":"Ciencia Ficción / Acción",
        "duration":122,"rating":"PG-13","age_limit":13,"age_label":"+13",
        "tags":"Ciencia Ficción,Acción,Cyberpunk,Aventura,Futuro",
        "director":"Robert Rodriguez","cast_list":"Rosa Salazar, Christoph Waltz, Jennifer Connelly",
        "language":"Subtitulada / Doblada",
        "description":"Un cyborg despierta sin memoria en un mundo futurista del siglo XXVI y descubre sus increíbles habilidades de combate mientras busca su identidad.",
        "poster_url":"/static/posters/alita.jpg","display_order":3
    },
    {
        "title":"Shang-Chi y la Leyenda de los Diez Anillos",
        "genre":"Acción / Artes Marciales",
        "duration":132,"rating":"PG-13","age_limit":13,"age_label":"+13",
        "tags":"Acción,Artes Marciales,Superhéroes,Marvel,Aventura",
        "director":"Destin Daniel Cretton","cast_list":"Simu Liu, Awkwafina, Tony Leung",
        "language":"Subtitulada / Doblada",
        "description":"Shang-Chi debe enfrentarse al pasado que creía haber dejado atrás cuando es arrastrado a la red de la misteriosa organización de los Diez Anillos.",
        "poster_url":"/static/posters/shangchi.jpg","display_order":4
    },
    {
        "title":"El Reino del Planeta de los Simios",
        "genre":"Ciencia Ficción / Aventura",
        "duration":145,"rating":"PG-13","age_limit":13,"age_label":"+13",
        "tags":"Ciencia Ficción,Aventura,Drama,Acción,Distopía",
        "director":"Wes Ball","cast_list":"Owen Teague, Freya Allan, Kevin Durand",
        "language":"Subtitulada / Doblada",
        "description":"Generaciones después del reinado de César, los simios son la especie dominante. Un joven simio emprende un viaje que cuestionará todo lo que cree.",
        "poster_url":"/static/posters/kingdomapes.jpg","display_order":5
    },
    {
        "title":"Kung Fu Panda 4",
        "genre":"Animación / Comedia",
        "duration":94,"rating":"PG","age_limit":0,"age_label":"ATP",
        "tags":"Animación,Comedia,Familiar,Aventura,Artes Marciales",
        "director":"Mike Mitchell","cast_list":"Jack Black, Awkwafina, Viola Davis",
        "language":"Doblada / Subtitulada",
        "description":"Po debe encontrar y entrenar a un nuevo Guerrero Dragón, mientras enfrenta a su villana más astuta: una camaleona con el poder de copiar a cualquier maestro.",
        "poster_url":"/static/posters/kungfupanda.jpg","display_order":6
    },
    {
        "title":"Mulan",
        "genre":"Acción / Aventura","duration":115,"rating":"PG-13",
        "age_limit":13,"age_label":"+13",
        "tags":"Acción,Aventura,Drama,Histórico,Familiar",
        "director":"Niki Caro","cast_list":"Yifei Liu, Donnie Yen, Jet Li",
        "language":"Subtitulada / Doblada",
        "description":"Una joven valiente se disfraza de hombre para luchar en el ejército en lugar de su anciano padre. Basada en la leyenda china de Hua Mulan.",
        "poster_url":"/static/posters/mulan.jpg","display_order":7
    },
    {
        "title":"Titanic",
        "genre":"Romance / Drama","duration":195,"rating":"PG-13",
        "age_limit":13,"age_label":"+13",
        "tags":"Romance,Drama,Histórico,Catástrofe,Clásico",
        "director":"James Cameron","cast_list":"Leonardo DiCaprio, Kate Winslet, Billy Zane",
        "language":"Subtitulada / Doblada",
        "description":"Una historia de amor que trasciende clases sociales a bordo del famoso transatlántico. Basada en el hundimiento del RMS Titanic en 1912.",
        "poster_url":"/static/posters/titanic.jpg","display_order":8
    },
    {
        "title":"Doctor Strange en el Multiverso de la Locura",
        "genre":"Acción / Ciencia Ficción",
        "duration":126,"rating":"PG-13","age_limit":13,"age_label":"+13",
        "tags":"Acción,Superhéroes,Ciencia Ficción,Terror,Marvel",
        "director":"Sam Raimi","cast_list":"Benedict Cumberbatch, Elizabeth Olsen, Rachel McAdams",
        "language":"Subtitulada / Doblada",
        "description":"Doctor Strange viaja a través del multiverso enfrentando versiones alternativas de sí mismo y peligros inimaginables junto a América Chávez.",
        "poster_url":"/static/posters/drstrange.jpg","display_order":9
    },
    {
        "title":"Thor: Amor y Trueno",
        "genre":"Acción / Superhéroes",
        "duration":119,"rating":"PG-13","age_limit":13,"age_label":"+13",
        "tags":"Acción,Superhéroes,Comedia,Marvel,Aventura",
        "director":"Taika Waititi","cast_list":"Chris Hemsworth, Natalie Portman, Christian Bale",
        "language":"Subtitulada / Doblada",
        "description":"Thor emprende un viaje diferente a todo lo que ha enfrentado: la búsqueda de la paz interior. Pero su retiro es interrumpido por un villain galáctico.",
        "poster_url":"/static/posters/thor.jpg","display_order":10
    },
    {
        "title":"Aladdin",
        "genre":"Fantasía / Musical",
        "duration":128,"rating":"PG","age_limit":0,"age_label":"ATP",
        "tags":"Fantasía,Musical,Aventura,Familiar,Romance",
        "director":"Guy Ritchie","cast_list":"Will Smith, Mena Massoud, Naomi Scott",
        "language":"Subtitulada / Doblada",
        "description":"Un joven de la calle encuentra una lámpara mágica que libera a un genio con poderes increíbles, cambiando su destino para siempre en Agrabah.",
        "poster_url":"/static/posters/aladdin.jpg","display_order":11
    },

    # ── NUEVAS PELÍCULAS ───────────────────────────────────────────────────────
    {
        "title":"Annabelle",
        "genre":"Terror / Suspenso",
        "duration":99,"rating":"R","age_limit":18,"age_label":"+18",
        "tags":"Terror,Suspenso,Sobrenatural,Muñeca,The Conjuring",
        "director":"John R. Leonetti","cast_list":"Annabelle Wallis, Ward Horton, Alfre Woodard",
        "language":"Subtitulada / Doblada",
        "description":"Antes de El Conjuro existía Annabelle. Una muñeca poseída desata el terror en una familia cuando fuerzas demoníacas comienzan a acecharlos sin descanso.",
        "poster_url":"/static/posters/annabelle.jpg","display_order":12
    },
    {
        "title":"Ouija: El Origen del Mal",
        "genre":"Terror / Sobrenatural",
        "duration":99,"rating":"PG-13","age_limit":13,"age_label":"+13",
        "tags":"Terror,Sobrenatural,Posesión,Suspenso,Ouija",
        "director":"Mike Flanagan","cast_list":"Elizabeth Reaser, Lulu Wilson, Annalise Basso",
        "language":"Subtitulada / Doblada",
        "description":"Una viuda y sus hijas usan una tabla Ouija como truco en su negocio de médium, pero sin saberlo convocan una presencia maligna que posee a la hija menor.",
        "poster_url":"/static/posters/ouija.jpg","display_order":13
    },
    {
        "title":"Terrifier 3",
        "genre":"Terror / Slasher",
        "duration":125,"rating":"NR","age_limit":18,"age_label":"+18",
        "tags":"Terror,Slasher,Gore,Art the Clown,Navidad",
        "director":"Damien Leone","cast_list":"David Howard Thornton, Lauren LaVera, Elliott Fullam",
        "language":"Subtitulada",
        "description":"Art the Clown regresa en Navidad para sembrar el terror más brutal. La temporada festiva nunca volverá a ser la misma en su noche de masacre más sangrienta.",
        "poster_url":"/static/posters/terrifier3.jpg","display_order":14
    },
    {
        "title":"Smile 2",
        "genre":"Terror / Psicológico",
        "duration":127,"rating":"R","age_limit":18,"age_label":"+18",
        "tags":"Terror,Psicológico,Suspenso,Maldición,Sonrisa",
        "director":"Parker Finn","cast_list":"Naomi Scott, Kyle Gallner, Lukas Gage",
        "language":"Subtitulada / Doblada",
        "description":"Una famosa estrella del pop empieza a experimentar sucesos aterradores justo antes de comenzar su gira mundial, atrapada en una maldición que no la dejará ir.",
        "poster_url":"/static/posters/smile2.jpg","display_order":15
    },
    {
        "title":"El Culto de Chucky",
        "genre":"Terror / Comedia",
        "duration":91,"rating":"NR","age_limit":18,"age_label":"+18",
        "tags":"Terror,Slasher,Muñeco,Comedia Negra,Chucky",
        "director":"Don Mancini","cast_list":"Brad Dourif, Fiona Dourif, Jennifer Tilly",
        "language":"Subtitulada / Doblada",
        "description":"Chucky regresa con múltiples copias de sí mismo para aterrorizar a los pacientes de un hospital psiquiátrico en su entrega más retorcida y caótica.",
        "poster_url":"/static/posters/chucky.jpg","display_order":16
    },
    {
        "title":"Big Hero 6",
        "genre":"Animación / Acción",
        "duration":102,"rating":"PG","age_limit":0,"age_label":"ATP",
        "tags":"Animación,Acción,Familiar,Superhéroes,Aventura",
        "director":"Don Hall, Chris Williams","cast_list":"Ryan Potter, Scott Adsit, T.J. Miller",
        "language":"Doblada / Subtitulada",
        "description":"Un joven prodigio de la robótica crea un equipo de superhéroes con su robot inflable Baymax para combatir a un villano enmascarado en San Fransokyo.",
        "poster_url":"/static/posters/bighero6.jpg","display_order":17
    },
    {
        "title":"Jumanji: Bienvenidos a la Jungla",
        "genre":"Aventura / Comedia",
        "duration":119,"rating":"PG-13","age_limit":13,"age_label":"+13",
        "tags":"Aventura,Comedia,Acción,Videojuego,Familiar",
        "director":"Jake Kasdan","cast_list":"Dwayne Johnson, Jack Black, Kevin Hart, Karen Gillan",
        "language":"Subtitulada / Doblada",
        "description":"Cuatro adolescentes son absorbidos hacia un videojuego de la selva y deben sobrevivir jugando como sus avatares adultos para regresar al mundo real.",
        "poster_url":"/static/posters/jumanji.jpg","display_order":18
    },
    {
        "title":"Clown in a Cornfield",
        "genre":"Terror / Slasher",
        "duration":98,"rating":"R","age_limit":18,"age_label":"+18",
        "tags":"Terror,Slasher,Payaso,Pueblo,Adolescentes",
        "director":"Carter Smith","cast_list":"Katie Douglas, Aaron Abrams, Carson MacCormac",
        "language":"Subtitulada",
        "description":"Una chica llega a un pueblo pequeño y queda atrapada en la mira de Frendo, el payaso mascota de la ciudad, cuando los lugareños deciden acabar con los jóvenes.",
        "poster_url":"/static/posters/clownincornfield.jpg","display_order":19
    },
    {
        "title":"Elementales",
        "genre":"Animación / Romance",
        "duration":101,"rating":"PG","age_limit":0,"age_label":"ATP",
        "tags":"Animación,Romance,Familiar,Aventura,Disney Pixar",
        "director":"Peter Sohn","cast_list":"Leah Lewis, Mamoudou Athie, Ronnie del Carmen",
        "language":"Doblada / Subtitulada",
        "description":"En Element City, donde fuego, agua, tierra y aire coexisten, Ember y Wade descubren algo sorprendente: quizás los opuestos sí se atraen.",
        "poster_url":"/static/posters/elementals.jpg","display_order":20
    },
    {
        "title":"Hansel y Gretel: Cazadores de Brujas",
        "genre":"Acción / Fantasía Oscura",
        "duration":88,"rating":"R","age_limit":18,"age_label":"+18",
        "tags":"Acción,Fantasía,Terror,Aventura,Brujas",
        "director":"Tommy Wirkola","cast_list":"Jeremy Renner, Gemma Arterton, Famke Janssen",
        "language":"Subtitulada / Doblada",
        "description":"Años después de sobrevivir a la bruja del cuento, Hansel y Gretel se convierten en legendarios cazadores de brujas que recorren el mundo eliminando hechiceras.",
        "poster_url":"/static/posters/hanselgretel.jpg","display_order":21
    },
    {
        "title":"Las Crónicas de Narnia: La Travesía del Viajero del Alba",
        "genre":"Fantasía / Aventura",
        "duration":113,"rating":"PG","age_limit":0,"age_label":"ATP",
        "tags":"Fantasía,Aventura,Familiar,Magia,Narnia",
        "director":"Michael Apted","cast_list":"Ben Barnes, Skandar Keynes, Georgie Henley",
        "language":"Subtitulada / Doblada",
        "description":"Lucy, Edmund y su primo Eustace regresan a Narnia a bordo del barco El Viajero del Alba para rescatar a almas perdidas y enfrentar una oscuridad creciente.",
        "poster_url":"/static/posters/narnia.jpg","display_order":22
    },
    {
        "title":"Percy Jackson y el Mar de los Monstruos",
        "genre":"Fantasía / Aventura",
        "duration":106,"rating":"PG","age_limit":0,"age_label":"ATP",
        "tags":"Fantasía,Aventura,Mitología,Familiar,Acción",
        "director":"Thor Freudenthal","cast_list":"Logan Lerman, Alexandra Daddario, Brandon T. Jackson",
        "language":"Subtitulada / Doblada",
        "description":"Percy Jackson y sus amigos se adentran en el Mar de los Monstruos para recuperar el Vellocino de Oro y salvar el Campamento Mestizo de su destrucción.",
        "poster_url":"/static/posters/percyjackson.jpg","display_order":23
    },
    {
        "title":"A Minecraft Movie",
        "genre":"Aventura / Comedia",
        "duration":101,"rating":"PG","age_limit":0,"age_label":"ATP",
        "tags":"Aventura,Comedia,Familiar,Videojuego,Acción",
        "director":"Jared Hess","cast_list":"Jack Black, Jason Momoa, Jennifer Coolidge",
        "language":"Subtitulada / Doblada",
        "description":"Cuatro inadaptados del mundo real son arrastrados al Overworld de Minecraft, donde deben construir, explorar y sobrevivir para encontrar el camino a casa.",
        "poster_url":"/static/posters/minecraft.jpg","display_order":24
    }
]

SHOWTIMES = ["2:00 PM","4:20 PM","6:40 PM","9:10 PM","9:30 PM"]
HALLS     = ["SALA 1","SALA 2","SALA 3","SALA 4","SALA 5"]
FORMATS   = ["2D","3D","IMAX"]
PRICES    = {"normal":18000,"vip":28000,"ultra":38000}


def seed_db():
    # ── Películas: upsert seguro película por película ──────────────────────────
    for md in MOVIES_DATA:
        try:
            existing = Movie.query.filter_by(title=md['title']).first()
            if existing:
                # Actualizar campos si la película ya existe
                for k, v in md.items():
                    setattr(existing, k, v)
            else:
                db.session.add(Movie(**md))
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"[SEED] Error con película '{md.get('title')}': {e}")

    # ── Horarios: verificar por película, no globalmente ──────────────────────
    # Así las películas nuevas que se agreguen después también reciben horarios.
    for movie in Movie.query.all():
        try:
            if Showtime.query.filter_by(movie_id=movie.id).count() == 0:
                for t in random.sample(SHOWTIMES, random.randint(2, 4)):
                    db.session.add(Showtime(
                        movie_id=movie.id,
                        hall=random.choice(HALLS),
                        show_time=t,
                        format_type=random.choice(FORMATS)
                    ))
                db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"[SEED] Error con horario para '{movie.title}': {e}")

    # ── Cuentas del equipo ───────────────────────────────────────────────────────
    SEED_ACCOUNTS = [
        # ── ADMINISTRADOR (acceso al panel de control) ────────────────────────
        {'email':'admin@cinemax.com', 'pass':'admin123',
         'name':'Administrador', 'role':'admin','color':'#ffd700','initials':'AD'},
        # ── Cuentas del equipo ────────────────────────────────────────────────
        {'email':'jesusbarriosrodrig6@gmail.com',     'pass':'123456',
         'name':'Jesús Barrios',  'role':'usuario','color':'#bf00ff','initials':'JB'},
        {'email':'eilinsolano0123@gmail.com',          'pass':'987654321',
         'name':'Eilin Solano',   'role':'usuario','color':'#00d4ff','initials':'ES'},
        {'email':'matiasserrato156@gmail.com',         'pass':'matias serrato 123',
         'name':'Matías Serrato','role':'usuario','color':'#ff006e','initials':'MS'},
        {'email':'123kevindavidgomezposada@gmail.com', 'pass':'123456789',
         'name':'Kevin Gómez',   'role':'usuario','color':'#00ff9f','initials':'KG'},
    ]
    for acc in SEED_ACCOUNTS:
        try:
            if not User.query.filter_by(email=acc['email']).first():
                db.session.add(User(
                    name=acc['name'], email=acc['email'],
                    password=generate_password_hash(acc['pass']),
                    role=acc['role'], color=acc['color'], initials=acc['initials']
                ))
                db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"[SEED] Error con cuenta '{acc['email']}': {e}")


# ─── HELPERS ───────────────────────────────────────────────────────────────────
def current_user():
    uid = session.get('user_id')
    if not uid:
        return None
    return User.query.get(uid)

def require_login():
    u = current_user()
    if not u:
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    return u


# ─── ROUTES ────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    movies = Movie.query.filter_by(is_active=True).order_by(Movie.display_order).all()
    return render_template('index.html', movies=movies, location_data=LOCATION_DATA)

@app.route('/api/movies')
def api_movies():
    movies = Movie.query.filter_by(is_active=True).all()
    return jsonify([{'id':m.id,'title':m.title,'genre':m.genre,'duration':m.duration,
        'rating':m.rating,'age_limit':m.age_limit,'age_label':m.age_label,
        'tags':m.tags,'director':m.director,'cast_list':m.cast_list,
        'language':m.language,'description':m.description,'poster_url':m.poster_url
    } for m in movies])

@app.route('/api/locations')
def api_locations():
    return jsonify(LOCATION_DATA)

@app.route('/api/showtimes/<int:movie_id>')
def api_showtimes(movie_id):
    return jsonify([{'id':s.id,'hall':s.hall,'show_time':s.show_time,'format_type':s.format_type}
                    for s in Showtime.query.filter_by(movie_id=movie_id).all()])


# ─── AUTH ──────────────────────────────────────────────────────────────────────
@app.route('/api/login', methods=['POST'])
def api_login():
    data     = request.json or {}
    email    = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password, password):
        return jsonify({'success': False, 'error': 'Correo o contraseña incorrectos'})
    session['user_id'] = user.id
    return jsonify({
        'success': True,
        'user': {
            'id':       user.id,
            'name':     user.name,
            'email':    user.email,
            'role':     user.role,
            'color':    user.color,
            'initials': user.initials
        }
    })

@app.route('/api/register', methods=['POST'])
def api_register():
    data     = request.json or {}
    name     = (data.get('name') or '').strip()
    email    = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    if not name or not email or not password:
        return jsonify({'success': False, 'error': 'Faltan datos'})
    if len(password) < 6:
        return jsonify({'success': False, 'error': 'La contraseña debe tener mínimo 6 caracteres'})
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'error': 'Ese correo ya está registrado'})
    initials = ''.join(w[0] for w in name.split() if w).upper()[:2] or '??'
    palette  = ['#00d4ff','#bf00ff','#ff006e','#ffd700','#00ff9f']
    color    = palette[User.query.count() % len(palette)]
    user = User(name=name, email=email,
                password=generate_password_hash(password),
                initials=initials, color=color)
    db.session.add(user)
    db.session.commit()
    session['user_id'] = user.id
    return jsonify({
        'success': True,
        'user': {
            'id':       user.id,
            'name':     user.name,
            'email':    user.email,
            'role':     user.role,
            'color':    user.color,
            'initials': user.initials
        }
    })

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.pop('user_id', None)
    return jsonify({'success': True})

@app.route('/api/me')
def api_me():
    """Devuelve el usuario de la sesión actual — usado al recargar la página."""
    u = current_user()
    if not u:
        return jsonify({'logged_in': False})
    return jsonify({
        'logged_in': True,
        'user': {
            'id':       u.id,
            'name':     u.name,
            'email':    u.email,
            'role':     u.role,
            'color':    u.color,
            'initials': u.initials
        }
    })


# ─── CARDS ─────────────────────────────────────────────────────────────────────
@app.route('/api/cards', methods=['GET'])
def get_cards():
    result = require_login()
    if isinstance(result, tuple): return result
    user = result
    return jsonify([{
        'id': c.id,
        'card_number': '**** **** **** ' + (c.card_number or '')[-4:],
        'holder_name': c.holder_name,
        'expiry_date': c.expiry_date or ''
    } for c in Card.query.filter_by(user_id=user.id).all()])

@app.route('/api/cards', methods=['POST'])
def create_card():
    result = require_login()
    if isinstance(result, tuple): return result
    user = result
    data = request.json or {}
    try:
        # Store only last 4 digits
        raw     = (data.get('card_number') or '').replace(' ','')
        last4   = raw[-4:] if len(raw) >= 4 else raw
        expiry  = data.get('expiry_date') or ''
        card = Card(user_id=user.id, card_number=last4,
                    holder_name=data.get('holder_name',''), expiry_date=expiry)
        db.session.add(card)
        db.session.commit()
        return jsonify({'success': True, 'id': card.id, 'last4': last4})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


# ─── TICKETS ───────────────────────────────────────────────────────────────────
@app.route('/api/tickets', methods=['POST'])
def buy_ticket():
    result = require_login()
    if isinstance(result, tuple): return result
    user = result
    data        = request.json or {}
    code        = 'CX-' + str(uuid.uuid4())[:8].upper()
    movie_title = data.get('movieTitle', '')
    show_time   = data.get('showTime', '')
    seats       = data.get('seats', '')
    total       = int(data.get('total', 0))
    payment     = data.get('payment', 'efectivo')
    combo       = data.get('combo', '')
    date_str    = data.get('date', fecha_es(datetime.utcnow()))

    # Token único para confirmar la compra por email
    confirm_token = hashlib.sha256(
        (code + user.email + str(datetime.utcnow().timestamp())).encode()
    ).hexdigest()[:40]

    ticket = Ticket(
        ticket_code    = code,
        user_id        = user.id,
        movie_title    = movie_title,
        show_time      = show_time,
        seats          = seats,
        total          = total,
        payment_method = payment,
        combo_detail   = combo,
        status         = 'pendiente',   # se activa al confirmar por email
        confirm_token  = confirm_token
    )
    db.session.add(ticket)
    db.session.commit()

    # Enviar email de confirmación (no bloqueante)
    confirm_url = f"{APP_URL}/confirmar/{confirm_token}"
    html = _build_confirmation_email(
        user_name   = user.name,
        ticket_code = code,
        confirm_url = confirm_url,
        movie_title = movie_title,
        show_time   = show_time,
        seats       = seats,
        total       = total,
        combo       = combo or 'Sin combos',
        date_str    = date_str
    )
    _send_email_async(
        to_email = user.email,
        subject  = f'🎬 Confirma tu compra — {movie_title} · CINEMAX',
        html_body = html
    )

    return jsonify({
        'success':     True,
        'ticket_code': code,
        'status':      'pendiente',
        'message':     f'Revisa tu correo {user.email} para confirmar la compra.'
    })

@app.route('/api/tickets', methods=['GET'])
def get_tickets():
    result = require_login()
    if isinstance(result, tuple): return result
    user = result
    tickets = Ticket.query.filter_by(user_id=user.id).order_by(Ticket.purchased_at.desc()).all()
    return jsonify([{
        'qrCode':      t.ticket_code,
        'movieTitle':  t.movie_title,
        'showTime':    t.show_time,
        'seats':       t.seats,
        'total':       t.total,
        'payment':     t.payment_method,
        'combo':       t.combo_detail or 'Sin combos',
        'date':        fecha_es(t.purchased_at),
        'status':      t.status   # pendiente / activo / usado / cancelado
    } for t in tickets])

@app.route('/api/tickets/validate', methods=['GET'])
def validate_ticket():
    code = (request.args.get('code') or '').strip().upper()
    t = Ticket.query.filter_by(ticket_code=code).first()
    if not t:
        return jsonify({'valid': False, 'error': 'Código no encontrado'})
    return jsonify({
        'valid': True,
        'qrCode':      t.ticket_code,
        'movieTitle':  t.movie_title,
        'showTime':    t.show_time,
        'seats':       t.seats,
        'total':       t.total,
        'payment':     t.payment_method,
        'status':      t.status,
        'date':        t.purchased_at.strftime('%d/%m/%Y %H:%M') if t.purchased_at else ''
    })


# ─── CONFIRM TICKET ───────────────────────────────────────────────────────────
@app.route('/confirmar/<token>')
def confirm_ticket(token):
    ticket = Ticket.query.filter_by(confirm_token=token).first()
    if not ticket:
        return render_template('confirm_result.html',
            success=False, message='Enlace de confirmación inválido o ya utilizado.')
    if ticket.status == 'activo':
        return render_template('confirm_result.html',
            success=True, already=True,
            ticket_code=ticket.ticket_code,
            movie_title=ticket.movie_title,
            show_time=ticket.show_time,
            seats=ticket.seats,
            total=ticket.total)
    # Activar el tiquete
    ticket.status        = 'activo'
    ticket.confirm_token = None   # consumir el token (un solo uso)
    db.session.commit()
    return render_template('confirm_result.html',
        success=True, already=False,
        ticket_code=ticket.ticket_code,
        movie_title=ticket.movie_title,
        show_time=ticket.show_time,
        seats=ticket.seats,
        total=ticket.total)

# ─── ADMIN API ────────────────────────────────────────────────────────────────
def require_admin():
    u = current_user()
    if not u:
        return jsonify({'error': 'No autenticado'}), 401
    if u.role != 'admin':
        return jsonify({'error': 'Acceso restringido'}), 403
    return u

@app.route('/api/admin/stats')
def admin_stats():
    result = require_admin()
    if isinstance(result, tuple): return result

    # ── Métricas generales ──────────────────────────────────────────────────────
    from sqlalchemy import func, case

    activos   = Ticket.query.filter(Ticket.status.in_(['activo','usado'])).all()
    pendientes = Ticket.query.filter_by(status='pendiente').count()
    total_tickets = len(activos)
    ingresos_total = sum(t.total for t in activos)

    # ── Por película ────────────────────────────────────────────────────────────
    por_pelicula = {}
    for t in activos:
        key = t.movie_title or 'Sin título'
        if key not in por_pelicula:
            por_pelicula[key] = {'tickets': 0, 'ingresos': 0}
        por_pelicula[key]['tickets']  += 1
        por_pelicula[key]['ingresos'] += t.total

    ranking = sorted(por_pelicula.items(), key=lambda x: x[1]['tickets'], reverse=True)

    # ── Por método de pago ──────────────────────────────────────────────────────
    por_pago = {}
    for t in activos:
        p = t.payment_method or 'efectivo'
        por_pago[p] = por_pago.get(p, 0) + 1

    # ── Snacks / combos ─────────────────────────────────────────────────────────
    snack_counter = {}
    import re
    for t in activos:
        if t.combo_detail and t.combo_detail != 'Sin combos':
            # Parse "🍿 Crispeta Grande x3, ☕ Café x1"
            parts = t.combo_detail.split(',')
            for part in parts:
                part = part.strip()
                if not part or part == 'Sin combos':
                    continue
                # Extract quantity suffix "xN"
                qty = 1
                if ' x' in part:
                    try:
                        qty = int(part.rsplit(' x', 1)[1].strip())
                        part = part.rsplit(' x', 1)[0].strip()
                    except Exception:
                        pass
                # Strip leading non-letter chars (emojis, spaces)
                name = part.lstrip()
                while name and not (name[0].isalpha() or name[0].isdigit()):
                    name = name[1:].lstrip()
                name = name.strip()
                if name:
                    snack_counter[name] = snack_counter.get(name, 0) + qty

    snacks = sorted(snack_counter.items(), key=lambda x: x[1], reverse=True)

    # ── Últimos 10 tiquetes ─────────────────────────────────────────────────────
    recientes = (Ticket.query
                 .filter(Ticket.status.in_(['activo', 'usado', 'pendiente']))
                 .order_by(Ticket.purchased_at.desc())
                 .limit(10)
                 .all())

    # ── Usuarios registrados ────────────────────────────────────────────────────
    total_usuarios = User.query.filter(User.role != 'admin').count()

    return jsonify({
        'total_tickets':   total_tickets,
        'ingresos_total':  ingresos_total,
        'pendientes':      pendientes,
        'total_usuarios':  total_usuarios,
        'ranking': [
            {'pelicula': k, 'tickets': v['tickets'], 'ingresos': v['ingresos']}
            for k, v in ranking
        ],
        'por_pago': por_pago,
        'snacks':   [{'nombre': k, 'cantidad': v} for k, v in snacks],
        'recientes': [{
            'codigo':   t.ticket_code,
            'pelicula': t.movie_title,
            'usuario':  (db.session.get(User, t.user_id).email if t.user_id and db.session.get(User, t.user_id) else '—'),
            'total':    t.total,
            'estado':   t.status,
            'fecha':    fecha_es(t.purchased_at),
            'asientos': t.seats or '—',
            'pago':     t.payment_method or '—',
        } for t in recientes],
    })

# ─── MIGRATION: agregar columnas nuevas si no existen (seguro en Render) ────────
def run_migrations():
    """
    db.create_all() NO agrega columnas a tablas existentes.
    Esta función las agrega manualmente con ALTER TABLE IF NOT EXISTS.
    Es idempotente: si la columna ya existe, no hace nada.
    """
    migrations = [
        # Tabla tickets — columnas añadidas después del deploy inicial
        "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'pendiente'",
        "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS confirm_token VARCHAR(80)",
        "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS purchased_at TIMESTAMP DEFAULT NOW()",
        "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS combo_detail TEXT",
        "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS seats TEXT",
        "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS show_time VARCHAR(20)",
        "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS movie_title VARCHAR(200)",
        "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS payment_method VARCHAR(30)",
        "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS total INTEGER DEFAULT 0",
        "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS user_id INTEGER",
        # Tabla users — columnas nuevas
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(60) DEFAULT 'usuario'",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS color VARCHAR(20) DEFAULT '#00d4ff'",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS initials VARCHAR(4) DEFAULT '??'",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW()",
        # Unique index para confirm_token (solo si no existe)
        """DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename='tickets' AND indexname='uq_tickets_confirm_token'
            ) THEN
                CREATE UNIQUE INDEX uq_tickets_confirm_token
                ON tickets (confirm_token) WHERE confirm_token IS NOT NULL;
            END IF;
        END $$""",
    ]
    import psycopg2
    try:
        conn = psycopg2.connect(os.environ.get('DATABASE_URL', '').replace('postgres://', 'postgresql://', 1))
        conn.autocommit = True
        cur = conn.cursor()
        for sql in migrations:
            try:
                cur.execute(sql)
                print(f"[MIGRATION] OK: {sql[:60]}...")
            except Exception as e:
                print(f"[MIGRATION] Skip (ya existe?): {e}")
        conn.close()
        print("[MIGRATION] Todas las migraciones completadas.")
    except Exception as e:
        print(f"[MIGRATION] Error de conexión: {e}")


def dedup_rascal():
    """
    Elimina entradas duplicadas de Rascal en la BD.
    Conserva la que tiene poster_url='/static/posters/RascalDoesNotDramofaDreamingGirl(2019).jpg'
    y elimina todas las demás variantes sin imagen o con título diferente.
    """
    # Buscar todas las películas cuyo título contenga 'Rascal' y 'Dream'
    rascals = Movie.query.filter(
        Movie.title.ilike('%rascal%does%not%dream%dreaming%')
    ).all()

    if len(rascals) <= 1:
        # Si hay 0 o 1, no hay duplicado de la primera película
        pass
    else:
        # Ordenar: primero los que tienen poster_url correcto
        rascals.sort(key=lambda m: (
            0 if (m.poster_url and 'RascalDoesNotDramofaDreamingGirl' in m.poster_url) else 1,
            m.id
        ))
        keep = rascals[0]  # el primero es el bueno
        for dup in rascals[1:]:
            try:
                # Eliminar horarios del duplicado
                Showtime.query.filter_by(movie_id=dup.id).delete()
                db.session.delete(dup)
                db.session.commit()
                print(f"[DEDUP] Eliminado duplicado Rascal id={dup.id} title='{dup.title}'")
            except Exception as e:
                db.session.rollback()
                print(f"[DEDUP] Error eliminando id={dup.id}: {e}")

    # También eliminar entradas sin imagen ni título exacto (typos en el título)
    # que puedan haber quedado de inserciones manuales
    imposters = Movie.query.filter(
        Movie.title.ilike('%rascal%dream%'),
        ~Movie.title.ilike('%dreaming girl%')
    ).all()
    for m in imposters:
        try:
            Showtime.query.filter_by(movie_id=m.id).delete()
            db.session.delete(m)
            db.session.commit()
            print(f"[DEDUP] Eliminado impostór id={m.id} title='{m.title}'")
        except Exception as e:
            db.session.rollback()
            print(f"[DEDUP] Error con impostór id={m.id}: {e}")


# ─── BOOT ──────────────────────────────────────────────────────────────────────
with app.app_context():
    run_migrations()   # ← PRIMERO: asegurar que todas las columnas existan
    db.create_all()    # ← crea tablas nuevas si no existen
    dedup_rascal()     # ← limpia duplicados de Rascal
    seed_db()          # ← inserta/actualiza películas y cuentas

if __name__ == '__main__':
    with app.app_context():
        run_migrations()
        db.create_all()
        dedup_rascal()
        seed_db()
    app.run(debug=False, port=5000)
