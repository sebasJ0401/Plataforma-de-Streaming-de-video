import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from patterns import APIResponseBuilder


# ─── PRUEBAS BÁSICAS ──────────────────────────────────────────────────────────

class TestAPIResponseBuilderBasico(unittest.TestCase):

    def test_build_retorna_diccionario(self):
        """build() debe retornar un diccionario"""
        result = APIResponseBuilder().build()
        self.assertIsInstance(result, dict)

    def test_build_vacio_es_diccionario_vacio(self):
        """Un Builder sin métodos retorna diccionario vacío"""
        result = APIResponseBuilder().build()
        self.assertEqual(result, {})

    def test_cada_instancia_es_independiente(self):
        """Dos instancias del Builder no comparten estado"""
        b1 = APIResponseBuilder().set_success(True).build()
        b2 = APIResponseBuilder().set_error('Error').build()
        self.assertNotEqual(b1, b2)


# ─── PRUEBAS set_success ──────────────────────────────────────────────────────

class TestAPIResponseBuilderSetSuccess(unittest.TestCase):

    def test_set_success_true(self):
        """set_success(True) debe agregar success=True"""
        result = APIResponseBuilder().set_success(True).build()
        self.assertTrue(result['success'])

    def test_set_success_false(self):
        """set_success(False) debe agregar success=False"""
        result = APIResponseBuilder().set_success(False).build()
        self.assertFalse(result['success'])

    def test_set_success_retorna_builder(self):
        """set_success() debe retornar el mismo Builder para encadenar"""
        builder = APIResponseBuilder()
        result = builder.set_success(True)
        self.assertIsInstance(result, APIResponseBuilder)


# ─── PRUEBAS set_error ────────────────────────────────────────────────────────

class TestAPIResponseBuilderSetError(unittest.TestCase):

    def test_set_error_agrega_mensaje(self):
        """set_error() debe agregar el mensaje de error"""
        result = APIResponseBuilder().set_error('Algo salió mal').build()
        self.assertEqual(result['error'], 'Algo salió mal')

    def test_set_error_marca_success_false(self):
        """set_error() debe marcar automáticamente success como False"""
        result = APIResponseBuilder().set_error('Error').build()
        self.assertFalse(result['success'])

    def test_set_error_no_necesita_set_success(self):
        """set_error() no requiere llamar set_success() manualmente"""
        result = APIResponseBuilder().set_error('Error').build()
        self.assertIn('success', result)

    def test_set_error_retorna_builder(self):
        """set_error() debe retornar el mismo Builder para encadenar"""
        builder = APIResponseBuilder()
        result = builder.set_error('Error')
        self.assertIsInstance(result, APIResponseBuilder)

    def test_diferentes_mensajes_error(self):
        """Debe soportar cualquier mensaje de error"""
        mensajes = [
            'Todos los campos son requeridos',
            'El email ya está registrado',
            'No autorizado',
            'Username taken',
            'Credenciales incorrectas'
        ]
        for msg in mensajes:
            result = APIResponseBuilder().set_error(msg).build()
            self.assertEqual(result['error'], msg)


# ─── PRUEBAS set_redirect ─────────────────────────────────────────────────────

class TestAPIResponseBuilderSetRedirect(unittest.TestCase):

    def test_set_redirect_agrega_url(self):
        """set_redirect() debe agregar la URL de redirección"""
        result = APIResponseBuilder().set_redirect('/').build()
        self.assertEqual(result['redirect'], '/')

    def test_set_redirect_cualquier_url(self):
        """set_redirect() debe soportar cualquier URL"""
        result = APIResponseBuilder().set_redirect('/browse').build()
        self.assertEqual(result['redirect'], '/browse')

    def test_set_redirect_retorna_builder(self):
        """set_redirect() debe retornar el mismo Builder para encadenar"""
        builder = APIResponseBuilder()
        result = builder.set_redirect('/')
        self.assertIsInstance(result, APIResponseBuilder)


# ─── PRUEBAS set_message ──────────────────────────────────────────────────────

class TestAPIResponseBuilderSetMessage(unittest.TestCase):

    def test_set_message_agrega_mensaje(self):
        """set_message() debe agregar el mensaje"""
        result = APIResponseBuilder().set_message('Operación exitosa').build()
        self.assertEqual(result['message'], 'Operación exitosa')

    def test_set_message_seed(self):
        """set_message() debe funcionar con el mensaje de seed"""
        msg = 'Seeded! admin@streamvault.com / admin123'
        result = APIResponseBuilder().set_message(msg).build()
        self.assertEqual(result['message'], msg)

    def test_set_message_retorna_builder(self):
        """set_message() debe retornar el mismo Builder para encadenar"""
        builder = APIResponseBuilder()
        result = builder.set_message('Hola')
        self.assertIsInstance(result, APIResponseBuilder)


# ─── PRUEBAS set_video_id ─────────────────────────────────────────────────────

class TestAPIResponseBuilderSetVideoId(unittest.TestCase):

    def test_set_video_id_agrega_id(self):
        """set_video_id() debe agregar el ID del video"""
        result = APIResponseBuilder().set_video_id(5).build()
        self.assertEqual(result['video_id'], 5)

    def test_set_video_id_es_entero(self):
        """El video_id debe ser un entero"""
        result = APIResponseBuilder().set_video_id(42).build()
        self.assertIsInstance(result['video_id'], int)

    def test_set_video_id_retorna_builder(self):
        """set_video_id() debe retornar el mismo Builder para encadenar"""
        builder = APIResponseBuilder()
        result = builder.set_video_id(1)
        self.assertIsInstance(result, APIResponseBuilder)


# ─── PRUEBAS set_subscription ─────────────────────────────────────────────────

class TestAPIResponseBuilderSetSubscription(unittest.TestCase):

    def test_set_subscription_free(self):
        """set_subscription() debe agregar plan free"""
        result = APIResponseBuilder().set_subscription('free').build()
        self.assertEqual(result['subscription'], 'free')

    def test_set_subscription_premium(self):
        """set_subscription() debe agregar plan premium"""
        result = APIResponseBuilder().set_subscription('premium').build()
        self.assertEqual(result['subscription'], 'premium')

    def test_set_subscription_retorna_builder(self):
        """set_subscription() debe retornar el mismo Builder para encadenar"""
        builder = APIResponseBuilder()
        result = builder.set_subscription('free')
        self.assertIsInstance(result, APIResponseBuilder)


# ─── PRUEBAS set_videos ───────────────────────────────────────────────────────

class TestAPIResponseBuilderSetVideos(unittest.TestCase):

    def test_set_videos_agrega_lista(self):
        """set_videos() debe agregar la lista de videos"""
        videos = [{'id': 1, 'title': 'Video 1'}, {'id': 2, 'title': 'Video 2'}]
        result = APIResponseBuilder().set_videos(videos).build()
        self.assertEqual(result['videos'], videos)

    def test_set_videos_lista_vacia(self):
        """set_videos() debe soportar lista vacía"""
        result = APIResponseBuilder().set_videos([]).build()
        self.assertEqual(result['videos'], [])

    def test_set_videos_retorna_builder(self):
        """set_videos() debe retornar el mismo Builder para encadenar"""
        builder = APIResponseBuilder()
        result = builder.set_videos([])
        self.assertIsInstance(result, APIResponseBuilder)


# ─── PRUEBAS DE ENCADENAMIENTO ────────────────────────────────────────────────

class TestAPIResponseBuilderEncadenamiento(unittest.TestCase):

    def test_encadenamiento_register(self):
        """Simula la respuesta de /api/register"""
        result = (APIResponseBuilder()
                  .set_success(True)
                  .set_redirect('/')
                  .build())
        self.assertTrue(result['success'])
        self.assertEqual(result['redirect'], '/')

    def test_encadenamiento_login(self):
        """Simula la respuesta de /api/login"""
        result = (APIResponseBuilder()
                  .set_success(True)
                  .set_redirect('/')
                  .build())
        self.assertTrue(result['success'])
        self.assertIn('redirect', result)

    def test_encadenamiento_upload(self):
        """Simula la respuesta de /api/upload"""
        result = (APIResponseBuilder()
                  .set_success(True)
                  .set_video_id(10)
                  .build())
        self.assertTrue(result['success'])
        self.assertEqual(result['video_id'], 10)

    def test_encadenamiento_upgrade(self):
        """Simula la respuesta de /api/upgrade"""
        result = (APIResponseBuilder()
                  .set_success(True)
                  .set_subscription('premium')
                  .build())
        self.assertTrue(result['success'])
        self.assertEqual(result['subscription'], 'premium')

    def test_encadenamiento_seed(self):
        """Simula la respuesta de /api/seed"""
        result = (APIResponseBuilder()
                  .set_success(True)
                  .set_message('Seeded!')
                  .build())
        self.assertTrue(result['success'])
        self.assertEqual(result['message'], 'Seeded!')

    def test_encadenamiento_error_register(self):
        """Simula un error de validación en /api/register"""
        result = (APIResponseBuilder()
                  .set_error('El email ya está registrado')
                  .build())
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'El email ya está registrado')

    def test_encadenamiento_error_login(self):
        """Simula credenciales incorrectas en /api/login"""
        result = (APIResponseBuilder()
                  .set_error('Credenciales incorrectas')
                  .build())
        self.assertFalse(result['success'])
        self.assertIn('error', result)

    def test_encadenamiento_error_no_autorizado(self):
        """Simula error de autorización en /api/video DELETE y PUT"""
        result = (APIResponseBuilder()
                  .set_error('No autorizado')
                  .build())
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'No autorizado')

    def test_solo_contiene_campos_agregados(self):
        """El Builder solo incluye los campos que se agregaron"""
        result = (APIResponseBuilder()
                  .set_success(True)
                  .build())
        self.assertIn('success', result)
        self.assertNotIn('error', result)
        self.assertNotIn('redirect', result)
        self.assertNotIn('video_id', result)
        self.assertNotIn('subscription', result)


# ─── EJECUTAR ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    unittest.main(verbosity=2)
