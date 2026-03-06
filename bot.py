import asyncio
import random
import string
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
MANAGER_USERNAME = os.getenv("MANAGER_USERNAME", "YourManager")
MANAGER_CARD = os.getenv("MANAGER_CARD", "Укажи реквизиты")
TON_WALLET = os.getenv("TON_WALLET", "")
USDT_WALLET = os.getenv("USDT_WALLET", "")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "YourSupport")
SITE_LINK = os.getenv("SITE_LINK", "https://example.com")
BOT_USERNAME = os.getenv("BOT_USERNAME", "YourBot")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан!")

storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

LOG_CHAT_ID = None
LOG_THREAD_ID = None
BANNER_FILE_ID = None

# ============ КУРСЫ ВАЛЮТ (1 RUB = X валюта) ============
CURRENCY_RATES = {
    'RUB': 1.0,
    'USD': 0.011,
    'EUR': 0.010,
    'GBP': 0.0086,
    'UAH': 0.44,
    'KZT': 5.0,
    'BYN': 0.036,
    'UZS': 140.0,
    'TRY': 0.37,
    'CNY': 0.079,
    'JPY': 1.65,
    'AED': 0.040,
    'GEL': 0.030,
    'AMD': 4.3,
    'AZN': 0.019,
    'MDL': 0.20,
    'KGS': 0.97,
    'TON': 0.0015,
    'BTC': 0.00000012,
    'ETH': 0.0000035,
    'USDT': 0.011,
    'USDC': 0.011,
    'SOL': 0.000075,
    'DOGE': 0.075,
    'XRP': 0.012,
    'LTC': 0.000085,
    'ADA': 0.015,
    'STARS': 0.22,
}

CURRENCY_SYMBOLS = {
    'RUB': '₽', 'USD': '$', 'EUR': '€', 'GBP': '£', 'UAH': '₴', 'KZT': '₸',
    'BYN': 'Br', 'UZS': "so'm", 'TRY': '₺', 'CNY': '¥', 'JPY': '¥',
    'AED': 'AED', 'GEL': '₾', 'AMD': '֏', 'AZN': '₼', 'MDL': 'lei',
    'KGS': 'с', 'TON': 'TON', 'BTC': '₿', 'ETH': 'Ξ', 'USDT': 'USDT',
    'USDC': 'USDC', 'SOL': 'SOL', 'DOGE': 'DOGE', 'XRP': 'XRP',
    'LTC': 'LTC', 'ADA': 'ADA', 'STARS': '⭐',
}

CRYPTO_CURRENCIES = ['TON', 'BTC', 'ETH', 'USDT', 'USDC', 'SOL', 'DOGE', 'XRP', 'LTC', 'ADA']

def convert_rub_to(amount_rub: float, currency: str) -> str:
    rate = CURRENCY_RATES.get(currency, 1.0)
    converted = amount_rub * rate
    sym = CURRENCY_SYMBOLS.get(currency, currency)
    if currency in CRYPTO_CURRENCIES:
        return f"≈{converted:.6f} {sym}"
    elif currency == 'STARS':
        return f"≈{int(converted)} {sym}"
    else:
        return f"≈{converted:.2f} {sym}"

# ============ ЛОГИРОВАНИЕ ============
async def log_event(event_type: str, user_id: int, description: str):
    if not LOG_CHAT_ID:
        return
    try:
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        emoji_map = {
            'join': '👤', 'deal_created': '🤝', 'deal_paid': '💰',
            'product_added': '📦', 'status_changed': '🚦',
            'review_left': '⭐', 'requisites': '💳',
            'payment_confirmed': '✅', 'payment_rejected': '❌'
        }
        emoji = emoji_map.get(event_type, '📝')
        await bot.send_message(LOG_CHAT_ID, f"{emoji} [{timestamp}] {description}",
                               message_thread_id=LOG_THREAD_ID)
    except Exception as e:
        print(f"Лог ошибка: {e}")

# ============ ХРАНИЛИЩА ============
users = {}
products = {}
deals = {}
reviews_db = {}
user_language = {}
user_requisites = {}
moderation_queue = []
user_stats = {}
temp_deal_data = {}
user_states = {}
payment_requests = {}

USER_STATUSES = {
    'new':        {'ru': '🟢 Новичок',      'en': '🟢 Newbie',      'kz': '🟢 Жаңадан',    'es': '🟢 Novato',     'de': '🟢 Neuling'},
    'verified':   {'ru': '✅ Проверенный',   'en': '✅ Verified',    'kz': '✅ Тексерілген', 'es': '✅ Verificado', 'de': '✅ Verifiziert'},
    'suspicious': {'ru': '⚠️ Сомнительный', 'en': '⚠️ Suspicious', 'kz': '⚠️ Күмәнді',    'es': '⚠️ Sospechoso', 'de': '⚠️ Verdächtig'},
    'scammer':    {'ru': '🔴 Мошенник',      'en': '🔴 Scammer',    'kz': '🔴 Алаяқ',      'es': '🔴 Estafador',  'de': '🔴 Betrüger'},
    'trusted':    {'ru': '💎 Доверенный',    'en': '💎 Trusted',    'kz': '💎 Сенімді',    'es': '💎 Confiable',  'de': '💎 Vertrauenswürdig'},
    'partner':    {'ru': '🤝 Партнер',       'en': '🤝 Partner',    'kz': '🤝 Серіктес',   'es': '🤝 Socio',      'de': '🤝 Partner'},
}

TRANSLATIONS = {
    'ru': {
        'catalog': '🛒 Каталог', 'create_deal': '🤝 Создать сделку',
        'sell_product': '📤 Продать товар', 'my_requisites': '💰 Мои реквизиты',
        'profile': '👤 Профиль', 'top_sellers': '⭐ Топ продавцов',
        'language': '🌐 Язык', 'support': '📞 Поддержка', 'site': '🌍 Сайт',
    },
    'en': {
        'catalog': '🛒 Catalog', 'create_deal': '🤝 Create Deal',
        'sell_product': '📤 Sell Product', 'my_requisites': '💰 My Requisites',
        'profile': '👤 Profile', 'top_sellers': '⭐ Top Sellers',
        'language': '🌐 Language', 'support': '📞 Support', 'site': '🌍 Website',
    },
    'kz': {
        'catalog': '🛒 Каталог', 'create_deal': '🤝 Мәміле жасау',
        'sell_product': '📤 Тауар сату', 'my_requisites': '💰 Менің деректерім',
        'profile': '👤 Профиль', 'top_sellers': '⭐ Үздік сатушылар',
        'language': '🌐 Тіл', 'support': '📞 Қолдау', 'site': '🌍 Сайт',
    },
    'es': {
        'catalog': '🛒 Catálogo', 'create_deal': '🤝 Crear Oferta',
        'sell_product': '📤 Vender', 'my_requisites': '💰 Mis Datos',
        'profile': '👤 Perfil', 'top_sellers': '⭐ Mejores Vendedores',
        'language': '🌐 Idioma', 'support': '📞 Soporte', 'site': '🌍 Sitio',
    },
    'de': {
        'catalog': '🛒 Katalog', 'create_deal': '🤝 Angebot Erstellen',
        'sell_product': '📤 Verkaufen', 'my_requisites': '💰 Meine Daten',
        'profile': '👤 Profil', 'top_sellers': '⭐ Top Verkäufer',
        'language': '🌐 Sprache', 'support': '📞 Support', 'site': '🌍 Website',
    },
}

TOP_SELLERS = [
    {"name": "@al**in",       "deals": 847, "rating": 4.9},
    {"name": "@ma**k_shop",   "deals": 832, "rating": 4.8},
    {"name": "@st**a_market", "deals": 821, "rating": 4.9},
    {"name": "@dm**y_pro",    "deals": 815, "rating": 4.7},
    {"name": "@ki**s_gaming", "deals": 809, "rating": 4.8},
    {"name": "@pr**e_seller", "deals": 798, "rating": 4.9},
    {"name": "@ve**s_shop",   "deals": 784, "rating": 4.8},
    {"name": "@ni**la_deals", "deals": 776, "rating": 4.7},
    {"name": "@ti**n_market", "deals": 765, "rating": 4.9},
    {"name": "@ro**l_trader", "deals": 752, "rating": 4.8},
]

def get_welcome_text(user_id=None):
    lang = user_language.get(user_id, 'ru') if user_id else 'ru'
    texts = {
        'ru': (
            "🛍️ LOLZ MARKET — твой надежный маркетплейс!\n\n"
            "✨ Что мы предлагаем:\n"
            "• 🎮 Игровые аккаунты и предметы\n"
            "• 💳 Цифровые товары и услуги\n"
            "• 🎁 Telegram NFT и подарки\n"
            "• 💎 Криптовалюта и кошельки\n"
            "• 🔑 Лицензионные ключи\n"
            "• 📱 Софт и программы\n"
            "• 💼 Услуги фрилансеров\n\n"
            "🔥 Наши преимущества:\n"
            "✅ Безопасные сделки с гарантом\n"
            "⭐ Рейтинг продавцов и отзывы\n"
            "💳 Мгновенные выплаты\n"
            "🤝 Поддержка 24/7\n\n"
            "📊 Статистика:\n"
            "👥 Пользователей: {users}\n"
            "📦 Товаров: {products}\n"
            "🤝 Сделок: {deals}\n\n"
            "Выбери действие в меню ниже 👇"
        ),
        'en': (
            "🛍️ LOLZ MARKET — your reliable marketplace!\n\n"
            "✨ What we offer:\n"
            "• 🎮 Game accounts and items\n"
            "• 💳 Digital goods and services\n"
            "• 🎁 Telegram NFT and gifts\n"
            "• 💎 Crypto and wallets\n"
            "• 🔑 License keys\n"
            "• 📱 Software\n"
            "• 💼 Freelance services\n\n"
            "🔥 Our advantages:\n"
            "✅ Safe deals with guarantor\n"
            "⭐ Seller ratings and reviews\n"
            "💳 Instant payouts\n"
            "🤝 Support 24/7\n\n"
            "📊 Statistics:\n"
            "👥 Users: {users}\n"
            "📦 Products: {products}\n"
            "🤝 Deals: {deals}\n\n"
            "Choose an action below 👇"
        ),
        'kz': (
            "🛍️ LOLZ MARKET — сенімді маркетплейсің!\n\n"
            "✨ Біз ұсынамыз:\n"
            "• 🎮 Ойын аккаунттары\n"
            "• 💳 Цифрлық тауарлар\n"
            "• 🎁 Telegram NFT сыйлықтары\n"
            "• 💎 Криптовалюта\n"
            "• 🔑 Лицензиялық кілттер\n"
            "• 📱 Бағдарламалар\n"
            "• 💼 Фриланс қызметтері\n\n"
            "🔥 Артықшылықтар:\n"
            "✅ Қауіпсіз мәмілелер\n"
            "⭐ Сатушы рейтингтері\n"
            "💳 Жедел төлемдер\n"
            "🤝 Қолдау 24/7\n\n"
            "📊 Статистика:\n"
            "👥 Пайдаланушылар: {users}\n"
            "📦 Тауарлар: {products}\n"
            "🤝 Мәмілелер: {deals}\n\n"
            "Төмендегі мәзірден таңда 👇"
        ),
        'es': (
            "🛍️ LOLZ MARKET — tu mercado confiable!\n\n"
            "✨ Lo que ofrecemos:\n"
            "• 🎮 Cuentas de juegos\n"
            "• 💳 Bienes digitales\n"
            "• 🎁 Telegram NFT\n"
            "• 💎 Cripto\n"
            "• 🔑 Claves de licencia\n"
            "• 📱 Software\n"
            "• 💼 Freelance\n\n"
            "🔥 Ventajas:\n"
            "✅ Acuerdos seguros\n"
            "⭐ Calificaciones\n"
            "💳 Pagos instantáneos\n"
            "🤝 Soporte 24/7\n\n"
            "📊 Estadísticas:\n"
            "👥 Usuarios: {users}\n"
            "📦 Productos: {products}\n"
            "🤝 Acuerdos: {deals}\n\n"
            "Elige una acción 👇"
        ),
        'de': (
            "🛍️ LOLZ MARKET — dein Marktplatz!\n\n"
            "✨ Was wir anbieten:\n"
            "• 🎮 Spielkonten\n"
            "• 💳 Digitale Waren\n"
            "• 🎁 Telegram NFT\n"
            "• 💎 Krypto\n"
            "• 🔑 Lizenzschlüssel\n"
            "• 📱 Software\n"
            "• 💼 Freelance\n\n"
            "🔥 Vorteile:\n"
            "✅ Sichere Geschäfte\n"
            "⭐ Bewertungen\n"
            "💳 Sofortige Zahlungen\n"
            "🤝 Support 24/7\n\n"
            "📊 Statistiken:\n"
            "👥 Benutzer: {users}\n"
            "📦 Produkte: {products}\n"
            "🤝 Angebote: {deals}\n\n"
            "Wählen Sie eine Aktion 👇"
        ),
    }
    tmpl = texts.get(lang, texts['ru'])
    return tmpl.format(users=len(users), products=len(products), deals=len(deals))

# ============ КАТАЛОГ ============
categories = [
    {"id": 0, "name": "🎮 Игры", "subcategories": [
        {"name": "Steam Аккаунты", "products": [
            {"name": "Steam с CS2", "price": 2500, "desc": "Prime статус, медали, 1000+ часов"},
            {"name": "Steam с Dota 2", "price": 1800, "desc": "Арканы, высокий рейтинг"},
            {"name": "Steam с 10 играми", "price": 3500, "desc": "GTA, Rust, CS, Dota и другие"},
            {"name": "Steam с GTA V", "price": 2200, "desc": "GTA V + онлайн, почта в подарок"},
            {"name": "Steam с Rust", "price": 2000, "desc": "Rust, скины, 500+ часов"},
            {"name": "Steam с PUBG", "price": 1900, "desc": "PUBG, скины, боевой пропуск"},
            {"name": "Steam с 20 играми", "price": 5000, "desc": "20 игр, коллекционные"},
            {"name": "Steam редкие игры", "price": 8000, "desc": "Удалённые из магазина игры"},
        ]},
        {"name": "Epic Games Аккаунты", "products": [
            {"name": "Epic Games с GTA V", "price": 1800, "desc": "Полный доступ, почта"},
            {"name": "Epic Games с Fortnite", "price": 2000, "desc": "Много скинов, редкие предметы"},
            {"name": "Epic Games с Rocket League", "price": 1500, "desc": "Много предметов, ранг"},
            {"name": "Epic Games 5 игр", "price": 2500, "desc": "5 популярных игр"},
            {"name": "Epic Games редкие скины", "price": 5000, "desc": "50+ редких скинов Fortnite"},
        ]},
        {"name": "Battle.net Аккаунты", "products": [
            {"name": "Battle.net Overwatch 2", "price": 1600, "desc": "Полный доступ, скины"},
            {"name": "Battle.net Diablo 4", "price": 3000, "desc": "Пройден сюжет"},
            {"name": "Battle.net WoW", "price": 2500, "desc": "Высокий уровень, Dragonflight"},
            {"name": "Battle.net CoD MW2", "price": 2000, "desc": "Call of Duty Modern Warfare 2"},
            {"name": "Battle.net Hearthstone", "price": 800, "desc": "Много карт, ранговый"},
        ]},
        {"name": "CS2 / CS:GO", "products": [
            {"name": "CS2 Prime Account", "price": 2000, "desc": "Prime статус, медали"},
            {"name": "CS2 с ножом", "price": 8500, "desc": "Нож + скины, 10+ скинов"},
            {"name": "CS2 редкие скины", "price": 15000, "desc": "Инвентарь 30000+ руб"},
            {"name": "CS2 Глобал Элит", "price": 5000, "desc": "Высокий ранг, медали"},
            {"name": "CS2 с оперативниками", "price": 3000, "desc": "Много оперативников, граффити"},
        ]},
        {"name": "Dota 2 Аккаунты", "products": [
            {"name": "Dota 2 с арканами", "price": 3000, "desc": "5+ аркан, много часов"},
            {"name": "Dota 2 высокий MMR", "price": 4000, "desc": "5000+ MMR, редкие предметы"},
            {"name": "Dota 2 с компендиумом", "price": 2000, "desc": "Компендиум, уровни"},
            {"name": "Dota 2 с имморталами", "price": 2500, "desc": "50+ имморталов"},
        ]},
        {"name": "Minecraft Аккаунты", "products": [
            {"name": "Minecraft Premium", "price": 1200, "desc": "Полный доступ, смена ника"},
            {"name": "Minecraft Java Edition", "price": 1500, "desc": "Java Edition, лицензия"},
            {"name": "Minecraft Bedrock", "price": 1300, "desc": "Windows 10/11, Xbox, мобилки"},
            {"name": "Minecraft с Hypixel", "price": 2000, "desc": "Разбан на Hypixel, ранги"},
            {"name": "Minecraft + Capes", "price": 3500, "desc": "Редкие плащи, миграция"},
        ]},
        {"name": "Игровая валюта", "products": [
            {"name": "V-Bucks 5000", "price": 3500, "desc": "5000 V-Bucks для Fortnite"},
            {"name": "V-Bucks 10000", "price": 6500, "desc": "10000 V-Bucks"},
            {"name": "Steam Wallet 1000р", "price": 950, "desc": "Пополнение Steam кошелька"},
            {"name": "Steam Wallet 5000р", "price": 4750, "desc": "Пополнение Steam кошелька"},
            {"name": "Robux 1000", "price": 1200, "desc": "1000 Robux для Roblox"},
            {"name": "Robux 5000", "price": 5500, "desc": "5000 Robux для Roblox"},
        ]},
        {"name": "Буст / Калибровка", "products": [
            {"name": "Буст MMR Dota 2", "price": 1500, "desc": "Поднятие MMR на 500"},
            {"name": "Буст ранга CS2", "price": 1200, "desc": "Поднятие ранга"},
            {"name": "Калибровка Dota 2", "price": 2000, "desc": "Калибровка под ваш уровень"},
            {"name": "Калибровка CS2", "price": 1800, "desc": "Калибровка под ваш ранг"},
        ]},
        {"name": "Ключи игр", "products": [
            {"name": "Cyberpunk 2077 ключ", "price": 2800, "desc": "GOG/Steam ключ"},
            {"name": "Hogwarts Legacy ключ", "price": 3500, "desc": "Steam ключ"},
            {"name": "Baldur's Gate 3 ключ", "price": 4000, "desc": "Steam ключ"},
            {"name": "Starfield ключ", "price": 3800, "desc": "Steam ключ"},
            {"name": "Diablo 4 ключ", "price": 4200, "desc": "Battle.net ключ"},
        ]},
    ]},
    {"id": 1, "name": "💳 Аккаунты", "subcategories": [
        {"name": "Netflix / Disney+", "products": [
            {"name": "Netflix 4K 1 месяц", "price": 600, "desc": "4K, 4 экрана, 1 месяц"},
            {"name": "Netflix Premium 3 месяца", "price": 1500, "desc": "Premium на 3 месяца"},
            {"name": "Netflix семейный год", "price": 4500, "desc": "4 профиля, год"},
            {"name": "Disney+ 1 месяц", "price": 600, "desc": "Все фильмы и сериалы"},
            {"name": "Disney+ на год", "price": 5000, "desc": "Годовая подписка"},
        ]},
        {"name": "Spotify", "products": [
            {"name": "Spotify Premium 1 мес", "price": 400, "desc": "Без рекламы"},
            {"name": "Spotify Family 3 мес", "price": 1500, "desc": "6 аккаунтов, 3 месяца"},
            {"name": "Spotify Premium 6 мес", "price": 2000, "desc": "Индивидуальная, 6 мес"},
        ]},
        {"name": "AI Сервисы", "products": [
            {"name": "ChatGPT Plus 1 месяц", "price": 1500, "desc": "GPT-4, быстрый ответ"},
            {"name": "ChatGPT Plus 3 месяца", "price": 4000, "desc": "GPT-4, экономия"},
            {"name": "Midjourney Basic", "price": 1500, "desc": "200 генераций"},
            {"name": "Midjourney Pro", "price": 2500, "desc": "Быстрая генерация, безлимит"},
        ]},
        {"name": "Adobe / Office", "products": [
            {"name": "Adobe Creative Cloud", "price": 2500, "desc": "Весь пакет Adobe, 1 мес"},
            {"name": "Office 365 Personal", "price": 1500, "desc": "Год, 1 пользователь"},
            {"name": "Office 365 Family", "price": 2500, "desc": "Год, 6 пользователей"},
            {"name": "Office 2021 навсегда", "price": 2000, "desc": "Бессрочная лицензия"},
        ]},
        {"name": "VPN", "products": [
            {"name": "NordVPN 1 год", "price": 2500, "desc": "6 устройств"},
            {"name": "ExpressVPN 6 мес", "price": 2000, "desc": "5 устройств"},
            {"name": "Surfshark 2 года", "price": 3000, "desc": "Безлимит устройств"},
        ]},
        {"name": "Соцсети / Почта", "products": [
            {"name": "GMail аккаунт 2010", "price": 1000, "desc": "Старый, с историей"},
            {"name": "Twitter/X 2015", "price": 1000, "desc": "Старый аккаунт"},
            {"name": "Instagram аккаунт", "price": 600, "desc": "1000+ подписчиков"},
            {"name": "TikTok аккаунт", "price": 800, "desc": "2000+ подписчиков"},
            {"name": "Telegram аккаунт", "price": 400, "desc": "Старый, без блокировок"},
        ]},
    ]},
    {"id": 2, "name": "🔑 Ключи", "subcategories": [
        {"name": "Windows 10/11", "products": [
            {"name": "Windows 10 Pro", "price": 500, "desc": "Лицензионный ключ"},
            {"name": "Windows 11 Home", "price": 550, "desc": "OEM ключ"},
            {"name": "Windows 11 Pro", "price": 600, "desc": "OEM ключ"},
            {"name": "Windows 10 Enterprise", "price": 700, "desc": "LTSB корпоративная"},
        ]},
        {"name": "Office ключи", "products": [
            {"name": "Office 2021 Pro", "price": 900, "desc": "Pro Plus, ПК"},
            {"name": "Office 2019", "price": 800, "desc": "Pro Plus"},
            {"name": "Office 365 ключ", "price": 1800, "desc": "Год, 1 ПК"},
        ]},
        {"name": "Антивирусы", "products": [
            {"name": "Kaspersky 1 год", "price": 700, "desc": "3 устройства"},
            {"name": "ESET NOD32", "price": 800, "desc": "5 устройств"},
            {"name": "Avast Premium", "price": 600, "desc": "10 устройств"},
        ]},
        {"name": "Игровые ключи", "products": [
            {"name": "Cyberpunk 2077", "price": 2800, "desc": "GOG/Steam"},
            {"name": "Hogwarts Legacy", "price": 3500, "desc": "Steam"},
            {"name": "Baldur's Gate 3", "price": 4000, "desc": "Steam"},
        ]},
    ]},
    {"id": 3, "name": "📱 Софт", "subcategories": [
        {"name": "Скрипты и Боты", "products": [
            {"name": "Скрипт парсинга", "price": 2000, "desc": "Python, любой сайт"},
            {"name": "Бот для Telegram", "price": 5000, "desc": "Готовый с админкой"},
            {"name": "Discord бот", "price": 4000, "desc": "Модерация, музыка"},
            {"name": "Магазин бот", "price": 6000, "desc": "С базой и платежами"},
        ]},
        {"name": "Десктоп программы", "products": [
            {"name": "Adobe Master Collection", "price": 3000, "desc": "Все программы Adobe"},
            {"name": "CorelDRAW", "price": 1500, "desc": "Graphics Suite, ключ"},
            {"name": "AutoCAD", "price": 1800, "desc": "Лицензия, бессрочно"},
        ]},
        {"name": "Графика и Шрифты", "products": [
            {"name": "Коллекция шрифтов 1000+", "price": 500, "desc": "Все стили"},
            {"name": "Иконки для сайта 1000+", "price": 400, "desc": "SVG, PNG"},
            {"name": "Мокапы 100+", "price": 400, "desc": "Для презентаций"},
        ]},
    ]},
    {"id": 4, "name": "🎁 Telegram", "subcategories": [
        {"name": "Telegram Подарки NFT", "products": [
            {"name": "NFT Durov's Cap", "price": 15000, "desc": "Редкий подарок от Дурова, лимитка"},
            {"name": "NFT Golden Star", "price": 25000, "desc": "Золотая звезда, самый редкий"},
            {"name": "NFT Plush Pepe", "price": 8000, "desc": "Мемный Pepe"},
            {"name": "NFT Eternal Rose", "price": 12000, "desc": "Вечная роза"},
            {"name": "NFT Diamond", "price": 35000, "desc": "Бриллиант, очень редкий"},
            {"name": "NFT Ruby", "price": 18000, "desc": "Рубин, редкий"},
            {"name": "NFT Emerald", "price": 16000, "desc": "Изумруд, редкий"},
            {"name": "NFT Birthday Cake", "price": 5000, "desc": "Торт на день рождения"},
            {"name": "NFT Teddy Bear", "price": 4500, "desc": "Плюшевый мишка"},
            {"name": "NFT Heart", "price": 3500, "desc": "Сердце"},
        ]},
        {"name": "Telegram Stars", "products": [
            {"name": "1000 Telegram Stars", "price": 1800, "desc": "Звёзды для поддержки"},
            {"name": "2500 Telegram Stars", "price": 4200, "desc": "2500 звёзд"},
            {"name": "5000 Telegram Stars", "price": 8000, "desc": "5000 звёзд"},
            {"name": "10000 Telegram Stars", "price": 15000, "desc": "10000 звёзд"},
        ]},
        {"name": "Telegram Premium", "products": [
            {"name": "Premium 1 месяц", "price": 350, "desc": "Telegram Premium"},
            {"name": "Premium 3 месяца", "price": 950, "desc": "Экономия"},
            {"name": "Premium 6 месяцев", "price": 1700, "desc": "Полгода"},
            {"name": "Premium 1 год", "price": 3000, "desc": "Год, максимальная экономия"},
        ]},
        {"name": "Telegram Аккаунты", "products": [
            {"name": "Аккаунт 2015 года", "price": 3500, "desc": "Старый, хорошая история"},
            {"name": "Аккаунт 2018 года", "price": 1800, "desc": "Без блокировок, чистый"},
            {"name": "Аккаунт с Premium", "price": 2500, "desc": "С активным Premium"},
        ]},
        {"name": "Telegram Каналы", "products": [
            {"name": "Канал 10k подписчиков", "price": 15000, "desc": "Живые, активные"},
            {"name": "Канал 5k подписчиков", "price": 8000, "desc": "Высокая активность"},
            {"name": "Канал 1k подписчиков", "price": 2000, "desc": "Живая аудитория"},
        ]},
        {"name": "Telegram Username", "products": [
            {"name": "@rare 4 символа", "price": 5000, "desc": "Редкое короткое имя"},
            {"name": "@brand имя бренда", "price": 3000, "desc": "Под компанию"},
            {"name": "@old с 2015 года", "price": 4000, "desc": "Старый юзернейм"},
        ]},
        {"name": "NFT Username (TON)", "products": [
            {"name": "@crypto NFT", "price": 5000, "desc": "Крипто-нейм, TON"},
            {"name": "@bitcoin NFT", "price": 12000, "desc": "Редкий"},
            {"name": "@ethereum NFT", "price": 10000, "desc": "Ethereum username"},
            {"name": "@ton NFT", "price": 7000, "desc": "TON username"},
        ]},
    ]},
    {"id": 5, "name": "💎 Крипто", "subcategories": [
        {"name": "TON Кошельки", "products": [
            {"name": "TON кошелек 10 TON", "price": 1200, "desc": "Готов к работе"},
            {"name": "TON кошелек 50 TON", "price": 5500, "desc": "Для операций"},
            {"name": "TON кошелек 100 TON", "price": 10500, "desc": "С историей"},
        ]},
        {"name": "BTC / ETH / USDT", "products": [
            {"name": "BTC кошелек 0.01 BTC", "price": 45000, "desc": "~$400"},
            {"name": "ETH кошелек 0.1 ETH", "price": 18000, "desc": "Ethereum"},
            {"name": "USDT 100 USDT", "price": 10000, "desc": "TRC20"},
            {"name": "USDT 500 USDT", "price": 49000, "desc": "TRC20"},
        ]},
        {"name": "Крипто-карты", "products": [
            {"name": "Binance Card", "price": 2000, "desc": "Виртуальная"},
            {"name": "Crypto.com Card", "price": 2500, "desc": "Металлическая"},
        ]},
    ]},
    {"id": 6, "name": "📚 Базы", "subcategories": [
        {"name": "Email базы", "products": [
            {"name": "Email база 100k", "price": 3000, "desc": "100к свежих"},
            {"name": "Email база 500k", "price": 12000, "desc": "500к целевых"},
            {"name": "Email база 1M", "price": 20000, "desc": "1 миллион"},
        ]},
        {"name": "Telegram базы", "products": [
            {"name": "Telegram база 50k", "price": 2500, "desc": "50к активных"},
            {"name": "Telegram база 100k", "price": 4500, "desc": "100к"},
            {"name": "Telegram крипто-база", "price": 3000, "desc": "Крипто-инвесторы"},
        ]},
        {"name": "Курсы и Книги", "products": [
            {"name": "Курс по Python", "price": 2000, "desc": "50 часов, полный"},
            {"name": "Курс по SMM", "price": 1500, "desc": "Продвижение в соцсетях"},
            {"name": "Курс по трейдингу", "price": 3000, "desc": "Крипто, стратегии"},
        ]},
    ]},
    {"id": 7, "name": "💼 Услуги", "subcategories": [
        {"name": "Разработка", "products": [
            {"name": "Telegram бот под ключ", "price": 6000, "desc": "Любая сложность"},
            {"name": "Сайт-визитка", "price": 8000, "desc": "Одностраничный, адаптивный"},
            {"name": "Интернет-магазин", "price": 20000, "desc": "Полноценный"},
        ]},
        {"name": "Дизайн", "products": [
            {"name": "Логотип", "price": 1500, "desc": "Уникальный, 3 варианта"},
            {"name": "Фирменный стиль", "price": 5000, "desc": "Полный брендбук"},
            {"name": "Дизайн сайта в Figma", "price": 3000, "desc": "Макет"},
        ]},
        {"name": "SMM / SEO", "products": [
            {"name": "Раскрутка Instagram", "price": 3000, "desc": "1000 живых подписчиков"},
            {"name": "Раскрутка Telegram", "price": 2500, "desc": "500 подписчиков"},
            {"name": "SEO аудит сайта", "price": 2000, "desc": "Полный аудит"},
        ]},
        {"name": "Обучение / Консультации", "products": [
            {"name": "Курс Python 5 занятий", "price": 5000, "desc": "10 часов, практика"},
            {"name": "Консультация 1 час", "price": 1000, "desc": "По вашему вопросу"},
        ]},
    ]},
    {"id": 8, "name": "🎨 NFT", "subcategories": [
        {"name": "NFT Арт", "products": [
            {"name": "Цифровая картина", "price": 2000, "desc": "Уникальный авторский арт"},
            {"name": "Анимированный NFT", "price": 4000, "desc": "GIF/видео"},
            {"name": "Пиксель-арт 8bit", "price": 1500, "desc": "Ретро стиль"},
        ]},
        {"name": "NFT Коллекции", "products": [
            {"name": "CryptoPunks", "price": 15000, "desc": "Коллекция"},
            {"name": "Bored Ape Yacht Club", "price": 55000, "desc": "Изображение"},
            {"name": "Azuki", "price": 25000, "desc": "Аниме стиль"},
        ]},
    ]},
    {"id": 9, "name": "🔞 Другое", "subcategories": [
        {"name": "Эксклюзив", "products": [
            {"name": "VIP доступ", "price": 5000, "desc": "Закрытый контент"},
            {"name": "Эксклюзивный товар", "price": 10000, "desc": "Только для избранных"},
            {"name": "Случайный товар-сюрприз", "price": 100, "desc": "Что-то интересное"},
        ]},
        {"name": "Коллекционное", "products": [
            {"name": "Лимитированная серия", "price": 5000, "desc": "Ограниченный тираж"},
            {"name": "Уникальный экземпляр", "price": 8000, "desc": "В единственном экземпляре"},
            {"name": "Реликвия", "price": 25000, "desc": "Настоящее сокровище"},
        ]},
    ]},
]

# ============ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ============

def generate_id():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

def get_user_status(user_id):
    if user_id not in user_stats:
        user_stats[user_id] = {'deals_total': 0, 'deals_success': 0, 'deals_failed': 0, 'status': 'new'}
    status = user_stats[user_id].get('status', 'new')
    lang = user_language.get(user_id, 'ru')
    status_data = USER_STATUSES.get(status, USER_STATUSES['new'])
    return status_data.get(lang, status_data['ru'])

def get_user_rating(user_id):
    if user_id not in reviews_db or not reviews_db[user_id]:
        return 0.0
    ratings = [r['rating'] for r in reviews_db[user_id]]
    return sum(ratings) / len(ratings)

def load_products():
    for cat in categories:
        for sub in cat["subcategories"]:
            for prod in sub["products"]:
                pid = generate_id()
                products[pid] = {
                    'id': pid, 'name': prod['name'], 'description': prod['desc'],
                    'price': prod['price'], 'category': cat['id'],
                    'category_name': cat['name'], 'subcategory': sub['name'],
                    'stock': random.randint(3, 10),
                }
    print(f"Загружено {len(products)} товаров")

# ============ УНИВЕРСАЛЬНАЯ ОТПРАВКА С БАННЕРОМ ============

async def send_menu(target, text: str, keyboard, is_new_message: bool = False):
    """
    Универсальная отправка меню с баннером или без.
    target — Message или CallbackQuery
    is_new_message — True при /start, False при callback
    """
    global BANNER_FILE_ID

    if is_new_message:
        # Просто отправляем новое сообщение
        msg = target  # это Message
        if BANNER_FILE_ID:
            try:
                await msg.answer_photo(photo=BANNER_FILE_ID, caption=text, reply_markup=keyboard)
                return
            except Exception as e:
                print(f"Баннер ошибка send: {e}")
                BANNER_FILE_ID = None
        await msg.answer(text, reply_markup=keyboard)
    else:
        # Это CallbackQuery
        call = target
        if BANNER_FILE_ID:
            # Удаляем старое, отправляем новое с фото
            try:
                await call.message.delete()
            except Exception:
                pass
            try:
                await call.message.chat.send_photo(photo=BANNER_FILE_ID, caption=text, reply_markup=keyboard)
                return
            except Exception as e:
                print(f"Баннер ошибка callback: {e}")
                BANNER_FILE_ID = None
        # Без баннера — редактируем
        try:
            await call.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            try:
                await call.message.answer(text, reply_markup=keyboard)
            except Exception:
                pass

async def edit_msg(call: CallbackQuery, text: str, keyboard):
    """Обычное редактирование без баннера (для внутренних страниц)"""
    try:
        await call.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        try:
            await call.message.answer(text, reply_markup=keyboard)
        except Exception:
            pass

# ============ КЛАВИАТУРЫ ============

def main_keyboard(user_id):
    lang = user_language.get(user_id, 'ru')
    T = TRANSLATIONS.get(lang, TRANSLATIONS['ru'])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=T['catalog'], callback_data="catalog")],
        [InlineKeyboardButton(text=T['create_deal'], callback_data="create_deal"),
         InlineKeyboardButton(text=T['sell_product'], callback_data="sell_product")],
        [InlineKeyboardButton(text=T['my_requisites'], callback_data="my_requisites"),
         InlineKeyboardButton(text=T['profile'], callback_data="profile")],
        [InlineKeyboardButton(text=T['top_sellers'], callback_data="top_sellers"),
         InlineKeyboardButton(text=T['language'], callback_data="language")],
        [InlineKeyboardButton(text=T['support'], url=f"https://t.me/{SUPPORT_USERNAME}"),
         InlineKeyboardButton(text=T['site'], url=SITE_LINK)],
    ])

def back_kb(target="back_to_menu"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data=target)]
    ])

def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users"),
         InlineKeyboardButton(text="🤝 Сделки", callback_data="admin_deals")],
        [InlineKeyboardButton(text="💰 Заявки на оплату", callback_data="admin_payments"),
         InlineKeyboardButton(text="📦 Товары", callback_data="admin_products")],
        [InlineKeyboardButton(text="⏳ Модерация", callback_data="admin_moderation"),
         InlineKeyboardButton(text="🚦 Статусы", callback_data="admin_statuses")],
        [InlineKeyboardButton(text="📝 Отзывы", callback_data="admin_reviews_panel"),
         InlineKeyboardButton(text="📸 Баннер", callback_data="admin_banner")],
        [InlineKeyboardButton(text="📋 Логи", callback_data="admin_logs"),
         InlineKeyboardButton(text="⭐ Выдать репутацию", callback_data="admin_give_rep")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")],
    ])

# ============ КОМАНДЫ ============

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    await state.clear()

    args = message.text.split()
    if len(args) > 1 and args[1].startswith('deal_'):
        deal_id = args[1].replace('deal_', '')
        deal = deals.get(deal_id)
        if deal:
            currency = deal.get('currency', 'RUB')
            amount_display = deal.get('amount_display', str(deal.get('amount', '?')))

            # Определяем куда платить
            if currency == 'TON':
                pay_info = f"💎 TON кошелёк:\n<code>{TON_WALLET}</code>"
            elif currency in ['USDT', 'USDC']:
                pay_info = f"💵 {currency} (TRC20):\n<code>{USDT_WALLET}</code>"
            elif currency in ['BTC', 'ETH', 'SOL', 'DOGE', 'XRP', 'LTC', 'ADA']:
                pay_info = f"🔗 {currency} — уточни адрес у менеджера @{MANAGER_USERNAME}"
            elif currency == 'STARS':
                pay_info = f"⭐ Telegram Stars — отправь боту @{BOT_USERNAME}"
            else:
                pay_info = f"💳 Карта / СБП:\n<code>{MANAGER_CARD}</code>"

            # Конвертация для подсказки
            hint_currencies = ['USD', 'EUR', 'KZT', 'TON', 'USDT']
            hints = []
            price_rub = deal.get('amount', 0)
            if isinstance(price_rub, (int, float)) and currency == 'RUB':
                for hc in hint_currencies:
                    hints.append(convert_rub_to(float(price_rub), hc))
            hint_line = "  |  ".join(hints) if hints else ""

            text = (
                f"📋 Сделка #{deal_id}\n\n"
                f"👤 Создатель: @{deal['buyer_username']}\n"
                f"🏷️ Тип: {deal['type']}\n"
                f"💰 Сумма: {amount_display}\n"
                + (f"💱 {hint_line}\n" if hint_line else "") +
                f"📝 Описание: {deal['description']}\n\n"
                f"━━━━━━━━━━━━━━━\n"
                f"{pay_info}\n"
                f"━━━━━━━━━━━━━━━\n\n"
                f"После оплаты нажми кнопку ниже 👇"
            )

            # Автоматически регистрируем второго участника
            if deal.get('seller_id') is None and user_id != deal['buyer_id']:
                deal['seller_id'] = user_id
                deal['seller_username'] = message.from_user.username or str(user_id)
                try:
                    await bot.send_message(
                        deal['buyer_id'],
                        f"👤 К сделке #{deal_id} присоединился @{deal['seller_username']}\n"
                        f"Сумма: {amount_display}"
                    )
                except Exception:
                    pass
                deal_markup = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_deal_{deal_id}"),
                     InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_deal_{deal_id}")],
                    [InlineKeyboardButton(text="📋 Детали", callback_data=f"deal_details_{deal_id}")],
                ])
                try:
                    await bot.send_message(
                        ADMIN_ID,
                        f"🤝 Участник вошёл в сделку!\n\n"
                        f"ID: {deal_id}\n"
                        f"Создатель: @{deal['buyer_username']}\n"
                        f"Участник: @{deal['seller_username']}\n"
                        f"Сумма: {amount_display}\n"
                        f"Описание: {deal['description']}",
                        reply_markup=deal_markup
                    )
                except Exception:
                    pass

            # Создаём заявку на оплату
            req_id = generate_id()
            payment_requests[req_id] = {
                'id': req_id, 'deal_id': deal_id,
                'buyer_id': user_id,
                'buyer_username': message.from_user.username or str(user_id),
                'amount': deal.get('amount', 0),
                'method': currency,
                'type': deal.get('type', '?'),
                'description': deal.get('description', ''),
                'status': 'pending',
                'created': datetime.now().strftime("%d.%m.%Y %H:%M"),
            }

            await message.answer(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"deal_paid_{req_id}")],
                    [InlineKeyboardButton(text="❓ Написать менеджеру", url=f"https://t.me/{MANAGER_USERNAME}")],
                    [InlineKeyboardButton(text="🔙 В меню", callback_data="back_to_menu")],
                ]),
                parse_mode="HTML"
            )
            return
        else:
            await message.answer("❌ Сделка не найдена или удалена")
            return

    if user_id not in users:
        users[user_id] = {
            'username': message.from_user.username or "нет",
            'reg_date': datetime.now().strftime("%d.%m.%Y"),
        }
        user_language[user_id] = 'ru'
        user_stats[user_id] = {'deals_total': 0, 'deals_success': 0, 'deals_failed': 0, 'status': 'new'}
        await log_event('join', user_id, f"Новый: @{message.from_user.username or 'unknown'} (id={user_id})")

    text = get_welcome_text(user_id)
    await send_menu(message, text, main_keyboard(user_id), is_new_message=True)

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа")
        return
    await message.answer("👑 Админ-панель", reply_markup=admin_keyboard())

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "ℹ️ Помощь\n\n/start — меню\n/admin — админ\n/getchatid — ID чата\n\n"
        f"Поддержка: @{SUPPORT_USERNAME}"
    )

@dp.message(Command("getchatid"))
async def cmd_getchatid(message: Message):
    text = f"ID чата: {message.chat.id}"
    if message.message_thread_id:
        text += f"\nID темы: {message.message_thread_id}"
    await message.answer(text)

# ============ НАЗАД В МЕНЮ ============

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    await state.clear()
    temp_deal_data.pop(user_id, None)
    user_states.pop(user_id, None)
    text = get_welcome_text(user_id)
    await send_menu(call, text, main_keyboard(user_id), is_new_message=False)

# ============ ЯЗЫК ============

@dp.callback_query(F.data == "language")
async def language_callback(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
         InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton(text="🇰🇿 Қазақша", callback_data="lang_kz"),
         InlineKeyboardButton(text="🇪🇸 Español", callback_data="lang_es")],
        [InlineKeyboardButton(text="🇩🇪 Deutsch", callback_data="lang_de")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")],
    ])
    await edit_msg(call, "🌐 Выбери язык / Choose language:", kb)

@dp.callback_query(F.data.in_({"lang_ru", "lang_en", "lang_kz", "lang_es", "lang_de"}))
async def set_language(call: CallbackQuery):
    user_id = call.from_user.id
    lang = call.data.split("_")[1]
    user_language[user_id] = lang
    msgs = {'ru': '✅ Русский', 'en': '✅ English', 'kz': '✅ Қазақша', 'es': '✅ Español', 'de': '✅ Deutsch'}
    await call.answer(msgs.get(lang, '✅'))
    text = get_welcome_text(user_id)
    await send_menu(call, text, main_keyboard(user_id), is_new_message=False)

# ============ ТОП ПРОДАВЦОВ ============

@dp.callback_query(F.data == "top_sellers")
async def top_sellers_callback(call: CallbackQuery):
    text = "⭐ Топ продавцов\n\n"
    for i, s in enumerate(TOP_SELLERS, 1):
        text += f"{i}. {s['name']} — {s['deals']} сделок, рейтинг {s['rating']}\n"
    await edit_msg(call, text, back_kb())

# ============ ПРОФИЛЬ ============

@dp.callback_query(F.data == "profile")
async def profile_callback(call: CallbackQuery):
    user_id = call.from_user.id
    user = users.get(user_id, {})
    stats = user_stats.get(user_id, {'deals_total': 0, 'deals_success': 0, 'deals_failed': 0, 'status': 'new'})
    rating = get_user_rating(user_id)
    reviews_count = len(reviews_db.get(user_id, []))
    req = user_requisites.get(user_id, {})
    text = (
        f"👤 Профиль\n\nID: {user_id}\n"
        f"Username: @{user.get('username', 'нет')}\n"
        f"Регистрация: {user.get('reg_date', '—')}\n"
        f"Статус: {get_user_status(user_id)}\n"
        f"Рейтинг: {rating:.1f}/5 ({reviews_count} отзывов)\n"
        f"Реквизиты: {req.get('card', 'не указаны')}\n\n"
        f"Сделки:\n  Всего: {stats['deals_total']}\n"
        f"  Успешных: {stats['deals_success']}\n"
        f"  Провалено: {stats['deals_failed']}"
    )
    await edit_msg(call, text, InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Оставить отзыв", callback_data="leave_review")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")],
    ]))

@dp.callback_query(F.data == "leave_review")
async def leave_review_callback(call: CallbackQuery):
    user_id = call.from_user.id
    user_states[user_id] = {'action': 'review_select_user'}
    await edit_msg(call, "Введи ID или @username пользователя для отзыва:", back_kb("profile"))

@dp.callback_query(F.data.startswith("rating_"))
async def rating_callback(call: CallbackQuery):
    user_id = call.from_user.id
    rating = int(call.data.split("_")[1])
    target_id = user_states.get(user_id, {}).get('target_id', user_id)
    user_states[user_id] = {'action': 'review_text', 'rating': rating, 'target_id': target_id}
    await edit_msg(call, f"Рейтинг: {rating}/5\n\nНапиши отзыв:", back_kb("profile"))

# ============ РЕКВИЗИТЫ ============

@dp.callback_query(F.data == "my_requisites")
async def my_requisites_callback(call: CallbackQuery):
    user_id = call.from_user.id
    req = user_requisites.get(user_id, {})
    text = (
        f"💰 Мои реквизиты\n\n"
        f"Карта/СБП: {req.get('card', 'не указаны')}\n"
        f"TON: {req.get('ton', 'не указан')}\n"
        f"USDT: {req.get('usdt', 'не указан')}\n\nВыбери что изменить:"
    )
    await edit_msg(call, text, InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Карта / СБП", callback_data="set_req_card")],
        [InlineKeyboardButton(text="💎 TON кошелёк", callback_data="set_req_ton")],
        [InlineKeyboardButton(text="💵 USDT кошелёк", callback_data="set_req_usdt")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")],
    ]))

@dp.callback_query(F.data.in_({"set_req_card", "set_req_ton", "set_req_usdt"}))
async def set_req_callback(call: CallbackQuery):
    user_id = call.from_user.id
    field_map = {"set_req_card": "card", "set_req_ton": "ton", "set_req_usdt": "usdt"}
    label_map = {"set_req_card": "номер карты или СБП", "set_req_ton": "TON адрес", "set_req_usdt": "USDT адрес"}
    field = field_map[call.data]
    user_states[user_id] = {'action': 'set_req', 'field': field}
    await edit_msg(call, f"Введи {label_map[call.data]}:", back_kb("my_requisites"))

# ============ КАТАЛОГ ============

@dp.callback_query(F.data == "catalog")
async def catalog_callback(call: CallbackQuery):
    buttons = [[InlineKeyboardButton(text=cat["name"], callback_data=f"cat_{cat['id']}")] for cat in categories]
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
    await edit_msg(call, "🛒 Каталог — выбери категорию:", InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("cat_"))
async def category_callback(call: CallbackQuery):
    cat_id = int(call.data.split("_")[1])
    cat = next((c for c in categories if c["id"] == cat_id), None)
    if not cat:
        await call.answer("Не найдено")
        return
    buttons = [[InlineKeyboardButton(text=sub["name"], callback_data=f"sub_{cat_id}_{i}")] for i, sub in enumerate(cat["subcategories"])]
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="catalog")])
    await edit_msg(call, f"{cat['name']}\n\nВыбери подкатегорию:", InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("sub_"))
async def subcategory_callback(call: CallbackQuery):
    parts = call.data.split("_")
    cat_id, sub_idx = int(parts[1]), int(parts[2])
    cat = next((c for c in categories if c["id"] == cat_id), None)
    if not cat or sub_idx >= len(cat["subcategories"]):
        await call.answer()
        return
    sub = cat["subcategories"][sub_idx]
    sub_products = [(pid, p) for pid, p in products.items() if p['category'] == cat_id and p['subcategory'] == sub['name']]
    buttons = [[InlineKeyboardButton(text=f"{p['name']} — {p['price']}₽", callback_data=f"prod_{pid}")] for pid, p in sub_products[:20]]
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"cat_{cat_id}")])
    await edit_msg(call, f"📦 {sub['name']}\n\nВыбери товар:", InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("prod_"))
async def product_callback(call: CallbackQuery):
    pid = call.data[5:]
    p = products.get(pid)
    if not p:
        await call.answer("Товар не найден")
        return

    user_id = call.from_user.id
    lang = user_language.get(user_id, 'ru')
    price_rub = p['price']

    # Конвертация цены в популярные валюты
    show_currencies = {
        'ru': ['USD', 'EUR', 'KZT', 'UAH', 'TON', 'USDT'],
        'en': ['USD', 'EUR', 'GBP', 'TON', 'USDT'],
        'kz': ['KZT', 'RUB', 'USD', 'EUR', 'TON'],
        'es': ['USD', 'EUR', 'GBP', 'TON'],
        'de': ['EUR', 'USD', 'GBP', 'TON'],
    }.get(lang, ['USD', 'EUR', 'TON', 'USDT'])

    hints = [convert_rub_to(float(price_rub), cur) for cur in show_currencies]
    hint_text = "  |  ".join(hints)

    # Ссылка на товар
    product_link = f"https://t.me/{BOT_USERNAME}?start=prod_{pid}"

    text = (
        f"📦 {p['name']}\n\n"
        f"📝 {p['description']}\n\n"
        f"🔗 Ссылка: {product_link}\n"
        f"💰 Цена: {price_rub}₽\n"
        f"💱 {hint_text}\n"
        f"📊 В наличии: {p['stock']} шт."
    )

    cat = next((c for c in categories if c["id"] == p['category']), None)
    sub_idx = 0
    if cat:
        for i, s in enumerate(cat["subcategories"]):
            if s["name"] == p['subcategory']:
                sub_idx = i
                break

    await edit_msg(call, text, InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Купить", callback_data=f"buy_{pid}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"sub_{p['category']}_{sub_idx}")],
    ]))

@dp.callback_query(F.data.startswith("buy_"))
async def buy_callback(call: CallbackQuery):
    pid = call.data[4:]
    p = products.get(pid)
    if not p:
        await call.answer()
        return
    price_rub = p['price']
    ton_hint = convert_rub_to(float(price_rub), 'TON')
    usdt_hint = convert_rub_to(float(price_rub), 'USDT')

    text = (
        f"🛒 Покупка: {p['name']}\n\n"
        f"💰 Цена: {price_rub}₽\n\n"
        f"Выбери способ оплаты:"
    )
    await edit_msg(call, text, InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💳 Карта / СБП — {price_rub}₽", callback_data=f"pay_card_{pid}")],
        [InlineKeyboardButton(text=f"💎 TON — {ton_hint}", callback_data=f"pay_ton_{pid}")],
        [InlineKeyboardButton(text=f"💵 USDT — {usdt_hint}", callback_data=f"pay_usdt_{pid}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"prod_{pid}")],
    ]))

@dp.callback_query(F.data.startswith("pay_"))
async def pay_callback(call: CallbackQuery):
    parts = call.data.split("_", 2)
    method, pid = parts[1], parts[2]
    p = products.get(pid)
    if not p:
        await call.answer()
        return

    price_rub = p['price']
    if method == "card":
        details = f"💳 Карта / СБП:\n{MANAGER_CARD}"
        hint = f"Сумма к оплате: {price_rub}₽"
    elif method == "ton":
        ton_amount = convert_rub_to(float(price_rub), 'TON')
        details = f"💎 TON кошелёк:\n{TON_WALLET}"
        hint = f"Сумма: {price_rub}₽  ({ton_amount})"
    else:
        usdt_amount = convert_rub_to(float(price_rub), 'USDT')
        details = f"💵 USDT (TRC20):\n{USDT_WALLET}"
        hint = f"Сумма: {price_rub}₽  ({usdt_amount})"

    text = (
        f"💰 Оплата: {p['name']}\n\n"
        f"{details}\n\n"
        f"{hint}\n\n"
        f"После оплаты нажми кнопку «Я оплатил» 👇\n"
        f"Вопросы: @{MANAGER_USERNAME}"
    )
    await edit_msg(call, text, InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"paid_{pid}_{method}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"buy_{pid}")],
    ]))

@dp.callback_query(F.data.startswith("paid_"))
async def paid_callback(call: CallbackQuery):
    parts = call.data.split("_", 2)
    pid, method = parts[1], parts[2]
    p = products.get(pid)
    user_id = call.from_user.id
    username = call.from_user.username or str(user_id)

    req_id = generate_id()
    payment_requests[req_id] = {
        'id': req_id, 'deal_id': None, 'product_id': pid,
        'product_name': p['name'] if p else '?',
        'buyer_id': user_id, 'buyer_username': username,
        'amount': p['price'] if p else 0,
        'method': method, 'type': 'catalog',
        'description': f"Покупка: {p['name']}" if p else "Покупка",
        'status': 'pending',
        'created': datetime.now().strftime("%d.%m.%Y %H:%M"),
    }

    await edit_msg(call,
        f"Заявка отправлена!\n\nМенеджер @{MANAGER_USERNAME} проверит и свяжется.\nОбычно до 15 минут.",
        back_kb()
    )

    await log_event('deal_paid', user_id, f"@{username} оплатил: {p['name'] if p else '?'} ({method})")

    try:
        await bot.send_message(ADMIN_ID,
            f"🛒 Новая заявка!\n\nID: {req_id}\n@{username} (id={user_id})\n"
            f"Товар: {p['name'] if p else '?'}\nСумма: {p['price'] if p else '?'}₽\nМетод: {method}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Оплата получена / Товар передан", callback_data=f"payment_confirm_{req_id}")],
                [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"payment_reject_{req_id}")],
            ])
        )
    except Exception:
        pass

# Оплата по сделке
@dp.callback_query(F.data.startswith("deal_paid_"))
async def deal_paid_callback(call: CallbackQuery):
    req_id = call.data.replace("deal_paid_", "")
    req = payment_requests.get(req_id)
    if not req:
        await call.answer("❌ Заявка не найдена")
        return
    req['status'] = 'pending_confirm'
    user_id = call.from_user.id
    username = call.from_user.username or str(user_id)
    await edit_msg(call,
        f"Заявка об оплате отправлена!\n\nОжидай подтверждения менеджера @{MANAGER_USERNAME}.",
        back_kb()
    )
    try:
        await bot.send_message(ADMIN_ID,
            f"💰 Оплата по сделке!\n\nID заявки: {req_id}\nСделка: {req.get('deal_id','?')}\n"
            f"@{username} (id={user_id})\nСумма: {req.get('amount','?')}\nМетод: {req.get('method','?')}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Оплата получена", callback_data=f"payment_confirm_{req_id}")],
                [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"payment_reject_{req_id}")],
            ])
        )
    except Exception:
        pass

# ============ СОЗДАТЬ СДЕЛКУ ============

@dp.callback_query(F.data == "create_deal")
async def create_deal_callback(call: CallbackQuery):
    await edit_msg(call, "🤝 Создать сделку\n\nВыбери тип:", InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 Игры / Аккаунты", callback_data="deal_type_game")],
        [InlineKeyboardButton(text="🎁 NFT / Подарки Telegram", callback_data="deal_type_nft")],
        [InlineKeyboardButton(text="🔗 NFT Username (TON)", callback_data="deal_type_nft_username")],
        [InlineKeyboardButton(text="💼 Услуги", callback_data="deal_type_service")],
        [InlineKeyboardButton(text="⭐ Telegram Stars", callback_data="deal_type_stars")],
        [InlineKeyboardButton(text="💎 Крипто", callback_data="deal_type_crypto")],
        [InlineKeyboardButton(text="📦 Товары / Другое", callback_data="deal_type_goods")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")],
    ]))

@dp.callback_query(F.data.startswith("deal_type_"))
async def deal_type_callback(call: CallbackQuery):
    user_id = call.from_user.id
    deal_type = call.data.replace("deal_type_", "")
    temp_deal_data[user_id] = {'type': deal_type, 'buyer_id': user_id}

    if deal_type == 'crypto':
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 TON", callback_data=f"cur_{deal_type}_TON"),
             InlineKeyboardButton(text="₿ BTC", callback_data=f"cur_{deal_type}_BTC"),
             InlineKeyboardButton(text="Ξ ETH", callback_data=f"cur_{deal_type}_ETH")],
            [InlineKeyboardButton(text="₮ USDT", callback_data=f"cur_{deal_type}_USDT"),
             InlineKeyboardButton(text="USDC", callback_data=f"cur_{deal_type}_USDC"),
             InlineKeyboardButton(text="SOL", callback_data=f"cur_{deal_type}_SOL")],
            [InlineKeyboardButton(text="DOGE", callback_data=f"cur_{deal_type}_DOGE"),
             InlineKeyboardButton(text="XRP", callback_data=f"cur_{deal_type}_XRP"),
             InlineKeyboardButton(text="LTC", callback_data=f"cur_{deal_type}_LTC")],
            [InlineKeyboardButton(text="ADA", callback_data=f"cur_{deal_type}_ADA"),
             InlineKeyboardButton(text="₽ RUB", callback_data=f"cur_{deal_type}_RUB"),
             InlineKeyboardButton(text="$ USD", callback_data=f"cur_{deal_type}_USD")],
            [InlineKeyboardButton(text="€ EUR", callback_data=f"cur_{deal_type}_EUR"),
             InlineKeyboardButton(text="£ GBP", callback_data=f"cur_{deal_type}_GBP")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="create_deal")],
        ])
    elif deal_type == 'stars':
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Telegram Stars", callback_data=f"cur_{deal_type}_STARS")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="create_deal")],
        ])
    elif deal_type == 'nft_username':
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 TON", callback_data=f"cur_{deal_type}_TON"),
             InlineKeyboardButton(text="₽ RUB", callback_data=f"cur_{deal_type}_RUB"),
             InlineKeyboardButton(text="$ USD", callback_data=f"cur_{deal_type}_USD")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="create_deal")],
        ])
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="₽ RUB", callback_data=f"cur_{deal_type}_RUB"),
             InlineKeyboardButton(text="$ USD", callback_data=f"cur_{deal_type}_USD"),
             InlineKeyboardButton(text="€ EUR", callback_data=f"cur_{deal_type}_EUR")],
            [InlineKeyboardButton(text="£ GBP", callback_data=f"cur_{deal_type}_GBP"),
             InlineKeyboardButton(text="₴ UAH", callback_data=f"cur_{deal_type}_UAH"),
             InlineKeyboardButton(text="₸ KZT", callback_data=f"cur_{deal_type}_KZT")],
            [InlineKeyboardButton(text="Br BYN", callback_data=f"cur_{deal_type}_BYN"),
             InlineKeyboardButton(text="₺ TRY", callback_data=f"cur_{deal_type}_TRY"),
             InlineKeyboardButton(text="¥ CNY", callback_data=f"cur_{deal_type}_CNY")],
            [InlineKeyboardButton(text="₾ GEL", callback_data=f"cur_{deal_type}_GEL"),
             InlineKeyboardButton(text="֏ AMD", callback_data=f"cur_{deal_type}_AMD"),
             InlineKeyboardButton(text="₼ AZN", callback_data=f"cur_{deal_type}_AZN")],
            [InlineKeyboardButton(text="💎 TON", callback_data=f"cur_{deal_type}_TON"),
             InlineKeyboardButton(text="₮ USDT", callback_data=f"cur_{deal_type}_USDT"),
             InlineKeyboardButton(text="⭐ STARS", callback_data=f"cur_{deal_type}_STARS")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="create_deal")],
        ])
    await edit_msg(call, "💱 Выбери валюту:", kb)

@dp.callback_query(F.data.startswith("cur_"))
async def currency_callback(call: CallbackQuery):
    user_id = call.from_user.id
    parts = call.data.split("_", 2)
    currency = parts[2]
    temp_deal_data.setdefault(user_id, {})['currency'] = currency
    temp_deal_data[user_id]['currency_symbol'] = CURRENCY_SYMBOLS.get(currency, currency)
    user_states[user_id] = {'action': 'deal_amount'}

    sym = CURRENCY_SYMBOLS.get(currency, currency)
    # Показываем подсказку: 5000₽ в этой валюте
    example_rub = 5000
    example_hint = convert_rub_to(float(example_rub), currency)

    if currency in CRYPTO_CURRENCIES:
        prompt = (
            f"💰 Введи сумму в {currency}:\n\n"
            f"Пример: 1.5 {sym}\n\n"
            f"Для справки: {example_rub}₽ = {example_hint}"
        )
    elif currency == 'STARS':
        prompt = (
            f"⭐ Введи количество Stars:\n\n"
            f"Пример: 500\n\n"
            f"Для справки: {example_rub}₽ = {example_hint}"
        )
    else:
        prompt = (
            f"💰 Введи сумму в {currency} ({sym}):\n\n"
            f"Пример: 5000\n\n"
            f"Для справки: {example_rub}₽ = {example_hint}"
        )

    await edit_msg(call, prompt, back_kb("create_deal"))

# ============ ПРОДАТЬ ТОВАР ============

@dp.callback_query(F.data == "sell_product")
async def sell_product_callback(call: CallbackQuery):
    user_id = call.from_user.id
    user_states[user_id] = {'action': 'sell_name'}
    await edit_msg(call, "📤 Продать товар\n\nВведи название товара:", back_kb())

# ============ ПОДТВЕРЖДЕНИЕ / ОТКЛОНЕНИЕ СДЕЛКИ ============

@dp.callback_query(F.data.startswith("confirm_deal_"))
async def confirm_deal_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ Только администратор", show_alert=True)
        return
    deal_id = call.data.replace("confirm_deal_", "")
    deal = deals.get(deal_id)
    if not deal:
        await call.answer("❌ Сделка не найдена")
        return
    deal['status'] = 'confirmed'
    await call.answer("✅ Сделка подтверждена!", show_alert=True)
    for uid in [deal.get('buyer_id'), deal.get('seller_id')]:
        if uid:
            try:
                await bot.send_message(uid, f"✅ Сделка #{deal_id} подтверждена!\nСумма: {deal.get('amount_display', deal['amount'])}")
            except Exception:
                pass
    try:
        await call.message.edit_text(f"✅ Сделка {deal_id} подтверждена.", reply_markup=back_kb("admin_panel"))
    except Exception:
        pass

@dp.callback_query(F.data.startswith("reject_deal_"))
async def reject_deal_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ Только администратор", show_alert=True)
        return
    deal_id = call.data.replace("reject_deal_", "")
    deal = deals.get(deal_id)
    if not deal:
        await call.answer("❌ Сделка не найдена")
        return
    deal['status'] = 'rejected'
    await call.answer("❌ Сделка отклонена!", show_alert=True)
    for uid in [deal.get('buyer_id'), deal.get('seller_id')]:
        if uid:
            try:
                await bot.send_message(uid, f"❌ Сделка #{deal_id} отклонена.\nСвяжитесь с @{MANAGER_USERNAME}")
            except Exception:
                pass
    try:
        await call.message.edit_text(f"❌ Сделка {deal_id} отклонена.", reply_markup=back_kb("admin_panel"))
    except Exception:
        pass

@dp.callback_query(F.data.startswith("deal_details_"))
async def deal_details_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ Только администратор", show_alert=True)
        return
    deal_id = call.data.replace("deal_details_", "")
    deal = deals.get(deal_id)
    if not deal:
        await call.answer("❌ Не найдена")
        return
    text = (
        f"📋 Детали #{deal_id}\n\n"
        f"Статус: {deal['status']}\nДата: {deal['created']}\n\n"
        f"Создатель: @{deal['buyer_username']} (id={deal['buyer_id']})\n"
        f"Участник: @{deal.get('seller_username','?')} (id={deal.get('seller_id','?')})\n\n"
        f"Сумма: {deal.get('amount_display', deal['amount'])}\n"
        f"Тип: {deal['type']}\nОписание: {deal['description']}"
    )
    await edit_msg(call, text, back_kb("admin_deals"))

# ============ АДМИН-ПАНЕЛЬ ============

@dp.callback_query(F.data == "admin_panel")
async def admin_panel_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ Нет доступа", show_alert=True)
        return
    await edit_msg(call, "👑 Админ-панель", admin_keyboard())

@dp.callback_query(F.data == "admin_stats")
async def admin_stats_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer()
        return
    pending_pay = len([r for r in payment_requests.values() if r.get('status') == 'pending'])
    text = (
        f"📊 Статистика\n\nПользователей: {len(users)}\nТоваров: {len(products)}\n"
        f"Сделок: {len(deals)}\nЗаявок (ожидают): {pending_pay}\n"
        f"Логи: {'вкл' if LOG_CHAT_ID else 'выкл'}\n"
        f"Баннер: {'загружен ✅' if BANNER_FILE_ID else 'нет ❌'}"
    )
    await edit_msg(call, text, admin_keyboard())

@dp.callback_query(F.data == "admin_users")
async def admin_users_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer()
        return
    text = f"👥 Пользователи ({len(users)} чел.)\n\n"
    for uid, u in list(users.items())[:15]:
        stats = user_stats.get(uid, {})
        status = USER_STATUSES.get(stats.get('status', 'new'), USER_STATUSES['new'])['ru']
        text += f"• @{u.get('username','нет')} (id={uid}) — {status}\n"
    await edit_msg(call, text, back_kb("admin_panel"))

@dp.callback_query(F.data == "admin_deals")
async def admin_deals_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer()
        return
    text = f"🤝 Сделки ({len(deals)})\n\n"
    for did, d in list(deals.items())[:10]:
        text += f"• #{did} — {d.get('type','?')} — {d.get('amount_display', d.get('amount','?'))} — {d.get('status','?')}\n"
    if not deals:
        text += "Пока нет."
    await edit_msg(call, text, back_kb("admin_panel"))

@dp.callback_query(F.data == "admin_statuses")
async def admin_statuses_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer()
        return
    user_states[call.from_user.id] = {'action': 'admin_set_status_id'}
    await edit_msg(call, "🚦 Изменить статус\n\nВведи ID пользователя:", back_kb("admin_panel"))

@dp.callback_query(F.data == "admin_give_rep")
async def admin_give_rep_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer()
        return
    user_states[call.from_user.id] = {'action': 'admin_give_reputation'}
    await edit_msg(call, "⭐ Выдать репутацию\n\nВведи ID или @username:", back_kb("admin_panel"))

@dp.callback_query(F.data.startswith("give_rep_"))
async def give_reputation_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ Только администратор", show_alert=True)
        return
    parts = call.data.split("_")
    rating, target_id = int(parts[2]), int(parts[3])
    reviews_db.setdefault(target_id, []).append({
        'author_id': ADMIN_ID, 'author_username': 'АДМИНИСТРАТОР',
        'rating': rating, 'text': 'Репутация выдана администратором',
        'created': datetime.now().strftime("%d.%m.%Y %H:%M"),
    })
    try:
        await bot.send_message(target_id, f"⭐ Репутация выдана!\n\nРейтинг: {rating}/5")
    except Exception:
        pass
    await call.answer("✅ Выдана!", show_alert=True)
    try:
        await call.message.edit_text(f"✅ Репутация {rating}/5 → пользователю {target_id}", reply_markup=back_kb("admin_panel"))
    except Exception:
        pass

@dp.callback_query(F.data == "admin_reviews_panel")
async def admin_reviews_panel_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer()
        return
    count = sum(len(v) for v in reviews_db.values())
    await edit_msg(call, f"📝 Отзывы\n\nВсего: {count}\nМодерация: {len(moderation_queue)}", back_kb("admin_panel"))

@dp.callback_query(F.data == "admin_moderation")
async def admin_moderation_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer()
        return
    if not moderation_queue:
        await edit_msg(call, "✅ Очередь пуста.", back_kb("admin_panel"))
        return
    item = moderation_queue[0]
    text = f"Модерация ({len(moderation_queue)})\n\n@{item.get('username','?')}\n{item.get('name','?')}\n{item.get('price','?')}₽\n{item.get('desc','?')}"
    await edit_msg(call, text, InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Одобрить", callback_data="mod_approve"),
         InlineKeyboardButton(text="❌ Отклонить", callback_data="mod_reject")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")],
    ]))

@dp.callback_query(F.data.in_({"mod_approve", "mod_reject"}))
async def mod_action_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer()
        return
    if moderation_queue:
        item = moderation_queue.pop(0)
        if call.data == "mod_approve":
            pid = generate_id()
            products[pid] = {'id': pid, 'name': item['name'], 'description': item.get('desc', ''),
                'price': item['price'], 'category': 9, 'category_name': '🔞 Другое',
                'subcategory': 'Эксклюзив', 'stock': 1}
            await call.answer("✅ Одобрено", show_alert=True)
        else:
            await call.answer("❌ Отклонено", show_alert=True)
    await edit_msg(call, "👑 Админ-панель", admin_keyboard())

@dp.callback_query(F.data == "admin_products")
async def admin_products_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer()
        return
    cat_counts = {}
    for p in products.values():
        cn = p.get('category_name', '?')
        cat_counts[cn] = cat_counts.get(cn, 0) + 1
    text = f"📦 Товары ({len(products)} шт.)\n\n" + "\n".join(f"• {cn}: {cnt}" for cn, cnt in cat_counts.items())
    await edit_msg(call, text, back_kb("admin_panel"))

# ============ БАННЕР ============

@dp.callback_query(F.data == "admin_banner")
async def admin_banner_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer()
        return
    status = "загружен ✅" if BANNER_FILE_ID else "не загружен ❌"
    text = (
        f"📸 Баннер: {status}\n\n"
        f"Как загрузить:\n"
        f"1. Отправь команду /admin_upload\n"
        f"2. Сразу после этого отправь фото\n\n"
        f"Баннер показывается в главном меню."
    )
    await edit_msg(call, text, InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑️ Удалить баннер", callback_data="delete_banner")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")],
    ]))

@dp.callback_query(F.data == "delete_banner")
async def delete_banner_callback(call: CallbackQuery):
    global BANNER_FILE_ID
    if call.from_user.id != ADMIN_ID:
        await call.answer()
        return
    BANNER_FILE_ID = None
    await call.answer("✅ Баннер удалён", show_alert=True)
    await edit_msg(call, "📸 Баннер удалён.", back_kb("admin_panel"))

@dp.message(Command("admin_upload"))
async def admin_upload_banner(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    user_states[message.from_user.id] = {'action': 'upload_banner'}
    await message.answer("📸 Теперь отправь фото для баннера:")

@dp.message(F.photo)
async def handle_photo(message: Message):
    global BANNER_FILE_ID
    user_id = message.from_user.id
    if user_states.get(user_id, {}).get('action') == 'upload_banner' and user_id == ADMIN_ID:
        BANNER_FILE_ID = message.photo[-1].file_id
        user_states.pop(user_id, None)
        await message.answer(
            f"✅ Баннер загружен успешно!\n\n"
            f"Теперь при открытии главного меню будет показываться это фото.\n"
            f"Проверь: напиши /start"
        )

# ============ ЛОГИ ============

@dp.callback_query(F.data == "admin_logs")
async def admin_logs_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ Нет доступа", show_alert=True)
        return
    text = f"📋 Логи: {'вкл (чат ' + str(LOG_CHAT_ID) + ')' if LOG_CHAT_ID else 'выкл'}"
    await edit_msg(call, text, InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Установить", callback_data="set_log_chat")],
        [InlineKeyboardButton(text="❌ Отключить", callback_data="disable_logs")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")],
    ]))

@dp.callback_query(F.data == "set_log_chat")
async def set_log_chat_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer()
        return
    user_states[call.from_user.id] = {'action': 'set_log_chat_id'}
    await edit_msg(call, "Введи ID чата (например -1001234567890):", back_kb("admin_logs"))

@dp.callback_query(F.data == "disable_logs")
async def disable_logs_callback(call: CallbackQuery):
    global LOG_CHAT_ID, LOG_THREAD_ID
    if call.from_user.id != ADMIN_ID:
        await call.answer()
        return
    LOG_CHAT_ID = None
    LOG_THREAD_ID = None
    await call.answer("✅ Логи выключены", show_alert=True)
    await edit_msg(call, "👑 Админ-панель", admin_keyboard())

# ============ ЗАЯВКИ НА ОПЛАТУ ============

@dp.callback_query(F.data == "admin_payments")
async def admin_payments_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer()
        return
    pending = [r for r in payment_requests.values() if r.get('status') == 'pending']
    if not pending:
        await edit_msg(call, "💰 Нет ожидающих заявок.", back_kb("admin_panel"))
        return
    req = pending[0]
    text = (
        f"💰 Заявок: {len(pending)}\n\n"
        f"ID: {req['id']}\n@{req['buyer_username']} (id={req['buyer_id']})\n"
        f"Товар/услуга: {req.get('description','?')}\n"
        f"Сумма: {req['amount']}\nМетод: {req.get('method','?')}\n"
        f"Создано: {req['created']}"
    )
    await edit_msg(call, text, InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Оплата получена / Товар передан", callback_data=f"payment_confirm_{req['id']}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"payment_reject_{req['id']}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")],
    ]))

@dp.callback_query(F.data.startswith("payment_confirm_"))
async def payment_confirm_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ Только администратор", show_alert=True)
        return
    req_id = call.data.replace("payment_confirm_", "")
    req = payment_requests.get(req_id)
    if not req:
        await call.answer("❌ Не найдено")
        return
    req['status'] = 'paid'
    buyer_id = req['buyer_id']
    try:
        await bot.send_message(buyer_id,
            f"✅ ОПЛАТА ПОДТВЕРЖДЕНА!\n\nСумма: {req['amount']}\nВопросы: @{MANAGER_USERNAME}"
        )
    except Exception:
        pass
    await call.answer("✅ Подтверждено!", show_alert=True)
    await log_event('payment_confirmed', buyer_id, f"Заявка {req_id} подтверждена")
    try:
        await call.message.edit_text("✅ Оплата подтверждена.", reply_markup=back_kb("admin_payments"))
    except Exception:
        pass

@dp.callback_query(F.data.startswith("payment_reject_"))
async def payment_reject_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ Только администратор", show_alert=True)
        return
    req_id = call.data.replace("payment_reject_", "")
    req = payment_requests.get(req_id)
    if not req:
        await call.answer("❌ Не найдено")
        return
    req['status'] = 'rejected'
    buyer_id = req['buyer_id']
    try:
        await bot.send_message(buyer_id, f"❌ Оплата отклонена.\n\nСвяжитесь с @{MANAGER_USERNAME}")
    except Exception:
        pass
    await call.answer("❌ Отклонено!", show_alert=True)
    await log_event('payment_rejected', buyer_id, f"Заявка {req_id} отклонена")
    try:
        await call.message.edit_text("❌ Оплата отклонена.", reply_markup=back_kb("admin_payments"))
    except Exception:
        pass

# ============ ОБРАБОТКА ТЕКСТА ============

@dp.message(F.text)
async def handle_text(message: Message, state: FSMContext):
    global LOG_CHAT_ID, LOG_THREAD_ID
    user_id = message.from_user.id
    state_data = user_states.get(user_id, {})
    action = state_data.get('action')
    if not action:
        return
    text = message.text.strip()

    if action == 'deal_amount':
        currency = temp_deal_data.get(user_id, {}).get('currency', 'RUB')
        currency_symbol = temp_deal_data.get(user_id, {}).get('currency_symbol', '₽')
        try:
            if currency in CRYPTO_CURRENCIES:
                amount = float(text.replace(',', '.'))
                temp_deal_data[user_id]['amount'] = amount
                temp_deal_data[user_id]['amount_display'] = f"{amount} {currency}"
            elif currency == 'STARS':
                amount = int(text.replace(' ', '').replace(',', ''))
                temp_deal_data[user_id]['amount'] = amount
                temp_deal_data[user_id]['amount_display'] = f"{amount} ⭐"
            else:
                amount = float(text.replace(' ', '').replace(',', '.'))
                temp_deal_data[user_id]['amount'] = amount
                temp_deal_data[user_id]['amount_display'] = f"{amount}{currency_symbol}"
            user_states[user_id] = {'action': 'deal_description'}
            display = temp_deal_data[user_id].get('amount_display', text)
            await message.answer(f"Сумма: {display}\n\n📝 Опиши что продаётся/покупается:", reply_markup=back_kb("create_deal"))
        except ValueError:
            await message.answer("❌ Введи сумму числом, например: 5000")
        return

    if action == 'deal_description':
        deal_data = temp_deal_data.get(user_id, {})
        deal_id = generate_id()
        buyer_id = deal_data.get('buyer_id', user_id)
        buyer_username = message.from_user.username or str(buyer_id)
        amount_display = deal_data.get('amount_display', str(deal_data.get('amount', 0)))
        currency = deal_data.get('currency', 'RUB')

        deals[deal_id] = {
            'id': deal_id, 'buyer_id': buyer_id, 'seller_id': None,
            'buyer_username': buyer_username, 'seller_username': '?',
            'type': deal_data.get('type', '?'), 'currency': currency,
            'amount': deal_data.get('amount', 0), 'amount_display': amount_display,
            'description': text, 'status': 'pending',
            'created': datetime.now().strftime("%d.%m.%Y %H:%M"),
        }
        user_stats.setdefault(buyer_id, {'deals_total': 0, 'deals_success': 0, 'deals_failed': 0, 'status': 'new'})
        user_stats[buyer_id]['deals_total'] += 1
        temp_deal_data.pop(user_id, None)
        del user_states[user_id]

        deal_link = f"https://t.me/{BOT_USERNAME}?start=deal_{deal_id}"
        await message.answer(
            f"✅ Сделка создана!\n\nID: {deal_id}\nСумма: {amount_display}\nОписание: {text}\n\n"
            f"Ссылка для второго участника:\n{deal_link}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔗 Открыть сделку", url=deal_link)],
                [InlineKeyboardButton(text="🔙 Меню", callback_data="back_to_menu")],
            ])
        )
        await log_event('deal_created', buyer_id, f"Сделка @{buyer_username} — {amount_display}")
        return

    if action == 'review_select_user':
        target_text = text.lstrip('@').lower()
        target_id = None
        try:
            target_id = int(target_text)
            if target_id not in users:
                target_id = None
        except ValueError:
            pass
        if not target_id:
            for uid, u in users.items():
                if u.get('username', '').lower() == target_text:
                    target_id = uid
                    break
        if not target_id:
            await message.answer("❌ Пользователь не найден")
            return
        target_username = users.get(target_id, {}).get('username', f"id{target_id}")
        user_states[user_id] = {'action': 'review_rating', 'target_id': target_id}
        await message.answer(f"Оцени @{target_username}:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐", callback_data="rating_1"),
             InlineKeyboardButton(text="⭐⭐", callback_data="rating_2"),
             InlineKeyboardButton(text="⭐⭐⭐", callback_data="rating_3")],
            [InlineKeyboardButton(text="⭐⭐⭐⭐", callback_data="rating_4"),
             InlineKeyboardButton(text="⭐⭐⭐⭐⭐", callback_data="rating_5")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="profile")],
        ]))
        return

    if action == 'review_text':
        rating = state_data.get('rating', 5)
        target_id = state_data.get('target_id', user_id)
        reviews_db.setdefault(target_id, []).append({
            'author_id': user_id, 'author_username': message.from_user.username,
            'rating': rating, 'text': text[:500],
            'created': datetime.now().strftime("%d.%m.%Y %H:%M"),
        })
        del user_states[user_id]
        target_username = users.get(target_id, {}).get('username', f"id{target_id}")
        await message.answer(f"✅ Отзыв добавлен!\n\nДля: @{target_username}\nРейтинг: {rating}/5", reply_markup=back_kb())
        await log_event('review_left', user_id, f"@{message.from_user.username} → отзыв {rating}/5 для {target_id}")
        return

    if action == 'set_req':
        field = state_data['field']
        user_requisites.setdefault(user_id, {})[field] = text
        del user_states[user_id]
        await message.answer("✅ Реквизиты сохранены!", reply_markup=back_kb("my_requisites"))
        return

    if action == 'set_log_chat_id':
        try:
            LOG_CHAT_ID = int(text)
            user_states[user_id] = {'action': 'set_log_thread_id'}
            await message.answer(f"Чат: {LOG_CHAT_ID}\n\nВведи ID темы или 0 для общего чата:")
        except ValueError:
            await message.answer("❌ Введи число")
        return

    if action == 'set_log_thread_id':
        try:
            tid = int(text)
            LOG_THREAD_ID = tid if tid != 0 else None
            del user_states[user_id]
            try:
                await bot.send_message(LOG_CHAT_ID, "✅ Логи активированы!", message_thread_id=LOG_THREAD_ID)
                await message.answer(f"✅ Логи включены!\nЧат: {LOG_CHAT_ID}\nТема: {LOG_THREAD_ID or 'нет'}")
            except Exception as e:
                await message.answer(f"❌ Ошибка: {e}")
                LOG_CHAT_ID = None
                LOG_THREAD_ID = None
        except ValueError:
            await message.answer("❌ Введи число")
        return

    if action == 'sell_name':
        temp_deal_data.setdefault(user_id, {})['name'] = text
        user_states[user_id] = {'action': 'sell_price'}
        await message.answer("💰 Введи цену (₽):")
        return

    if action == 'sell_price':
        try:
            price = int(text.replace(' ', ''))
            temp_deal_data.setdefault(user_id, {})['price'] = price
            user_states[user_id] = {'action': 'sell_desc'}
            await message.answer("📝 Введи описание:")
        except ValueError:
            await message.answer("❌ Введи число")
        return

    if action == 'sell_desc':
        sell_data = temp_deal_data.get(user_id, {})
        sell_data['desc'] = text
        sell_data['seller_id'] = user_id
        sell_data['username'] = message.from_user.username or str(user_id)
        moderation_queue.append(sell_data)
        temp_deal_data.pop(user_id, None)
        del user_states[user_id]
        await message.answer(f"✅ Товар на модерации!\n\n{sell_data['name']}\n{sell_data['price']}₽", reply_markup=back_kb())
        try:
            await bot.send_message(ADMIN_ID, f"Товар на модерации!\n\n@{sell_data['username']}\n{sell_data['name']}\n{sell_data['price']}₽\n{text}")
        except Exception:
            pass
        return

    if action == 'admin_give_reputation':
        target_text = text.lstrip('@').lower()
        target_id = None
        try:
            target_id = int(target_text)
            if target_id not in users:
                target_id = None
        except ValueError:
            pass
        if not target_id:
            for uid, u in users.items():
                if u.get('username', '').lower() == target_text:
                    target_id = uid
                    break
        if not target_id:
            await message.answer("❌ Не найден")
            return
        target_username = users.get(target_id, {}).get('username', f"id{target_id}")
        user_states[user_id] = {'action': 'admin_set_reputation_rating', 'target_id': target_id}
        await message.answer(
            f"Выдать репутацию @{target_username}:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⭐", callback_data=f"give_rep_1_{target_id}"),
                 InlineKeyboardButton(text="⭐⭐", callback_data=f"give_rep_2_{target_id}"),
                 InlineKeyboardButton(text="⭐⭐⭐", callback_data=f"give_rep_3_{target_id}")],
                [InlineKeyboardButton(text="⭐⭐⭐⭐", callback_data=f"give_rep_4_{target_id}"),
                 InlineKeyboardButton(text="⭐⭐⭐⭐⭐", callback_data=f"give_rep_5_{target_id}")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")],
            ])
        )
        return

    if action == 'admin_set_status_id':
        try:
            target_id = int(text)
            user_states[user_id] = {'action': 'admin_set_status_val', 'target_id': target_id}
            statuses_list = "\n".join([f"• {k} — {v['ru']}" for k, v in USER_STATUSES.items()])
            await message.answer(f"Статус для id={target_id}:\n\n{statuses_list}")
        except ValueError:
            await message.answer("❌ Введи числовой ID")
        return

    if action == 'admin_set_status_val':
        target_id = state_data.get('target_id')
        if text in USER_STATUSES:
            user_stats.setdefault(target_id, {'deals_total': 0, 'deals_success': 0, 'deals_failed': 0, 'status': 'new'})
            user_stats[target_id]['status'] = text
            del user_states[user_id]
            await message.answer(f"✅ Статус id={target_id} → {USER_STATUSES[text]['ru']}")
            await log_event('status_changed', target_id, f"Статус → {USER_STATUSES[text]['ru']}")
        else:
            await message.answer(f"❌ Варианты: {', '.join(USER_STATUSES.keys())}")
        return

# ============ ЗАПУСК ============

async def main():
    load_products()
    print(f"LOLZ MARKET запущен! Товаров: {len(products)}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
