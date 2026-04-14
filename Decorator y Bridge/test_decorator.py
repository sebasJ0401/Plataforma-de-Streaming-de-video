import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from patterns import (
    BaseVideoQuery,
    CategoryFilterDecorator,
    SearchFilterDecorator,
    PremiumFilterDecorator,
    PopularFilterDecorator,
    VideoQuery,
    VideoQueryDecorator,
)


# ─── MOCK DE VIDEO ────────────────────────────────────────────────────────────
# Simula objetos Video sin necesitar Flask ni base de datos

class MockVideo:
    def __init__(self, id, title, category, is_premium=False, views=0):
        self.id         = id
        self.title      = title
        self.category   = category
        self.is_premium = is_premium
        self.views      = views

    def __repr__(self):
        return f'<Video {self.id}: {self.title}>'


# ─── CONSULTA BASE MOCK ───────────────────────────────────────────────────────
# Reemplaza BaseVideoQuery para no necesitar la BD

class MockBaseQuery(VideoQuery):
    """Consulta base de prueba que devuelve una lista fija de videos mock."""
    def __init__(self, videos):
        self._videos = videos

    def execute(self) -> list:
        return list(self._videos)


# ─── DATOS DE PRUEBA ──────────────────────────────────────────────────────────

def get_videos():
    return [
        MockVideo(1, 'Python para principiantes', 'Tecnología',  is_premium=False, views=500),
        MockVideo(2, 'Django avanzado',            'Tecnología',  is_premium=True,  views=300),
        MockVideo(3, 'Fútbol resumen',             'Deportes',    is_premium=False, views=800),
        MockVideo(4, 'Yoga premium',               'Deportes',    is_premium=True,  views=200),
        MockVideo(5, 'Cocina italiana',            'Gastronomía', is_premium=False, views=100),
        MockVideo(6, 'Recetas premium',            'Gastronomía', is_premium=True,  views=150),
    ]


# ─── PRUEBAS BASE VIDEO QUERY ─────────────────────────────────────────────────

class TestMockBaseQuery(unittest.TestCase):

    def test_devuelve_todos_los_videos(self):
        """La consulta base debe devolver todos los videos"""
        query = MockBaseQuery(get_videos())
        result = query.execute()
        self.assertEqual(len(result), 6)

    def test_devuelve_lista(self):
        """execute() debe retornar una lista"""
        query = MockBaseQuery(get_videos())
        result = query.execute()
        self.assertIsInstance(result, list)

    def test_lista_vacia(self):
        """Debe manejar correctamente una lista vacía"""
        query = MockBaseQuery([])
        result = query.execute()
        self.assertEqual(result, [])


# ─── PRUEBAS CATEGORY FILTER DECORATOR ───────────────────────────────────────

class TestCategoryFilterDecorator(unittest.TestCase):

    def test_filtra_por_categoria_tecnologia(self):
        """Debe devolver solo videos de Tecnología"""
        query = CategoryFilterDecorator(MockBaseQuery(get_videos()), 'Tecnología')
        result = query.execute()
        self.assertEqual(len(result), 2)
        for v in result:
            self.assertEqual(v.category, 'Tecnología')

    def test_filtra_por_categoria_deportes(self):
        """Debe devolver solo videos de Deportes"""
        query = CategoryFilterDecorator(MockBaseQuery(get_videos()), 'Deportes')
        result = query.execute()
        self.assertEqual(len(result), 2)
        for v in result:
            self.assertEqual(v.category, 'Deportes')

    def test_categoria_vacia_no_filtra(self):
        """Con categoría vacía debe devolver todos los videos"""
        query = CategoryFilterDecorator(MockBaseQuery(get_videos()), '')
        result = query.execute()
        self.assertEqual(len(result), 6)

    def test_categoria_inexistente_devuelve_vacio(self):
        """Una categoría que no existe debe devolver lista vacía"""
        query = CategoryFilterDecorator(MockBaseQuery(get_videos()), 'Música')
        result = query.execute()
        self.assertEqual(len(result), 0)

    def test_retorna_lista(self):
        """execute() debe retornar una lista"""
        query = CategoryFilterDecorator(MockBaseQuery(get_videos()), 'Deportes')
        self.assertIsInstance(query.execute(), list)


# ─── PRUEBAS SEARCH FILTER DECORATOR ─────────────────────────────────────────

class TestSearchFilterDecorator(unittest.TestCase):

    def test_busca_por_texto_exacto(self):
        """Debe encontrar videos que contengan el texto buscado"""
        query = SearchFilterDecorator(MockBaseQuery(get_videos()), 'Python')
        result = query.execute()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].title, 'Python para principiantes')

    def test_busca_sin_importar_mayusculas(self):
        """La búsqueda no debe distinguir mayúsculas de minúsculas"""
        query = SearchFilterDecorator(MockBaseQuery(get_videos()), 'python')
        result = query.execute()
        self.assertEqual(len(result), 1)

    def test_busca_texto_parcial(self):
        """Debe encontrar videos que contengan parte del texto"""
        query = SearchFilterDecorator(MockBaseQuery(get_videos()), 'premium')
        result = query.execute()
        self.assertEqual(len(result), 2)

    def test_busqueda_vacia_no_filtra(self):
        """Con búsqueda vacía debe devolver todos los videos"""
        query = SearchFilterDecorator(MockBaseQuery(get_videos()), '')
        result = query.execute()
        self.assertEqual(len(result), 6)

    def test_busqueda_sin_resultados(self):
        """Un texto que no existe debe devolver lista vacía"""
        query = SearchFilterDecorator(MockBaseQuery(get_videos()), 'blockchain')
        result = query.execute()
        self.assertEqual(len(result), 0)


# ─── PRUEBAS PREMIUM FILTER DECORATOR ────────────────────────────────────────

class TestPremiumFilterDecorator(unittest.TestCase):

    def test_free_no_ve_premium(self):
        """Un usuario free no debe ver videos premium"""
        query = PremiumFilterDecorator(MockBaseQuery(get_videos()), 'free')
        result = query.execute()
        for v in result:
            self.assertFalse(v.is_premium)

    def test_free_solo_ve_gratuitos(self):
        """Un usuario free debe ver exactamente 3 videos gratuitos"""
        query = PremiumFilterDecorator(MockBaseQuery(get_videos()), 'free')
        result = query.execute()
        self.assertEqual(len(result), 3)

    def test_premium_ve_todo(self):
        """Un usuario premium debe ver todos los videos"""
        query = PremiumFilterDecorator(MockBaseQuery(get_videos()), 'premium')
        result = query.execute()
        self.assertEqual(len(result), 6)

    def test_admin_ve_todo(self):
        """Un usuario admin debe ver todos los videos"""
        query = PremiumFilterDecorator(MockBaseQuery(get_videos()), 'admin')
        result = query.execute()
        self.assertEqual(len(result), 6)


# ─── PRUEBAS POPULAR FILTER DECORATOR ────────────────────────────────────────

class TestPopularFilterDecorator(unittest.TestCase):

    def test_ordena_por_vistas_descendente(self):
        """Los videos deben quedar ordenados de mayor a menor vistas"""
        query = PopularFilterDecorator(MockBaseQuery(get_videos()))
        result = query.execute()
        for i in range(len(result) - 1):
            self.assertGreaterEqual(result[i].views, result[i + 1].views)

    def test_el_mas_popular_es_primero(self):
        """El video con más vistas debe ser el primero"""
        query = PopularFilterDecorator(MockBaseQuery(get_videos()))
        result = query.execute()
        self.assertEqual(result[0].views, 800)

    def test_no_elimina_videos(self):
        """El filtro de popularidad no debe eliminar ningún video"""
        query = PopularFilterDecorator(MockBaseQuery(get_videos()))
        result = query.execute()
        self.assertEqual(len(result), 6)


# ─── PRUEBAS DE ENCADENAMIENTO ────────────────────────────────────────────────

class TestDecoratorEncadenamiento(unittest.TestCase):

    def test_categoria_y_busqueda(self):
        """Categoría + búsqueda deben aplicarse juntos"""
        query = MockBaseQuery(get_videos())
        query = CategoryFilterDecorator(query, 'Tecnología')
        query = SearchFilterDecorator(query, 'Django')
        result = query.execute()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].title, 'Django avanzado')

    def test_categoria_y_free(self):
        """Categoría + plan free deben filtrar premium"""
        query = MockBaseQuery(get_videos())
        query = CategoryFilterDecorator(query, 'Tecnología')
        query = PremiumFilterDecorator(query, 'free')
        result = query.execute()
        self.assertEqual(len(result), 1)
        self.assertFalse(result[0].is_premium)

    def test_todos_los_filtros_encadenados(self):
        """Todos los decoradores encadenados deben funcionar correctamente"""
        query = MockBaseQuery(get_videos())
        query = CategoryFilterDecorator(query, 'Deportes')
        query = PremiumFilterDecorator(query, 'free')
        query = PopularFilterDecorator(query)
        result = query.execute()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].title, 'Fútbol resumen')
        self.assertFalse(result[0].is_premium)

    def test_encadenamiento_no_modifica_original(self):
        """Encadenar decoradores no debe modificar la lista original"""
        videos = get_videos()
        base   = MockBaseQuery(videos)
        query  = CategoryFilterDecorator(base, 'Deportes')
        query.execute()
        self.assertEqual(len(base.execute()), 6)


# ─── EJECUTAR ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    unittest.main(verbosity=2)
