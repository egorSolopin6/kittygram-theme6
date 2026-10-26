#!/bin/sh
set -eu
cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:/usr/local/bin:/Applications/Docker.app/Contents/Resources/bin:$PATH"
if ! docker --context desktop-linux info >/dev/null 2>&1; then
    echo 'Сначала запустите Docker Desktop и дождитесь Engine running.'
    exit 1
fi
python3 setup_env.py
docker --context desktop-linux compose up -d --build --wait
echo 'Kittygram запущен: http://localhost:8000/admin/ (порт PORT можно изменить в .env)'
