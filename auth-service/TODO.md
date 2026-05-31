# Auth Service TODO

## Суть сервиса

Сервис отвечает за регистрацию, вход пользователя в систему и выдачу JWT-токенов.

## Заметки

- Используется отдельная БД PostgreSQL `bingo_auth`.
- Остальные сервисы получают `auth_user_id` из JWT.
- `user-service` может обновлять username/email в `auth-service` через внутренний `PATCH /auth/internal/users/{user_id}` с `X-Internal-Service-Token`.
- Сейчас таблицы создаются автоматически при старте сервиса.
