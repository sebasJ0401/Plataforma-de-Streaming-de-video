from enum import Enum

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


# ─── FACTORY ─────────────────────────────────────────────────────────────────
# Centraliza la creación de objetos User y Video.
# app.py deja de crear estos objetos directamente.

class UserFactory:
    @staticmethod
    def create(username: str, email: str, password: str, subscription: str = 'free'):
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


# ─── ABSTRACT FACTORY ────────────────────────────────────────────────────────
# Define una familia de objetos según el tipo de suscripción del usuario.
# FreeSubscription  → acceso limitado, solo 480p, sin contenido premium.
# PremiumSubscription → acceso completo, 720p, todo el contenido.

from abc import ABC, abstractmethod


# ── Productos abstractos ──────────────────────────────────────────────────────

class VideoPlayer(ABC):
    """Define qué calidades puede ver el usuario."""
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


# ── Productos concretos FREE ──────────────────────────────────────────────────

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


# ── Productos concretos PREMIUM ───────────────────────────────────────────────

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


# ── Abstract Factory ──────────────────────────────────────────────────────────

class SubscriptionFactory(ABC):
    """Fábrica abstracta que define cómo crear la familia de objetos."""
    @abstractmethod
    def create_player(self) -> VideoPlayer:
        pass

    @abstractmethod
    def create_access(self) -> ContentAccess:
        pass


# ── Factories concretos ───────────────────────────────────────────────────────

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


# ── Selector del factory según suscripción ────────────────────────────────────

def get_subscription_factory(subscription: str) -> SubscriptionFactory:
    """Devuelve el factory correcto según el plan del usuario."""
    if subscription in ('premium', 'admin'):
        return PremiumSubscriptionFactory()
    return FreeSubscriptionFactory()


# ─── BUILDER ─────────────────────────────────────────────────────────────────
# Construye respuestas JSON de la API de forma estructurada y encadenada.
# Cada ruta de app.py deja de armar diccionarios a mano.
# El Builder garantiza que todas las respuestas tienen el mismo formato.

class APIResponseBuilder:
    """
    Builder para construir respuestas JSON de la API.
    Permite encadenar métodos para agregar campos de forma legible.
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


# ─── PROTOTYPE ────────────────────────────────────────────────────────────────
# Permite clonar un video existente para crear una copia independiente.
# El clon hereda todos los atributos del original pero es un objeto distinto
# que puede modificarse sin afectar al video original.

import copy

class VideoPrototype:
    """
    Prototype para clonar videos existentes.
    Recibe un objeto Video y produce copias independientes de él.
    """

    def __init__(self, video):
        self._video = video

    def clone(self, new_title: str = None, new_category: str = None,
              new_is_premium: bool = None):
        """
        Clona el video original y permite sobrescribir atributos específicos.
        Devuelve un nuevo objeto Video independiente del original.
        """
        from app import Video
        cloned = Video(
            title=new_title if new_title is not None else self._video.title + ' (copia)',
            description=self._video.description,
            category=new_category if new_category is not None else self._video.category,
            uploader_id=self._video.uploader_id,
            is_premium=new_is_premium if new_is_premium is not None else self._video.is_premium,
        )
        cloned.filename_480p = self._video.filename_480p
        cloned.filename_720p = self._video.filename_720p
        cloned.thumbnail     = self._video.thumbnail
        return cloned


# ─── ADAPTER ──────────────────────────────────────────────────────────────────
# Problema: los proveedores de autenticación externos (Google, GitHub)
# tienen interfaces completamente distintas a la autenticación local.
# Google devuelve un token JWT con campos como 'sub', 'email', 'name'.
# La autenticación local usa email + password con check_password().
# La ruta /api/login no debería conocer estas diferencias.
#
# Solución: un Adapter por proveedor que traduce su interfaz particular
# a una interfaz común con get_email() y get_username().
# La ruta /api/login solo habla con la interfaz común.

class LocalAuthProvider:
    """
    Proveedor de autenticación local de StreamVault.
    Recibe email y password directamente del formulario.
    """
    def __init__(self, email: str, password: str):
        self._email    = email
        self._password = password

    def get_email(self) -> str:
        return self._email

    def get_password(self) -> str:
        return self._password

    def get_username(self) -> str:
        return self._email.split('@')[0]


class GoogleAuthProvider:
    """
    Proveedor de autenticación de Google.
    Recibe el token decodificado del JWT de Google.
    Sus campos son incompatibles con la autenticación local:
    usa 'sub' en lugar de id, 'name' en lugar de username.
    """
    def __init__(self, google_token: dict):
        self._token = google_token

    def fetch_google_email(self) -> str:
        return self._token.get('email', '')

    def fetch_google_name(self) -> str:
        return self._token.get('name', self._token.get('email', '').split('@')[0])

    def fetch_google_id(self) -> str:
        return self._token.get('sub', '')


class AuthProviderAdapter:
    """
    Adapter que unifica LocalAuthProvider y GoogleAuthProvider
    bajo una interfaz común con get_email() y get_username().
    La ruta /api/login solo usa esta interfaz sin saber
    qué proveedor de autenticación hay por debajo.
    """

    def __init__(self, provider):
        self._provider = provider

    def get_email(self) -> str:
        """Devuelve el email sin importar el proveedor."""
        if isinstance(self._provider, LocalAuthProvider):
            return self._provider.get_email()
        elif isinstance(self._provider, GoogleAuthProvider):
            return self._provider.fetch_google_email()
        raise ValueError(f'Proveedor no soportado: {type(self._provider)}')

    def get_username(self) -> str:
        """Devuelve el nombre de usuario sin importar el proveedor."""
        if isinstance(self._provider, LocalAuthProvider):
            return self._provider.get_username()
        elif isinstance(self._provider, GoogleAuthProvider):
            return self._provider.fetch_google_name()
        raise ValueError(f'Proveedor no soportado: {type(self._provider)}')

    def is_google(self) -> bool:
        """Indica si el proveedor es Google para manejo especial de contraseña."""
        return isinstance(self._provider, GoogleAuthProvider)


def get_auth_adapter(data: dict) -> AuthProviderAdapter:
    """
    Selecciona el proveedor correcto según los datos recibidos
    y lo envuelve en el Adapter para exponer la interfaz común.
    Si los datos incluyen google_token se usa Google, si no se usa local.
    """
    if 'google_token' in data:
        return AuthProviderAdapter(GoogleAuthProvider(data['google_token']))
    return AuthProviderAdapter(LocalAuthProvider(
        email=data.get('email', ''),
        password=data.get('password', '')
    ))


# ─── DECORATOR ────────────────────────────────────────────────────────────────
# Problema: la búsqueda de videos en /browse es una consulta simple.
# Se necesita agregar filtros opcionales (por categoría, por plan, por
# popularidad) sin modificar la consulta base ni crear combinaciones fijas.
#
# Solución: una interfaz VideoQuery con un método execute(). La consulta
# base la implementa BaseVideoQuery. Cada filtro es un Decorator que
# envuelve la consulta anterior y le agrega su condición.
# Se pueden encadenar tantos decoradores como se necesite.

class VideoQuery(ABC):
    """Interfaz base que toda consulta de videos debe implementar."""
    @abstractmethod
    def execute(self) -> list:
        pass


class BaseVideoQuery(VideoQuery):
    """
    Consulta base sin filtros.
    Devuelve todos los videos ordenados por fecha de creación.
    """
    def execute(self) -> list:
        from app import Video
        return Video.query.order_by(Video.created_at.desc()).all()


class VideoQueryDecorator(VideoQuery, ABC):
    """
    Decorator abstracto. Envuelve una VideoQuery existente
    y delega execute() añadiendo su propio filtro.
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
    """Decorator que filtra mostrando solo videos gratuitos a usuarios free."""
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


# ─── BRIDGE ───────────────────────────────────────────────────────────────────
# Problema: las notificaciones del sistema (registro exitoso, video subido,
# upgrade de plan) pueden enviarse por distintos canales — consola, email,
# push. Sin Bridge habría una clase por cada combinación posible:
# EmailRegistroNotif, ConsoleVideoNotif, PushUpgradeNotif, etc.
#
# Solución: separar QUÉ se notifica (abstracción) de CÓMO se envía
# (implementación). La abstracción Notification define los eventos.
# La interfaz NotificationSender define el canal de envío.
# Ambas jerarquías crecen de forma independiente.

class NotificationSender(ABC):
    """
    Interfaz de implementación del Bridge.
    Define cómo se envía un mensaje sin importar qué evento ocurrió.
    """
    @abstractmethod
    def send(self, recipient: str, subject: str, body: str) -> None:
        pass


class ConsoleNotificationSender(NotificationSender):
    """Implementación que imprime la notificación en consola."""
    def send(self, recipient: str, subject: str, body: str) -> None:
        print(f'[NOTIFICACIÓN] Para: {recipient} | {subject} | {body}')


class EmailNotificationSender(NotificationSender):
    """Implementación que simula el envío por email."""
    def send(self, recipient: str, subject: str, body: str) -> None:
        print(f'[EMAIL] → {recipient} | Asunto: {subject} | {body}')


class PushNotificationSender(NotificationSender):
    """Implementación que simula el envío como notificación push."""
    def send(self, recipient: str, subject: str, body: str) -> None:
        print(f'[PUSH] → {recipient} | {subject}')


class Notification(ABC):
    """
    Abstracción del Bridge.
    Conoce QUÉ evento ocurrió y delega el envío al NotificationSender.
    """
    def __init__(self, sender: NotificationSender):
        self._sender = sender

    @abstractmethod
    def notify(self, recipient: str) -> None:
        pass


class RegisterNotification(Notification):
    """Notificación de registro exitoso."""
    def notify(self, recipient: str) -> None:
        self._sender.send(
            recipient=recipient,
            subject='Bienvenido a StreamVault',
            body=f'Hola {recipient}, tu cuenta fue creada exitosamente.'
        )


class VideoUploadedNotification(Notification):
    """Notificación de video subido exitosamente."""
    def __init__(self, sender: NotificationSender, video_title: str):
        super().__init__(sender)
        self._video_title = video_title

    def notify(self, recipient: str) -> None:
        self._sender.send(
            recipient=recipient,
            subject='Video publicado',
            body=f'Tu video "{self._video_title}" ya está disponible en StreamVault.'
        )


class UpgradeNotification(Notification):
    """Notificación de upgrade de plan exitoso."""
    def __init__(self, sender: NotificationSender, plan: str):
        super().__init__(sender)
        self._plan = plan

    def notify(self, recipient: str) -> None:
        self._sender.send(
            recipient=recipient,
            subject='Plan actualizado',
            body=f'Tu plan fue actualizado a {self._plan}. ¡Disfruta el contenido premium!'
        )
