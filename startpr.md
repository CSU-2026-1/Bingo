# Запуск Bingo

1. Установить Docker Desktop.

2. Открыть терминал в корне проекта: cd D:\Programs\Fork\Bingo


3. Проверить, что есть файлик `.env`. Пример в проекте есть.

4. Запустить все контейнеры: docker compose up --build (либо через docker-compose.yml)

5. Дождаться запуска PostgreSQL, Redis, RabbitMQ и backend-сервисов.

6. Открыть фронт в браузере: http://localhost:8080

7. Для остановки проекта нажать `Ctrl+C` в терминале.
