from patterns import DatabaseConfig, UserFactory, VideoFactory

# ─── SINGLETON ────────────────────────────────────────
print('=' * 40)
print('SINGLETON - Variante Enum')
print('=' * 40)

uri1 = DatabaseConfig.get_uri()
uri2 = DatabaseConfig.get_uri()

print(f'URI obtenida:        {uri1}')
print(f'Segunda llamada:     {uri2}')
print(f'Es la misma?:        {uri1 == uri2}')
print(f'Misma instancia?:    {DatabaseConfig.INSTANCE is DatabaseConfig.INSTANCE}')

# ─── FACTORY ──────────────────────────────────────────
print()
print('=' * 40)
print('FACTORY - UserFactory')
print('=' * 40)

# Simulamos crear un usuario sin tocar la BD
import sys
sys.path.insert(0, '.')

# Solo mostramos que la clase existe y sus métodos
print(f'UserFactory.create:  {UserFactory.create}')
print(f'VideoFactory.create: {VideoFactory.create}')

print()
print('Patron Factory encapsula la creacion de:')
print('  - User  → UserFactory.create(username, email, password)')
print('  - Video → VideoFactory.create(title, category, uploader_id)')
print()
print('El app.py ya no crea User() ni Video() directamente.')
print('Toda la logica de construccion queda en patterns.py')
