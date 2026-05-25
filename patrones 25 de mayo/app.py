from patterns import (DatabaseConfig, UserFactory, VideoFactory,
                      get_subscription_factory, APIResponseBuilder,
                      BaseVideoQuery, CategoryFilterDecorator,
                      SearchFilterDecorator, PremiumFilterDecorator,
                      PopularFilterDecorator,
                      UserRegistrationFacade,
                      ProfileCommandHistory, ChangeUsernameCommand,
                      ChangePasswordCommand,
                      RecommendationContext, get_recommendation_strategy,
                      create_achievement_system,
                      ParentalControl,
                      StatsFacade,
                      download_proxy)

# ── Observer — sistema de logros (instancia global) ───────────────────────────
achievement_system = create_achievement_system()

# ── State — control parental por usuario (dict user_id → ParentalControl) ────
parental_controls: dict = {}

# ── Proxy — descarga temporal (instancia global desde patterns.py) ────────────
# download_proxy ya viene importado directamente desde patterns.py

# ── Facade — estadísticas: se instancia por petición pasando db y user ────────
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, Response, abort
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from functools import wraps
import os, uuid, json
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'streamvault-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = DatabaseConfig.get_uri()  # ← SINGLETON
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
ALLOWED_EXTENSIONS = {'mp4', 'webm', 'mkv', 'avi', 'mov'}

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# ─── MODELS ──────────────────────────────────────────────────────────────────

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    subscription = db.Column(db.String(20), default='free')
    avatar = db.Column(db.String(200), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    favorite_categories = db.Column(db.Text, default='[]')
    watch_history = db.relationship('WatchHistory', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def get_favorite_categories(self):
        try:
            return json.loads(self.favorite_categories)
        except:
            return []


class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    category = db.Column(db.String(50), nullable=False)
    filename_480p = db.Column(db.String(200), default='')
    filename_720p = db.Column(db.String(200), default='')
    thumbnail = db.Column(db.String(200), default='')
    subtitle_file = db.Column(db.String(200), default='')  # ← Decorator subtítulos
    duration = db.Column(db.Integer, default=0)
    views = db.Column(db.Integer, default=0)
    is_premium = db.Column(db.Boolean, default=False)
    is_adult_content = db.Column(db.Boolean, default=False)
    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    watch_histories = db.relationship('WatchHistory', backref='video', lazy=True)


class WatchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'), nullable=False)
    watched_at = db.Column(db.DateTime, default=datetime.utcnow)
    progress = db.Column(db.Integer, default=0)


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        user = User.query.get(session['user_id'])
        if not user or user.subscription != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

# ─── PAGE ROUTES ─────────────────────────────────────────────────────────────

@app.route('/')
def index():
    user = get_current_user()
    featured = Video.query.order_by(Video.views.desc()).limit(6).all()
    categories = db.session.query(Video.category).distinct().all()
    categories = [c[0] for c in categories]
    return render_template('index.html', user=user, featured=featured, categories=categories)

@app.route('/login')
def login_page():
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('auth.html', mode='login')

@app.route('/register')
def register_page():
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('auth.html', mode='register')

@app.route('/browse')
def browse():
    user     = get_current_user()
    category = request.args.get('category', '')
    search   = request.args.get('search', '')
    popular  = request.args.get('popular', '')

    # ── Decorator ─────────────────────────────────────────────────────────────
    # Se inyecta Video para evitar problemas de contexto con Flask-SQLAlchemy.
    # Se parte de la consulta base y se encadenan decoradores según
    # los filtros activos. Cada decorador agrega su condición sin
    # modificar los anteriores.
    query = BaseVideoQuery(Video)

    if category:
        query = CategoryFilterDecorator(query, category)
    if search:
        query = SearchFilterDecorator(query, search)
    if user:
        query = PremiumFilterDecorator(query, user.subscription)
    if popular:
        query = PopularFilterDecorator(query)

    videos = query.execute()
    # ─────────────────────────────────────────────────────────────────────────

    categories = db.session.query(Video.category).distinct().all()
    categories = [c[0] for c in categories]
    return render_template('browse.html', user=user, videos=videos,
                           categories=categories,
                           current_category=category, search=search)

@app.route('/watch/<int:video_id>')
@login_required
def watch(video_id):
    user = get_current_user()
    video = Video.query.get_or_404(video_id)

    # ── Abstract Factory ──────────────────────────────────────────────────────
    factory = get_subscription_factory(user.subscription)
    player  = factory.create_player()
    access  = factory.create_access()
    # ─────────────────────────────────────────────────────────────────────────

    if video.is_premium and not access.can_watch_premium():
        return render_template('upgrade.html', user=user, video=video)

    # ── State — control parental ───────────────────────────────────────────────
    pc = parental_controls.get(user.id)
    if pc and pc.is_active() and not pc.can_watch(video):
        return render_template('parental_block.html', user=user,
                               label=pc.get_label())
    # ─────────────────────────────────────────────────────────────────────────

    video.views += 1

    history = WatchHistory.query.filter_by(user_id=user.id,
                                           video_id=video_id).first()
    if not history:
        history = WatchHistory(user_id=user.id, video_id=video_id)
        db.session.add(history)
    else:
        history.watched_at = datetime.utcnow()

    cats = user.get_favorite_categories()
    if video.category not in cats:
        cats.append(video.category)
        user.favorite_categories = json.dumps(cats[-5:])

    db.session.commit()

    # ── Observer ──────────────────────────────────────────────────────────────
    watch_count  = WatchHistory.query.filter_by(user_id=user.id).count()
    achievements = achievement_system.notify('video_watched', user,
                                             {'watch_count': watch_count})
    # ─────────────────────────────────────────────────────────────────────────

    recommended = Video.query\
        .filter(Video.category == video.category, Video.id != video_id)\
        .order_by(Video.views.desc()).limit(6).all()

    # ── Adapter ───────────────────────────────────────────────────────────────
    # El Adapter de autenticación opera en /api/login.
    # Esta ruta solo usa Abstract Factory para calidades y acceso.
    # ─────────────────────────────────────────────────────────────────────────

    return render_template('watch.html',
        user=user,
        video=video,
        recommended=recommended,
        available_qualities=player.get_available_qualities(),
        default_quality=player.get_default_quality(),
        access_label=access.get_access_label(),
        achievements=achievements,
        parental_label=pc.get_label() if pc else None
    )

@app.route('/profile')
@login_required
def profile():
    user = get_current_user()
    history = WatchHistory.query.filter_by(user_id=user.id)\
        .order_by(WatchHistory.watched_at.desc()).limit(10).all()
    return render_template('profile.html', user=user, history=history)

@app.route('/upload')
@login_required
def upload_page():
    user = get_current_user()
    categories = ['Películas', 'Series', 'Documentales', 'Deportes', 'Música', 'Tecnología', 'Educación', 'Entretenimiento']
    return render_template('upload.html', user=user, categories=categories)

@app.route('/dashboard')
@login_required
def dashboard():
    user = get_current_user()
    my_videos = Video.query.filter_by(uploader_id=user.id).all()
    return render_template('dashboard.html', user=user, videos=my_videos)

@app.route('/pricing')
def pricing():
    user = get_current_user()
    return render_template('pricing.html', user=user)

# ─── API ROUTES ───────────────────────────────────────────────────────────────

@app.route('/api/register', methods=['POST'])
def register():
    data     = request.get_json()
    username = data.get('username', '').strip()
    email    = data.get('email', '').strip()
    password = data.get('password', '')

    # ── Facade ────────────────────────────────────────────────────────────────
    # Un solo método reemplaza: validación, Factory, BD y sesión.
    # Se inyecta User para que la Facade pueda consultar la BD
    # dentro del contexto correcto de Flask.
    facade = UserRegistrationFacade(db, session, User)
    result = facade.register(username=username, email=email, password=password)
    # ─────────────────────────────────────────────────────────────────────────

    if not result.success:
        return jsonify(APIResponseBuilder().set_error(result.error).build()), 400

    # ── Observer ──────────────────────────────────────────────────────────────
    achievements = achievement_system.notify('user_registered', result.user)
    # ─────────────────────────────────────────────────────────────────────────

    response = (APIResponseBuilder()
                .set_success(True)
                .set_redirect('/')
                .build())
    if achievements:
        response['achievements'] = achievements
    return jsonify(response)  # ← BUILDER

@app.route('/api/login', methods=['POST'])
def login():
    data     = request.get_json()
    email    = data.get('email', '').strip()
    password = data.get('password', '')

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify(APIResponseBuilder().set_error('Credenciales incorrectas').build()), 401

    session['user_id'] = user.id

    # ── Builder ───────────────────────────────────────────────────────────────
    response = (APIResponseBuilder()
                .set_success(True)
                .set_redirect('/')
                .build())
    return jsonify(response)  # ← BUILDER

@app.route('/api/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/api/upload', methods=['POST'])
@login_required
def upload_video():
    user = get_current_user()
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    category = request.form.get('category', '').strip()
    is_premium = request.form.get('is_premium') == 'true'
    is_adult_content = request.form.get('is_adult_content') == 'true'

    if not title or not category:
        return jsonify(APIResponseBuilder().set_error('Título y categoría son requeridos').build()), 400

    video = VideoFactory.create(
        title=title,
        category=category,
        uploader_id=user.id,
        description=description,
        is_premium=is_premium
    )
    video.is_adult_content = is_adult_content

    if 'video_480p' in request.files:
        f = request.files['video_480p']
        if f and allowed_file(f.filename):
            ext = f.filename.rsplit('.', 1)[1].lower()
            filename = f"{uuid.uuid4().hex}_480p.{ext}"
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            video.filename_480p = filename

    if 'video_720p' in request.files:
        f = request.files['video_720p']
        if f and allowed_file(f.filename):
            ext = f.filename.rsplit('.', 1)[1].lower()
            filename = f"{uuid.uuid4().hex}_720p.{ext}"
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            video.filename_720p = filename

    if 'thumbnail' in request.files:
        f = request.files['thumbnail']
        if f and f.filename:
            ext = f.filename.rsplit('.', 1)[1].lower()
            filename = f"{uuid.uuid4().hex}_thumb.{ext}"
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            video.thumbnail = filename

    # ── Decorator — subtítulos ────────────────────────────────────────────────
    # El archivo de subtítulos es una capa adicional sobre el video base.
    # Si se sube un archivo .vtt el reproductor lo muestra automáticamente.
    if 'subtitle' in request.files:
        f = request.files['subtitle']
        if f and f.filename and f.filename.endswith('.vtt'):
            filename = f"{uuid.uuid4().hex}_sub.vtt"
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            video.subtitle_file = filename
    # ─────────────────────────────────────────────────────────────────────────

    db.session.add(video)
    db.session.commit()

    # ── Observer ──────────────────────────────────────────────────────────────
    video_count  = Video.query.filter_by(uploader_id=user.id).count()
    achievements = achievement_system.notify('video_uploaded', user,
                                             {'video_count': video_count})
    # ─────────────────────────────────────────────────────────────────────────

    # ── Builder ───────────────────────────────────────────────────────────────
    response = (APIResponseBuilder()
                .set_success(True)
                .set_video_id(video.id)
                .build())
    if achievements:
        response['achievements'] = achievements
    return jsonify(response)  # ← BUILDER

@app.route('/api/video/<int:video_id>', methods=['DELETE'])
@login_required
def delete_video(video_id):
    user = get_current_user()
    video = Video.query.get_or_404(video_id)
    if video.uploader_id != user.id:
        return jsonify(APIResponseBuilder().set_error('No autorizado').build()), 403

    for fname in [video.filename_480p, video.filename_720p, video.thumbnail]:
        if fname:
            path = os.path.join(app.config['UPLOAD_FOLDER'], fname)
            if os.path.exists(path):
                os.remove(path)

    WatchHistory.query.filter_by(video_id=video_id).delete()
    db.session.delete(video)
    db.session.commit()

    # ── Builder ───────────────────────────────────────────────────────────────
    return jsonify(APIResponseBuilder().set_success(True).build())  # ← BUILDER

@app.route('/api/video/<int:video_id>', methods=['PUT'])
@login_required
def edit_video(video_id):
    user = get_current_user()
    video = Video.query.get_or_404(video_id)
    if video.uploader_id != user.id:
        return jsonify(APIResponseBuilder().set_error('No autorizado').build()), 403
    data = request.get_json()
    if 'title' in data:
        video.title = data['title']
    if 'description' in data:
        video.description = data['description']
    if 'category' in data:
        video.category = data['category']
    if 'is_premium' in data:
        video.is_premium = data['is_premium']
    db.session.commit()

    # ── Builder ───────────────────────────────────────────────────────────────
    return jsonify(APIResponseBuilder().set_success(True).build())  # ← BUILDER

@app.route('/api/stream/<int:video_id>/<quality>')
@login_required
def stream(video_id, quality):
    user = get_current_user()
    video = Video.query.get_or_404(video_id)

    if video.is_premium and user.subscription == 'free':
        abort(403)

    if quality == '720p':
        filename = video.filename_720p or video.filename_480p
    else:
        filename = video.filename_480p or video.filename_720p

    if not filename:
        abort(404)

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        abort(404)

    def generate(path):
        with open(path, 'rb') as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                yield chunk

    range_header = request.headers.get('Range', None)
    if range_header:
        file_size = os.path.getsize(filepath)
        byte_start = 0
        byte_end = file_size - 1
        parts = range_header.replace('bytes=', '').split('-')
        if parts[0]:
            byte_start = int(parts[0])
        if parts[1]:
            byte_end = int(parts[1])
        length = byte_end - byte_start + 1
        with open(filepath, 'rb') as f:
            f.seek(byte_start)
            data = f.read(length)
        rv = Response(data, 206, mimetype='video/mp4', direct_passthrough=True)
        rv.headers.add('Content-Range', f'bytes {byte_start}-{byte_end}/{file_size}')
        rv.headers.add('Accept-Ranges', 'bytes')
        rv.headers.add('Content-Length', str(length))
        rv.headers.add('Cache-Control', 'no-store')
        rv.headers.add('Content-Disposition', 'inline')
        return rv

    file_size = os.path.getsize(filepath)
    response = Response(generate(filepath), mimetype='video/mp4')
    response.headers.add('Content-Length', str(file_size))
    response.headers.add('Accept-Ranges', 'bytes')
    response.headers.add('Cache-Control', 'no-store')
    response.headers.add('Content-Disposition', 'inline')
    return response

@app.route('/api/upgrade', methods=['POST'])
@login_required
def upgrade():
    user = get_current_user()
    data = request.get_json()
    plan = data.get('plan', 'premium')
    user.subscription = plan
    db.session.commit()

    # ── Observer ──────────────────────────────────────────────────────────────
    achievements = achievement_system.notify('plan_upgraded', user,
                                             {'plan': plan})
    # ─────────────────────────────────────────────────────────────────────────

    # ── Builder ───────────────────────────────────────────────────────────────
    response = (APIResponseBuilder()
                .set_success(True)
                .set_subscription(user.subscription)
                .build())
    if achievements:
        response['achievements'] = achievements
    return jsonify(response)  # ← BUILDER


# Historial de comandos por usuario (Command pattern)
profile_histories: dict = {}


@app.route('/api/profile', methods=['PUT'])
@login_required
def update_profile():
    user = get_current_user()
    data = request.get_json()

    # ── Command ───────────────────────────────────────────────────────────────
    # Cada cambio de perfil es un Command que guarda el estado anterior
    # y puede deshacerse. El historial permite revertir el último cambio.
    history = profile_histories.setdefault(user.id, ProfileCommandHistory())

    if 'username' in data and data['username']:
        existing = User.query.filter_by(username=data['username']).first()
        if existing and existing.id != user.id:
            return jsonify(
                APIResponseBuilder().set_error('Username taken').build()), 400
        cmd = ChangeUsernameCommand(user, data['username'], db)
        history.execute(cmd)

    if 'password' in data and data['password']:
        cmd = ChangePasswordCommand(user, data['password'], db)
        history.execute(cmd)
    # ─────────────────────────────────────────────────────────────────────────

    return jsonify(APIResponseBuilder().set_success(True).build())  # ← BUILDER


@app.route('/api/profile/undo', methods=['POST'])
@login_required
def undo_profile():
    """Deshace el último cambio de perfil usando el patrón Command."""
    user    = get_current_user()
    history = profile_histories.get(user.id)

    if not history or not history.has_history():
        return jsonify(
            APIResponseBuilder().set_error('No hay cambios para deshacer')
            .build()), 400

    # ── Command — deshacer ────────────────────────────────────────────────────
    message = history.undo_last()
    # ─────────────────────────────────────────────────────────────────────────

    response = (APIResponseBuilder()
                .set_success(True)
                .set_message(message)
                .build())
    return jsonify(response)


@app.route('/api/recommendations')
@login_required
def recommendations():
    user = get_current_user()
    mode = request.args.get('mode', 'popular')

    # ── Strategy ──────────────────────────────────────────────────────────────
    # Selecciona el algoritmo de recomendación según el parámetro mode.
    # popular   → videos más vistos
    # category  → categorías favoritas del usuario
    # recent    → videos más recientes
    strategy = get_recommendation_strategy(mode)
    context  = RecommendationContext(strategy)
    videos   = context.recommend(user, Video, limit=12)
    # ─────────────────────────────────────────────────────────────────────────

    videos_data = [{
        'id': v.id, 'title': v.title, 'category': v.category,
        'views': v.views, 'is_premium': v.is_premium,
        'thumbnail': v.thumbnail
    } for v in videos]

    response = (APIResponseBuilder()
                .set_success(True)
                .set_videos(videos_data)
                .set_message(f'Estrategia: {mode}')
                .build())
    return jsonify(response)


@app.route('/api/parental', methods=['POST'])
@login_required
def parental_control():
    """Activa o desactiva el control parental usando el patrón State."""
    user = get_current_user()
    data = request.get_json()
    pin  = data.get('pin', '')

    # ── State ─────────────────────────────────────────────────────────────────
    # Obtiene o crea el control parental del usuario.
    # El estado actual decide qué hace toggle() —
    # si está inactivo activa con PIN, si está activo desactiva verificando PIN.
    pc      = parental_controls.setdefault(user.id, ParentalControl())
    message = pc.toggle(pin)
    # ─────────────────────────────────────────────────────────────────────────

    response = (APIResponseBuilder()
                .set_success(True)
                .set_message(message)
                .build())
    response['parental_active'] = pc.is_active()
    response['parental_label']  = pc.get_label()
    return jsonify(response)


@app.route('/api/parental/status')
@login_required
def parental_status():
    """Devuelve el estado actual del control parental."""
    user = get_current_user()
    pc   = parental_controls.get(user.id)

    response = (APIResponseBuilder()
                .set_success(True)
                .build())
    response['parental_active'] = pc.is_active() if pc else False
    response['parental_label']  = pc.get_label() if pc else '🔓 Control parental inactivo'
    return jsonify(response)


# ── OBSERVER — logros del usuario ─────────────────────────────────────────────
@app.route('/api/achievements')
@login_required
def get_achievements():
    """Devuelve todos los logros desbloqueados por el usuario."""
    user        = get_current_user()
    video_count = Video.query.filter_by(uploader_id=user.id).count()
    watch_count = WatchHistory.query.filter_by(user_id=user.id).count()

    unlocked = []
    if True:
        unlocked.append({'icon': '🎉', 'title': 'Bienvenido', 'desc': 'Te registraste en StreamVault', 'unlocked': True})
    if video_count >= 1:
        unlocked.append({'icon': '🎬', 'title': 'Primer Video', 'desc': 'Subiste tu primer video', 'unlocked': True})
    if watch_count >= 5:
        unlocked.append({'icon': '👁️', 'title': 'Espectador Activo', 'desc': 'Viste 5 videos', 'unlocked': True})
    if user.subscription in ('premium', 'admin'):
        unlocked.append({'icon': '⭐', 'title': 'Usuario Premium', 'desc': 'Actualizaste tu plan', 'unlocked': True})

    locked = []
    if watch_count < 5:
        locked.append({'icon': '👁️', 'title': 'Espectador Activo', 'desc': f'Ve 5 videos ({watch_count}/5)', 'unlocked': False})
    if video_count < 1:
        locked.append({'icon': '🎬', 'title': 'Primer Video', 'desc': 'Sube tu primer video', 'unlocked': False})
    if user.subscription == 'free':
        locked.append({'icon': '⭐', 'title': 'Usuario Premium', 'desc': 'Actualiza tu plan', 'unlocked': False})

    response = APIResponseBuilder().set_success(True).build()
    response['unlocked'] = unlocked
    response['locked']   = locked
    return jsonify(response)


# ── FACADE — estadísticas del creador ────────────────────────────────────────
@app.route('/stats')
@login_required
def stats_page():
    """Página de estadísticas usando StatsFacade."""
    user  = get_current_user()
    facade = StatsFacade()
    data   = facade.get_stats(user, Video, WatchHistory)
    return render_template('stats.html', user=user, stats=data)


# ── PROXY — descarga temporal Premium ────────────────────────────────────────
@app.route('/api/download/<int:video_id>', methods=['POST'])
@login_required
def request_download(video_id):
    """Solicita descarga temporal de un video usando DownloadProxy."""
    user  = get_current_user()
    video = Video.query.get_or_404(video_id)

    # ── Proxy ─────────────────────────────────────────────────────────────────
    result = download_proxy.request_download(user, video)
    # ─────────────────────────────────────────────────────────────────────────

    if not result['allowed']:
        return jsonify(
            APIResponseBuilder().set_error(result['message']).build()), 403

    response = APIResponseBuilder().set_success(True).set_message(result['message']).build()
    response['url']        = result.get('url')
    response['expires_in'] = result.get('expires_in')
    return jsonify(response)


@app.route('/api/download/<int:video_id>/status')
@login_required
def download_status(video_id):
    """Devuelve el estado actual de la descarga temporal."""
    user  = get_current_user()
    video = Video.query.get_or_404(video_id)

    # ── Proxy ─────────────────────────────────────────────────────────────────
    status = download_proxy.check_status(user, video)
    # ─────────────────────────────────────────────────────────────────────────

    response = APIResponseBuilder().set_success(True).build()
    response.update(status)
    return jsonify(response)


@app.route('/api/seed')
def seed():
    if User.query.count() > 0:
        return jsonify(APIResponseBuilder().set_message('Already seeded').build())
    admin = UserFactory.create(username='admin', email='admin@streamvault.com', password='admin123', subscription='admin')
    demo  = UserFactory.create(username='demo',  email='demo@streamvault.com',  password='demo123',  subscription='premium')
    db.session.add(admin)
    db.session.add(demo)
    db.session.commit()

    # ── Builder ───────────────────────────────────────────────────────────────
    response = (APIResponseBuilder()
                .set_success(True)
                .set_message('Seeded! admin@streamvault.com / admin123 | demo@streamvault.com / demo123')
                .build())
    return jsonify(response)  # ← BUILDER





# ─── INIT ─────────────────────────────────────────────────────────────────────

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
