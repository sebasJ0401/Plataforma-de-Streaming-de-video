import unittest
import sys
import os
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from patterns import (
    NotificationSender,
    ConsoleNotificationSender,
    EmailNotificationSender,
    PushNotificationSender,
    Notification,
    RegisterNotification,
    VideoUploadedNotification,
    UpgradeNotification,
)


# ─── SENDER MOCK ──────────────────────────────────────────────────────────────
# Captura los mensajes enviados sin imprimirlos en consola

class MockNotificationSender(NotificationSender):
    """Sender de prueba que guarda los mensajes en lugar de imprimirlos."""
    def __init__(self):
        self.sent = []

    def send(self, recipient: str, subject: str, body: str) -> None:
        self.sent.append({
            'recipient': recipient,
            'subject':   subject,
            'body':      body
        })

    def last(self) -> dict:
        """Devuelve el último mensaje enviado."""
        return self.sent[-1] if self.sent else None


# ─── PRUEBAS SENDERS ──────────────────────────────────────────────────────────

class TestConsoleNotificationSender(unittest.TestCase):

    def test_send_no_lanza_error(self):
        """send() no debe lanzar ninguna excepción"""
        sender = ConsoleNotificationSender()
        try:
            sender.send('usuario', 'Asunto', 'Cuerpo del mensaje')
        except Exception as e:
            self.fail(f'send() lanzó una excepción: {e}')

    def test_send_imprime_en_consola(self):
        """send() debe producir salida en consola"""
        sender = ConsoleNotificationSender()
        captured = StringIO()
        sys.stdout = captured
        sender.send('usuario', 'Asunto', 'Cuerpo')
        sys.stdout = sys.__stdout__
        self.assertGreater(len(captured.getvalue()), 0)

    def test_es_instancia_de_notification_sender(self):
        """ConsoleNotificationSender debe implementar NotificationSender"""
        sender = ConsoleNotificationSender()
        self.assertIsInstance(sender, NotificationSender)


class TestEmailNotificationSender(unittest.TestCase):

    def test_send_no_lanza_error(self):
        """send() no debe lanzar ninguna excepción"""
        sender = EmailNotificationSender()
        try:
            sender.send('usuario@test.com', 'Asunto', 'Cuerpo')
        except Exception as e:
            self.fail(f'send() lanzó una excepción: {e}')

    def test_es_instancia_de_notification_sender(self):
        """EmailNotificationSender debe implementar NotificationSender"""
        sender = EmailNotificationSender()
        self.assertIsInstance(sender, NotificationSender)


class TestPushNotificationSender(unittest.TestCase):

    def test_send_no_lanza_error(self):
        """send() no debe lanzar ninguna excepción"""
        sender = PushNotificationSender()
        try:
            sender.send('usuario', 'Asunto', 'Cuerpo')
        except Exception as e:
            self.fail(f'send() lanzó una excepción: {e}')

    def test_es_instancia_de_notification_sender(self):
        """PushNotificationSender debe implementar NotificationSender"""
        sender = PushNotificationSender()
        self.assertIsInstance(sender, NotificationSender)


# ─── PRUEBAS REGISTER NOTIFICATION ───────────────────────────────────────────

class TestRegisterNotification(unittest.TestCase):

    def setUp(self):
        self.sender = MockNotificationSender()
        self.notif  = RegisterNotification(self.sender)

    def test_notify_llama_send(self):
        """notify() debe llamar send() exactamente una vez"""
        self.notif.notify('sebastian')
        self.assertEqual(len(self.sender.sent), 1)

    def test_notify_destinatario_correcto(self):
        """El destinatario debe ser el username pasado"""
        self.notif.notify('sebastian')
        self.assertEqual(self.sender.last()['recipient'], 'sebastian')

    def test_notify_subject_correcto(self):
        """El asunto debe indicar bienvenida a StreamVault"""
        self.notif.notify('sebastian')
        self.assertIn('StreamVault', self.sender.last()['subject'])

    def test_notify_body_contiene_username(self):
        """El cuerpo debe mencionar al usuario"""
        self.notif.notify('sebastian')
        self.assertIn('sebastian', self.sender.last()['body'])

    def test_es_instancia_de_notification(self):
        """RegisterNotification debe ser instancia de Notification"""
        self.assertIsInstance(self.notif, Notification)


# ─── PRUEBAS VIDEO UPLOADED NOTIFICATION ─────────────────────────────────────

class TestVideoUploadedNotification(unittest.TestCase):

    def setUp(self):
        self.sender = MockNotificationSender()
        self.notif  = VideoUploadedNotification(self.sender, 'Python avanzado')

    def test_notify_llama_send(self):
        """notify() debe llamar send() exactamente una vez"""
        self.notif.notify('sebastian')
        self.assertEqual(len(self.sender.sent), 1)

    def test_notify_destinatario_correcto(self):
        """El destinatario debe ser el username pasado"""
        self.notif.notify('sebastian')
        self.assertEqual(self.sender.last()['recipient'], 'sebastian')

    def test_notify_body_contiene_titulo_video(self):
        """El cuerpo debe mencionar el título del video"""
        self.notif.notify('sebastian')
        self.assertIn('Python avanzado', self.sender.last()['body'])

    def test_notify_subject_correcto(self):
        """El asunto debe indicar que el video fue publicado"""
        self.notif.notify('sebastian')
        self.assertIn('publicado', self.sender.last()['subject'].lower())

    def test_es_instancia_de_notification(self):
        """VideoUploadedNotification debe ser instancia de Notification"""
        self.assertIsInstance(self.notif, Notification)


# ─── PRUEBAS UPGRADE NOTIFICATION ────────────────────────────────────────────

class TestUpgradeNotification(unittest.TestCase):

    def setUp(self):
        self.sender = MockNotificationSender()
        self.notif  = UpgradeNotification(self.sender, 'premium')

    def test_notify_llama_send(self):
        """notify() debe llamar send() exactamente una vez"""
        self.notif.notify('sebastian')
        self.assertEqual(len(self.sender.sent), 1)

    def test_notify_destinatario_correcto(self):
        """El destinatario debe ser el username pasado"""
        self.notif.notify('sebastian')
        self.assertEqual(self.sender.last()['recipient'], 'sebastian')

    def test_notify_body_contiene_plan(self):
        """El cuerpo debe mencionar el plan al que se actualizó"""
        self.notif.notify('sebastian')
        self.assertIn('premium', self.sender.last()['body'].lower())

    def test_notify_subject_correcto(self):
        """El asunto debe indicar que el plan fue actualizado"""
        self.notif.notify('sebastian')
        self.assertIn('actualizado', self.sender.last()['subject'].lower())

    def test_es_instancia_de_notification(self):
        """UpgradeNotification debe ser instancia de Notification"""
        self.assertIsInstance(self.notif, Notification)


# ─── PRUEBAS DEL BRIDGE (sender intercambiable) ───────────────────────────────

class TestBridgeSenderIntercambiable(unittest.TestCase):

    def test_misma_notificacion_distinto_sender(self):
        """La misma notificación debe funcionar con cualquier sender"""
        senders = [
            MockNotificationSender(),
            MockNotificationSender(),
            MockNotificationSender(),
        ]
        notifs = [
            RegisterNotification(senders[0]),
            RegisterNotification(senders[1]),
            RegisterNotification(senders[2]),
        ]
        for i, notif in enumerate(notifs):
            notif.notify('usuario')
            self.assertEqual(len(senders[i].sent), 1)

    def test_mismo_sender_distintas_notificaciones(self):
        """El mismo sender debe poder usarse en distintas notificaciones"""
        sender = MockNotificationSender()
        RegisterNotification(sender).notify('usuario1')
        VideoUploadedNotification(sender, 'Video test').notify('usuario2')
        UpgradeNotification(sender, 'premium').notify('usuario3')
        self.assertEqual(len(sender.sent), 3)

    def test_cambiar_sender_no_modifica_notificacion(self):
        """Cambiar el sender no debe afectar el contenido de la notificación"""
        sender1 = MockNotificationSender()
        sender2 = MockNotificationSender()
        RegisterNotification(sender1).notify('sebastian')
        RegisterNotification(sender2).notify('sebastian')
        self.assertEqual(
            sender1.last()['subject'],
            sender2.last()['subject']
        )

    def test_registro_con_tres_canales_mismo_contenido(self):
        """La misma notificación con distintos canales debe tener el mismo asunto"""
        senders = [MockNotificationSender() for _ in range(3)]
        for s in senders:
            RegisterNotification(s).notify('usuario')
        subjects = [s.last()['subject'] for s in senders]
        self.assertEqual(subjects[0], subjects[1])
        self.assertEqual(subjects[1], subjects[2])

    def test_notificacion_no_conoce_tipo_de_sender(self):
        """La notificación debe funcionar igual con cualquier tipo de sender"""
        for SenderClass in [ConsoleNotificationSender,
                            EmailNotificationSender,
                            PushNotificationSender]:
            try:
                notif = RegisterNotification(SenderClass())
                notif.notify('usuario')
            except Exception as e:
                self.fail(f'{SenderClass.__name__} falló: {e}')


# ─── EJECUTAR ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    unittest.main(verbosity=2)
