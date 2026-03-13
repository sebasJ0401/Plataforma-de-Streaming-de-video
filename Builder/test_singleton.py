import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from patterns import DatabaseConfig


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


# ─── EJECUTAR ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    unittest.main(verbosity=2)
