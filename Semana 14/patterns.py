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
