import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from patterns import UserFactory, VideoFactory


# ─── PRUEBAS USER FACTORY ─────────────────────────────────────────────────────

class TestUserFactory(unittest.TestCase):

    def setUp(self):
        """Configura el contexto de Flask para poder crear objetos User"""
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


# ─── PRUEBAS VIDEO FACTORY ────────────────────────────────────────────────────

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


# ─── EJECUTAR ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    unittest.main(verbosity=2)
