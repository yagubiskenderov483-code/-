import asyncio
import random
import string
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import os
from dotenv import load_dotenv

load_dotenv()

# ============ КОНФИГУРАЦИЯ (из .env) ============
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
MANAGER_USERNAME = os.getenv("MANAGER_USERNAME", "YourManagerUsername")
MANAGER_CARD = os.getenv("MANAGER_CARD", "Укажи реквизиты")
TON_WALLET = os.getenv("TON_WALLET", "")
USDT_WALLET = os.getenv("USDT_WALLET", "")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "YourSupportUsername")
SITE_LINK = os.getenv("SITE_LINK", "https://example.com")
BOT_USERNAME = os.getenv("BOT_USERNAME", "YourBotUsername")
BANNER_PATH = os.getenv("BANNER_PATH", "banner.jpg")
LOG_CHAT_ID = None  # Будет заполнено админом

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан! Создай .env файл на основе .env.example")

storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

class DealStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_link = State()
    waiting_for_description = State()

users = {}
products = {}
deals = {}
purchases = {}
reviews_db = {}
user_language = {}
user_requisites = {}
moderation_queue = []
user_stats = {}
temp_deal_data = {}
user_states = {}

USER_STATUSES = {
    'new': {'name_ru': '🟢 Новичок', 'name_en': '🟢 Newbie', 'color': '🟢', 'emoji': '🆕'},
    'verified': {'name_ru': '✅ Проверенный', 'name_en': '✅ Verified', 'color': '✅', 'emoji': '⭐'},
    'suspicious': {'name_ru': '⚠️ Сомнительный', 'name_en': '⚠️ Suspicious', 'color': '⚠️', 'emoji': '❓'},
    'scammer': {'name_ru': '🔴 Мошенник', 'name_en': '🔴 Scammer', 'color': '🔴', 'emoji': '🚫'},
    'trusted': {'name_ru': '💎 Доверенный', 'name_en': '💎 Trusted', 'color': '💎', 'emoji': '👑'},
    'partner': {'name_ru': '🤝 Партнер', 'name_en': '🤝 Partner', 'color': '🤝', 'emoji': '💼'}
}

# ============ ЛОГИРОВАНИЕ ============
async def log_event(event_type: str, user_id: int, description: str):
    """Отправляет событие в чат логов"""
    global LOG_CHAT_ID
    if not LOG_CHAT_ID:
        return
    
    try:
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        
        emoji_map = {
            'join': '👤',
            'deal_created': '🤝',
            'deal_paid': '💰',
            'nft_transfer': '🎁',
            'product_added': '📦',
            'status_changed': '🚦',
            'review_left': '⭐',
            'requisites': '💳',
            'payment_confirmed': '✅',
            'payment_rejected': '❌'
        }
        
        emoji = emoji_map.get(event_type, '📝')
        message_text = f"{emoji} `[{timestamp}]` {description}"
        
        await bot.send_message(LOG_CHAT_ID, message_text, parse_mode="Markdown")
    except Exception as e:
        print(f"❌ Ошибка при отправке лога: {e}")

TOP_SELLERS = [
    {"name": "@a***n", "deals": 847, "rating": 4.9, "revenue": 12450},
    {"name": "@m***l", "deals": 832, "rating": 4.8, "revenue": 11800},
    {"name": "@s***a", "deals": 821, "rating": 4.9, "revenue": 15600},
    {"name": "@d***v", "deals": 815, "rating": 4.7, "revenue": 9800},
    {"name": "@k***y", "deals": 809, "rating": 4.8, "revenue": 14300},
    {"name": "@p***r", "deals": 798, "rating": 4.9, "revenue": 16700},
    {"name": "@v***n", "deals": 784, "rating": 4.8, "revenue": 11200},
    {"name": "@n***k", "deals": 776, "rating": 4.7, "revenue": 8900},
    {"name": "@t***a", "deals": 765, "rating": 4.9, "revenue": 17800},
    {"name": "@r***o", "deals": 752, "rating": 4.8, "revenue": 13400},
    {"name": "@e***v", "deals": 743, "rating": 4.7, "revenue": 9200},
    {"name": "@i***n", "deals": 738, "rating": 4.8, "revenue": 11500},
    {"name": "@g***l", "deals": 729, "rating": 4.9, "revenue": 18900},
    {"name": "@y***a", "deals": 715, "rating": 4.7, "revenue": 8700},
    {"name": "@u***m", "deals": 708, "rating": 4.8, "revenue": 12100},
    {"name": "@w***s", "deals": 694, "rating": 4.9, "revenue": 15600},
    {"name": "@o***t", "deals": 687, "rating": 4.7, "revenue": 7800},
    {"name": "@b***n", "deals": 675, "rating": 4.8, "revenue": 13200},
    {"name": "@h***r", "deals": 663, "rating": 4.9, "revenue": 14500},
    {"name": "@f***d", "deals": 652, "rating": 4.7, "revenue": 8900},
    {"name": "@c***p", "deals": 648, "rating": 4.8, "revenue": 11300},
    {"name": "@z***e", "deals": 634, "rating": 4.9, "revenue": 16700},
    {"name": "@x***y", "deals": 621, "rating": 4.7, "revenue": 7600},
    {"name": "@q***s", "deals": 615, "rating": 4.8, "revenue": 10200},
    {"name": "@l***k", "deals": 603, "rating": 4.9, "revenue": 18900},
    {"name": "@j***h", "deals": 598, "rating": 4.7, "revenue": 8400},
    {"name": "@w***g", "deals": 584, "rating": 4.8, "revenue": 9700},
    {"name": "@r***b", "deals": 572, "rating": 4.9, "revenue": 15600},
    {"name": "@t***m", "deals": 565, "rating": 4.7, "revenue": 6900},
    {"name": "@n***p", "deals": 553, "rating": 4.8, "revenue": 10800}
]

WELCOME_TEXT = """
🛍️ **LOLZ MARKET** — твой надежный маркетплейс!

✨ **Что мы предлагаем:**
• 🎮 Игровые аккаунты и предметы
• 💳 Цифровые товары и услуги
• 🎁 Telegram NFT и подарки
• 💎 Криптовалюта и кошельки
• 🔑 Лицензионные ключи
• 📱 Софт и программы
• 💼 Услуги фрилансеров

🔥 **Наши преимущества:**
✅ Безопасные сделки с гарантом
⭐ Рейтинг продавцов и отзывы
💳 Мгновенные выплаты
🤝 Поддержка 24/7
🔐 Конфиденциальность

📊 **Статистика:**
👥 Пользователей: {users}
📦 Товаров: {products}
🤝 Сделок: {deals}

Выбери действие в меню ниже 👇
"""

# ============ ТВОЙ ПОЛНЫЙ КАТАЛОГ ============
categories = [
    {
        "id": 0,
        "name": "🎮 Игры",
        "subcategories": [
            {
                "name": "Steam Аккаунты",
                "products": [
                    {"name": "Steam Аккаунт с CS2", "price": 2500, "desc": "Prime статус, медали, 1000+ часов, почта в подарок"},
                    {"name": "Steam Аккаунт с Dota 2", "price": 1800, "desc": "Арканы, много часов, высокий рейтинг, 10+ аркан"},
                    {"name": "Steam Аккаунт с 10 играми", "price": 3500, "desc": "Библиотека из 10 популярных игр (GTA, Rust, CS, Dota)"},
                    {"name": "Steam Аккаунт с GTA V", "price": 2200, "desc": "GTA V + онлайн, почта в подарок, есть достижения"},
                    {"name": "Steam Аккаунт с Rust", "price": 2000, "desc": "Rust, скины, много часов, 500+ часов"},
                    {"name": "Steam Аккаунт с PUBG", "price": 1900, "desc": "PUBG, скины, боевой пропуск"},
                    {"name": "Steam Аккаунт с 20 играми", "price": 5000, "desc": "Библиотека из 20 игр, коллекционные"},
                    {"name": "Steam Аккаунт с редкими играми", "price": 8000, "desc": "Удаленные из магазина игры"}
                ]
            },
            {
                "name": "Epic Games Аккаунты",
                "products": [
                    {"name": "Epic Games Аккаунт с GTA V", "price": 1800, "desc": "Аккаунт с GTA V, полный доступ, почта"},
                    {"name": "Epic Games Аккаунт с Fortnite", "price": 2000, "desc": "Много скинов, редкие предметы, battle pass"},
                    {"name": "Epic Games Аккаунт с Rocket League", "price": 1500, "desc": "Rocket League, много предметов, ранг"},
                    {"name": "Epic Games Аккаунт с 5 играми", "price": 2500, "desc": "5 популярных игр, включая GTA"},
                    {"name": "Epic Games Аккаунт с редкими скинами", "price": 5000, "desc": "Редкие скины Fortnite, 50+ скинов"},
                    {"name": "Epic Games Аккаунт с боевым пропуском", "price": 1200, "desc": "Активный боевой пропуск"}
                ]
            },
            {
                "name": "Battle.net Аккаунты",
                "products": [
                    {"name": "Battle.net Аккаунт с Overwatch 2", "price": 1600, "desc": "Полный доступ, кастомизация, скины"},
                    {"name": "Battle.net Аккаунт с Diablo 4", "price": 3000, "desc": "Аккаунт с Diablo 4, пройден сюжет"},
                    {"name": "Battle.net Аккаунт с WoW", "price": 2500, "desc": "World of Warcraft, высокий уровень, Dragonflight"},
                    {"name": "Battle.net Аккаунт с CoD", "price": 2000, "desc": "Call of Duty Modern Warfare 2"},
                    {"name": "Battle.net Аккаунт с Hearthstone", "price": 800, "desc": "Много карт, ранговый"},
                    {"name": "Battle.net Аккаунт с Diablo 3", "price": 1200, "desc": "Diablo 3, пройден сюжет, парагон"}
                ]
            },
            {
                "name": "Origin Аккаунты",
                "products": [
                    {"name": "Origin Аккаунт с FIFA 24", "price": 2200, "desc": "FIFA 24, режим карьеры, UT, много монет"},
                    {"name": "Origin Аккаунт с Sims 4", "price": 1400, "desc": "The Sims 4 со всеми дополнениями"},
                    {"name": "Origin Аккаунт с Battlefield", "price": 1200, "desc": "Battlefield 2042, полный доступ"},
                    {"name": "Origin Аккаунт с Apex Legends", "price": 1000, "desc": "Скины, боевой пропуск, легенды"},
                    {"name": "Origin Аккаунт с 3 играми", "price": 2500, "desc": "3 популярные игры на выбор"}
                ]
            },
            {
                "name": "Uplay Аккаунты",
                "products": [
                    {"name": "Uplay Аккаунт с Rainbow Six", "price": 1700, "desc": "Rainbow Six Siege, много оперативников"},
                    {"name": "Uplay Аккаунт с Watch Dogs", "price": 1300, "desc": "Watch Dogs Legion, полный доступ"},
                    {"name": "Uplay Аккаунт с Far Cry 6", "price": 1500, "desc": "Far Cry 6, прохождение, DLC"},
                    {"name": "Uplay Аккаунт с Assassin's Creed", "price": 1400, "desc": "Assassin's Creed Valhalla"},
                    {"name": "Uplay Аккаунт с 4 играми", "price": 3000, "desc": "4 игры из серии Far Cry/AC"}
                ]
            },
            {
                "name": "Minecraft Аккаунты",
                "products": [
                    {"name": "Minecraft Premium", "price": 1200, "desc": "Полный доступ, смена ника, почта"},
                    {"name": "Minecraft Java Edition", "price": 1500, "desc": "Java Edition, лицензия, полный доступ"},
                    {"name": "Minecraft Bedrock Edition", "price": 1300, "desc": "Для Windows 10/11, Xbox, мобилок"},
                    {"name": "Minecraft с Hypixel", "price": 2000, "desc": "Аккаунт с разбаном на Hypixel, много рангов"},
                    {"name": "Minecraft + Capes", "price": 3500, "desc": "С редкими плащами, миграция"},
                    {"name": "Minecraft с модами", "price": 1800, "desc": "Установлены популярные моды"}
                ]
            },
            {
                "name": "CS:GO / CS2",
                "products": [
                    {"name": "CS2 Prime Account", "price": 2000, "desc": "Prime статус, медали, старый аккаунт"},
                    {"name": "CS2 с ножом", "price": 8500, "desc": "Аккаунт с ножом и скинами, 10+ скинов"},
                    {"name": "CS2 с редкими скинами", "price": 15000, "desc": "Инвентарь на 30000+ ₽, нож, перчатки"},
                    {"name": "CS2 Глобал Элит", "price": 5000, "desc": "Аккаунт с высоким рангом, медали"},
                    {"name": "CS2 с оперативниками", "price": 3000, "desc": "Много оперативников и граффити, старый акк"},
                    {"name": "CS2 с фейсами", "price": 1800, "desc": "Задоначенные фейсы, медали"}
                ]
            },
            {
                "name": "Dota 2 Аккаунты",
                "products": [
                    {"name": "Dota 2 с арканами", "price": 3000, "desc": "Аккаунт с арканами, много часов, 5+ аркан"},
                    {"name": "Dota 2 высокий MMR", "price": 4000, "desc": "Аккаунт с высоким MMR (5000+), редкие предметы"},
                    {"name": "Dota 2 с компендиумом", "price": 2000, "desc": "Аккаунт с компендиумом, уровни"},
                    {"name": "Dota 2 с редкими сетами", "price": 3500, "desc": "Редкие сеты, дорогие предметы"},
                    {"name": "Dota 2 с имморталами", "price": 2500, "desc": "50+ имморталов, много сокровищниц"}
                ]
            },
            {
                "name": "Игровая валюта",
                "products": [
                    {"name": "V-Bucks 5000", "price": 3500, "desc": "5000 V-Bucks для Fortnite"},
                    {"name": "V-Bucks 10000", "price": 6500, "desc": "10000 V-Bucks"},
                    {"name": "RP 4000", "price": 2800, "desc": "4000 RP для League of Legends"},
                    {"name": "Steam Wallet 1000₽", "price": 950, "desc": "Пополнение Steam кошелька"},
                    {"name": "Steam Wallet 5000₽", "price": 4750, "desc": "Пополнение Steam кошелька"},
                    {"name": "Robux 1000", "price": 1200, "desc": "1000 Robux для Roblox"},
                    {"name": "Robux 5000", "price": 5500, "desc": "5000 Robux для Roblox"}
                ]
            },
            {
                "name": "Буст услуг",
                "products": [
                    {"name": "Буст MMR Dota 2", "price": 1500, "desc": "Поднятие MMR на 500"},
                    {"name": "Буст ранга CS:GO", "price": 1200, "desc": "Поднятие ранга"},
                    {"name": "Калибровка Dota 2", "price": 2000, "desc": "Калибровка аккаунта под ваш уровень"},
                    {"name": "Калибровка CS2", "price": 1800, "desc": "Калибровка под ваш ранг"}
                ]
            },
            {
                "name": "Ключи игр",
                "products": [
                    {"name": "Cyberpunk 2077 ключ", "price": 2800, "desc": "Лицензионный ключ Cyberpunk 2077"},
                    {"name": "Hogwarts Legacy ключ", "price": 3500, "desc": "Ключ Hogwarts Legacy"},
                    {"name": "Baldur's Gate 3 ключ", "price": 4000, "desc": "Ключ Baldur's Gate 3"},
                    {"name": "Starfield ключ", "price": 3800, "desc": "Ключ Starfield"},
                    {"name": "Diablo 4 ключ", "price": 4200, "desc": "Ключ Diablo 4"},
                    {"name": "Spider-Man 2 ключ", "price": 3500, "desc": "Ключ Spider-Man 2"}
                ]
            }
        ]
    },
    {
        "id": 1,
        "name": "💳 Аккаунты",
        "subcategories": [
            {
                "name": "Netflix Аккаунты",
                "products": [
                    {"name": "Netflix 4K 1 месяц", "price": 600, "desc": "4K качество, 4 экрана, на 1 месяц"},
                    {"name": "Netflix Premium 3 месяца", "price": 1500, "desc": "Premium подписка на 3 месяца"},
                    {"name": "Netflix семейный на год", "price": 4500, "desc": "Семейный аккаунт на 1 год, 4 профиля"},
                    {"name": "Netflix профиль", "price": 300, "desc": "Профиль в семейном аккаунте на месяц"},
                    {"name": "Netflix с историей", "price": 800, "desc": "Аккаунт с историей просмотров, рекомендации"}
                ]
            },
            {
                "name": "Spotify Аккаунты",
                "products": [
                    {"name": "Spotify Premium 1 месяц", "price": 400, "desc": "Premium подписка без рекламы"},
                    {"name": "Spotify Family 3 месяца", "price": 1500, "desc": "Семейная подписка на 3 месяца, 6 акков"},
                    {"name": "Spotify Premium 6 месяцев", "price": 2000, "desc": "Индивидуальная подписка на 6 месяцев"},
                    {"name": "Spotify Duo 6 месяцев", "price": 2500, "desc": "Для двоих на 6 месяцев"},
                    {"name": "Spotify с плейлистами", "price": 800, "desc": "Аккаунт с большими плейлистами"}
                ]
            },
            {
                "name": "Disney+ Аккаунты",
                "products": [
                    {"name": "Disney+ 1 месяц", "price": 600, "desc": "Доступ ко всем фильмам и сериалам"},
                    {"name": "Disney+ на год", "price": 5000, "desc": "Годовая подписка Disney+, экономия"},
                    {"name": "Disney+ Bundle", "price": 1200, "desc": "Disney+ Hulu ESPN, 1 месяц"},
                    {"name": "Disney+ семейный", "price": 4000, "desc": "Семейный аккаунт на год, 7 профилей"}
                ]
            },
            {
                "name": "ChatGPT Аккаунты",
                "products": [
                    {"name": "ChatGPT Plus 1 месяц", "price": 1500, "desc": "ChatGPT-4 доступ, быстрый ответ"},
                    {"name": "ChatGPT Plus 3 месяца", "price": 4000, "desc": "GPT-4, быстрый ответ, экономия"},
                    {"name": "ChatGPT API доступ", "price": 2500, "desc": "API ключ для разработчиков"},
                    {"name": "ChatGPT Team аккаунт", "price": 3000, "desc": "Командный аккаунт, общий доступ"},
                    {"name": "ChatGPT с историей", "price": 1200, "desc": "Аккаунт с историей диалогов"}
                ]
            },
            {
                "name": "Midjourney Аккаунты",
                "products": [
                    {"name": "Midjourney Basic", "price": 1500, "desc": "Базовый аккаунт Midjourney, 200 генераций"},
                    {"name": "Midjourney Pro", "price": 2500, "desc": "Pro аккаунт, быстрая генерация, безлимит"},
                    {"name": "Midjourney Mega", "price": 3500, "desc": "Mega аккаунт, безлимит, приоритет"},
                    {"name": "Midjourney с историей", "price": 2000, "desc": "Аккаунт с историей генераций"}
                ]
            },
            {
                "name": "Adobe Аккаунты",
                "products": [
                    {"name": "Adobe Creative Cloud", "price": 2500, "desc": "Весь пакет Adobe на месяц"},
                    {"name": "Adobe Photoshop", "price": 1200, "desc": "Photoshop на месяц, отдельно"},
                    {"name": "Adobe Premiere Pro", "price": 1500, "desc": "Premiere Pro на месяц"},
                    {"name": "Adobe After Effects", "price": 1500, "desc": "After Effects на месяц"},
                    {"name": "Adobe Illustrator", "price": 1200, "desc": "Illustrator на месяц"},
                    {"name": "Adobe All Apps год", "price": 18000, "desc": "Весь пакет Adobe на год"}
                ]
            },
            {
                "name": "Office 365 Аккаунты",
                "products": [
                    {"name": "Office 365 Personal", "price": 1500, "desc": "Личная подписка на год, 1 пользователь"},
                    {"name": "Office 365 Family", "price": 2500, "desc": "Семейная подписка на год, 6 пользователей"},
                    {"name": "Office 365 Business", "price": 3000, "desc": "Бизнес подписка, Exchange, Teams"},
                    {"name": "Office 2021 навсегда", "price": 2000, "desc": "Office 2021, бессрочная лицензия"}
                ]
            },
            {
                "name": "VPN Аккаунты",
                "products": [
                    {"name": "NordVPN 1 год", "price": 2500, "desc": "NordVPN подписка на год, 6 устройств"},
                    {"name": "ExpressVPN 6 месяцев", "price": 2000, "desc": "ExpressVPN на полгода, 5 устройств"},
                    {"name": "ProtonVPN Plus", "price": 1000, "desc": "ProtonVPN Plus на месяц, все серверы"},
                    {"name": "VPN Unlimited", "price": 1500, "desc": "Навсегда, 5 устройств, пожизненно"},
                    {"name": "Surfshark 2 года", "price": 3000, "desc": "Surfshark на 2 года, безлимит устройств"}
                ]
            },
            {
                "name": "Почтовые аккаунты",
                "products": [
                    {"name": "GMail аккаунт 2010", "price": 1000, "desc": "Старый GMail аккаунт, 2010 год"},
                    {"name": "Yahoo аккаунт", "price": 500, "desc": "Yahoo аккаунт с историей, 2015"},
                    {"name": "ProtonMail аккаунт", "price": 800, "desc": "Защищенная почта, шифрование"},
                    {"name": "Outlook аккаунт", "price": 400, "desc": "Аккаунт Outlook, чистый"},
                    {"name": "GMail аккаунт 2015", "price": 600, "desc": "Аккаунт 2015 года, с историей"}
                ]
            },
            {
                "name": "Социальные сети",
                "products": [
                    {"name": "Instagram аккаунт", "price": 600, "desc": "Аккаунт Instagram с подписчиками, 1000+"},
                    {"name": "Twitter аккаунт 2015", "price": 1000, "desc": "Старый Twitter аккаунт, 2015 год"},
                    {"name": "Facebook аккаунт", "price": 500, "desc": "Facebook аккаунт с историей, друзья"},
                    {"name": "TikTok аккаунт", "price": 800, "desc": "TikTok аккаунт с подписчиками, 2000+"},
                    {"name": "Telegram аккаунт", "price": 400, "desc": "Telegram аккаунт, старый, без блокировок"}
                ]
            },
            {
                "name": "Базы данных",
                "products": [
                    {"name": "База email 100k", "price": 3000, "desc": "100 000 email адресов"},
                    {"name": "База Telegram 50k", "price": 2500, "desc": "50 000 Telegram пользователей"},
                    {"name": "База WhatsApp 10k", "price": 1500, "desc": "10 000 WhatsApp номеров"},
                    {"name": "База Instagram 10k", "price": 2000, "desc": "10 000 Instagram аккаунтов"},
                    {"name": "База компаний РФ", "price": 5000, "desc": "База компаний России"}
                ]
            }
        ]
    },
    {
        "id": 2,
        "name": "🔑 Ключи",
        "subcategories": [
            {
                "name": "Windows 10/11 Ключи",
                "products": [
                    {"name": "Windows 10 Pro ключ", "price": 500, "desc": "Лицензионный ключ Windows 10 Pro"},
                    {"name": "Windows 11 Home ключ", "price": 550, "desc": "Ключ Windows 11 Home, OEM"},
                    {"name": "Windows 11 Pro ключ", "price": 600, "desc": "Ключ Windows 11 Pro, OEM"},
                    {"name": "Windows 10 Enterprise", "price": 700, "desc": "Корпоративная версия LTSB"},
                    {"name": "Windows 11 Enterprise", "price": 750, "desc": "Корпоративная версия LTSC"},
                    {"name": "Windows 10 Home ключ", "price": 450, "desc": "Ключ Windows 10 Home"}
                ]
            },
            {
                "name": "Office Ключи",
                "products": [
                    {"name": "Office 2021 Pro ключ", "price": 900, "desc": "Ключ Office 2021 Pro Plus, ПК"},
                    {"name": "Office 2019 ключ", "price": 800, "desc": "Ключ Office 2019 Pro Plus"},
                    {"name": "Office 365 ключ", "price": 1800, "desc": "Ключ Office 365 на год, 1 ПК"},
                    {"name": "Office 2016 ключ", "price": 600, "desc": "Ключ Office 2016 Pro"},
                    {"name": "Office для Mac", "price": 1200, "desc": "Office 2021 для Mac, бессрочно"}
                ]
            },
            {
                "name": "Антивирусы",
                "products": [
                    {"name": "Kaspersky 1 год", "price": 700, "desc": "Антивирус Kaspersky на год, 3 устройства"},
                    {"name": "ESET NOD32", "price": 800, "desc": "ESET NOD32 на год, 5 устройств"},
                    {"name": "Avast Premium", "price": 600, "desc": "Avast Premium на год, 10 устройств"},
                    {"name": "McAfee 1 год", "price": 650, "desc": "McAfee Total Protection, 5 устройств"},
                    {"name": "Norton 360", "price": 750, "desc": "Norton 360 Deluxe, 3 устройства"},
                    {"name": "Bitdefender", "price": 700, "desc": "Bitdefender Total Security, год"}
                ]
            },
            {
                "name": "Игровые ключи",
                "products": [
                    {"name": "Cyberpunk 2077", "price": 2800, "desc": "Ключ Cyberpunk 2077, GOG/Steam"},
                    {"name": "Hogwarts Legacy", "price": 3500, "desc": "Ключ Hogwarts Legacy, Steam"},
                    {"name": "Baldur's Gate 3", "price": 4000, "desc": "Ключ Baldur's Gate 3, Steam"},
                    {"name": "Starfield", "price": 3800, "desc": "Ключ Starfield, Steam"},
                    {"name": "Diablo 4", "price": 4200, "desc": "Ключ Diablo 4, Battle.net"},
                    {"name": "Spider-Man 2", "price": 3500, "desc": "Ключ Spider-Man 2, PS5/PC"}
                ]
            },
            {
                "name": "VPN Ключи",
                "products": [
                    {"name": "NordVPN ключ", "price": 2500, "desc": "NordVPN на год, 6 устройств"},
                    {"name": "ExpressVPN ключ", "price": 2800, "desc": "ExpressVPN на год, 5 устройств"},
                    {"name": "Surfshark ключ", "price": 2000, "desc": "Surfshark на 2 года, безлимит"},
                    {"name": "IPVanish ключ", "price": 1800, "desc": "IPVanish на год, 10 устройств"}
                ]
            },
            {
                "name": "Программное обеспечение",
                "products": [
                    {"name": "Adobe Photoshop", "price": 1200, "desc": "Лицензия Photoshop, бессрочно"},
                    {"name": "Adobe Premiere", "price": 1500, "desc": "Лицензия Premiere Pro, бессрочно"},
                    {"name": "WinRAR", "price": 300, "desc": "Лицензия WinRAR, бессрочно"},
                    {"name": "VMware", "price": 800, "desc": "VMware Workstation Pro, ключ"},
                    {"name": "Parallels Desktop", "price": 2000, "desc": "Parallels для Mac, год"}
                ]
            },
            {
                "name": "Подписки",
                "products": [
                    {"name": "ChatGPT Plus", "price": 1500, "desc": "ChatGPT Plus на месяц"},
                    {"name": "Midjourney", "price": 1500, "desc": "Midjourney на месяц"},
                    {"name": "Spotify Premium", "price": 400, "desc": "Spotify Premium на месяц"},
                    {"name": "Netflix Premium", "price": 600, "desc": "Netflix Premium на месяц"}
                ]
            }
        ]
    },
    {
        "id": 3,
        "name": "📱 Софт",
        "subcategories": [
            {
                "name": "Мобильные приложения",
                "products": [
                    {"name": "Nova Launcher Prime", "price": 300, "desc": "Лицензия Nova Launcher Prime"},
                    {"name": "Tasker", "price": 400, "desc": "Автоматизация для Android, полная версия"},
                    {"name": "Poweramp Full", "price": 250, "desc": "Полная версия Poweramp, плеер"},
                    {"name": "PicsArt Gold", "price": 350, "desc": "PicsArt Gold на год, премиум"},
                    {"name": "VSCO Premium", "price": 300, "desc": "VSCO Premium на год, фильтры"}
                ]
            },
            {
                "name": "Десктоп программы",
                "products": [
                    {"name": "Adobe Master Collection", "price": 3000, "desc": "Весь пакет Adobe, все программы"},
                    {"name": "CorelDRAW", "price": 1500, "desc": "CorelDRAW Graphics Suite, ключ"},
                    {"name": "3ds Max", "price": 2000, "desc": "Autodesk 3ds Max, ключ"},
                    {"name": "AutoCAD", "price": 1800, "desc": "AutoCAD лицензия, бессрочно"},
                    {"name": "MatLab", "price": 2500, "desc": "MatLab полная версия, ключ"}
                ]
            },
            {
                "name": "Скрипты",
                "products": [
                    {"name": "Скрипт для парсинга", "price": 2000, "desc": "Парсинг сайтов на Python, любой сайт"},
                    {"name": "SEO скрипт", "price": 1500, "desc": "Сбор семантики, анализ сайтов, ключей"},
                    {"name": "Скрипт для рассылок", "price": 1800, "desc": "Рассылка по Telegram/Email, готовый"},
                    {"name": "Торговый скрипт", "price": 3000, "desc": "Скрипт для крипто-бирж, арбитраж"},
                    {"name": "Парсер маркетплейсов", "price": 2500, "desc": "Парсинг WB, Ozon, Wildberries"}
                ]
            },
            {
                "name": "Боты",
                "products": [
                    {"name": "Бот для Telegram", "price": 5000, "desc": "Готовый бот с админ-панелью, любой функционал"},
                    {"name": "Discord бот", "price": 4000, "desc": "Модерация, музыка, игры, экономика"},
                    {"name": "Торговый бот", "price": 8000, "desc": "Бот для крипто-бирж, автоматическая торговля"},
                    {"name": "Парсинг бот", "price": 3500, "desc": "Бот для парсинга, мониторинга цен"},
                    {"name": "Магазин бот", "price": 6000, "desc": "Бот-магазин с базой, платежами"}
                ]
            },
            {
                "name": "Плагины",
                "products": [
                    {"name": "WordPress плагин", "price": 1000, "desc": "Премиум плагин для WordPress, nulled"},
                    {"name": "Minecraft плагин", "price": 800, "desc": "Плагин для Minecraft сервера, любой"},
                    {"name": "Chrome расширение", "price": 1200, "desc": "Расширение для браузера, готовое"},
                    {"name": "Figma плагин", "price": 600, "desc": "Плагин для Figma, премиум"},
                    {"name": "Photoshop плагин", "price": 500, "desc": "Плагины для Photoshop, набор"}
                ]
            },
            {
                "name": "Темы оформления",
                "products": [
                    {"name": "Windows тема", "price": 200, "desc": "Тема для Windows 10/11, темная"},
                    {"name": "Android тема", "price": 150, "desc": "Тема для Android, с иконками"},
                    {"name": "WordPress тема", "price": 800, "desc": "Премиум тема для WordPress, nulled"},
                    {"name": "VS Code тема", "price": 100, "desc": "Тема для VS Code, настройка"},
                    {"name": "MacOS тема", "price": 250, "desc": "Тема для MacOS, кастомизация"}
                ]
            },
            {
                "name": "Шрифты",
                "products": [
                    {"name": "Коллекция шрифтов", "price": 500, "desc": "1000+ премиум шрифтов, все стили"},
                    {"name": "Кириллические шрифты", "price": 300, "desc": "500+ кириллических шрифтов, дизайн"},
                    {"name": "Латинские шрифты", "price": 300, "desc": "500+ латинских шрифтов, каллиграфия"},
                    {"name": "Граффити шрифты", "price": 250, "desc": "100+ граффити шрифтов, уличный стиль"},
                    {"name": "Handwritten шрифты", "price": 200, "desc": "Рукописные шрифты, 200+"}
                ]
            },
            {
                "name": "Графика",
                "products": [
                    {"name": "Иконки для сайта", "price": 400, "desc": "1000+ иконок в векторе, SVG, PNG"},
                    {"name": "Паттерны", "price": 300, "desc": "200+ паттернов для дизайна, бесшовные"},
                    {"name": "Текстуры", "price": 350, "desc": "500+ текстур высокого разрешения"},
                    {"name": "Векторные файлы", "price": 500, "desc": "1000+ векторных изображений, AI, EPS"},
                    {"name": "Мокапы", "price": 400, "desc": "100+ мокапов для презентации дизайна"}
                ]
            }
        ]
    },
    {
        "id": 4,
        "name": "🎁 Telegram",
        "subcategories": [
            {
                "name": "Telegram Подарки (NFT)",
                "products": [
                    {"name": "🎩 NFT Durov's Cap", "price": 15000, "desc": "Редкий NFT подарок от Павла Дурова, лимитка"},
                    {"name": "⭐ NFT Golden Star", "price": 25000, "desc": "Золотая звезда, самый редкий подарок в TG"},
                    {"name": "🐸 NFT Plush Pepe", "price": 8000, "desc": "Мемный NFT Pepe, популярный"},
                    {"name": "🌹 NFT Eternal Rose", "price": 12000, "desc": "Вечная роза, символ любви"},
                    {"name": "💎 NFT Diamond", "price": 35000, "desc": "Бриллиант, очень редкий"},
                    {"name": "🔴 NFT Ruby", "price": 18000, "desc": "Рубин, редкий"},
                    {"name": "💚 NFT Emerald", "price": 16000, "desc": "Изумруд, редкий"},
                    {"name": "🔵 NFT Sapphire", "price": 17000, "desc": "Сапфир, редкий"},
                    {"name": "🎂 NFT Birthday Cake", "price": 5000, "desc": "Торт на день рождения"},
                    {"name": "🎆 NFT Fireworks", "price": 6000, "desc": "Фейерверк, праздничный"},
                    {"name": "🎈 NFT Balloons", "price": 4000, "desc": "Воздушные шары"},
                    {"name": "🎁 NFT Gift Box", "price": 3000, "desc": "Подарочная коробка"},
                    {"name": "🧸 NFT Teddy Bear", "price": 4500, "desc": "Плюшевый мишка"},
                    {"name": "❤️ NFT Heart", "price": 3500, "desc": "Сердце, валентинка"},
                    {"name": "💋 NFT Kiss", "price": 3800, "desc": "Поцелуй"},
                    {"name": "💌 NFT Love Letter", "price": 3200, "desc": "Любовное письмо"}
                ]
            },
            {
                "name": "Telegram Stars",
                "products": [
                    {"name": "1000 Telegram Stars", "price": 1800, "desc": "1000 звезд для поддержки каналов"},
                    {"name": "2500 Telegram Stars", "price": 4200, "desc": "2500 звезд"},
                    {"name": "5000 Telegram Stars", "price": 8000, "desc": "5000 звезд"},
                    {"name": "10000 Telegram Stars", "price": 15000, "desc": "10000 звезд"},
                    {"name": "25000 Telegram Stars", "price": 35000, "desc": "25000 звезд"}
                ]
            },
            {
                "name": "Telegram Premium",
                "products": [
                    {"name": "Premium на 1 месяц", "price": 350, "desc": "Telegram Premium на месяц"},
                    {"name": "Premium на 3 месяца", "price": 950, "desc": "Telegram Premium на 3 месяца"},
                    {"name": "Premium на 6 месяцев", "price": 1700, "desc": "Telegram Premium на полгода"},
                    {"name": "Premium на 1 год", "price": 3000, "desc": "Telegram Premium на год, экономия"},
                    {"name": "Premium + Stars", "price": 2000, "desc": "Premium + 500 Stars"}
                ]
            },
            {
                "name": "Telegram Аккаунты",
                "products": [
                    {"name": "Аккаунт 2015 года", "price": 3500, "desc": "Старый аккаунт, хорошая история, 2015"},
                    {"name": "Аккаунт 2018 года", "price": 1800, "desc": "Аккаунт 2018, без блокировок, чистый"},
                    {"name": "Аккаунт 2020 года", "price": 1000, "desc": "Аккаунт 2020, чистый, без истории"},
                    {"name": "Аккаунт с Premium", "price": 2500, "desc": "Аккаунт с активным Premium"},
                    {"name": "Аккаунт с историей", "price": 1500, "desc": "Аккаунт с историей переписок, чаты"},
                    {"name": "Аккаунт с подписками", "price": 1200, "desc": "Аккаунт с подписками на каналы"}
                ]
            },
            {
                "name": "Telegram Боты",
                "products": [
                    {"name": "Бот для магазина", "price": 6000, "desc": "Готовый бот-магазин с базой, админка"},
                    {"name": "Бот для рассылок", "price": 3500, "desc": "Рассылка по подписчикам, авто-постинг"},
                    {"name": "Бот-админ", "price": 4500, "desc": "Управление группой/каналом, модерация"},
                    {"name": "Игровой бот", "price": 4000, "desc": "Мини-игры в Telegram, экономика"},
                    {"name": "Торговый бот", "price": 8000, "desc": "Бот для крипто-бирж, сигналы"}
                ]
            },
            {
                "name": "Telegram Каналы",
                "products": [
                    {"name": "Канал 10k подписчиков", "price": 15000, "desc": "Крипто-канал, 10к живых, активных"},
                    {"name": "Канал 5k подписчиков", "price": 8000, "desc": "Новостной канал, 5к, высокая активность"},
                    {"name": "Канал 1k подписчиков", "price": 2000, "desc": "Юмористический канал, 1к, живая аудитория"},
                    {"name": "VIP канал 500 подписчиков", "price": 5000, "desc": "Закрытый канал с контентом, элита"},
                    {"name": "Канал с отлепленным", "price": 3000, "desc": "Канал с отлепленным, 2000 подписчиков"}
                ]
            },
            {
                "name": "Telegram Чаты",
                "products": [
                    {"name": "Чат 5000 участников", "price": 7000, "desc": "Активный чат, 5к участников, флуд"},
                    {"name": "Чат 1000 участников", "price": 1500, "desc": "Чат по интересам, активный"},
                    {"name": "VIP чат", "price": 3000, "desc": "Закрытый чат с элитой, бизнес"},
                    {"name": "Чат с ботом", "price": 2500, "desc": "Чат с игровым ботом, экономика"}
                ]
            },
            {
                "name": "Telegram Username",
                "products": [
                    {"name": "@rare короткое имя", "price": 5000, "desc": "Короткое имя 4 символа, редкое"},
                    {"name": "@brand имя бренда", "price": 3000, "desc": "Имя под бренд/компанию, красивое"},
                    {"name": "@beauty красивое имя", "price": 2000, "desc": "Красивое звучное имя, 6 символов"},
                    {"name": "@old старый юзернейм", "price": 4000, "desc": "Юзернейм с 2015 года, старый"},
                    {"name": "@crypto username", "price": 3500, "desc": "Крипто-нейм, для трейдеров"}
                ]
            },
            {
                "name": "NFT Username",
                "products": [
                    {"name": "@crypto NFT Username", "price": 5000, "desc": "Крипто-нейм в блокчейне TON"},
                    {"name": "@nft NFT Username", "price": 8000, "desc": "NFT нейм для коллекционера"},
                    {"name": "@bitcoin NFT Username", "price": 12000, "desc": "Bitcoin username, редкий"},
                    {"name": "@ethereum NFT Username", "price": 10000, "desc": "Ethereum username"},
                    {"name": "@ton NFT Username", "price": 7000, "desc": "TON username, для сообщества"}
                ]
            },
            {
                "name": "NFT Домены",
                "products": [
                    {"name": "crypto.eth", "price": 3000, "desc": "Ethereum Name Service домен, .eth"},
                    {"name": "nft.eth", "price": 5000, "desc": "NFT.eth домен, престижный"},
                    {"name": "wallet.crypto", "price": 2500, "desc": "Wallet.crypto домен, для кошелька"},
                    {"name": "dao.eth", "price": 3500, "desc": "DAO.eth домен, для организации"},
                    {"name": "defi.eth", "price": 3800, "desc": "DeFi.eth домен, для проектов"}
                ]
            }
        ]
    },
    {
        "id": 5,
        "name": "💎 Крипто",
        "subcategories": [
            {
                "name": "TON Кошельки",
                "products": [
                    {"name": "TON кошелек 10 TON", "price": 1200, "desc": "Кошелек с 10 TON, готов к работе"},
                    {"name": "TON кошелек 50 TON", "price": 5500, "desc": "Кошелек с 50 TON, для операций"},
                    {"name": "TON кошелек 100 TON", "price": 10500, "desc": "Кошелек с 100 TON, с историей"},
                    {"name": "Пустой TON кошелек", "price": 600, "desc": "Чистый кошелек, можно пополнить"},
                    {"name": "TON кошелек с историей", "price": 1500, "desc": "Кошелек с историей транзакций"}
                ]
            },
            {
                "name": "BTC Кошельки",
                "products": [
                    {"name": "BTC кошелек 0.01 BTC", "price": 45000, "desc": "Кошелек с 0.01 BTC, ~$400"},
                    {"name": "BTC кошелек 0.05 BTC", "price": 225000, "desc": "Кошелек с 0.05 BTC"},
                    {"name": "BTC кошелек 0.1 BTC", "price": 450000, "desc": "Кошелек с 0.1 BTC"},
                    {"name": "Пустой BTC кошелек", "price": 1000, "desc": "Чистый BTC кошелек, адрес"}
                ]
            },
            {
                "name": "ETH Кошельки",
                "products": [
                    {"name": "ETH кошелек 0.1 ETH", "price": 18000, "desc": "Кошелек с 0.1 ETH"},
                    {"name": "ETH кошелек 0.5 ETH", "price": 90000, "desc": "Кошелек с 0.5 ETH"},
                    {"name": "ETH кошелек 1 ETH", "price": 180000, "desc": "Кошелек с 1 ETH"},
                    {"name": "Пустой ETH кошелек", "price": 800, "desc": "Чистый ETH кошелек, адрес"}
                ]
            },
            {
                "name": "USDT Кошельки",
                "products": [
                    {"name": "USDT кошелек 100 USDT", "price": 10000, "desc": "Кошелек с 100 USDT"},
                    {"name": "USDT кошелек 500 USDT", "price": 49000, "desc": "Кошелек с 500 USDT"},
                    {"name": "USDT кошелек 1000 USDT", "price": 97000, "desc": "Кошелек с 1000 USDT"},
                    {"name": "Пустой USDT кошелек", "price": 600, "desc": "Чистый USDT кошелек, TRC20"}
                ]
            },
            {
                "name": "NFT Коллекции",
                "products": [
                    {"name": "CryptoPunks", "price": 15000, "desc": "Коллекция CryptoPunks, копия"},
                    {"name": "Bored Ape", "price": 55000, "desc": "Bored Ape Yacht Club, изображение"},
                    {"name": "Moonbirds", "price": 18000, "desc": "Коллекция Moonbirds, арт"},
                    {"name": "Azuki", "price": 25000, "desc": "Коллекция Azuki, аниме стиль"},
                    {"name": "CloneX", "price": 20000, "desc": "CloneX коллекция, японский стиль"}
                ]
            },
            {
                "name": "Крипто-ключи",
                "products": [
                    {"name": "Ключ от Bitcoin", "price": 2500, "desc": "Приватный ключ BTC, новый"},
                    {"name": "Seed фраза 12 слов", "price": 1800, "desc": "Seed фраза для кошелька, новый"},
                    {"name": "Seed фраза 24 слова", "price": 3000, "desc": "Seed фраза 24 слова, безопасный"},
                    {"name": "Ключ от Ethereum", "price": 2200, "desc": "Приватный ключ ETH"},
                    {"name": "Ключ от TON", "price": 1500, "desc": "Приватный ключ TON"}
                ]
            },
            {
                "name": "Майнинг",
                "products": [
                    {"name": "Майнинг-риг", "price": 150000, "desc": "Готовый майнинг-риг 6 карт RTX"},
                    {"name": "ASIC майнер", "price": 200000, "desc": "ASIC для майнинга BTC, Antminer"},
                    {"name": "Облачный майнинг", "price": 5000, "desc": "1 TH/s на месяц, договор"},
                    {"name": "Контракт на майнинг", "price": 10000, "desc": "Майнинг контракт на год"}
                ]
            },
            {
                "name": "Крипто-карты",
                "products": [
                    {"name": "Binance Card", "price": 2000, "desc": "Карта Binance с балансом, виртуальная"},
                    {"name": "Crypto.com Card", "price": 2500, "desc": "Карта Crypto.com, металлическая"},
                    {"name": "Bybit Card", "price": 2000, "desc": "Карта Bybit, виртуальная"},
                    {"name": "Coinbase Card", "price": 2200, "desc": "Карта Coinbase, физическая"}
                ]
            }
        ]
    },
    {
        "id": 6,
        "name": "📚 Базы",
        "subcategories": [
            {
                "name": "Email базы",
                "products": [
                    {"name": "Email база 100k", "price": 3000, "desc": "100 000 email адресов, свежие"},
                    {"name": "Email база 500k", "price": 12000, "desc": "500 000 email адресов, целевые"},
                    {"name": "Email база 1M", "price": 20000, "desc": "1 000 000 email адресов, мега-база"},
                    {"name": "Email база РФ", "price": 5000, "desc": "Email база России 200k, регионы"}
                ]
            },
            {
                "name": "Telegram базы",
                "products": [
                    {"name": "Telegram база 50k", "price": 2500, "desc": "50 000 Telegram пользователей, активные"},
                    {"name": "Telegram база 100k", "price": 4500, "desc": "100 000 Telegram пользователей"},
                    {"name": "Telegram база 500k", "price": 18000, "desc": "500 000 Telegram пользователей"},
                    {"name": "Telegram база крипто", "price": 3000, "desc": "Telegram база крипто-инвесторов"}
                ]
            },
            {
                "name": "WhatsApp базы",
                "products": [
                    {"name": "WhatsApp база 10k", "price": 1500, "desc": "10 000 WhatsApp номеров"},
                    {"name": "WhatsApp база 50k", "price": 6000, "desc": "50 000 WhatsApp номеров"},
                    {"name": "WhatsApp база 100k", "price": 10000, "desc": "100 000 WhatsApp номеров"}
                ]
            },
            {
                "name": "Instagram базы",
                "products": [
                    {"name": "Instagram база 10k", "price": 2000, "desc": "10 000 Instagram аккаунтов"},
                    {"name": "Instagram база 50k", "price": 8000, "desc": "50 000 Instagram аккаунтов"},
                    {"name": "Instagram база 100k", "price": 14000, "desc": "100 000 Instagram аккаунтов"}
                ]
            },
            {
                "name": "Базы компаний",
                "products": [
                    {"name": "База компаний РФ", "price": 5000, "desc": "Юридические лица РФ 500k, контакты"},
                    {"name": "База ИП", "price": 3000, "desc": "Индивидуальные предприниматели"},
                    {"name": "База компаний EU", "price": 10000, "desc": "Европейские компании, 200k"},
                    {"name": "База CEO контакты", "price": 4000, "desc": "Контакты руководителей, email"}
                ]
            },
            {
                "name": "Обучающие курсы",
                "products": [
                    {"name": "Курс по Python", "price": 2000, "desc": "Полный курс Python, 50 часов"},
                    {"name": "Курс по SMM", "price": 1500, "desc": "Продвижение в соцсетях, инстаграм"},
                    {"name": "Курс по трейдингу", "price": 3000, "desc": "Крипто-трейдинг, стратегии"},
                    {"name": "Курс по дизайну", "price": 2500, "desc": "Figma, Photoshop, иллюстрация"}
                ]
            },
            {
                "name": "Книги",
                "products": [
                    {"name": "Коллекция бизнес-книг", "price": 1000, "desc": "50 книг по бизнесу, PDF"},
                    {"name": "Коллекция IT-книг", "price": 1500, "desc": "100 книг по программированию"},
                    {"name": "Коллекция фэнтези", "price": 800, "desc": "Книги в жанре фэнтези, 30 книг"},
                    {"name": "Коллекция по психологии", "price": 900, "desc": "Книги по психологии, саморазвитие"}
                ]
            }
        ]
    },
    {
        "id": 7,
        "name": "💼 Услуги",
        "subcategories": [
            {
                "name": "Разработка ботов",
                "products": [
                    {"name": "Telegram бот под ключ", "price": 6000, "desc": "Разработка бота любой сложности"},
                    {"name": "Discord бот", "price": 5000, "desc": "Бот для Discord сервера, модерация"},
                    {"name": "Торговый бот", "price": 10000, "desc": "Бот для автоматической торговли"},
                    {"name": "Бот для магазина", "price": 8000, "desc": "Бот-магазин с базой, платежи"}
                ]
            },
            {
                "name": "Веб-разработка",
                "products": [
                    {"name": "Сайт-визитка", "price": 8000, "desc": "Одностраничный сайт, адаптивный"},
                    {"name": "Интернет-магазин", "price": 20000, "desc": "Полноценный магазин, корзина"},
                    {"name": "Лендинг", "price": 5000, "desc": "Посадочная страница, конверсия"},
                    {"name": "Корпоративный сайт", "price": 15000, "desc": "Сайт для компании, 5 страниц"}
                ]
            },
            {
                "name": "Дизайн",
                "products": [
                    {"name": "Логотип", "price": 1500, "desc": "Уникальный логотип, 3 варианта"},
                    {"name": "Фирменный стиль", "price": 5000, "desc": "Полный брендбук, визитки"},
                    {"name": "Дизайн сайта", "price": 3000, "desc": "Дизайн-макет сайта, Figma"},
                    {"name": "Дизайн упаковки", "price": 2500, "desc": "Дизайн упаковки товара"}
                ]
            },
            {
                "name": "SMM продвижение",
                "products": [
                    {"name": "Раскрутка Instagram", "price": 3000, "desc": "1000 живых подписчиков"},
                    {"name": "Раскрутка Telegram", "price": 2500, "desc": "500 подписчиков на канал"},
                    {"name": "Таргетолог", "price": 4000, "desc": "Настройка рекламы, FB/IG"},
                    {"name": "Ведение соцсетей", "price": 5000, "desc": "Ведение на месяц, постинг"}
                ]
            },
            {
                "name": "SEO оптимизация",
                "products": [
                    {"name": "Аудит сайта", "price": 2000, "desc": "Полный SEO-аудит, рекомендации"},
                    {"name": "Продвижение сайта", "price": 5000, "desc": "Вывод в топ по запросам"},
                    {"name": "Сбор семантики", "price": 1500, "desc": "Сбор ключевых слов, кластеризация"},
                    {"name": "Оптимизация контента", "price": 3000, "desc": "Оптимизация текстов, мета-теги"}
                ]
            },
            {
                "name": "Маркетинг",
                "products": [
                    {"name": "Маркетинг-план", "price": 3000, "desc": "Стратегия продвижения, анализ"},
                    {"name": "Контекстная реклама", "price": 2000, "desc": "Настройка Яндекс.Директ, Google Ads"},
                    {"name": "Email-маркетинг", "price": 1500, "desc": "Рассылка, воронки, автоматизация"},
                    {"name": "Аналитика", "price": 2500, "desc": "Настройка аналитики, отчеты"}
                ]
            },
            {
                "name": "Консультации",
                "products": [
                    {"name": "Консультация 1 час", "price": 1000, "desc": "Консультация по вашему вопросу"},
                    {"name": "Разбор бизнеса", "price": 3000, "desc": "Полный разбор и рекомендации"},
                    {"name": "Менторство месяц", "price": 10000, "desc": "Индивидуальное менторство"},
                    {"name": "Коуч-сессия", "price": 2000, "desc": "Коуч-сессия 2 часа"}
                ]
            },
            {
                "name": "Копирайтинг",
                "products": [
                    {"name": "SEO-текст 1000 знаков", "price": 300, "desc": "Текст для сайта, уникальный"},
                    {"name": "Пост для соцсетей", "price": 200, "desc": "Креативный пост, вовлекающий"},
                    {"name": "Сценарий для видео", "price": 500, "desc": "Сценарий для ролика"},
                    {"name": "Продающий текст", "price": 400, "desc": "Продающий текст для лендинга"}
                ]
            },
            {
                "name": "Переводы",
                "products": [
                    {"name": "Перевод 1000 знаков", "price": 300, "desc": "Перевод с/на английский"},
                    {"name": "Технический перевод", "price": 500, "desc": "Перевод документации, инструкций"},
                    {"name": "Юридический перевод", "price": 600, "desc": "Перевод договоров, контрактов"},
                    {"name": "Художественный перевод", "price": 400, "desc": "Перевод текстов, статей"}
                ]
            },
            {
                "name": "Обучение",
                "products": [
                    {"name": "Урок Python 1 час", "price": 500, "desc": "Индивидуальный урок, онлайн"},
                    {"name": "Курс Python", "price": 5000, "desc": "5 занятий по 2 часа, практика"},
                    {"name": "Интенсив 3 дня", "price": 3000, "desc": "Интенсив по веб-разработке"},
                    {"name": "Наставничество", "price": 8000, "desc": "Наставник на месяц, поддержка"}
                ]
            }
        ]
    },
    {
        "id": 8,
        "name": "🎨 NFT",
        "subcategories": [
            {
                "name": "NFT Подарки (Telegram)",
                "products": [
                    {"name": "🎩 NFT Durov's Cap", "price": 15000, "desc": "Редкий NFT подарок от Павла Дурова"},
                    {"name": "⭐ NFT Golden Star", "price": 25000, "desc": "Золотая звезда, самый редкий подарок"},
                    {"name": "🐸 NFT Plush Pepe", "price": 8000, "desc": "Мемный NFT Pepe, популярный"},
                    {"name": "🌹 NFT Eternal Rose", "price": 12000, "desc": "Вечная роза, символ любви"},
                    {"name": "💎 NFT Diamond", "price": 35000, "desc": "Бриллиант, очень редкий"},
                    {"name": "🔴 NFT Ruby", "price": 18000, "desc": "Рубин, редкий"},
                    {"name": "💚 NFT Emerald", "price": 16000, "desc": "Изумруд, редкий"},
                    {"name": "🔵 NFT Sapphire", "price": 17000, "desc": "Сапфир, редкий"}
                ]
            },
            {
                "name": "NFT Фоны",
                "products": [
                    {"name": "Cyberpunk City фон", "price": 2000, "desc": "Фон в стиле киберпанк, 4K"},
                    {"name": "Space Galaxy фон", "price": 2500, "desc": "Космическая галактика, звезды"},
                    {"name": "Neon Dreams фон", "price": 1800, "desc": "Неоновые огни, ретро"},
                    {"name": "Abstract Art фон", "price": 1500, "desc": "Абстрактное искусство, ярко"},
                    {"name": "Nature Forest фон", "price": 1200, "desc": "Лесная природа, лес"},
                    {"name": "Ocean Waves фон", "price": 1300, "desc": "Океанские волны, море"}
                ]
            },
            {
                "name": "NFT Модели",
                "products": [
                    {"name": "3D Cyberpunk модель", "price": 5000, "desc": "3D модель в стиле киберпанк"},
                    {"name": "Anime Character", "price": 3500, "desc": "Аниме персонаж, уникальный"},
                    {"name": "Fantasy Dragon", "price": 4500, "desc": "Фэнтези дракон, 3D"},
                    {"name": "Robot Model", "price": 4000, "desc": "Модель робота, механика"},
                    {"name": "Car Model", "price": 3000, "desc": "3D модель автомобиля, спорткар"}
                ]
            },
            {
                "name": "NFT Username",
                "products": [
                    {"name": "@crypto NFT Username", "price": 5000, "desc": "Крипто-нейм в блокчейне TON"},
                    {"name": "@nft NFT Username", "price": 8000, "desc": "NFT нейм для коллекционера"},
                    {"name": "@bitcoin NFT Username", "price": 12000, "desc": "Bitcoin username, редкий"},
                    {"name": "@ethereum NFT Username", "price": 10000, "desc": "Ethereum username"},
                    {"name": "@ton NFT Username", "price": 7000, "desc": "TON username, для сообщества"}
                ]
            },
            {
                "name": "NFT Домены",
                "products": [
                    {"name": "crypto.eth", "price": 3000, "desc": "Ethereum Name Service, .eth"},
                    {"name": "nft.eth", "price": 5000, "desc": "NFT.eth домен, престижный"},
                    {"name": "wallet.crypto", "price": 2500, "desc": "Wallet.crypto домен"},
                    {"name": "dao.eth", "price": 3500, "desc": "DAO.eth домен"},
                    {"name": "defi.eth", "price": 3800, "desc": "DeFi.eth домен"}
                ]
            },
            {
                "name": "NFT Коллекции",
                "products": [
                    {"name": "CryptoPunks", "price": 15000, "desc": "Коллекция CryptoPunks, копия"},
                    {"name": "Bored Ape", "price": 55000, "desc": "Bored Ape Yacht Club"},
                    {"name": "Moonbirds", "price": 18000, "desc": "Коллекция Moonbirds"},
                    {"name": "Azuki", "price": 25000, "desc": "Коллекция Azuki"},
                    {"name": "CloneX", "price": 20000, "desc": "CloneX коллекция"}
                ]
            },
            {
                "name": "NFT Арт",
                "products": [
                    {"name": "Цифровая картина", "price": 2000, "desc": "Уникальный NFT арт, авторский"},
                    {"name": "Анимированный NFT", "price": 4000, "desc": "GIF/видео NFT, анимация"},
                    {"name": "Генеративное искусство", "price": 3000, "desc": "Алгоритмическое искусство"},
                    {"name": "Пиксель-арт", "price": 1500, "desc": "Ретро пиксель-арт, 8bit"}
                ]
            },
            {
                "name": "NFT Игры",
                "products": [
                    {"name": "Игровой NFT скин", "price": 2000, "desc": "Редкий скин для игры, CS2/Dota"},
                    {"name": "Игровой персонаж", "price": 3000, "desc": "Уникальный персонаж, RPG"},
                    {"name": "Игровая земля", "price": 5000, "desc": "Виртуальная земля, метавселенная"},
                    {"name": "Игровой предмет", "price": 1500, "desc": "Редкий предмет, оружие"}
                ]
            },
            {
                "name": "Метавселенные",
                "products": [
                    {"name": "Земля в Decentraland", "price": 10000, "desc": "Участок в метавселенной"},
                    {"name": "Аватар для VR", "price": 2000, "desc": "Уникальный аватар"},
                    {"name": "Одежда для аватара", "price": 800, "desc": "Цифровая одежда"},
                    {"name": "Дом в метавселенной", "price": 15000, "desc": "Виртуальный дом"}
                ]
            }
        ]
    },
    {
        "id": 9,
        "name": "🔞 Другое",
        "subcategories": [
            {
                "name": "Разное",
                "products": [
                    {"name": "Случайный товар", "price": 100, "desc": "Что-то интересное, сюрприз"},
                    {"name": "Секретный товар", "price": 500, "desc": "Откроется после покупки"},
                    {"name": "Подарочный набор", "price": 1000, "desc": "Набор разных товаров"},
                    {"name": "Набор ключей", "price": 800, "desc": "5 ключей от разных игр"}
                ]
            },
            {
                "name": "Эксклюзив",
                "products": [
                    {"name": "VIP доступ", "price": 5000, "desc": "Доступ к закрытому контенту"},
                    {"name": "Эксклюзивный товар", "price": 10000, "desc": "Только для избранных"},
                    {"name": "Ранний доступ", "price": 2000, "desc": "Доступ к новинкам"},
                    {"name": "Закрытый раздел", "price": 3000, "desc": "Доступ к закрытому разделу"}
                ]
            },
            {
                "name": "Коллекционное",
                "products": [
                    {"name": "Винтажный товар", "price": 3000, "desc": "Редкая вещь, старая"},
                    {"name": "Лимитированная серия", "price": 5000, "desc": "Ограниченный тираж"},
                    {"name": "С подписью автора", "price": 7000, "desc": "Автограф, цифровой"},
                    {"name": "Уникальный экземпляр", "price": 8000, "desc": "В единственном экземпляре"}
                ]
            },
            {
                "name": "Редкие товары",
                "products": [
                    {"name": "Уникальный экземпляр", "price": 10000, "desc": "В единственном экземпляре"},
                    {"name": "Артефакт", "price": 15000, "desc": "Историческая ценность"},
                    {"name": "Сокровище", "price": 20000, "desc": "Настоящая находка"},
                    {"name": "Реликвия", "price": 25000, "desc": "Древняя реликвия"}
                ]
            }
        ]
    }
]

def load_products():
    for cat in categories:
        for sub in cat["subcategories"]:
            for prod in sub["products"]:
                prod_id = generate_id()
                products[prod_id] = {
                    'id': prod_id,
                    'name': prod['name'],
                    'description': prod['desc'],
                    'price': prod['price'],
                    'category': cat['id'],
                    'subcategory': sub['name'],
                    'stock': random.randint(3, 10)
                }
    print(f"✅ Загружено {len(products)} товаров")

LANGUAGES = {
    'ru': {
        'welcome': WELCOME_TEXT,
        'profile': '👤 Профиль',
        'language': '🌐 Язык',
        'support': '📞 Поддержка',
        'site': '🌍 Сайт',
        'requisites': '💰 Мои реквизиты',
        'top': '⭐ Топ продавцов',
        'back': '🔙 Назад',
        'catalog': '🛒 Каталог',
        'create_deal': '🤝 Создать сделку',
        'sell_product': '📤 Продать товар',
    },
    'en': {
        'welcome': "🛍️ **LOLZ MARKET** — Your reliable marketplace!",
        'profile': '👤 Profile',
        'language': '🌐 Language',
        'support': '📞 Support',
        'site': '🌍 Website',
        'requisites': '💰 My requisites',
        'top': '⭐ Top sellers',
        'back': '🔙 Back',
        'catalog': '🛒 Catalog',
        'create_deal': '🤝 Create deal',
        'sell_product': '📤 Sell product',
    }
}

DEAL_TYPES = {
    "nft": {"name_ru": "🎁 NFT", "name_en": "🎁 NFT", "fields": ["link", "amount"]},
    "game": {"name_ru": "🎮 Игры", "name_en": "🎮 Games", "fields": ["link", "amount"]},
    "service": {"name_ru": "💳 Услуги", "name_en": "💳 Services", "fields": ["description", "amount"]}
}

CURRENCIES = {
    'RUB': '🇷🇺 RUB', 'USD': '🇺🇸 USD', 'EUR': '🇪🇺 EUR',
    'TON': '💎 TON', 'STARS': '⭐ Stars'
}

def generate_id():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

def get_text(user_id, key):
    lang = user_language.get(user_id, 'ru')
    return LANGUAGES[lang].get(key, key)

def get_user_status(user_id):
    if user_id not in user_stats:
        user_stats[user_id] = {'deals_total': 0, 'deals_success': 0, 'deals_failed': 0, 'revenue': 0, 'status': 'new'}
    status = user_stats[user_id].get('status', 'new')
    lang = user_language.get(user_id, 'ru')
    return USER_STATUSES[status][f'name_{lang}']

def get_user_rating(user_id):
    if user_id not in reviews_db or not reviews_db[user_id]:
        return 0
    ratings = [r['rating'] for r in reviews_db[user_id]]
    return sum(ratings) / len(ratings)

# ============ КЛАВИАТУРЫ ============
def main_keyboard(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(user_id, 'catalog'), callback_data="catalog")],
        [InlineKeyboardButton(text=get_text(user_id, 'create_deal'), callback_data="create_deal"),
         InlineKeyboardButton(text=get_text(user_id, 'sell_product'), callback_data="sell_product")],
        [InlineKeyboardButton(text=get_text(user_id, 'requisites'), callback_data="my_requisites"),
         InlineKeyboardButton(text=get_text(user_id, 'profile'), callback_data="profile")],
        [InlineKeyboardButton(text=get_text(user_id, 'top'), callback_data="top_sellers"),
         InlineKeyboardButton(text=get_text(user_id, 'language'), callback_data="language")],
        [InlineKeyboardButton(text=get_text(user_id, 'support'), url=f"https://t.me/{SUPPORT_USERNAME}"),
         InlineKeyboardButton(text=get_text(user_id, 'site'), url=SITE_LINK)]
    ])

def back_keyboard(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(user_id, 'back'), callback_data="back_to_menu")]
    ])

def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users"),
         InlineKeyboardButton(text="🤝 Сделки", callback_data="admin_deals")],
        [InlineKeyboardButton(text="⏳ Модерация", callback_data="admin_moderation"),
         InlineKeyboardButton(text="⭐ Репутация", callback_data="admin_reputation")],
        [InlineKeyboardButton(text="📝 Отзывы", callback_data="admin_reviews"),
         InlineKeyboardButton(text="🚦 Статусы", callback_data="admin_statuses")],
        [InlineKeyboardButton(text="📦 Товары", callback_data="admin_products")],
        [InlineKeyboardButton(text="🖼️ Баннер", callback_data="admin_banner")],
        [InlineKeyboardButton(text="📋 Логи", callback_data="admin_logs")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ])

# ============ ОБРАБОТЧИКИ ЛОГИРОВАНИЯ ============

@dp.callback_query(F.data == "admin_logs")
async def admin_logs_callback(call: CallbackQuery):
    global LOG_CHAT_ID
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ Нет доступа", show_alert=True)
        return

    if LOG_CHAT_ID:
        text = f"📋 **Логирование включено**\n\n📍 Чат логов: `{LOG_CHAT_ID}`\n\n✅ Все события записываются в этот чат"
    else:
        text = f"📋 **Логирование отключено**\n\nВключить логирование: введите ID чата для логов"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Установить чат логов", callback_data="set_log_chat")],
        [InlineKeyboardButton(text="❌ Отключить логи", callback_data="disable_logs")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
    ])

    await call.message.edit_text(text, reply_markup=keyboard)

@dp.callback_query(F.data == "set_log_chat")
async def set_log_chat_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ Нет доступа", show_alert=True)
        return

    user_states[call.from_user.id] = {'action': 'set_log_chat'}
    await call.message.edit_text(
        "📍 **Введи ID чата для логов:**\n\nКак получить ID:\n1. Создай приватный чат\n2. Напиши боту: /getchatid\n3. Скопируй ID и отправь сюда",
        reply_markup=back_keyboard(call.from_user.id)
    )

@dp.callback_query(F.data == "disable_logs")
async def disable_logs_callback(call: CallbackQuery):
    global LOG_CHAT_ID
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ Нет доступа", show_alert=True)
        return

    LOG_CHAT_ID = None
    await call.answer("✅ Логирование отключено", show_alert=True)
    await call.message.edit_text("📋 **Логирование отключено**", reply_markup=admin_keyboard())

@dp.callback_query(F.data == "admin_panel")
async def admin_panel_back_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer()
        return
    await call.message.edit_text("👑 **Админ-панель**", reply_markup=admin_keyboard())

@dp.message(Command("getchatid"))
async def get_chat_id_command(message: Message):
    chat_id = message.chat.id
    await message.answer(f"📍 **ID этого чата:**\n\n`{chat_id}`\n\nИспользуй этот номер для установки логов")

# ============ ОСНОВНЫЕ КОМАНДЫ ============

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if user_id not in users:
        users[user_id] = {
            'balance': 0,
            'username': message.from_user.username or "Нет",
            'reg_date': datetime.now().strftime("%d.%m.%Y"),
            'reputation': 0
        }
        user_language[user_id] = 'ru'

        if user_id not in user_stats:
            user_stats[user_id] = {
                'deals_total': 0,
                'deals_success': 0,
                'deals_failed': 0,
                'revenue': 0,
                'status': 'new'
            }

        # ✅ ЛОГИРОВАНИЕ НОВОГО ПОЛЬЗОВАТЕЛЯ
        await log_event('join', user_id, f"Новый пользователь @{message.from_user.username or 'unknown'}")

    await state.clear()

    welcome_text = WELCOME_TEXT.format(
        users=len(users),
        products=len(products),
        deals=len(deals)
    )

    await message.answer(welcome_text, reply_markup=main_keyboard(user_id))

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        await message.answer("❌ Нет доступа")
        return
    await message.answer("👑 **Админ-панель**\n\nВыбери раздел:", reply_markup=admin_keyboard())

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "ℹ️ **Помощь по боту**\n\n"
        "/start - Запустить бота\n"
        "/help - Показать это сообщение\n"
        "/admin - Админ-панель\n"
        "/getchatid - ID текущего чата (для логов)\n\n"
        f"📞 Поддержка: @{SUPPORT_USERNAME}"
    )

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    await state.clear()
    if user_id in temp_deal_data:
        del temp_deal_data[user_id]
    await call.message.delete()
    welcome_text = WELCOME_TEXT.format(
        users=len(users),
        products=len(products),
        deals=len(deals)
    )
    await bot.send_message(call.message.chat.id, welcome_text, reply_markup=main_keyboard(user_id))

@dp.callback_query(F.data == "profile")
async def profile_callback(call: CallbackQuery):
    user_id = call.from_user.id
    user = users.get(user_id, {})
    stats = user_stats.get(user_id, {'deals_total': 0, 'deals_success': 0, 'deals_failed': 0, 'revenue': 0, 'status': 'new'})

    status = get_user_status(user_id)
    rating = get_user_rating(user_id)
    reviews_count = len(reviews_db.get(user_id, []))

    text = f"👤 **Профиль**\n\n"
    text += f"🆔 ID: `{user_id}`\n"
    text += f"📛 Username: @{user.get('username', 'Нет')}\n"
    text += f"🚦 Статус: {status}\n"
    text += f"📝 Отзывы: {reviews_count} | Рейтинг: {rating:.1f}/5\n"
    text += f"⭐ Репутация: {user.get('reputation', 0)}\n\n"
    text += f"📊 **Статистика сделок:**\n"
    text += f"• Всего сделок: {stats['deals_total']}\n"
    text += f"• ✅ Успешных: {stats['deals_success']}\n"
    text += f"• ❌ Проваленных: {stats['deals_failed']}"

    await call.message.edit_text(text, reply_markup=back_keyboard(user_id))

@dp.callback_query(F.data == "admin_stats")
async def admin_stats_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer()
        return

    active_deals = len([d for d in deals.values() if d['status'] == 'active'])

    text = f"📊 **Статистика**\n\n"
    text += f"👥 Пользователей: {len(users)}\n"
    text += f"📦 Товаров: {len(products)}\n"
    text += f"🤝 Всего сделок: {len(deals)}\n"
    text += f"🟡 Активных сделок: {active_deals}"

    await call.message.edit_text(text, reply_markup=admin_keyboard())

# ============ ОБРАБОТКА ТЕКСТА ============

@dp.message(F.text)
async def handle_text(message: Message):
    user_id = message.from_user.id

    if user_id not in user_states:
        return

    state = user_states[user_id]
    action = state.get('action')

    if action == 'set_log_chat':
        try:
            log_chat_id = int(message.text)
            global LOG_CHAT_ID
            LOG_CHAT_ID = log_chat_id

            try:
                await bot.send_message(log_chat_id, "✅ **Логирование активировано!**\n\nВсе события будут записываться сюда")
                await message.answer(f"✅ **Логи установлены!**\n\nID чата: `{log_chat_id}`")

                # ✅ ЛОГИРОВАНИЕ ВКЛЮЧЕНИЯ ЛОГОВ
                await log_event('status_changed', user_id, f"Логирование включено администратором для чата {log_chat_id}")
            except:
                await message.answer("❌ Бот не может отправлять сообщения в этот чат\n\nДобавь бота администратором в чат")
                LOG_CHAT_ID = None
        except:
            await message.answer("❌ Введи корректный ID (только числа)")

        del user_states[user_id]
        return

# ============ ЗАПУСК ============

async def main():
    load_products()
    print("✅ LOLZ MARKET бот запущен!")
    print(f"🤖 Бот: @{BOT_USERNAME}")
    print(f"👑 Админ ID: {ADMIN_ID}")
    print(f"📦 Товаров: {len(products)}")
    print(f"📋 Логирование: включено!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
