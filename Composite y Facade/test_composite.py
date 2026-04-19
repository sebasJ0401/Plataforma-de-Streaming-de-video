import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from patterns import (
    CatalogComponent,
    VideoLeaf,
    CategoryNode,
)


# ─── PRUEBAS VIDEO LEAF (nodo hoja) ──────────────────────────────────────────

class TestVideoLeaf(unittest.TestCase):

    def setUp(self):
        self.video         = VideoLeaf(1, 'Python avanzado', 500, is_premium=False)
        self.video_premium = VideoLeaf(2, 'Django premium',  300, is_premium=True)

    def test_es_instancia_de_catalog_component(self):
        """VideoLeaf debe implementar CatalogComponent"""
        self.assertIsInstance(self.video, CatalogComponent)

    def test_get_name_retorna_titulo(self):
        """get_name() debe retornar el título del video"""
        self.assertEqual(self.video.get_name(), 'Python avanzado')

    def test_get_total_views_retorna_vistas(self):
        """get_total_views() debe retornar las vistas del video"""
        self.assertEqual(self.video.get_total_views(), 500)

    def test_get_video_count_es_uno(self):
        """get_video_count() de una hoja siempre debe ser 1"""
        self.assertEqual(self.video.get_video_count(), 1)

    def test_get_info_contiene_titulo(self):
        """get_info() debe contener el título del video"""
        info = self.video.get_info()
        self.assertIn('Python avanzado', info)

    def test_get_info_contiene_vistas(self):
        """get_info() debe contener el número de vistas"""
        info = self.video.get_info()
        self.assertIn('500', info)

    def test_get_info_premium_contiene_etiqueta(self):
        """get_info() de video premium debe indicar que es premium"""
        info = self.video_premium.get_info()
        self.assertIn('PREMIUM', info.upper())

    def test_get_info_gratuito_no_contiene_etiqueta_premium(self):
        """get_info() de video gratuito no debe indicar premium"""
        info = self.video.get_info()
        self.assertNotIn('PREMIUM', info.upper())

    def test_get_info_retorna_string(self):
        """get_info() debe retornar una cadena de texto"""
        self.assertIsInstance(self.video.get_info(), str)


# ─── PRUEBAS CATEGORY NODE (nodo compuesto) ───────────────────────────────────

class TestCategoryNodeVacio(unittest.TestCase):

    def setUp(self):
        self.categoria = CategoryNode('Tecnología')

    def test_es_instancia_de_catalog_component(self):
        """CategoryNode debe implementar CatalogComponent"""
        self.assertIsInstance(self.categoria, CatalogComponent)

    def test_get_name_retorna_nombre(self):
        """get_name() debe retornar el nombre de la categoría"""
        self.assertEqual(self.categoria.get_name(), 'Tecnología')

    def test_get_total_views_vacio_es_cero(self):
        """Una categoría vacía debe tener 0 vistas"""
        self.assertEqual(self.categoria.get_total_views(), 0)

    def test_get_video_count_vacio_es_cero(self):
        """Una categoría vacía debe tener 0 videos"""
        self.assertEqual(self.categoria.get_video_count(), 0)

    def test_get_info_contiene_nombre(self):
        """get_info() debe contener el nombre de la categoría"""
        info = self.categoria.get_info()
        self.assertIn('Tecnología', info)


class TestCategoryNodeConHijos(unittest.TestCase):

    def setUp(self):
        self.categoria = CategoryNode('Tecnología')
        self.video1    = VideoLeaf(1, 'Python', 500)
        self.video2    = VideoLeaf(2, 'Django', 300)
        self.categoria.add(self.video1)
        self.categoria.add(self.video2)

    def test_get_video_count_suma_hijos(self):
        """get_video_count() debe sumar todos los videos hijos"""
        self.assertEqual(self.categoria.get_video_count(), 2)

    def test_get_total_views_suma_hijos(self):
        """get_total_views() debe sumar las vistas de todos los hijos"""
        self.assertEqual(self.categoria.get_total_views(), 800)

    def test_get_info_contiene_hijos(self):
        """get_info() debe mostrar los videos hijos"""
        info = self.categoria.get_info()
        self.assertIn('Python', info)
        self.assertIn('Django', info)

    def test_get_info_contiene_total_videos(self):
        """get_info() debe indicar la cantidad total de videos"""
        info = self.categoria.get_info()
        self.assertIn('2', info)

    def test_get_info_contiene_total_vistas(self):
        """get_info() debe indicar el total de vistas"""
        info = self.categoria.get_info()
        self.assertIn('800', info)

    def test_remove_elimina_hijo(self):
        """remove() debe eliminar un video de la categoría"""
        self.categoria.remove(self.video1)
        self.assertEqual(self.categoria.get_video_count(), 1)

    def test_remove_actualiza_vistas(self):
        """Tras remove() las vistas deben recalcularse"""
        self.categoria.remove(self.video1)
        self.assertEqual(self.categoria.get_total_views(), 300)


# ─── PRUEBAS COMPOSITE RECURSIVO (árbol de varios niveles) ───────────────────

class TestCompositeRecursivo(unittest.TestCase):

    def setUp(self):
        """
        Construye este árbol:
        Catálogo
        ├── Tecnología  (2 videos, 800 vistas)
        │   ├── Python   (500 vistas)
        │   └── Django   (300 vistas)
        └── Deportes    (2 videos, 1000 vistas)
            ├── Fútbol   (800 vistas)
            └── Yoga     (200 vistas)
        """
        self.root       = CategoryNode('Catálogo')
        self.tecnologia = CategoryNode('Tecnología')
        self.deportes   = CategoryNode('Deportes')

        self.tecnologia.add(VideoLeaf(1, 'Python', 500))
        self.tecnologia.add(VideoLeaf(2, 'Django', 300))
        self.deportes.add(VideoLeaf(3, 'Fútbol', 800))
        self.deportes.add(VideoLeaf(4, 'Yoga',   200))

        self.root.add(self.tecnologia)
        self.root.add(self.deportes)

    def test_raiz_cuenta_todos_los_videos(self):
        """La raíz debe contar todos los videos del árbol"""
        self.assertEqual(self.root.get_video_count(), 4)

    def test_raiz_suma_todas_las_vistas(self):
        """La raíz debe sumar todas las vistas del árbol"""
        self.assertEqual(self.root.get_total_views(), 1800)

    def test_categoria_cuenta_solo_sus_videos(self):
        """Cada categoría debe contar solo sus propios videos"""
        self.assertEqual(self.tecnologia.get_video_count(), 2)
        self.assertEqual(self.deportes.get_video_count(),   2)

    def test_categoria_suma_solo_sus_vistas(self):
        """Cada categoría debe sumar solo sus propias vistas"""
        self.assertEqual(self.tecnologia.get_total_views(), 800)
        self.assertEqual(self.deportes.get_total_views(),   1000)

    def test_get_info_raiz_contiene_todas_categorias(self):
        """get_info() de la raíz debe mostrar todas las categorías"""
        info = self.root.get_info()
        self.assertIn('Tecnología', info)
        self.assertIn('Deportes', info)

    def test_get_info_raiz_contiene_todos_los_videos(self):
        """get_info() de la raíz debe mostrar todos los videos"""
        info = self.root.get_info()
        self.assertIn('Python', info)
        self.assertIn('Django', info)
        self.assertIn('Fútbol', info)
        self.assertIn('Yoga',   info)

    def test_interfaz_uniforme_video_y_categoria(self):
        """VideoLeaf y CategoryNode deben responder a los mismos métodos"""
        componentes = [
            self.tecnologia,
            VideoLeaf(99, 'Test', 100)
        ]
        for comp in componentes:
            self.assertTrue(hasattr(comp, 'get_name'))
            self.assertTrue(hasattr(comp, 'get_total_views'))
            self.assertTrue(hasattr(comp, 'get_video_count'))
            self.assertTrue(hasattr(comp, 'get_info'))

    def test_agregar_categoria_a_raiz_actualiza_conteo(self):
        """Agregar una nueva categoría debe actualizar el conteo total"""
        nueva = CategoryNode('Música')
        nueva.add(VideoLeaf(5, 'Jazz', 150))
        self.root.add(nueva)
        self.assertEqual(self.root.get_video_count(), 5)
        self.assertEqual(self.root.get_total_views(), 1950)

    def test_get_info_retorna_string(self):
        """get_info() siempre debe retornar una cadena"""
        self.assertIsInstance(self.root.get_info(), str)

    def test_indentacion_aumenta_por_nivel(self):
        """get_info() con indent=1 debe tener más espacios que indent=0"""
        info_0 = self.tecnologia.get_info(indent=0)
        info_1 = self.tecnologia.get_info(indent=1)
        self.assertGreater(len(info_1), len(info_0))


# ─── EJECUTAR ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    unittest.main(verbosity=2)
