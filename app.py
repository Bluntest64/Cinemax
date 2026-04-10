from flask import Flask, render_template, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os, uuid

app = Flask(__name__)
db = SQLAlchemy(app)
app.secret_key = os.environ.get('SECRET_KEY', 'cinemax-secret-2024')

DB_URL = os.environ.get('DATABASE_URL', 'sqlite:///cinemax.db')
if DB_URL.startswith('postgres://'):
    DB_URL = DB_URL.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False



# ─── MODELS ────────────────────────────────────────────────────────────────────
class Movie(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(200), nullable=False)
    genre       = db.Column(db.String(100))
    duration    = db.Column(db.Integer)
    rating      = db.Column(db.String(10))
    age_limit   = db.Column(db.Integer, default=0)
    age_label   = db.Column(db.String(20), default='ATP')
    tags        = db.Column(db.String(300))
    director    = db.Column(db.String(150))
    cast_list   = db.Column(db.String(300))
    language    = db.Column(db.String(50), default='Subtitulada')
    description = db.Column(db.Text)
    poster_url  = db.Column(db.String(500))
    is_active   = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=99)

class Showtime(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    movie_id    = db.Column(db.Integer, db.ForeignKey('movie.id'))
    hall        = db.Column(db.String(50))
    show_time   = db.Column(db.String(10))
    format_type = db.Column(db.String(20))
    movie       = db.relationship('Movie', backref='showtimes')

class Card(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    user_session  = db.Column(db.String(100))
    card_number   = db.Column(db.String(20))
    holder_name   = db.Column(db.String(100))
    purchase_date = db.Column(db.Date)
    expiry_date   = db.Column(db.Date)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

class Ticket(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    ticket_code    = db.Column(db.String(50), unique=True)
    movie_id       = db.Column(db.Integer, db.ForeignKey('movie.id'))
    showtime_id    = db.Column(db.Integer, db.ForeignKey('showtime.id'))
    seat_type      = db.Column(db.String(20))
    payment_method = db.Column(db.String(20))
    card_id        = db.Column(db.Integer, db.ForeignKey('card.id'), nullable=True)
    price          = db.Column(db.Float)
    purchased_at   = db.Column(db.DateTime, default=datetime.utcnow)
    user_session   = db.Column(db.String(100))
    movie          = db.relationship('Movie')
    showtime       = db.relationship('Showtime')

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
    },
]

SHOWTIMES = ["2:00 PM","4:20 PM","6:40 PM","9:10 PM","9:30 PM"]
HALLS     = ["SALA 1","SALA 2","SALA 3","SALA 4","SALA 5"]
FORMATS   = ["2D","3D","IMAX"]
PRICES    = {"normal":18000,"vip":28000,"ultra":38000}

def seed_db():
    import random
    existing = {m.title: m for m in Movie.query.all()}
    for md in MOVIES_DATA:
        if md['title'] in existing:
            for k,v in md.items(): setattr(existing[md['title']], k, v)
        else:
            db.session.add(Movie(**md))
    db.session.flush()
    if Showtime.query.count() == 0:
        for movie in Movie.query.all():
            for t in random.sample(SHOWTIMES, random.randint(2,4)):
                db.session.add(Showtime(movie_id=movie.id, hall=random.choice(HALLS),
                                        show_time=t, format_type=random.choice(FORMATS)))
    db.session.commit()

# ─── ROUTES ────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
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

@app.route('/api/cards', methods=['GET'])
def get_cards():
    uid = session.get('user_id','')
    return jsonify([{'id':c.id,'card_number':'**** **** **** '+c.card_number[-4:],
        'holder_name':c.holder_name,'expiry_date':c.expiry_date.strftime('%m/%Y') if c.expiry_date else ''}
        for c in Card.query.filter_by(user_session=uid).all()])

@app.route('/api/cards', methods=['POST'])
def create_card():
    data = request.json
    uid  = session.get('user_id', str(uuid.uuid4())); session['user_id'] = uid
    try:
        card = Card(user_session=uid, card_number=data['card_number'].replace(' ',''),
            holder_name=data['holder_name'],
            purchase_date=datetime.strptime(data['purchase_date'],'%Y-%m-%d').date(),
            expiry_date=datetime.strptime(data['expiry_date'],'%Y-%m-%d').date())
        db.session.add(card); db.session.commit()
        return jsonify({'success':True,'id':card.id,'last4':card.card_number[-4:]})
    except Exception as e:
        return jsonify({'success':False,'error':str(e)}), 400

@app.route('/api/purchase', methods=['POST'])
def purchase_ticket():
    data = request.json
    uid  = session.get('user_id', str(uuid.uuid4())); session['user_id'] = uid
    movie    = Movie.query.get(data['movie_id'])
    showtime = Showtime.query.get(data['showtime_id'])
    seat_type= data.get('seat_type','normal')
    payment  = data.get('payment_method','cash')
    price    = PRICES.get(seat_type,18000)
    card_id  = None; card_last4 = None
    if payment == 'card':
        card_id = data.get('card_id')
        card = Card.query.get(card_id)
        if not card: return jsonify({'success':False,'error':'Tarjeta no encontrada'}), 400
        card_last4 = card.card_number[-4:]
    code = 'CX-'+str(uuid.uuid4())[:8].upper()
    db.session.add(Ticket(ticket_code=code,movie_id=movie.id,showtime_id=showtime.id,
        seat_type=seat_type,payment_method=payment,card_id=card_id,price=price,user_session=uid))
    db.session.commit()
    msg  = f"✅ Tiquete comprado para <strong>{movie.title}</strong><br>"
    msg += f"🎬 {showtime.show_time} – {showtime.hall} ({showtime.format_type})<br>"
    msg += f"💺 {seat_type.upper()} | 💰 ${price:,.0f} COP | 🎟️ <strong>{code}</strong><br>"
    if payment=='card':
        msg += f"💳 Tarjeta terminada en <strong>****{card_last4}</strong> utilizada para comprar el tiquete de <strong>{movie.title}</strong>."
    else:
        msg += "💵 Pago en efectivo registrado."
    return jsonify({'success':True,'message':msg,'ticket_code':code})

@app.route('/api/my-tickets')
def my_tickets():
    uid = session.get('user_id','')
    return jsonify([{'ticket_code':t.ticket_code,'movie':t.movie.title if t.movie else '',
        'showtime':t.showtime.show_time if t.showtime else '','hall':t.showtime.hall if t.showtime else '',
        'seat_type':t.seat_type,'payment_method':t.payment_method,'price':t.price,
        'purchased_at':t.purchased_at.strftime('%d/%m/%Y %H:%M')}
        for t in Ticket.query.filter_by(user_session=uid).order_by(Ticket.purchased_at.desc()).all()])



# crear tablas y seed siempre (Render / Gunicorn)
with app.app_context():
    db.create_all()
    seed_db()

if __name__ == '__main__':
    with app.app_context():
        db.create_all(); seed_db()
    app.run(debug=True, port=5000)
