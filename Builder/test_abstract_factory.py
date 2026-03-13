import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from patterns import (
    get_subscription_factory,
    FreeSubscriptionFactory,
    PremiumSubscriptionFactory,
    FreeVideoPlayer,
    PremiumVideoPlayer,
    FreeContentAccess,
    PremiumContentAccess,
)


# ─── PRUEBAS SELECTOR DE FACTORY ─────────────────────────────────────────────

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


# ─── PRUEBAS FREE FACTORY ─────────────────────────────────────────────────────

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


# ─── PRUEBAS PREMIUM FACTORY ──────────────────────────────────────────────────

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
