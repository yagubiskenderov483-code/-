# 🛍️ LOLZ MARKET Bot

Telegram-бот маркетплейса с каталогом товаров, сделками и админ-панелью.

## 🚀 Установка

```bash
git clone https://github.com/yourusername/lolz-market-bot
cd lolz-market-bot
pip install -r requirements.txt
```

## ⚙️ Настройка

1. Скопируй `.env.example` в `.env`:
   ```bash
   cp .env.example .env
   ```
2. Заполни `.env` своими данными (токен бота, ID админа и т.д.)

## ▶️ Запуск

```bash
python bot.py
```

## 📦 Зависимости

```
aiogram>=3.0
python-dotenv
```

Установить:
```bash
pip install aiogram python-dotenv
```

## 📋 Команды

| Команда | Описание |
|---------|----------|
| `/start` | Запустить бота |
| `/admin` | Админ-панель |
| `/help` | Помощь |
| `/getchatid` | ID чата (для логов) |

## ⚠️ Важно

Никогда не публикуй `.env` файл с реальными токенами в публичный репозиторий!
