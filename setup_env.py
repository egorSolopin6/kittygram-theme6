"""Create local secrets using only the Python standard library; keep existing .env."""
from pathlib import Path
import os
import secrets


def main():
    path = Path(__file__).resolve().parent / '.env'
    content = (
        f'DJANGO_SECRET_KEY={secrets.token_urlsafe(48)}\n'
        'DJANGO_DEBUG=True\n'
        'DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,[::1]\n'
        f'DEMO_PASSWORD={secrets.token_urlsafe(18)}\n'
        'LOAD_DEMO_DATA=true\n'
        'PORT=8000\n'
    )
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        print('Файл .env уже существует; значения сохранены.')
        return
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        stream.write(content)
    print('Создан .env. Пароль демонстрационных пользователей: DEMO_PASSWORD в этом файле.')


if __name__ == '__main__':
    main()
