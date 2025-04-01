# Демонстрация работы api
![Скриншот 01-04-2025 180116](https://github.com/user-attachments/assets/0ce24ad7-82b5-42d2-b248-08ba3fba3677)
![Скриншот 01-04-2025 175417](https://github.com/user-attachments/assets/8dec9d53-9f7e-4882-b0cc-5c60dfcc83c3)
![Скриншот 01-04-2025 175440](https://github.com/user-attachments/assets/4c77a909-0b00-45fe-87bb-9130cf2dc851)
![Скриншот 01-04-2025 175740](https://github.com/user-attachments/assets/4c7148b6-eb52-493a-8b73-d77af0ac2f13)
![Скриншот 01-04-2025 175815](https://github.com/user-attachments/assets/3b5c0479-c030-4953-82a5-8c62cda07aef)
![Скриншот 01-04-2025 175923](https://github.com/user-attachments/assets/dc710a7a-47a4-4bdf-98ac-5fa0507471b9)  
![Скриншот 01-04-2025 180014](https://github.com/user-attachments/assets/9eb30ddd-bf96-4e6f-8efb-ea946f650cbf)  
![Скриншот 01-04-2025 180035](https://github.com/user-attachments/assets/f4ea25eb-6b7f-44f4-930d-6caff43d87d1)  

# Инструкция по запуску TinyURL (bash-версия)

## 1. Клонируем репозиторий
git clone https://github.com/crychenet/TinyURL
cd TinyURL

## 2. Создаём .env файл с настройками (пример)
DATABASE_URL=sqlite+aiosqlite:///./tinyurl.db
SECRET_KEY=secret123
ACCESS_TOKEN_EXPIRE_MINUTES=30
REDIS_URL=redis://redis:6379/0
LINK_TTL_SECONDS=86400
STATS_TTL_SECONDS=900
STATS_SYNC_INTERVAL_SECONDS=600
LOG_DIR=logs

## 3. Собираем и запускаем контейнеры
docker-compose up --build


# Описание TinyURL API

API для сокращения ссылок с поддержкой авторизации, кэширования и импорта из CSV.

## Аутентификация

Аутентификация реализована через JWT.  
Для доступа к защищённым маршрутам необходимо передавать заголовок:

```
Authorization: Bearer <ваш_токен>
```

---

## Ссылки

### POST `/links/shorten`  
Создаёт новую короткую ссылку. Можно задать собственный alias и дату истечения.

**Тело запроса:**
```json
{
  "original_url": "https://example.com",
  "custom_alias": "myalias",       
  "expires_at": "2025-04-30T23:59:59Z"
}
```

**Ответ:**
```json
{
  "id": 1,
  "original_url": "https://example.com",
  "short_code": "myalias",
  "created_at": "2025-04-01T00:00:00Z",
  "expires_at": "2025-04-30T23:59:59Z"
}
```

---

### GET `/links/search`  
Ищет все короткие ссылки пользователя, созданные для указанного оригинального URL.

**Параметры запроса:**
```
original_url=https://example.com
```

**Ответ:**
```json
[
  {
    "id": 1,
    "original_url": "https://example.com",
    "short_code": "myalias",
    "created_at": "...",
    "expires_at": "..."
  }
]
```

---

### POST `/links/import_csv`  
Импортирует ссылки из CSV-файла. Формат CSV должен быть валидным.

**Тип запроса:** `multipart/form-data`  
**Поле:** `file`

**Ответ:**
```json
{
  "created": [],
  "errors": []
}
```

---

### GET `/links/{short_code}`  
Редирект на оригинальный URL по короткому коду.  
Если ссылка устарела — 410. Если не найдена — 404.

**Ответ:** HTTP 307 Redirect

---

### DELETE `/links/{short_code}`  
Удаляет ссылку, если она принадлежит текущему пользователю.

**Ответ:** HTTP 204 No Content

---

### PUT `/links/{short_code}`  
Обновляет оригинальный URL для существующей короткой ссылки пользователя.

**Тело запроса:**
```json
{
  "original_url": "https://new-url.com"
}
```

**Ответ:**
```json
{
  "id": 1,
  "original_url": "https://new-url.com",
  "short_code": "myalias"
}
```

---

### GET `/links/{short_code}/stats`  
Возвращает статистику по ссылке: число переходов и последнее использование.

**Ответ:**
```json
{
  "id": 1,
  "original_url": "...",
  "short_code": "...",
  "created_at": "...",
  "expires_at": "...",
  "redirect_count": 15,
  "last_used": "2025-04-01T18:00:00Z"
}
```

---

## Пользователи

### POST `/auth/register`  
Регистрирует нового пользователя.

**Тело запроса:**
```json
{
  "email": "user@example.com",
  "password": "string"
}
```

---

### POST `/auth/jwt/login`  
Аутентификация пользователя, возвращает JWT токен.

**Тело запроса:**
```json
{
  "username": "user@example.com",
  "password": "string"
}
```

**Ответ:**
```json
{
  "access_token": "<токен>",
  "token_type": "bearer"
}
```

### GET `/me`  
Возвращает информацию о текущем авторизованном пользователе.

**Ответ:**
```json
{
  "email": "user@example.com",
  "id": "uuid-пользователя"
}
```


# Описание БД

База данных содержит две основные таблицы: `user` и `links`, связанные отношением один-ко-многим.

## Таблица `user`

Хранит информацию о пользователях, включая поля от `fastapi-users`.

| Поле         | Тип данных | Описание                        |
|--------------|------------|---------------------------------|
| id           | UUID       | Уникальный идентификатор        |
| email        | String     | Email пользователя              |
| hashed_password | String | Хэш пароля                      |
| is_active    | Boolean    | Флаг активности аккаунта        |
| is_verified  | Boolean    | Подтверждён ли email            |
| is_superuser | Boolean    | Админские права                 |
| full_name    | String     | Полное имя (опционально)        |

## Таблица `links`

Хранит информацию о каждой короткой ссылке.

| Поле           | Тип данных | Описание                                      |
|----------------|------------|-----------------------------------------------|
| id             | Integer    | Уникальный ID                                 |
| original_url   | String     | Оригинальный URL                              |
| short_code     | String     | Уникальный короткий код                       |
| created_at     | DateTime   | Время создания                                |
| expires_at     | DateTime   | Время истечения ссылки (может быть null)     |
| redirect_count | Integer    | Количество переходов по ссылке                |
| last_used      | DateTime   | Время последнего использования                |
| user_id        | String     | Внешний ключ на таблицу `user`                |


## Инициализация базы данных

База инициализируется при запуске скрипта `init_db.py`
