from patterns import DatabaseConfig, UserFactory, VideoFactory
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
    duration = db.Column(db.Integer, default=0)
    views = db.Column(db.Integer, default=0)
    is_premium = db.Column(db.Boolean, default=False)
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
    user = get_current_user()
    category = request.args.get('category', '')
    search = request.args.get('search', '')
    query = Video.query
    if category:
        query = query.filter_by(category=category)
    if search:
        query = query.filter(Video.title.ilike(f'%{search}%'))
    videos = query.order_by(Video.created_at.desc()).all()
    categories = db.session.query(Video.category).distinct().all()
    categories = [c[0] for c in categories]
    return render_template('browse.html', user=user, videos=videos, categories=categories,
                           current_category=category, search=search)

@app.route('/watch/<int:video_id>')
@login_required
def watch(video_id):
    user = get_current_user()
    video = Video.query.get_or_404(video_id)
    if video.is_premium and user.subscription == 'free':
        return render_template('upgrade.html', user=user, video=video)

    video.views += 1

    history = WatchHistory.query.filter_by(user_id=user.id, video_id=video_id).first()
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

    recommended = Video.query\
        .filter(Video.category == video.category, Video.id != video_id)\
        .order_by(Video.views.desc()).limit(6).all()

    return render_template('watch.html', user=user, video=video, recommended=recommended)

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
    data = request.get_json()
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')

    if not username or not email or not password:
        return jsonify({'error': 'Todos los campos son requeridos'}), 400
    if len(password) < 6:
        return jsonify({'error': 'La contraseña debe tener al menos 6 caracteres'}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'El nombre de usuario ya existe'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'El email ya está registrado'}), 400

    user = UserFactory.create(username=username, email=email, password=password)  # ← FACTORY
    db.session.add(user)
    db.session.commit()
    session['user_id'] = user.id
    return jsonify({'success': True, 'redirect': '/'})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Credenciales incorrectas'}), 401
    session['user_id'] = user.id
    return jsonify({'success': True, 'redirect': '/'})

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

    if not title or not category:
        return jsonify({'error': 'Título y categoría son requeridos'}), 400

    video = VideoFactory.create(  # ← FACTORY
        title=title,
        category=category,
        uploader_id=user.id,
        description=description,
        is_premium=is_premium
    )

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

    db.session.add(video)
    db.session.commit()
    return jsonify({'success': True, 'video_id': video.id})

@app.route('/api/video/<int:video_id>', methods=['DELETE'])
@login_required
def delete_video(video_id):
    user = get_current_user()
    video = Video.query.get_or_404(video_id)
    if video.uploader_id != user.id:
        return jsonify({'error': 'No autorizado'}), 403

    for fname in [video.filename_480p, video.filename_720p, video.thumbnail]:
        if fname:
            path = os.path.join(app.config['UPLOAD_FOLDER'], fname)
            if os.path.exists(path):
                os.remove(path)

    WatchHistory.query.filter_by(video_id=video_id).delete()
    db.session.delete(video)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/video/<int:video_id>', methods=['PUT'])
@login_required
def edit_video(video_id):
    user = get_current_user()
    video = Video.query.get_or_404(video_id)
    if video.uploader_id != user.id:
        return jsonify({'error': 'No autorizado'}), 403
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
    return jsonify({'success': True})

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

@app.route('/api/recommendations')
@login_required
def recommendations():
    user = get_current_user()
    fav_cats = user.get_favorite_categories()

    cat_videos = []
    if fav_cats:
        cat_videos = Video.query.filter(Video.category.in_(fav_cats))\
            .order_by(Video.views.desc()).limit(6).all()

    popular = Video.query.order_by(Video.views.desc()).limit(6).all()
    seen_ids = {v.id for v in cat_videos}
    combined = cat_videos + [v for v in popular if v.id not in seen_ids]

    return jsonify([{
        'id': v.id, 'title': v.title, 'category': v.category,
        'views': v.views, 'is_premium': v.is_premium, 'thumbnail': v.thumbnail
    } for v in combined[:12]])

@app.route('/api/upgrade', methods=['POST'])
@login_required
def upgrade():
    user = get_current_user()
    data = request.get_json()
    plan = data.get('plan', 'premium')
    user.subscription = plan
    db.session.commit()
    return jsonify({'success': True, 'subscription': user.subscription})

@app.route('/api/profile', methods=['PUT'])
@login_required
def update_profile():
    user = get_current_user()
    data = request.get_json()
    if 'username' in data:
        existing = User.query.filter_by(username=data['username']).first()
        if existing and existing.id != user.id:
            return jsonify({'error': 'Username taken'}), 400
        user.username = data['username']
    if 'password' in data and data['password']:
        user.set_password(data['password'])
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/seed')
def seed():
    if User.query.count() > 0:
        return jsonify({'message': 'Already seeded'})
    admin = UserFactory.create(username='admin', email='admin@streamvault.com', password='admin123', subscription='admin')  # ← FACTORY
    demo = UserFactory.create(username='demo', email='demo@streamvault.com', password='demo123', subscription='premium')    # ← FACTORY
    db.session.add(admin)
    db.session.add(demo)
    db.session.commit()
    return jsonify({'message': 'Seeded! admin@streamvault.com / admin123 | demo@streamvault.com / demo123'})

# ─── INIT ─────────────────────────────────────────────────────────────────────

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
