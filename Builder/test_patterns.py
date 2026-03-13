import unittest
import sys
import os

# Permite importar patterns.py desde la misma carpeta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from patterns import (
    DatabaseConfig,
    UserFactory,
    VideoFactory,
    get_subscription_factory,
    FreeSubscriptionFactory,
    PremiumSubscriptionFactory,
    FreeVideoPlayer,
    PremiumVideoPlayer,
    FreeContentAccess,
    PremiumContentAccess,
)


# ─── PRUEBAS SINGLETON ────────────────────────────────────────────────────────

class TestSingletonDatabaseConfig(unittest.TestCase):

    def test_get_uri_retorna_string(self):
        """get_uri() debe retornar una cadena de texto"""
        uri = DatabaseConfig.get_uri()
        self.assertIsInstance(uri, str)

    def test_get_uri_contiene_sqlite(self):
        """La URI debe contener sqlite"""
        uri = DatabaseConfig.get_uri()
        self.assertIn('sqlite', uri)

    def test_get_uri_siempre_igual(self):
        """Dos llamadas a get_uri() deben retornar el mismo valor"""
        uri1 = DatabaseConfig.get_uri()
        uri2 = DatabaseConfig.get_uri()
        self.assertEqual(uri1, uri2)

    def test_instancia_es_unica(self):
        """DatabaseConfig.INSTANCE siempre es la misma instancia"""
        instancia1 = DatabaseConfig.INSTANCE
        instancia2 = DatabaseConfig.INSTANCE
        self.assertIs(instancia1, instancia2)

    def test_uri_no_esta_vacia(self):
        """La URI no debe estar vacía"""
        uri = DatabaseConfig.get_uri()
        self.assertTrue(len(uri) > 0)


# ─── PRUEBAS FACTORY ─────────────────────────────────────────────────────────

class TestUserFactory(unittest.TestCase):

    def setUp(self):
        """Configura la app de Flask para poder crear objetos User"""
        from app import app, db
        self.app = app
        self.db = db
        self.ctx = app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def test_create_retorna_objeto_user(self):
        """UserFactory.create() debe retornar un objeto User"""
        from app import User
        user = UserFactory.create(
            username='testuser',
            email='test@test.com',
            password='123456'
        )
        self.assertIsInstance(user, User)

    def test_password_encriptada(self):
        """La contraseña debe quedar encriptada, no en texto plano"""
        user = UserFactory.create(
            username='testuser2',
            email='test2@test.com',
            password='mipassword'
        )
        self.assertNotEqual(user.password_hash, 'mipassword')

    def test_password_verifica_correctamente(self):
        """check_password() debe validar la contraseña original"""
        user = UserFactory.create(
            username='testuser3',
            email='test3@test.com',
            password='secreto123'
        )
        self.assertTrue(user.check_password('secreto123'))

    def test_password_incorrecta_falla(self):
        """check_password() debe fallar con contraseña incorrecta"""
        user = UserFactory.create(
            username='testuser4',
            email='test4@test.com',
            password='correcta'
        )
        self.assertFalse(user.check_password('incorrecta'))

    def test_suscripcion_por_defecto_es_free(self):
        """La suscripción por defecto debe ser free"""
        user = UserFactory.create(
            username='testuser5',
            email='test5@test.com',
            password='123456'
        )
        self.assertEqual(user.subscription, 'free')

    def test_suscripcion_premium(self):
        """Se puede crear un usuario con suscripción premium"""
        user = UserFactory.create(
            username='testuser6',
            email='test6@test.com',
            password='123456',
            subscription='premium'
        )
        self.assertEqual(user.subscription, 'premium')

    def test_username_asignado_correctamente(self):
        """El username debe quedar asignado correctamente"""
        user = UserFactory.create(
            username='sebastian',
            email='seba@test.com',
            password='123456'
        )
        self.assertEqual(user.username, 'sebastian')


class TestVideoFactory(unittest.TestCase):

    def setUp(self):
        from app import app
        self.ctx = app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def test_create_retorna_objeto_video(self):
        """VideoFactory.create() debe retornar un objeto Video"""
        from app import Video
        video = VideoFactory.create(
            title='Mi Video',
            category='Tecnología',
            uploader_id=1
        )
        self.assertIsInstance(video, Video)

    def test_titulo_asignado_correctamente(self):
        """El título debe quedar asignado correctamente"""
        video = VideoFactory.create(
            title='Video de Prueba',
            category='Educación',
            uploader_id=1
        )
        self.assertEqual(video.title, 'Video de Prueba')

    def test_categoria_asignada_correctamente(self):
        """La categoría debe quedar asignada correctamente"""
        video = VideoFactory.create(
            title='Test',
            category='Deportes',
            uploader_id=1
        )
        self.assertEqual(video.category, 'Deportes')

    def test_no_es_premium_por_defecto(self):
        """Un video no debe ser premium por defecto"""
        video = VideoFactory.create(
            title='Test',
            category='Música',
            uploader_id=1
        )
        self.assertFalse(video.is_premium)

    def test_puede_crearse_como_premium(self):
        """Se puede crear un video marcado como premium"""
        video = VideoFactory.create(
            title='Video Premium',
            category='Películas',
            uploader_id=1,
            is_premium=True
        )
        self.assertTrue(video.is_premium)


# ─── PRUEBAS ABSTRACT FACTORY ─────────────────────────────────────────────────

class TestGetSubscriptionFactory(unittest.TestCase):

    def test_free_retorna_free_factory(self):
        """Plan free debe retornar FreeSubscriptionFactory"""
        factory = get_subscription_factory('free')
        self.assertIsInstance(factory, FreeSubscriptionFactory)

    def test_premium_retorna_premium_factory(self):
        """Plan premium debe retornar PremiumSubscriptionFactory"""
        factory = get_subscription_factory('premium')
        self.assertIsInstance(factory, PremiumSubscriptionFactory)

    def test_admin_retorna_premium_factory(self):
        """Plan admin debe retornar PremiumSubscriptionFactory"""
        factory = get_subscription_factory('admin')
        self.assertIsInstance(factory, PremiumSubscriptionFactory)

    def test_plan_desconocido_retorna_free(self):
        """Un plan desconocido debe retornar FreeSubscriptionFactory"""
        factory = get_subscription_factory('desconocido')
        self.assertIsInstance(factory, FreeSubscriptionFactory)


class TestFreeSubscriptionFactory(unittest.TestCase):

    def setUp(self):
        self.factory = FreeSubscriptionFactory()
        self.player = self.factory.create_player()
        self.access = self.factory.create_access()

    def test_player_es_free(self):
        """El player debe ser FreeVideoPlayer"""
        self.assertIsInstance(self.player, FreeVideoPlayer)

    def test_access_es_free(self):
        """El access debe ser FreeContentAccess"""
        self.assertIsInstance(self.access, FreeContentAccess)

    def test_solo_tiene_480p(self):
        """Free solo debe tener calidad 480p"""
        qualities = self.player.get_available_qualities()
        self.assertEqual(qualities, ['480p'])

    def test_no_tiene_720p(self):
        """Free no debe tener calidad 720p"""
        qualities = self.player.get_available_qualities()
        self.assertNotIn('720p', qualities)

    def test_calidad_por_defecto_es_480p(self):
        """La calidad por defecto de Free debe ser 480p"""
        self.assertEqual(self.player.get_default_quality(), '480p')

    def test_no_puede_ver_premium(self):
        """Free no debe poder ver contenido premium"""
        self.assertFalse(self.access.can_watch_premium())

    def test_etiqueta_correcta(self):
        """La etiqueta de Free debe ser Plan Gratuito"""
        self.assertEqual(self.access.get_access_label(), 'Plan Gratuito')


class TestPremiumSubscriptionFactory(unittest.TestCase):

    def setUp(self):
        self.factory = PremiumSubscriptionFactory()
        self.player = self.factory.create_player()
        self.access = self.factory.create_access()

    def test_player_es_premium(self):
        """El player debe ser PremiumVideoPlayer"""
        self.assertIsInstance(self.player, PremiumVideoPlayer)

    def test_access_es_premium(self):
        """El access debe ser PremiumContentAccess"""
        self.assertIsInstance(self.access, PremiumContentAccess)

    def test_tiene_480p_y_720p(self):
        """Premium debe tener ambas calidades"""
        qualities = self.player.get_available_qualities()
        self.assertIn('480p', qualities)
        self.assertIn('720p', qualities)

    def test_calidad_por_defecto_es_720p(self):
        """La calidad por defecto de Premium debe ser 720p"""
        self.assertEqual(self.player.get_default_quality(), '720p')

    def test_puede_ver_premium(self):
        """Premium debe poder ver contenido premium"""
        self.assertTrue(self.access.can_watch_premium())

    def test_etiqueta_correcta(self):
        """La etiqueta de Premium debe ser Plan Premium"""
        self.assertEqual(self.access.get_access_label(), 'Plan Premium')


# ─── EJECUTAR ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    unittest.main(verbosity=2)
