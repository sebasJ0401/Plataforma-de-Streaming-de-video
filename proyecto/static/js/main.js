// ─── TOAST NOTIFICATIONS ─────────────────────────────
function showToast(message, type = 'success') {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('show'));
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 400);
    }, 3500);
}

// ─── API HELPER ──────────────────────────────────────
async function apiFetch(url, method = 'GET', body = null) {
    const opts = {
        method,
        headers: { 'Content-Type': 'application/json' },
    };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(url, opts);
    return res.json();
}

// ─── AUTH FORMS ───────────────────────────────────────
function initAuthForm() {
    const form = document.getElementById('auth-form');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = form.querySelector('.submit-btn');
        const errEl = form.querySelector('.error-msg');
        const mode = form.dataset.mode;

        btn.disabled = true;
        btn.textContent = 'Procesando...';
        errEl.style.display = 'none';

        const payload = {};
        if (mode === 'register') {
            payload.username = form.username.value;
        }
        payload.email = form.email.value;
        payload.password = form.password.value;

        try {
            const data = await apiFetch(`/api/${mode}`, 'POST', payload);
            if (data.error) {
                errEl.textContent = data.error;
                errEl.style.display = 'block';
                btn.disabled = false;
                btn.textContent = mode === 'login' ? 'Ingresar' : 'Crear cuenta';
            } else {
                showToast('¡Bienvenido!');
                window.location.href = data.redirect || '/';
            }
        } catch {
            errEl.textContent = 'Error de conexión. Intenta de nuevo.';
            errEl.style.display = 'block';
            btn.disabled = false;
            btn.textContent = mode === 'login' ? 'Ingresar' : 'Crear cuenta';
        }
    });
}

// ─── VIDEO PLAYER ─────────────────────────────────────
function initPlayer() {
    const video = document.getElementById('main-player');
    if (!video) return;

    const videoId = video.dataset.videoId;
    const has480 = video.dataset.has480 === 'true';
    const has720 = video.dataset.has720 === 'true';

    let currentQuality = has720 ? '720p' : '480p';

    function switchQuality(q) {
        if (!video.dataset[`has${q.replace('p', '')}p`] === 'true' && q !== currentQuality) {
            showToast(`Calidad ${q} no disponible`, 'error');
            return;
        }
        const currentTime = video.currentTime;
        const playing = !video.paused;

        video.src = `/api/stream/${videoId}/${q}`;
        video.load();
        video.currentTime = currentTime;
        if (playing) video.play();

        currentQuality = q;
        document.querySelectorAll('.quality-btn').forEach(b => {
            b.classList.toggle('active', b.dataset.quality === q);
        });
    }

    document.querySelectorAll('.quality-btn').forEach(btn => {
        btn.addEventListener('click', () => switchQuality(btn.dataset.quality));
    });

    // Set initial source
    video.src = `/api/stream/${videoId}/${currentQuality}`;

    // Right-click protection (DRM-lite)
    video.addEventListener('contextmenu', e => e.preventDefault());

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        if (e.code === 'Space') { e.preventDefault(); video.paused ? video.play() : video.pause(); }
        if (e.code === 'ArrowRight') { e.preventDefault(); video.currentTime += 10; }
        if (e.code === 'ArrowLeft') { e.preventDefault(); video.currentTime -= 10; }
        if (e.code === 'ArrowUp') { e.preventDefault(); video.volume = Math.min(1, video.volume + 0.1); }
        if (e.code === 'ArrowDown') { e.preventDefault(); video.volume = Math.max(0, video.volume - 0.1); }
        if (e.code === 'KeyF') {
            if (!document.fullscreenElement) video.requestFullscreen();
            else document.exitFullscreen();
        }
    });
}

// ─── UPLOAD ───────────────────────────────────────────
function initUpload() {
    const form = document.getElementById('upload-form');
    if (!form) return;

    // Drag and drop areas
    document.querySelectorAll('.upload-area').forEach(area => {
        area.addEventListener('dragover', (e) => {
            e.preventDefault();
            area.classList.add('dragover');
        });
        area.addEventListener('dragleave', () => area.classList.remove('dragover'));
        area.addEventListener('drop', (e) => {
            e.preventDefault();
            area.classList.remove('dragover');
            const file = e.dataTransfer.files[0];
            if (file) {
                const input = area.querySelector('input[type="file"]') || document.querySelector(`#${area.dataset.input}`);
                if (input) {
                    const dt = new DataTransfer();
                    dt.items.add(file);
                    input.files = dt.files;
                    area.querySelector('.upload-text').innerHTML = `<strong>${file.name}</strong> seleccionado`;
                }
            }
        });
    });

    // File input label update
    document.querySelectorAll('input[type="file"]').forEach(input => {
        input.addEventListener('change', () => {
            const area = input.closest('.upload-area');
            if (area && input.files[0]) {
                const txt = area.querySelector('.upload-text');
                if (txt) txt.innerHTML = `<strong>${input.files[0].name}</strong> seleccionado`;
            }
        });
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = form.querySelector('.submit-btn');
        const errEl = form.querySelector('.error-msg');
        const succEl = form.querySelector('.success-msg');
        errEl.style.display = 'none';
        succEl.style.display = 'none';

        const formData = new FormData(form);
        btn.disabled = true;
        btn.textContent = 'Subiendo...';

        try {
            const res = await fetch('/api/upload', { method: 'POST', body: formData });
            const data = await res.json();
            if (data.error) {
                errEl.textContent = data.error;
                errEl.style.display = 'block';
                btn.disabled = false;
                btn.textContent = 'Subir Video';
            } else {
                succEl.textContent = '¡Video subido exitosamente!';
                succEl.style.display = 'block';
                showToast('Video subido con éxito');
                setTimeout(() => window.location.href = `/watch/${data.video_id}`, 1500);
            }
        } catch {
            errEl.textContent = 'Error al subir. Intenta de nuevo.';
            errEl.style.display = 'block';
            btn.disabled = false;
            btn.textContent = 'Subir Video';
        }
    });
}

// ─── DASHBOARD ACTIONS ────────────────────────────────
function initDashboard() {
    // Delete video
    document.querySelectorAll('.delete-video-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const videoId = btn.dataset.id;
            if (!confirm('¿Eliminar este video permanentemente?')) return;
            const data = await apiFetch(`/api/video/${videoId}`, 'DELETE');
            if (data.success) {
                btn.closest('tr').remove();
                showToast('Video eliminado');
            } else {
                showToast('Error al eliminar', 'error');
            }
        });
    });

    // Edit video inline
    document.querySelectorAll('.edit-video-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const row = btn.closest('tr');
            const videoId = btn.dataset.id;
            const titleCell = row.querySelector('.title-cell');
            const currentTitle = titleCell.textContent;
            
            const input = document.createElement('input');
            input.type = 'text';
            input.value = currentTitle;
            input.className = 'form-input';
            input.style.padding = '6px 10px';
            titleCell.textContent = '';
            titleCell.appendChild(input);
            input.focus();
            
            const save = async () => {
                const newTitle = input.value.trim();
                if (!newTitle) { titleCell.textContent = currentTitle; return; }
                const data = await apiFetch(`/api/video/${videoId}`, 'PUT', { title: newTitle });
                if (data.success) {
                    titleCell.textContent = newTitle;
                    showToast('Título actualizado');
                } else {
                    titleCell.textContent = currentTitle;
                    showToast('Error al actualizar', 'error');
                }
            };

            input.addEventListener('blur', save);
            input.addEventListener('keydown', (e) => { if (e.key === 'Enter') save(); });
        });
    });
}

// ─── UPGRADE ─────────────────────────────────────────
function initUpgrade() {
    document.querySelectorAll('.upgrade-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const plan = btn.dataset.plan;
            btn.disabled = true;
            btn.textContent = 'Procesando...';
            const data = await apiFetch('/api/upgrade', 'POST', { plan });
            if (data.success) {
                showToast(`¡Plan ${plan} activado!`);
                setTimeout(() => window.location.href = '/', 1500);
            } else {
                showToast('Error al actualizar plan', 'error');
                btn.disabled = false;
                btn.textContent = 'Seleccionar Plan';
            }
        });
    });
}

// ─── PROFILE ─────────────────────────────────────────
function initProfile() {
    const form = document.getElementById('profile-form');
    if (!form) return;
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const data = await apiFetch('/api/profile', 'PUT', {
            username: form.username.value,
            password: form.password.value
        });
        if (data.success) showToast('Perfil actualizado');
        else showToast(data.error || 'Error', 'error');
    });
}

// ─── INIT ALL ─────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initAuthForm();
    initPlayer();
    initUpload();
    initDashboard();
    initUpgrade();
    initProfile();
});
