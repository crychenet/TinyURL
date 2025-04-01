# Демонстрация работы api
## Хостинг на сервере
![image](https://github.com/user-attachments/assets/a653a56a-329c-4da3-abc6-898b8fe0a076)

## Swagger UI
![image](https://github.com/user-attachments/assets/bc5f28a5-981d-437a-a842-bbe705908612)
![image](https://github.com/user-attachments/assets/0beca6cd-8300-4b0b-8441-bb44e4c286cc)

## Демонстрация работы из Docker
![Скриншот 01-04-2025 180116](https://github.com/user-attachments/assets/f8772d21-6dd7-4237-9099-37ba34232890)  
![Скриншот 01-04-2025 175417](https://github.com/user-attachments/assets/05fcbe92-186e-4d53-a671-f2ba0dcb49c6)  
![Скриншот 01-04-2025 175440](https://github.com/user-attachments/assets/63765b19-07f8-4293-b968-aafc6a09c72b)  
![Скриншот 01-04-2025 175740](https://github.com/user-attachments/assets/c72d27e9-8483-4dd3-a077-7c5befcc27e7)  
![Скриншот 01-04-2025 175815](https://github.com/user-attachments/assets/21add5c7-e82a-4534-b389-b783a7f76153)  
![Скриншот 01-04-2025 175923](https://github.com/user-attachments/assets/9c98d568-d2a7-427b-8e13-90b05ad341e3)  
![Скриншот 01-04-2025 180014](https://github.com/user-attachments/assets/c374b18c-baae-4cef-a77b-432cb06a0e86)  
![Скриншот 01-04-2025 180035](https://github.com/user-attachments/assets/61a2f504-cccd-4427-97c3-6d4f3c382004)  


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
