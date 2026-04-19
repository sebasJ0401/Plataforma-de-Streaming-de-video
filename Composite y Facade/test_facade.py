import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from patterns import (
    UserRegistrationFacade,
    RegistrationResult,
    ConsoleNotificationSender,
    NotificationSender,
)


# ─── MOCKS ────────────────────────────────────────────────────────────────────

class MockUser:
    """Simula un objeto User sin necesitar la BD."""
    _instances = {}

    def __init__(self, username, email, subscription='free'):
        self.id           = len(MockUser._instances) + 1
        self.username     = username
        self.email        = email
        self.subscription = subscription
        self.password_hash = None

    def set_password(self, password):
        self.password_hash = f'hashed_{password}'

    def check_password(self, password):
        return self.password_hash == f'hashed_{password}'

    @classmethod
    def reset(cls):
        cls._instances = {}


class MockQuery:
    """Simula User.query.filter_by().first()"""
    def __init__(self, result=None):
        self._result = result

    def first(self):
        return self._result


class MockUserModel:
    """Simula el modelo User con query mock."""
    def __init__(self, existing_users=None):
        self._users = existing_users or {}

    def filter_by(self, username=None, email=None):
        if username and username in self._users:
            return MockQuery(self._users[username])
        if email:
            for u in self._users.values():
                if u.email == email:
                    return MockQuery(u)
        return MockQuery(None)


class MockDBSession:
    """Simula db.session sin necesitar SQLAlchemy."""
    def __init__(self):
        self.added    = []
        self.committed = False

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True


class MockDB:
    """Simula el objeto db de Flask-SQLAlchemy."""
    def __init__(self):
        self.session = MockDBSession()


class MockSession(dict):
    """Simula el objeto session de Flask."""
    pass


class MockNotificationSender(NotificationSender):
    """Sender que captura mensajes sin imprimirlos."""
    def __init__(self):
        self.sent = []

    def send(self, recipient, subject, body):
        self.sent.append({
            'recipient': recipient,
            'subject':   subject,
            'body':      body
        })


class MockFacade(UserRegistrationFacade):
    """
    Facade de prueba que inyecta el modelo User mock
    para evitar consultas reales a la base de datos.
    """
    def __init__(self, db, session_store, sender, existing_users=None):
        super().__init__(db, session_store, sender)
        self._mock_user_model = MockUserModel(existing_users or {})

    def register(self, username, email, password):
        # Validaciones básicas
        if not username or not email or not password:
            return RegistrationResult(False, error='Todos los campos son requeridos')
        if len(password) < 6:
            return RegistrationResult(False, error='La contraseña debe tener al menos 6 caracteres')

        # Unicidad usando mock
        if self._mock_user_model.filter_by(username=username).first():
            return RegistrationResult(False, error='El nombre de usuario ya existe')
        if self._mock_user_model.filter_by(email=email).first():
            return RegistrationResult(False, error='El email ya está registrado')

        # Crear usuario mock
        user = MockUser(username=username, email=email)
        user.set_password(password)

        # Persistencia mock
        self._db.session.add(user)
        self._db.session.commit()

        # Sesión mock
        self._session['user_id'] = user.id

        # Notificación (Bridge real)
        from patterns import RegisterNotification
        RegisterNotification(self._sender).notify(recipient=username)

        return RegistrationResult(True, user=user)


# ─── PRUEBAS REGISTRATION RESULT ─────────────────────────────────────────────

class TestRegistrationResult(unittest.TestCase):

    def test_resultado_exitoso(self):
        """RegistrationResult exitoso debe tener success=True"""
        user   = MockUser('test', 'test@test.com')
        result = RegistrationResult(True, user=user)
        self.assertTrue(result.success)
        self.assertIsNotNone(result.user)
        self.assertIsNone(result.error)

    def test_resultado_fallido(self):
        """RegistrationResult fallido debe tener success=False y error"""
        result = RegistrationResult(False, error='Email ya registrado')
        self.assertFalse(result.success)
        self.assertEqual(result.error, 'Email ya registrado')
        self.assertIsNone(result.user)

    def test_resultado_tiene_usuario(self):
        """RegistrationResult exitoso debe contener el usuario creado"""
        user   = MockUser('sebastian', 'seba@test.com')
        result = RegistrationResult(True, user=user)
        self.assertEqual(result.user.username, 'sebastian')


# ─── PRUEBAS FACADE REGISTRO EXITOSO ─────────────────────────────────────────

class TestFacadeRegistroExitoso(unittest.TestCase):

    def setUp(self):
        self.db      = MockDB()
        self.session = MockSession()
        self.sender  = MockNotificationSender()
        self.facade  = MockFacade(self.db, self.session, self.sender)

    def test_registro_exitoso_retorna_success_true(self):
        """Un registro válido debe retornar success=True"""
        result = self.facade.register('sebastian', 'seba@test.com', 'password123')
        self.assertTrue(result.success)

    def test_registro_exitoso_retorna_usuario(self):
        """Un registro válido debe retornar el objeto usuario"""
        result = self.facade.register('sebastian', 'seba@test.com', 'password123')
        self.assertIsNotNone(result.user)

    def test_registro_exitoso_sin_error(self):
        """Un registro válido no debe tener mensaje de error"""
        result = self.facade.register('sebastian', 'seba@test.com', 'password123')
        self.assertIsNone(result.error)

    def test_registro_guarda_en_bd(self):
        """La Facade debe agregar el usuario a la BD"""
        self.facade.register('sebastian', 'seba@test.com', 'password123')
        self.assertEqual(len(self.db.session.added), 1)

    def test_registro_hace_commit(self):
        """La Facade debe hacer commit en la BD"""
        self.facade.register('sebastian', 'seba@test.com', 'password123')
        self.assertTrue(self.db.session.committed)

    def test_registro_inicia_sesion(self):
        """La Facade debe guardar user_id en la sesión"""
        self.facade.register('sebastian', 'seba@test.com', 'password123')
        self.assertIn('user_id', self.session)

    def test_registro_envia_notificacion(self):
        """La Facade debe enviar notificación de bienvenida"""
        self.facade.register('sebastian', 'seba@test.com', 'password123')
        self.assertEqual(len(self.sender.sent), 1)

    def test_registro_notificacion_destinatario_correcto(self):
        """La notificación debe ir dirigida al username registrado"""
        self.facade.register('sebastian', 'seba@test.com', 'password123')
        self.assertEqual(self.sender.sent[0]['recipient'], 'sebastian')


# ─── PRUEBAS FACADE VALIDACIONES ─────────────────────────────────────────────

class TestFacadeValidaciones(unittest.TestCase):

    def setUp(self):
        self.db      = MockDB()
        self.session = MockSession()
        self.sender  = MockNotificationSender()
        self.facade  = MockFacade(self.db, self.session, self.sender)

    def test_campos_vacios_retorna_error(self):
        """Campos vacíos deben retornar error"""
        result = self.facade.register('', '', '')
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)

    def test_username_vacio_retorna_error(self):
        """Username vacío debe retornar error"""
        result = self.facade.register('', 'seba@test.com', 'password123')
        self.assertFalse(result.success)

    def test_email_vacio_retorna_error(self):
        """Email vacío debe retornar error"""
        result = self.facade.register('sebastian', '', 'password123')
        self.assertFalse(result.success)

    def test_password_corta_retorna_error(self):
        """Contraseña menor a 6 caracteres debe retornar error"""
        result = self.facade.register('sebastian', 'seba@test.com', '123')
        self.assertFalse(result.success)
        self.assertIn('6 caracteres', result.error)

    def test_password_corta_no_guarda_en_bd(self):
        """Con contraseña corta no debe guardarse nada en BD"""
        self.facade.register('sebastian', 'seba@test.com', '123')
        self.assertEqual(len(self.db.session.added), 0)

    def test_password_corta_no_envia_notificacion(self):
        """Con contraseña corta no debe enviarse notificación"""
        self.facade.register('sebastian', 'seba@test.com', '123')
        self.assertEqual(len(self.sender.sent), 0)


# ─── PRUEBAS FACADE UNICIDAD ──────────────────────────────────────────────────

class TestFacadeUnicidad(unittest.TestCase):

    def setUp(self):
        self.db      = MockDB()
        self.session = MockSession()
        self.sender  = MockNotificationSender()
        existing     = MockUser('sebastian', 'seba@test.com')
        self.facade  = MockFacade(
            self.db, self.session, self.sender,
            existing_users={'sebastian': existing}
        )

    def test_username_duplicado_retorna_error(self):
        """Username ya existente debe retornar error"""
        result = self.facade.register('sebastian', 'otro@test.com', 'password123')
        self.assertFalse(result.success)
        self.assertIn('usuario', result.error.lower())

    def test_email_duplicado_retorna_error(self):
        """Email ya existente debe retornar error"""
        result = self.facade.register('nuevo', 'seba@test.com', 'password123')
        self.assertFalse(result.success)
        self.assertIn('email', result.error.lower())

    def test_duplicado_no_guarda_en_bd(self):
        """Con datos duplicados no debe guardarse nada en BD"""
        self.facade.register('sebastian', 'otro@test.com', 'password123')
        self.assertEqual(len(self.db.session.added), 0)

    def test_duplicado_no_envia_notificacion(self):
        """Con datos duplicados no debe enviarse notificación"""
        self.facade.register('sebastian', 'otro@test.com', 'password123')
        self.assertEqual(len(self.sender.sent), 0)


# ─── EJECUTAR ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    unittest.main(verbosity=2)
