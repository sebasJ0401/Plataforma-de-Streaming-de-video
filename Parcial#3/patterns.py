from enum import Enum
from abc import ABC, abstractmethod


# ─── SINGLETON (Variante Enum) ────────────────────────────────────────────────
# Garantiza una única instancia de la configuración de la base de datos.
# La variante Enum es thread-safe por naturaleza en Python.

class DatabaseConfig(Enum):
    INSTANCE = "sqlite:///streamvault.db"

    @property
    def uri(self):
        return self.value

    @staticmethod
    def get_uri():
        return DatabaseConfig.INSTANCE.uri


# ─── FACTORY ──────────────────────────────────────────────────────────────────
# Centraliza la creación de objetos User y Video.
# UserFactory garantiza que toda contraseña siempre queda encriptada.
# VideoFactory centraliza los valores por defecto del video.

class UserFactory:
    @staticmethod
    def create(username: str, email: str, password: str,
               subscription: str = 'free'):
        from app import User
        user = User(username=username, email=email, subscription=subscription)
        user.set_password(password)
        return user


class VideoFactory:
    @staticmethod
    def create(title: str, category: str, uploader_id: int,
               description: str = '', is_premium: bool = False):
        from app import Video
        return Video(
            title=title,
            category=category,
            uploader_id=uploader_id,
            description=description,
            is_premium=is_premium
        )


# ─── ABSTRACT FACTORY ─────────────────────────────────────────────────────────
# Define una familia de objetos según el tipo de suscripción del usuario.
# FreeSubscription   → solo 480p, sin acceso a contenido premium.
# PremiumSubscription → 480p + 720p, acceso completo.
# Visible en el frontend: botones de calidad y pantalla de upgrade.

class VideoPlayer(ABC):
    """Define qué calidades puede reproducir el usuario."""
    @abstractmethod
    def get_available_qualities(self) -> list:
        pass

    @abstractmethod
    def get_default_quality(self) -> str:
        pass


class ContentAccess(ABC):
    """Define a qué contenido puede acceder el usuario."""
    @abstractmethod
    def can_watch_premium(self) -> bool:
        pass

    @abstractmethod
    def get_access_label(self) -> str:
        pass


class FreeVideoPlayer(VideoPlayer):
    def get_available_qualities(self) -> list:
        return ['480p']

    def get_default_quality(self) -> str:
        return '480p'


class FreeContentAccess(ContentAccess):
    def can_watch_premium(self) -> bool:
        return False

    def get_access_label(self) -> str:
        return 'Plan Gratuito'


class PremiumVideoPlayer(VideoPlayer):
    def get_available_qualities(self) -> list:
        return ['480p', '720p']

    def get_default_quality(self) -> str:
        return '720p'


class PremiumContentAccess(ContentAccess):
    def can_watch_premium(self) -> bool:
        return True

    def get_access_label(self) -> str:
        return 'Plan Premium'


class SubscriptionFactory(ABC):
    """Fábrica abstracta que define cómo crear la familia de objetos."""
    @abstractmethod
    def create_player(self) -> VideoPlayer:
        pass

    @abstractmethod
    def create_access(self) -> ContentAccess:
        pass


class FreeSubscriptionFactory(SubscriptionFactory):
    """Crea la familia de objetos para usuarios con plan gratuito."""
    def create_player(self) -> VideoPlayer:
        return FreeVideoPlayer()

    def create_access(self) -> ContentAccess:
        return FreeContentAccess()


class PremiumSubscriptionFactory(SubscriptionFactory):
    """Crea la familia de objetos para usuarios con plan premium."""
    def create_player(self) -> VideoPlayer:
        return PremiumVideoPlayer()

    def create_access(self) -> ContentAccess:
        return PremiumContentAccess()


def get_subscription_factory(subscription: str) -> SubscriptionFactory:
    """Devuelve el factory correcto según el plan del usuario."""
    if subscription in ('premium', 'admin'):
        return PremiumSubscriptionFactory()
    return FreeSubscriptionFactory()


# ─── BUILDER ──────────────────────────────────────────────────────────────────
# Construye respuestas JSON de la API de forma estructurada y encadenada.
# Cada ruta de app.py deja de armar diccionarios a mano.
# El Builder garantiza que todas las respuestas tienen el mismo formato.
# Visible en el frontend: mensajes de error, redirecciones, respuestas JSON.

class APIResponseBuilder:
    """
    Builder para construir respuestas JSON de la API.
    Permite encadenar métodos para agregar campos de forma legible.
    Cada método devuelve self para permitir el encadenamiento.
    """

    def __init__(self):
        self._response = {}

    def set_success(self, value: bool = True):
        """Indica si la operación fue exitosa."""
        self._response['success'] = value
        return self

    def set_error(self, message: str):
        """Agrega un mensaje de error y marca la respuesta como fallida."""
        self._response['success'] = False
        self._response['error'] = message
        return self

    def set_redirect(self, url: str):
        """Agrega una URL de redirección."""
        self._response['redirect'] = url
        return self

    def set_message(self, message: str):
        """Agrega un mensaje informativo."""
        self._response['message'] = message
        return self

    def set_video_id(self, video_id: int):
        """Agrega el ID del video creado."""
        self._response['video_id'] = video_id
        return self

    def set_subscription(self, subscription: str):
        """Agrega el plan de suscripción del usuario."""
        self._response['subscription'] = subscription
        return self

    def set_videos(self, videos: list):
        """Agrega una lista de videos serializados."""
        self._response['videos'] = videos
        return self

    def build(self) -> dict:
        """Retorna el diccionario final construido."""
        return self._response


# ─── DECORATOR ────────────────────────────────────────────────────────────────
# Agrega filtros opcionales a la consulta de videos en /browse
# sin modificar la consulta base ni crear combinaciones fijas.
# Visible en el frontend: resultados de búsqueda y filtros en catálogo.

class VideoQuery(ABC):
    """Interfaz base que toda consulta de videos debe implementar."""
    @abstractmethod
    def execute(self) -> list:
        pass


class BaseVideoQuery(VideoQuery):
    """
    Consulta base sin filtros.
    Devuelve todos los videos ordenados por fecha de creación.
    Recibe el modelo Video inyectado desde app.py para evitar
    problemas de contexto con Flask-SQLAlchemy.
    """
    def __init__(self, video_model):
        self._video_model = video_model

    def execute(self) -> list:
        return self._video_model.query.order_by(
            self._video_model.created_at.desc()
        ).all()


class VideoQueryDecorator(VideoQuery, ABC):
    """
    Decorator abstracto. Envuelve una VideoQuery existente
    y delega execute() añadiendo su propio filtro encima.
    """
    def __init__(self, query: VideoQuery):
        self._query = query

    @abstractmethod
    def execute(self) -> list:
        pass


class CategoryFilterDecorator(VideoQueryDecorator):
    """Decorator que filtra los videos por categoría."""
    def __init__(self, query: VideoQuery, category: str):
        super().__init__(query)
        self._category = category

    def execute(self) -> list:
        results = self._query.execute()
        if not self._category:
            return results
        return [v for v in results if v.category == self._category]


class SearchFilterDecorator(VideoQueryDecorator):
    """Decorator que filtra los videos por texto en el título."""
    def __init__(self, query: VideoQuery, search: str):
        super().__init__(query)
        self._search = search.lower()

    def execute(self) -> list:
        results = self._query.execute()
        if not self._search:
            return results
        return [v for v in results if self._search in v.title.lower()]


class PremiumFilterDecorator(VideoQueryDecorator):
    """Decorator que oculta videos premium a usuarios con plan free."""
    def __init__(self, query: VideoQuery, subscription: str):
        super().__init__(query)
        self._subscription = subscription

    def execute(self) -> list:
        results = self._query.execute()
        if self._subscription in ('premium', 'admin'):
            return results
        return [v for v in results if not v.is_premium]


class PopularFilterDecorator(VideoQueryDecorator):
    """Decorator que reordena los resultados por número de vistas."""
    def __init__(self, query: VideoQuery):
        super().__init__(query)

    def execute(self) -> list:
        results = self._query.execute()
        return sorted(results, key=lambda v: v.views, reverse=True)


# ─── FACADE ───────────────────────────────────────────────────────────────────
# Simplifica el proceso completo de registro en un solo método.
# Coordina internamente: validación, Factory, BD y sesión.
# La ruta /api/register solo interactúa con esta clase.

class RegistrationResult:
    """Resultado devuelto por la Facade al terminar el registro."""
    def __init__(self, success: bool, user=None, error: str = None):
        self.success = success
        self.user    = user
        self.error   = error


class UserRegistrationFacade:
    """
    Facade que simplifica el proceso completo de registro.
    Coordina internamente: validación, Factory, BD y sesión.
    La ruta /api/register solo interactúa con esta clase.
    """

    def __init__(self, db_session, session_store, user_model):
        self._db         = db_session
        self._session    = session_store
        self._user_model = user_model

    def register(self, username: str, email: str,
                 password: str) -> RegistrationResult:
        """
        Ejecuta el flujo completo de registro en un solo método:
        1. Valida los datos de entrada
        2. Verifica unicidad de username y email
        3. Crea el usuario con UserFactory
        4. Guarda en base de datos
        5. Inicia la sesión
        """
        # Paso 1 — Validación básica
        if not username or not email or not password:
            return RegistrationResult(False,
                                      error='Todos los campos son requeridos')
        if len(password) < 6:
            return RegistrationResult(False,
                                      error='La contraseña debe tener al menos 6 caracteres')

        # Paso 2 — Unicidad (usa el modelo inyectado desde app.py)
        if self._user_model.query.filter_by(username=username).first():
            return RegistrationResult(False,
                                      error='El nombre de usuario ya existe')
        if self._user_model.query.filter_by(email=email).first():
            return RegistrationResult(False,
                                      error='El email ya está registrado')

        # Paso 3 — Factory
        user = UserFactory.create(username=username,
                                  email=email,
                                  password=password)

        # Paso 4 — Persistencia
        self._db.session.add(user)
        self._db.session.commit()

        # Paso 5 — Sesión
        self._session['user_id'] = user.id

        return RegistrationResult(True, user=user)


# ─── COMMAND ──────────────────────────────────────────────────────────────────
# Problema: cuando el usuario edita su perfil (username o password) no hay
# forma de deshacer los cambios si se equivoca. Cada campo se sobreescribe
# directamente en la BD sin guardar el estado anterior.
#
# Solución: encapsular cada cambio de perfil como un objeto Command que
# guarda el estado anterior y sabe cómo ejecutarse y deshacerse.
# ProfileCommandHistory mantiene el historial de comandos ejecutados.

class ProfileCommand(ABC):
    """Interfaz base de todos los comandos de perfil."""
    @abstractmethod
    def execute(self) -> None:
        pass

    @abstractmethod
    def undo(self) -> None:
        pass

    @abstractmethod
    def description(self) -> str:
        pass


class ChangeUsernameCommand(ProfileCommand):
    """Comando que cambia el username del usuario guardando el anterior."""
    def __init__(self, user, new_username: str, db_session):
        self._user         = user
        self._new_username = new_username
        self._old_username = user.username
        self._db           = db_session

    def execute(self) -> None:
        self._user.username = self._new_username
        self._db.session.commit()

    def undo(self) -> None:
        self._user.username = self._old_username
        self._db.session.commit()

    def description(self) -> str:
        return f'Cambio de username: {self._old_username} → {self._new_username}'


class ChangePasswordCommand(ProfileCommand):
    """Comando que cambia la contraseña guardando el hash anterior."""
    def __init__(self, user, new_password: str, db_session):
        self._user             = user
        self._new_password     = new_password
        self._old_password_hash = user.password_hash
        self._db               = db_session

    def execute(self) -> None:
        self._user.set_password(self._new_password)
        self._db.session.commit()

    def undo(self) -> None:
        self._user.password_hash = self._old_password_hash
        self._db.session.commit()

    def description(self) -> str:
        return 'Cambio de contraseña'


class ProfileCommandHistory:
    """
    Historial de comandos ejecutados en el perfil.
    Permite deshacer el último comando ejecutado.
    """
    def __init__(self):
        self._history: list[ProfileCommand] = []

    def execute(self, command: ProfileCommand) -> None:
        command.execute()
        self._history.append(command)

    def undo_last(self) -> str:
        if not self._history:
            return 'No hay cambios para deshacer'
        command = self._history.pop()
        command.undo()
        return f'Deshecho: {command.description()}'

    def get_history(self) -> list:
        return [c.description() for c in self._history]

    def has_history(self) -> bool:
        return len(self._history) > 0


# ─── STRATEGY ─────────────────────────────────────────────────────────────────
# Problema: el sistema de recomendaciones siempre usa el mismo algoritmo.
# Se necesita poder cambiar entre distintos algoritmos (por popularidad,
# por categoría favorita, por historial reciente) sin modificar la ruta
# que devuelve las recomendaciones.
#
# Solución: cada algoritmo es una estrategia intercambiable que implementa
# la misma interfaz recommend(). La ruta solo conoce la interfaz.

class RecommendationStrategy(ABC):
    """Interfaz común para todos los algoritmos de recomendación."""
    @abstractmethod
    def recommend(self, user, video_model, limit: int = 6) -> list:
        pass


class PopularRecommendationStrategy(RecommendationStrategy):
    """Recomienda los videos más vistos de toda la plataforma."""
    def recommend(self, user, video_model, limit: int = 6) -> list:
        return (video_model.query
                .order_by(video_model.views.desc())
                .limit(limit).all())


class CategoryRecommendationStrategy(RecommendationStrategy):
    """Recomienda videos de las categorías favoritas del usuario."""
    def recommend(self, user, video_model, limit: int = 6) -> list:
        import json
        try:
            favorite_cats = json.loads(user.favorite_categories or '[]')
        except Exception:
            favorite_cats = []

        if not favorite_cats:
            return (video_model.query
                    .order_by(video_model.views.desc())
                    .limit(limit).all())

        results = []
        seen    = set()
        for cat in favorite_cats:
            videos = (video_model.query
                      .filter_by(category=cat)
                      .order_by(video_model.views.desc())
                      .limit(limit).all())
            for v in videos:
                if v.id not in seen:
                    seen.add(v.id)
                    results.append(v)
        return results[:limit]


class RecentRecommendationStrategy(RecommendationStrategy):
    """Recomienda los videos subidos más recientemente."""
    def recommend(self, user, video_model, limit: int = 6) -> list:
        return (video_model.query
                .order_by(video_model.created_at.desc())
                .limit(limit).all())


class RecommendationContext:
    """
    Contexto que usa una estrategia de recomendación.
    Permite cambiar la estrategia en tiempo de ejecución.
    """
    def __init__(self, strategy: RecommendationStrategy = None):
        self._strategy = strategy or PopularRecommendationStrategy()

    def set_strategy(self, strategy: RecommendationStrategy) -> None:
        self._strategy = strategy

    def recommend(self, user, video_model, limit: int = 6) -> list:
        return self._strategy.recommend(user, video_model, limit)


def get_recommendation_strategy(mode: str) -> RecommendationStrategy:
    """Devuelve la estrategia correcta según el modo solicitado."""
    if mode == 'category':
        return CategoryRecommendationStrategy()
    elif mode == 'recent':
        return RecentRecommendationStrategy()
    return PopularRecommendationStrategy()


# ─── OBSERVER ─────────────────────────────────────────────────────────────────
# Problema: cuando un usuario realiza acciones (registrarse, subir un video,
# ver un video), el sistema debería otorgar logros automáticamente sin que
# cada ruta tenga que saber qué logros existen.
#
# Solución: un sistema de eventos donde las rutas publican eventos y los
# observadores (logros) reaccionan automáticamente. Agregar un logro nuevo
# solo requiere crear un nuevo observador sin tocar las rutas.

class AchievementObserver(ABC):
    """Interfaz base para todos los observadores de logros."""
    @abstractmethod
    def update(self, event: str, user, context: dict) -> str | None:
        pass


class WelcomeAchievement(AchievementObserver):
    """Logro por registrarse en la plataforma."""
    def update(self, event: str, user, context: dict) -> str | None:
        if event == 'user_registered':
            return '🎉 Logro desbloqueado: ¡Bienvenido a StreamVault!'
        return None


class FirstUploadAchievement(AchievementObserver):
    """Logro por subir el primer video."""
    def update(self, event: str, user, context: dict) -> str | None:
        if event == 'video_uploaded':
            video_count = context.get('video_count', 0)
            if video_count == 1:
                return '🎬 Logro desbloqueado: ¡Primer video subido!'
        return None


class ActiveViewerAchievement(AchievementObserver):
    """Logro por ver 5 videos."""
    def update(self, event: str, user, context: dict) -> str | None:
        if event == 'video_watched':
            watch_count = context.get('watch_count', 0)
            if watch_count == 5:
                return '👁️ Logro desbloqueado: ¡Espectador activo! (5 videos vistos)'
        return None


class PremiumAchievement(AchievementObserver):
    """Logro por actualizar al plan premium."""
    def update(self, event: str, user, context: dict) -> str | None:
        if event == 'plan_upgraded':
            return '⭐ Logro desbloqueado: ¡Usuario Premium!'
        return None


class AchievementSystem:
    """
    Sistema de logros que actúa como publicador de eventos.
    Las rutas publican eventos y el sistema notifica a todos
    los observadores registrados automáticamente.
    """
    def __init__(self):
        self._observers: list[AchievementObserver] = []

    def register(self, observer: AchievementObserver) -> None:
        self._observers.append(observer)

    def notify(self, event: str, user, context: dict = {}) -> list:
        """Notifica a todos los observadores y retorna los logros obtenidos."""
        achievements = []
        for observer in self._observers:
            result = observer.update(event, user, context)
            if result:
                achievements.append(result)
        return achievements


def create_achievement_system() -> AchievementSystem:
    """Crea el sistema de logros con todos los observadores registrados."""
    system = AchievementSystem()
    system.register(WelcomeAchievement())
    system.register(FirstUploadAchievement())
    system.register(ActiveViewerAchievement())
    system.register(PremiumAchievement())
    return system


# ─── STATE ────────────────────────────────────────────────────────────────────
# Problema: cuando el control parental está activo el sistema debe comportarse
# diferente — filtrando contenido adulto, solicitando PIN para desactivarse
# y mostrando indicadores visuales. Sin State habría condicionales dispersos
# por todo el código verificando si el control parental está activo.
#
# Solución: dos estados concretos (Activo e Inactivo) que implementan la
# misma interfaz. El contexto ParentalControl delega su comportamiento al
# estado actual. Cambiar de estado es simplemente cambiar el objeto de estado.

class ParentalControlState(ABC):
    """Interfaz base para los estados del control parental."""
    @abstractmethod
    def can_watch(self, video) -> bool:
        pass

    @abstractmethod
    def get_label(self) -> str:
        pass

    @abstractmethod
    def is_active(self) -> bool:
        pass

    @abstractmethod
    def toggle(self, context, pin: str) -> str:
        pass


class ParentalControlActive(ParentalControlState):
    """
    Estado activo del control parental.
    Solo permite ver videos marcados como aptos para todas las edades.
    Requiere PIN para desactivarse.
    """
    def can_watch(self, video) -> bool:
        return not getattr(video, 'is_adult_content', False)

    def get_label(self) -> str:
        return '🔒 Control parental activo'

    def is_active(self) -> bool:
        return True

    def toggle(self, context, pin: str) -> str:
        if context.verify_pin(pin):
            context.set_state(ParentalControlInactive())
            return 'Control parental desactivado'
        return 'PIN incorrecto'


class ParentalControlInactive(ParentalControlState):
    """
    Estado inactivo del control parental.
    Permite ver todo el contenido sin restricciones de edad.
    Requiere crear un PIN para activarse.
    """
    def can_watch(self, video) -> bool:
        return True

    def get_label(self) -> str:
        return '🔓 Control parental inactivo'

    def is_active(self) -> bool:
        return False

    def toggle(self, context, pin: str) -> str:
        context.set_pin(pin)
        context.set_state(ParentalControlActive())
        return 'Control parental activado'


class ParentalControl:
    """
    Contexto del patrón State para el control parental.
    Delega su comportamiento al estado actual.
    El estado puede cambiar en tiempo de ejecución.
    """
    def __init__(self):
        self._state = ParentalControlInactive()
        self._pin   = None

    def set_state(self, state: ParentalControlState) -> None:
        self._state = state

    def set_pin(self, pin: str) -> None:
        self._pin = pin

    def verify_pin(self, pin: str) -> bool:
        return self._pin == pin

    def can_watch(self, video) -> bool:
        return self._state.can_watch(video)

    def get_label(self) -> str:
        return self._state.get_label()

    def is_active(self) -> bool:
        return self._state.is_active()

    def toggle(self, pin: str) -> str:
        return self._state.toggle(self, pin)


# ─── PROXY ────────────────────────────────────────────────────────────────────
# Problema: los usuarios Premium pueden descargar videos temporalmente,
# pero la descarga debe expirar después de 48 horas y solo estar disponible
# para usuarios con plan premium. Sin Proxy habría condicionales dispersos
# en múltiples rutas verificando permisos y tiempos de expiración.
#
# Solución: VideoDownloadProxy controla el acceso al recurso real (el archivo).
# Verifica el plan del usuario y si el permiso sigue vigente antes de
# permitir la descarga. El cliente solo habla con el Proxy.

from datetime import datetime, timedelta

class VideoDownloadService:
    """Servicio real que entrega el archivo de video para descarga."""
    def get_download_url(self, video, quality: str) -> str:
        filename = video.filename_720p if quality == '720p' else video.filename_480p
        return f'/static/uploads/{filename}' if filename else None


class VideoDownloadProxy:
    """
    Proxy que controla el acceso al VideoDownloadService.
    Verifica:
    1. Que el usuario tenga plan premium
    2. Que el permiso de descarga no haya expirado (48 horas)
    """
    EXPIRY_HOURS = 48

    def __init__(self):
        self._service = VideoDownloadService()
        self._permissions: dict = {}

    def request_download(self, user, video, quality: str = '480p') -> dict:
        """
        Solicita acceso de descarga. Solo permite si es Premium.
        Registra el tiempo de permiso y devuelve la URL o un error.
        """
        if user.subscription == 'free':
            return {'success': False,
                    'error': 'La descarga temporal es exclusiva para usuarios Premium'}

        key = f'{user.id}_{video.id}'
        now = datetime.utcnow()
        self._permissions[key] = now + timedelta(hours=self.EXPIRY_HOURS)

        url = self._service.get_download_url(video, quality)
        if not url:
            return {'success': False, 'error': 'Archivo no disponible'}

        expires_at = self._permissions[key].strftime('%d/%m/%Y %H:%M')
        return {
            'success':    True,
            'url':        url,
            'expires_at': expires_at,
            'message':    f'Descarga disponible por {self.EXPIRY_HOURS} horas'
        }

    def check_permission(self, user_id: int, video_id: int) -> bool:
        """Verifica si el permiso de descarga sigue vigente."""
        key = f'{user_id}_{video_id}'
        if key not in self._permissions:
            return False
        return datetime.utcnow() < self._permissions[key]


# ─── FACADE DE ESTADÍSTICAS ───────────────────────────────────────────────────
# Problema: el panel de estadísticas requiere múltiples consultas complejas
# a la base de datos — videos del usuario, total de vistas, video más popular,
# categorías con más contenido, historial de watchers. Hacer todo eso en la
# ruta /stats la haría larga e ilegible.
#
# Solución: StatsFacade agrupa todas esas consultas en un solo método
# get_stats(). La ruta /stats solo llama a la Facade y recibe un dict
# con todos los datos listos para renderizar.

class StatsFacade:
    """
    Facade que centraliza todas las consultas del panel de estadísticas.
    La ruta /stats solo interactúa con esta clase.
    """

    def get_stats(self, user, video_model, watch_history_model) -> dict:
        """
        Reúne todas las estadísticas del usuario en un solo método:
        1. Total de videos subidos
        2. Total de vistas acumuladas
        3. Video más popular
        4. Categoría con más videos
        5. Total de usuarios que vieron sus videos
        6. Videos ordenados por vistas para la tabla
        """
        # Paso 1 — Videos del usuario
        videos = video_model.query.filter_by(uploader_id=user.id).all()
        total_videos = len(videos)

        # Paso 2 — Total de vistas
        total_views = sum(v.views for v in videos)

        # Paso 3 — Video más popular
        top_video = max(videos, key=lambda v: v.views) if videos else None

        # Paso 4 — Categoría dominante
        from collections import Counter
        cat_counts  = Counter(v.category for v in videos)
        top_category = cat_counts.most_common(1)[0][0] if cat_counts else 'N/A'

        # Paso 5 — Watchers únicos
        video_ids = [v.id for v in videos]
        unique_watchers = 0
        if video_ids:
            unique_watchers = (watch_history_model.query
                               .filter(watch_history_model.video_id.in_(video_ids))
                               .distinct(watch_history_model.user_id)
                               .count())

        # Paso 6 — Tabla de videos por vistas
        videos_sorted = sorted(videos, key=lambda v: v.views, reverse=True)

        return {
            'total_videos':    total_videos,
            'total_views':     total_views,
            'top_video':       top_video,
            'top_category':    top_category,
            'unique_watchers': unique_watchers,
            'videos_sorted':   videos_sorted,
        }


# ─── PROXY ────────────────────────────────────────────────────────────────────
# Problema: los usuarios Premium pueden descargar videos temporalmente
# pero la descarga debe expirar después de 48 horas. Sin Proxy, cada
# ruta tendría que verificar manualmente si el permiso sigue vigente.
#
# Solución: DownloadProxy actúa como intermediario entre el usuario
# y el archivo de video. Verifica si el usuario tiene plan Premium,
# registra la fecha de descarga y controla que no hayan pasado 48h.

from datetime import datetime, timedelta

class VideoDownloader:
    """Objeto real que sirve el archivo de video para descarga."""
    def get_download_url(self, video) -> str:
        filename = video.filename_480p or video.filename_720p
        if not filename:
            return None
        return f'/static/uploads/{filename}'


class DownloadProxy:
    """
    Proxy que controla el acceso a la descarga temporal.
    Verifica plan Premium y que no hayan pasado 48 horas.
    """
    EXPIRY_HOURS = 48
    # Registro en memoria: {(user_id, video_id): datetime_de_descarga}
    _download_log: dict = {}

    def __init__(self):
        self._downloader = VideoDownloader()

    def request_download(self, user, video) -> dict:
        """
        Verifica acceso y devuelve la URL de descarga con tiempo restante.
        Retorna dict con: allowed, url, expires_in_hours, message.
        """
        # Control 1 — Solo Premium
        if user.subscription not in ('premium', 'admin'):
            return {
                'allowed': False,
                'message': 'La descarga temporal es exclusiva para usuarios Premium'
            }

        # Control 2 — Verificar si ya descargó y si expiró
        key = (user.id, video.id)
        if key in self._download_log:
            downloaded_at = self._download_log[key]
            elapsed       = datetime.utcnow() - downloaded_at
            remaining     = timedelta(hours=self.EXPIRY_HOURS) - elapsed
            if remaining.total_seconds() > 0:
                hours_left = int(remaining.total_seconds() // 3600)
                mins_left  = int((remaining.total_seconds() % 3600) // 60)
                return {
                    'allowed':        True,
                    'url':            self._downloader.get_download_url(video),
                    'expires_in':     f'{hours_left}h {mins_left}m restantes',
                    'message':        'Descarga activa'
                }

        # Control 3 — Registrar nueva descarga
        self._download_log[key] = datetime.utcnow()
        return {
            'allowed':    True,
            'url':        self._downloader.get_download_url(video),
            'expires_in': f'{self.EXPIRY_HOURS}h restantes',
            'message':    'Descarga iniciada — válida por 48 horas'
        }

    def check_status(self, user, video) -> dict:
        """Devuelve el estado actual de la descarga sin registrar una nueva."""
        if user.subscription not in ('premium', 'admin'):
            return {'allowed': False, 'active': False}

        key = (user.id, video.id)
        if key not in self._download_log:
            return {'allowed': True, 'active': False}

        downloaded_at = self._download_log[key]
        elapsed       = datetime.utcnow() - downloaded_at
        remaining     = timedelta(hours=self.EXPIRY_HOURS) - elapsed

        if remaining.total_seconds() <= 0:
            del self._download_log[key]
            return {'allowed': True, 'active': False}

        hours_left = int(remaining.total_seconds() // 3600)
        mins_left  = int((remaining.total_seconds() % 3600) // 60)
        return {
            'allowed':    True,
            'active':     True,
            'expires_in': f'{hours_left}h {mins_left}m restantes'
        }


# Instancia global del proxy (compartida entre peticiones)
download_proxy = DownloadProxy()


# ─── TEMPLATE METHOD ──────────────────────────────────────────────────────────
# Problema: la plataforma tiene distintos tipos de eventos especiales de
# visualización — Maratón, Estreno y Evento en Vivo. Cada uno sigue el
# mismo esquema general: verificar elegibilidad, preparar el entorno,
# ejecutar la visualización y finalizar el evento. Pero cada tipo
# implementa esos pasos de forma diferente.
#
# Solución: ViewingEvent define el esquema general con un método template
# start() que llama los pasos en orden. Cada subclase sobreescribe solo
# los pasos que le corresponden sin cambiar el orden del proceso.

class ViewingEvent(ABC):
    """
    Clase base abstracta — Template Method.
    Define el esquema fijo del proceso de un evento de visualización.
    Las subclases sobreescriben los pasos hook sin cambiar el orden.
    """

    def start(self, user, video) -> dict:
        """
        Método template: define el orden fijo de los pasos.
        No se puede sobreescribir — el orden siempre es el mismo.
        """
        result = {}

        # Paso 1 — Verificar elegibilidad (cada evento define sus reglas)
        check = self.check_eligibility(user, video)
        if not check['allowed']:
            return {'allowed': False, 'reason': check['reason']}

        # Paso 2 — Preparar el entorno del evento
        context = self.prepare_context(user, video)

        # Paso 3 — Generar el mensaje de bienvenida al evento
        result['welcome_message'] = self.get_welcome_message(user, video)

        # Paso 4 — Aplicar beneficios especiales del evento
        result['benefits'] = self.apply_benefits(user, video)

        # Paso 5 — Registrar participación
        self.register_participation(user, video)

        result['allowed']      = True
        result['event_type']   = self.get_event_type()
        result['event_label']  = self.get_event_label()
        result['context']      = context
        return result

    # ── Pasos abstractos — cada subclase DEBE implementarlos ─────────────────

    @abstractmethod
    def check_eligibility(self, user, video) -> dict:
        """Verifica si el usuario puede participar en este evento."""
        pass

    @abstractmethod
    def get_welcome_message(self, user, video) -> str:
        """Genera el mensaje de bienvenida específico del evento."""
        pass

    @abstractmethod
    def get_event_type(self) -> str:
        """Retorna el identificador del tipo de evento."""
        pass

    @abstractmethod
    def get_event_label(self) -> str:
        """Retorna la etiqueta visible del evento."""
        pass

    # ── Pasos hook — las subclases PUEDEN sobreescribir ──────────────────────

    def prepare_context(self, user, video) -> dict:
        """Prepara datos de contexto adicionales. Por defecto vacío."""
        return {}

    def apply_benefits(self, user, video) -> list:
        """Aplica beneficios especiales. Por defecto ninguno."""
        return []

    def register_participation(self, user, video) -> None:
        """Registra la participación. Por defecto no hace nada."""
        pass


class MarathonEvent(ViewingEvent):
    """
    Evento Maratón: el usuario ve varios videos seguidos de una categoría.
    Disponible para todos los usuarios. Otorga puntos por cada video visto.
    """
    def __init__(self, category: str):
        self._category = category

    def check_eligibility(self, user, video) -> dict:
        if video.category != self._category:
            return {'allowed': False,
                    'reason': f'Este video no pertenece a la maratón de {self._category}'}
        return {'allowed': True}

    def get_welcome_message(self, user, video) -> str:
        return (f'🎬 ¡Maratón de {self._category} en curso, {user.username}! '
                f'Sigue viendo para completar la maratón.')

    def get_event_type(self) -> str:
        return 'marathon'

    def get_event_label(self) -> str:
        return f'🎬 Maratón — {self._category}'

    def apply_benefits(self, user, video) -> list:
        return ['Vistas cuentan doble durante la maratón',
                'Insignia de maratón al completar 5 videos']

    def prepare_context(self, user, video) -> dict:
        return {'category': self._category, 'bonus_views': True}


class PremiereEvent(ViewingEvent):
    """
    Evento Estreno: primer día de disponibilidad de un video.
    Solo para usuarios Premium. Muestra contenido exclusivo de detrás de cámaras.
    """
    def check_eligibility(self, user, video) -> dict:
        if user.subscription not in ('premium', 'admin'):
            return {'allowed': False,
                    'reason': 'Los estrenos son exclusivos para usuarios Premium'}
        return {'allowed': True}

    def get_welcome_message(self, user, video) -> str:
        return (f'⭐ ¡Bienvenido al estreno de "{video.title}", {user.username}! '
                f'Eres de los primeros en verlo.')

    def get_event_type(self) -> str:
        return 'premiere'

    def get_event_label(self) -> str:
        return '⭐ Estreno Premium'

    def apply_benefits(self, user, video) -> list:
        return ['Acceso anticipado 24h antes del lanzamiento general',
                'Contenido exclusivo de detrás de cámaras',
                'Insignia de espectador temprano']

    def prepare_context(self, user, video) -> dict:
        return {'is_premiere': True, 'exclusive_content': True}


class LiveEvent(ViewingEvent):
    """
    Evento en Vivo: transmisión en tiempo real.
    Disponible para todos. Habilita el chat en vivo durante la reproducción.
    """
    def __init__(self, live_id: str):
        self._live_id = live_id

    def check_eligibility(self, user, video) -> dict:
        return {'allowed': True}

    def get_welcome_message(self, user, video) -> str:
        return (f'🔴 ¡Estás en vivo, {user.username}! '
                f'Únete al chat y comenta en tiempo real.')

    def get_event_type(self) -> str:
        return 'live'

    def get_event_label(self) -> str:
        return '🔴 En Vivo'

    def apply_benefits(self, user, video) -> list:
        return ['Chat en vivo habilitado',
                'Reacciones en tiempo real',
                'Insignia de espectador en vivo']

    def prepare_context(self, user, video) -> dict:
        return {'live_id': self._live_id, 'chat_enabled': True}

    def register_participation(self, user, video) -> None:
        print(f'[LIVE] {user.username} joined live event {self._live_id}')


def get_viewing_event(event_type: str, **kwargs) -> ViewingEvent:
    """Selecciona y crea el evento de visualización según el tipo."""
    if event_type == 'marathon':
        return MarathonEvent(category=kwargs.get('category', 'General'))
    elif event_type == 'premiere':
        return PremiereEvent()
    elif event_type == 'live':
        return LiveEvent(live_id=kwargs.get('live_id', 'live_1'))
    return None


# ─── CHAIN OF RESPONSIBILITY ──────────────────────────────────────────────────
# Problema: cuando un usuario sube un video, el sistema debe aprobarlo
# pasando por múltiples verificaciones: formato del archivo, tamaño,
# título apropiado y categoría válida. Sin Chain, la ruta tendría todos
# esos if anidados mezclados con la lógica de guardado.
#
# Solución: cada verificación es un eslabón de la cadena. Si pasa,
# delega al siguiente. Si falla, detiene la cadena y devuelve el error.
# Agregar una nueva verificación es solo agregar un eslabón nuevo.

class ContentApprovalHandler(ABC):
    """Interfaz base para todos los eslabones de la cadena de aprobación."""

    def __init__(self):
        self._next: 'ContentApprovalHandler' = None

    def set_next(self, handler: 'ContentApprovalHandler') -> 'ContentApprovalHandler':
        """Encadena el siguiente eslabón y lo retorna para encadenamiento fluido."""
        self._next = handler
        return handler

    def handle(self, data: dict) -> dict:
        """Procesa la solicitud y delega al siguiente si pasa."""
        result = self.check(data)
        if not result['approved']:
            return result
        if self._next:
            return self._next.handle(data)
        return {'approved': True, 'message': 'Contenido aprobado por todos los filtros'}

    @abstractmethod
    def check(self, data: dict) -> dict:
        """Verifica su condición específica."""
        pass


class FileFormatHandler(ContentApprovalHandler):
    """Eslabón 1 — Verifica que el archivo sea un formato de video válido."""
    ALLOWED = {'mp4', 'mov', 'avi', 'mkv', 'webm'}

    def check(self, data: dict) -> dict:
        filename = data.get('filename_480p', '') or data.get('filename_720p', '')
        if not filename:
            return {'approved': False,
                    'reason': 'No se subió ningún archivo de video'}
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if ext not in self.ALLOWED:
            return {'approved': False,
                    'reason': f'Formato .{ext} no permitido. Use: {", ".join(self.ALLOWED)}'}
        return {'approved': True}


class TitleHandler(ContentApprovalHandler):
    """Eslabón 2 — Verifica que el título tenga longitud adecuada."""
    MIN_LEN = 5
    MAX_LEN = 100

    def check(self, data: dict) -> dict:
        title = data.get('title', '').strip()
        if len(title) < self.MIN_LEN:
            return {'approved': False,
                    'reason': f'El título debe tener al menos {self.MIN_LEN} caracteres'}
        if len(title) > self.MAX_LEN:
            return {'approved': False,
                    'reason': f'El título no puede superar {self.MAX_LEN} caracteres'}
        return {'approved': True}


class CategoryHandler(ContentApprovalHandler):
    """Eslabón 3 — Verifica que la categoría sea válida."""
    VALID = {'Tecnología', 'Deportes', 'Música', 'Educación',
             'Entretenimiento', 'Gastronomía', 'Viajes', 'Gaming',
             'Ciencia', 'Arte', 'Películas', 'Series', 'General'}

    def check(self, data: dict) -> dict:
        category = data.get('category', '').strip()
        if not category:
            return {'approved': False, 'reason': 'La categoría es requerida'}
        if category not in self.VALID:
            return {'approved': False,
                    'reason': f'Categoría "{category}" no válida'}
        return {'approved': True}


class DescriptionHandler(ContentApprovalHandler):
    """Eslabón 4 — Verifica que la descripción no tenga palabras prohibidas."""
    BANNED = {'spam', 'click aquí', 'ganar dinero', 'oferta', 'gratis ya'}

    def check(self, data: dict) -> dict:
        desc = data.get('description', '').lower()
        for word in self.BANNED:
            if word in desc:
                return {'approved': False,
                        'reason': f'La descripción contiene contenido no permitido: "{word}"'}
        return {'approved': True}


def build_approval_chain() -> ContentApprovalHandler:
    """
    Construye la cadena de aprobación de contenido en orden.
    FileFormat → Title → Category → Description
    """
    file_handler  = FileFormatHandler()
    title_handler = TitleHandler()
    cat_handler   = CategoryHandler()
    desc_handler  = DescriptionHandler()

    file_handler.set_next(title_handler)\
                .set_next(cat_handler)\
                .set_next(desc_handler)

    return file_handler


# ─── MEMENTO ──────────────────────────────────────────────────────────────────
# Problema: el usuario puede agregar videos a su biblioteca personal,
# pero si reorganiza o elimina videos por error no puede restaurar
# el estado anterior de su biblioteca.
#
# Solución: LibraryMemento guarda una instantánea del estado de la
# biblioteca. LibraryCaretaker mantiene el historial de snapshots.
# El usuario puede guardar el estado actual y restaurarlo después
# sin que el sistema de biblioteca conozca los detalles del guardado.

class LibraryMemento:
    """
    Memento que guarda una instantánea del estado de la biblioteca personal.
    Solo LibraryCaretaker y Library pueden acceder a su estado interno.
    """
    def __init__(self, video_ids: list, label: str = ''):
        self._video_ids = list(video_ids)
        self._label     = label
        self._saved_at  = datetime.utcnow()

    def get_video_ids(self) -> list:
        return list(self._video_ids)

    def get_label(self) -> str:
        return self._label

    def get_saved_at(self) -> str:
        return self._saved_at.strftime('%d %b %Y %H:%M')


class PersonalLibrary:
    """
    La biblioteca personal del usuario — Originator del Memento.
    Mantiene la lista de videos guardados y puede crear/restaurar snapshots.
    """
    def __init__(self, user_id: int):
        self._user_id  = user_id
        self._video_ids: list = []

    def add_video(self, video_id: int) -> None:
        if video_id not in self._video_ids:
            self._video_ids.append(video_id)

    def remove_video(self, video_id: int) -> None:
        if video_id in self._video_ids:
            self._video_ids.remove(video_id)

    def get_videos(self) -> list:
        return list(self._video_ids)

    def save(self, label: str = '') -> LibraryMemento:
        """Crea y retorna un Memento con el estado actual."""
        return LibraryMemento(self._video_ids, label)

    def restore(self, memento: LibraryMemento) -> None:
        """Restaura el estado desde un Memento guardado."""
        self._video_ids = memento.get_video_ids()


class LibraryCaretaker:
    """
    Caretaker del Memento — administra el historial de snapshots.
    Sabe cuándo guardar y restaurar pero no conoce el contenido del Memento.
    """
    def __init__(self, library: PersonalLibrary):
        self._library  = library
        self._history: list[LibraryMemento] = []

    def backup(self, label: str = '') -> None:
        """Guarda el estado actual de la biblioteca."""
        self._history.append(self._library.save(label))

    def undo(self) -> str:
        """Restaura el último snapshot guardado."""
        if not self._history:
            return 'No hay estados guardados para restaurar'
        memento = self._history.pop()
        self._library.restore(memento)
        return f'Biblioteca restaurada al estado: {memento.get_label() or memento.get_saved_at()}'

    def get_snapshots(self) -> list:
        """Devuelve el historial de snapshots disponibles."""
        return [{'label': m.get_label() or 'Sin etiqueta',
                 'saved_at': m.get_saved_at()}
                for m in self._history]

    def has_history(self) -> bool:
        return len(self._history) > 0


# Almacén global de bibliotecas y caretakers por usuario
user_libraries:   dict = {}
user_caretakers:  dict = {}


def get_user_library(user_id: int) -> tuple:
    """Obtiene o crea la biblioteca y caretaker del usuario."""
    if user_id not in user_libraries:
        lib = PersonalLibrary(user_id)
        user_libraries[user_id]  = lib
        user_caretakers[user_id] = LibraryCaretaker(lib)
    return user_libraries[user_id], user_caretakers[user_id]


# ─── MEMENTO — BORRADORES DE VIDEOS ──────────────────────────────────────────
# Extensión del Memento existente aplicada al formulario de subida.
# El usuario puede guardar borradores del formulario antes de publicar
# y restaurarlos si cierra el navegador o cambia de idea.

class DraftMemento:
    """Snapshot del estado del formulario de subida."""
    def __init__(self, title: str, description: str,
                 category: str, is_premium: bool, label: str = ''):
        self._title       = title
        self._description = description
        self._category    = category
        self._is_premium  = is_premium
        self._label       = label
        self._saved_at    = datetime.utcnow()

    def get_data(self) -> dict:
        return {
            'title':       self._title,
            'description': self._description,
            'category':    self._category,
            'is_premium':  self._is_premium,
            'label':       self._label,
            'saved_at':    self._saved_at.strftime('%d %b %Y %H:%M')
        }


class DraftCaretaker:
    """
    Administra el historial de borradores del formulario de subida.
    Permite guardar hasta 5 borradores por usuario.
    """
    MAX_DRAFTS = 5

    def __init__(self):
        self._drafts: list[DraftMemento] = []

    def save_draft(self, title: str, description: str,
                   category: str, is_premium: bool,
                   label: str = '') -> None:
        """Guarda un borrador nuevo. Si hay más de MAX_DRAFTS elimina el más antiguo."""
        draft = DraftMemento(title, description, category, is_premium, label)
        self._drafts.append(draft)
        if len(self._drafts) > self.MAX_DRAFTS:
            self._drafts.pop(0)

    def get_drafts(self) -> list:
        """Devuelve todos los borradores disponibles."""
        return [d.get_data() for d in reversed(self._drafts)]

    def get_draft(self, index: int) -> dict:
        """Devuelve un borrador específico por índice."""
        drafts = list(reversed(self._drafts))
        if 0 <= index < len(drafts):
            return drafts[index].get_data()
        return None

    def delete_draft(self, index: int) -> bool:
        """Elimina un borrador específico."""
        drafts = list(reversed(self._drafts))
        if 0 <= index < len(drafts):
            self._drafts.remove(list(reversed(self._drafts))[index])
            return True
        return False

    def has_drafts(self) -> bool:
        return len(self._drafts) > 0


# Almacén global de borradores por usuario
user_drafts: dict = {}


def get_draft_caretaker(user_id: int) -> DraftCaretaker:
    """Obtiene o crea el caretaker de borradores del usuario."""
    if user_id not in user_drafts:
        user_drafts[user_id] = DraftCaretaker()
    return user_drafts[user_id]


# ─── COMPOSITE — PLAYLISTS ANIDADAS ──────────────────────────────────────────
# Extensión del Composite con interfaz visual en /library.
# Una playlist puede contener videos individuales (VideoLeaf)
# o sub-playlists (PlaylistNode), calculando estadísticas recursivamente.

class PlaylistComponent(ABC):
    """Interfaz común del Composite para playlists."""
    @abstractmethod
    def get_name(self) -> str:
        pass

    @abstractmethod
    def get_total_views(self) -> int:
        pass

    @abstractmethod
    def get_video_count(self) -> int:
        pass

    @abstractmethod
    def to_dict(self) -> dict:
        pass


class PlaylistVideoItem(PlaylistComponent):
    """
    Nodo hoja — representa un video individual dentro de una playlist.
    """
    def __init__(self, video_id: int, title: str,
                 views: int, thumbnail: str = '', category: str = ''):
        self._video_id  = video_id
        self._title     = title
        self._views     = views
        self._thumbnail = thumbnail
        self._category  = category

    def get_name(self) -> str:
        return self._title

    def get_total_views(self) -> int:
        return self._views

    def get_video_count(self) -> int:
        return 1

    def to_dict(self) -> dict:
        return {
            'type':      'video',
            'video_id':  self._video_id,
            'title':     self._title,
            'views':     self._views,
            'thumbnail': self._thumbnail,
            'category':  self._category,
            'count':     1
        }


class PlaylistNode(PlaylistComponent):
    """
    Nodo compuesto — representa una playlist que puede contener
    videos y sub-playlists. Las estadísticas se calculan recursivamente.
    """
    def __init__(self, name: str, playlist_id: str = None):
        self._name        = name
        self._id          = playlist_id or name.lower().replace(' ', '_')
        self._children: list[PlaylistComponent] = []

    def add(self, component: PlaylistComponent) -> None:
        self._children.append(component)

    def remove_by_name(self, name: str) -> bool:
        for c in self._children:
            if c.get_name() == name:
                self._children.remove(c)
                return True
        return False

    def get_name(self) -> str:
        return self._name

    def get_id(self) -> str:
        return self._id

    def get_total_views(self) -> int:
        return sum(c.get_total_views() for c in self._children)

    def get_video_count(self) -> int:
        return sum(c.get_video_count() for c in self._children)

    def get_children(self) -> list:
        return self._children

    def to_dict(self) -> dict:
        return {
            'type':        'playlist',
            'id':          self._id,
            'name':        self._name,
            'video_count': self.get_video_count(),
            'total_views': self.get_total_views(),
            'children':    [c.to_dict() for c in self._children]
        }


class UserPlaylistManager:
    """
    Administra todas las playlists del usuario.
    Contiene una playlist raíz que agrupa todas las demás.
    """
    def __init__(self, user_id: int):
        self._user_id = user_id
        self._root    = PlaylistNode('Mis Playlists', 'root')

    def create_playlist(self, name: str) -> PlaylistNode:
        """Crea una nueva playlist y la agrega a la raíz."""
        playlist = PlaylistNode(name)
        self._root.add(playlist)
        return playlist

    def get_playlist(self, playlist_id: str) -> PlaylistNode:
        """Busca una playlist por ID."""
        for child in self._root.get_children():
            if isinstance(child, PlaylistNode) and child.get_id() == playlist_id:
                return child
        return None

    def add_video_to_playlist(self, playlist_id: str,
                               video_id: int, title: str,
                               views: int, thumbnail: str = '',
                               category: str = '') -> bool:
        """Agrega un video a una playlist específica."""
        playlist = self.get_playlist(playlist_id)
        if not playlist:
            return False
        playlist.add(PlaylistVideoItem(video_id, title, views, thumbnail, category))
        return True

    def get_all(self) -> dict:
        """Devuelve el árbol completo de playlists."""
        return self._root.to_dict()

    def get_playlists(self) -> list:
        """Devuelve solo las playlists de primer nivel."""
        return [c.to_dict() for c in self._root.get_children()
                if isinstance(c, PlaylistNode)]


# Almacén global de playlists por usuario
user_playlists: dict = {}


def get_playlist_manager(user_id: int) -> UserPlaylistManager:
    """Obtiene o crea el manager de playlists del usuario."""
    if user_id not in user_playlists:
        user_playlists[user_id] = UserPlaylistManager(user_id)
    return user_playlists[user_id]
