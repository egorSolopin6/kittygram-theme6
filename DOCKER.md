# Запуск в Docker Desktop

## Новая копия проекта

Запустите Docker Desktop (в Windows выберите Linux containers), откройте терминал
в папке проекта и выполните:

```sh
python3 setup_env.py
docker compose up -d --build --wait
```

Windows: `py setup_env.py`. Альтернатива без Python: скопировать `.env.example`
в `.env` и вручную задать случайные `DJANGO_SECRET_KEY` и `DEMO_PASSWORD`.
`setup_env.py` не перезаписывает существующий `.env` и не выводит секреты в терминал.
Если порт занят, измените `PORT=8000` на другой свободный порт, например `8001`.
Все адреса ниже указаны для порта 8000.

На Mac с ранее установленной Colima сначала выполните:

```sh
docker context use desktop-linux
```

`docker info --format '{{.OperatingSystem}}'` должен показать `Docker Desktop`.
Colima для запуска этого проекта не требуется.

## Как устроен запуск

`compose.yaml` создаёт проект **kittygram**, контейнер **kittygram-web-1**,
образ **kittygram-web:local** и постоянный том **kittygram_data**.
Порт доступен на `127.0.0.1`. В Docker Desktop проект отображается в **Containers**.
Раскройте его и нажмите ссылку порта 8000 — откроется админ-панель.

При каждом запуске применяются миграции и создаются недостающие группы доступа.
При первом запуске с `LOAD_DEMO_DATA=true` добавляются демонстрационные пользователи,
коты и голоса. Файл `/data/.demo_initialized` предотвращает повторное наполнение
при перезапуске и сохраняет последующие изменения ролей пользователей.
Пароли существующих аккаунтов не меняются.

Для базы без демонстрационных записей до первого старта задайте
`LOAD_DEMO_DATA=false`, затем создайте администратора:

```sh
docker compose exec web python manage.py createsuperuser
```

Повторное ручное наполнение доступно командой ниже. Она назначает демопользователям
стандартные роли, добавляет недостающую историю за последние семь дат и пересчитывает
баллы, не удаляя существующие записи:

```sh
docker compose exec web python manage.py seed_showcase
```

## Управление

```sh
docker compose ps
docker compose logs --tail=100 web
docker compose stop
docker compose up -d --wait
```

В Docker Desktop используйте кнопки Stop и Start у проекта kittygram.
`docker compose down` удаляет контейнер и сеть с сохранением базы.
`docker compose down -v` удаляет также базу — для обычной остановки используйте `stop`.

## Резервная копия и перенос

Перед копированием остановите приложение, чтобы получить согласованную SQLite-базу:

```sh
docker compose stop
docker compose cp web:/data/db.sqlite3 ./kittygram-backup.sqlite3
```

Восстановление в уже созданный контейнер с остановленным приложением:

```sh
docker compose cp ./kittygram-backup.sqlite3 web:/data/db.sqlite3
docker compose run --rm --user root --entrypoint sh web -c 'chown 10001:10001 /data/db.sqlite3'
docker compose up -d --wait
```

Сохраните `.env` отдельно, если переносите уже созданные аккаунты: значение
`DEMO_PASSWORD` должно соответствовать их исходному паролю. Само изменение
этой переменной не меняет пароли пользователей в базе.

На текущем Mac прежняя база из Colima перенесена в Docker Desktop.
Исходный остановленный контейнер и том Colima сохранены.

## Проверки

```sh
docker compose exec web python manage.py check
docker compose exec web python manage.py makemigrations --check --dry-run
docker compose exec web python manage.py test showcase --verbosity 2
```

Конфигурация предназначена для локального учебного запуска: Django runserver,
SQLite и публикация порта только на localhost.
