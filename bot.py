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

# ============ КОНФИГ ============
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
    raise ValueError("BOT_TOKEN не задан! Создай .env файл.")

storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# Логи
LOG_CHAT_ID = None
LOG_THREAD_ID = None

# Баннер — храним file_id после первой отправки
BANNER_FILE_ID = None   # Telegram file_id (быстрее всего)
BANNER_BYTES = None     # raw bytes как резерв

# ============ ЛОГИРОВАНИЕ ============
async def log_event(event_type: str, user_id: int, description: str):
    if not LOG_CHAT_ID:
        return
    try:
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        emoji_map = {
            'join': '👤', 'deal_created': '🤝', 'deal_paid': '💰',
            'nft_transfer': '🎁', 'product_added': '📦', 'status_changed': '🚦',
            'review_left': '⭐', 'requisites': '💳', 'payment_confirmed': '✅',
            'payment_rejected': '❌'
        }
        emoji = emoji_map.get(event_type, '📝')
        text = f"{emoji} [{timestamp}] {description}"
        await bot.send_message(
            LOG_CHAT_ID, text,
            message_thread_id=LOG_THREAD_ID
        )
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
    'new':        {'name_ru': '🟢 Новичок',      'name_en': '🟢 Newbie',      'name_es': '🟢 Novato',     'name_fr': '🟢 Novice',     'name_de': '🟢 Neuling'},
    'verified':   {'name_ru': '✅ Проверенный',   'name_en': '✅ Verified',    'name_es': '✅ Verificado', 'name_fr': '✅ Vérifié',    'name_de': '✅ Verifiziert'},
    'suspicious': {'name_ru': '⚠️ Сомнительный', 'name_en': '⚠️ Suspicious', 'name_es': '⚠️ Sospechoso','name_fr': '⚠️ Suspect',    'name_de': '⚠️ Verdächtig'},
    'scammer':    {'name_ru': '🔴 Мошенник',      'name_en': '🔴 Scammer',    'name_es': '🔴 Estafador',  'name_fr': '🔴 Arnaqueur',  'name_de': '🔴 Betrüger'},
    'trusted':    {'name_ru': '💎 Доверенный',    'name_en': '💎 Trusted',    'name_es': '💎 Confiable',  'name_fr': '💎 Fiable',     'name_de': '💎 Vertrauenswürdig'},
    'partner':    {'name_ru': '🤝 Партнер',       'name_en': '🤝 Partner',    'name_es': '🤝 Socio',      'name_fr': '🤝 Partenaire', 'name_de': '🤝 Partner'},
}

TRANSLATIONS = {
    'ru': {
        'welcome': '🛍️ LOLZ MARKET — твой надежный маркетплейс!',
        'back': '🔙 Назад',
        'catalog': '🛒 Каталог',
        'create_deal': '🤝 Создать сделку',
        'sell_product': '📤 Продать товар',
        'my_requisites': '💰 Мои реквизиты',
        'profile': '👤 Профиль',
        'top_sellers': '⭐ Топ продавцов',
        'language': '🌐 Язык',
        'support': '📞 Поддержка',
        'site': '🌍 Сайт',
        'menu': 'Выбери действие в меню ниже 👇',
        'users': 'Пользователей',
        'products': 'Товаров',
        'deals': 'Сделок',
        'admin_panel': '👑 Админ-панель',
    },
    'en': {
        'welcome': '🛍️ LOLZ MARKET — your reliable marketplace!',
        'back': '🔙 Back',
        'catalog': '🛒 Catalog',
        'create_deal': '🤝 Create Deal',
        'sell_product': '📤 Sell Product',
        'my_requisites': '💰 My Requisites',
        'profile': '👤 Profile',
        'top_sellers': '⭐ Top Sellers',
        'language': '🌐 Language',
        'support': '📞 Support',
        'site': '🌍 Website',
        'menu': 'Choose an action from the menu below 👇',
        'users': 'Users',
        'products': 'Products',
        'deals': 'Deals',
        'admin_panel': '👑 Admin Panel',
    },
    'es': {
        'welcome': '🛍️ LOLZ MARKET — ¡tu mercado confiable!',
        'back': '🔙 Atrás',
        'catalog': '🛒 Catálogo',
        'create_deal': '🤝 Crear Oferta',
        'sell_product': '📤 Vender Producto',
        'my_requisites': '💰 Mis Requisitos',
        'profile': '👤 Perfil',
        'top_sellers': '⭐ Mejores Vendedores',
        'language': '🌐 Idioma',
        'support': '📞 Soporte',
        'site': '🌍 Sitio Web',
        'menu': 'Elige una acción del menú a continuación 👇',
        'users': 'Usuarios',
        'products': 'Productos',
        'deals': 'Ofertas',
        'admin_panel': '👑 Panel de Administración',
    },
    'fr': {
        'welcome': '🛍️ LOLZ MARKET — votre marché fiable!',
        'back': '🔙 Retour',
        'catalog': '🛒 Catalogue',
        'create_deal': '🤝 Créer une Offre',
        'sell_product': '📤 Vendre un Produit',
        'my_requisites': '💰 Mes Coordonnées',
        'profile': '👤 Profil',
        'top_sellers': '⭐ Meilleurs Vendeurs',
        'language': '🌐 Langue',
        'support': '📞 Support',
        'site': '🌍 Site Web',
        'menu': 'Choisissez une action ci-dessous 👇',
        'users': 'Utilisateurs',
        'products': 'Produits',
        'deals': 'Offres',
        'admin_panel': "👑 Panneau d'Administration",
    },
    'de': {
        'welcome': '🛍️ LOLZ MARKET — dein zuverlässiger Marktplatz!',
        'back': '🔙 Zurück',
        'catalog': '🛒 Katalog',
        'create_deal': '🤝 Angebot Erstellen',
        'sell_product': '📤 Produkt Verkaufen',
        'my_requisites': '💰 Meine Daten',
        'profile': '👤 Profil',
        'top_sellers': '⭐ Top Verkäufer',
        'language': '🌐 Sprache',
        'support': '📞 Unterstützung',
        'site': '🌍 Website',
        'menu': 'Wählen Sie eine Aktion unten 👇',
        'users': 'Benutzer',
        'products': 'Produkte',
        'deals': 'Angebote',
        'admin_panel': '👑 Admin-Panel',
    },
}

TOP_SELLERS = [
    {"name": "@al**in",        "deals": 847, "rating": 4.9},
    {"name": "@ma**k_shop",    "deals": 832, "rating": 4.8},
    {"name": "@st**a_market",  "deals": 821, "rating": 4.9},
    {"name": "@dm**y_pro",     "deals": 815, "rating": 4.7},
    {"name": "@ki**s_gaming",  "deals": 809, "rating": 4.8},
    {"name": "@pr**e_seller",  "deals": 798, "rating": 4.9},
    {"name": "@ve**s_shop",    "deals": 784, "rating": 4.8},
    {"name": "@ni**la_deals",  "deals": 776, "rating": 4.7},
    {"name": "@ti**n_market",  "deals": 765, "rating": 4.9},
    {"name": "@ro**l_trader",  "deals": 752, "rating": 4.8},
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
            "🤝 Поддержка 24/7\n"
            "🔐 Конфиденциальность\n\n"
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
            "• 📱 Software and apps\n"
            "• 💼 Freelance services\n\n"
            "🔥 Our advantages:\n"
            "✅ Safe deals with guarantor\n"
            "⭐ Seller ratings and reviews\n"
            "💳 Instant payouts\n"
            "🤝 Support 24/7\n"
            "🔐 Privacy\n\n"
            "📊 Statistics:\n"
            "👥 Users: {users}\n"
            "📦 Products: {products}\n"
            "🤝 Deals: {deals}\n\n"
            "Choose an action from the menu below 👇"
        ),
        'es': (
            "🛍️ LOLZ MARKET — ¡tu mercado confiable!\n\n"
            "✨ Lo que ofrecemos:\n"
            "• 🎮 Cuentas y artículos de juegos\n"
            "• 💳 Bienes y servicios digitales\n"
            "• 🎁 Telegram NFT y regalos\n"
            "• 💎 Cripto y billeteras\n"
            "• 🔑 Claves de licencia\n"
            "• 📱 Software y apps\n"
            "• 💼 Servicios freelance\n\n"
            "🔥 Nuestras ventajas:\n"
            "✅ Acuerdos seguros\n"
            "⭐ Calificaciones de vendedores\n"
            "💳 Pagos instantáneos\n"
            "🤝 Soporte 24/7\n"
            "🔐 Privacidad\n\n"
            "📊 Estadísticas:\n"
            "👥 Usuarios: {users}\n"
            "📦 Productos: {products}\n"
            "🤝 Acuerdos: {deals}\n\n"
            "Elige una acción del menú a continuación 👇"
        ),
        'fr': (
            "🛍️ LOLZ MARKET — votre marché fiable!\n\n"
            "✨ Ce que nous offrons:\n"
            "• 🎮 Comptes et objets de jeux\n"
            "• 💳 Biens et services numériques\n"
            "• 🎁 Telegram NFT et cadeaux\n"
            "• 💎 Crypto et portefeuilles\n"
            "• 🔑 Clés de licence\n"
            "• 📱 Logiciels et applis\n"
            "• 💼 Services freelance\n\n"
            "🔥 Nos avantages:\n"
            "✅ Transactions sécurisées\n"
            "⭐ Évaluations des vendeurs\n"
            "💳 Paiements instantanés\n"
            "🤝 Support 24/7\n"
            "🔐 Confidentialité\n\n"
            "📊 Statistiques:\n"
            "👥 Utilisateurs: {users}\n"
            "📦 Produits: {products}\n"
            "🤝 Offres: {deals}\n\n"
            "Choisissez une action ci-dessous 👇"
        ),
        'de': (
            "🛍️ LOLZ MARKET — dein zuverlässiger Marktplatz!\n\n"
            "✨ Was wir anbieten:\n"
            "• 🎮 Spielkonten und Gegenstände\n"
            "• 💳 Digitale Waren und Dienste\n"
            "• 🎁 Telegram NFT und Geschenke\n"
            "• 💎 Krypto und Wallets\n"
            "• 🔑 Lizenzschlüssel\n"
            "• 📱 Software und Apps\n"
            "• 💼 Freelance-Dienste\n\n"
            "🔥 Unsere Vorteile:\n"
            "✅ Sichere Geschäfte\n"
            "⭐ Verkäuferbewertungen\n"
            "💳 Sofortige Auszahlungen\n"
            "🤝 Support 24/7\n"
            "🔐 Datenschutz\n\n"
            "📊 Statistiken:\n"
            "👥 Benutzer: {users}\n"
            "📦 Produkte: {products}\n"
            "🤝 Angebote: {deals}\n\n"
            "Wählen Sie eine Aktion unten 👇"
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
            {"name": "Disney+ Bundle", "price": 1200, "desc": "Disney+ Hulu ESPN, 1 месяц"},
        ]},
        {"name": "Spotify", "products": [
            {"name": "Spotify Premium 1 мес", "price": 400, "desc": "Без рекламы"},
            {"name": "Spotify Family 3 мес", "price": 1500, "desc": "6 аккаунтов, 3 месяца"},
            {"name": "Spotify Premium 6 мес", "price": 2000, "desc": "Индивидуальная, 6 мес"},
            {"name": "Spotify Duo 6 мес", "price": 2500, "desc": "Для двоих, 6 мес"},
        ]},
        {"name": "AI Сервисы", "products": [
            {"name": "ChatGPT Plus 1 месяц", "price": 1500, "desc": "GPT-4, быстрый ответ"},
            {"name": "ChatGPT Plus 3 месяца", "price": 4000, "desc": "GPT-4, экономия"},
            {"name": "ChatGPT API доступ", "price": 2500, "desc": "API ключ для разработчиков"},
            {"name": "Midjourney Basic", "price": 1500, "desc": "200 генераций"},
            {"name": "Midjourney Pro", "price": 2500, "desc": "Быстрая генерация, безлимит"},
            {"name": "Midjourney Mega", "price": 3500, "desc": "Безлимит, приоритет"},
        ]},
        {"name": "Adobe / Office", "products": [
            {"name": "Adobe Creative Cloud", "price": 2500, "desc": "Весь пакет Adobe, 1 мес"},
            {"name": "Adobe Photoshop", "price": 1200, "desc": "Photoshop на месяц"},
            {"name": "Adobe Premiere Pro", "price": 1500, "desc": "Premiere Pro на месяц"},
            {"name": "Adobe All Apps год", "price": 18000, "desc": "Весь пакет на год"},
            {"name": "Office 365 Personal", "price": 1500, "desc": "Год, 1 пользователь"},
            {"name": "Office 365 Family", "price": 2500, "desc": "Год, 6 пользователей"},
            {"name": "Office 2021 навсегда", "price": 2000, "desc": "Бессрочная лицензия"},
        ]},
        {"name": "VPN", "products": [
            {"name": "NordVPN 1 год", "price": 2500, "desc": "6 устройств"},
            {"name": "ExpressVPN 6 мес", "price": 2000, "desc": "5 устройств"},
            {"name": "ProtonVPN Plus", "price": 1000, "desc": "Все серверы, 1 мес"},
            {"name": "Surfshark 2 года", "price": 3000, "desc": "Безлимит устройств"},
        ]},
        {"name": "Соцсети / Почта", "products": [
            {"name": "GMail аккаунт 2010", "price": 1000, "desc": "Старый, с историей"},
            {"name": "GMail аккаунт 2015", "price": 600, "desc": "2015 год"},
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
            {"name": "Windows 11 Enterprise", "price": 750, "desc": "LTSC корпоративная"},
        ]},
        {"name": "Office ключи", "products": [
            {"name": "Office 2021 Pro", "price": 900, "desc": "Pro Plus, ПК"},
            {"name": "Office 2019", "price": 800, "desc": "Pro Plus"},
            {"name": "Office 365 ключ", "price": 1800, "desc": "Год, 1 ПК"},
            {"name": "Office 2016", "price": 600, "desc": "Pro"},
            {"name": "Office для Mac 2021", "price": 1200, "desc": "Бессрочно"},
        ]},
        {"name": "Антивирусы", "products": [
            {"name": "Kaspersky 1 год", "price": 700, "desc": "3 устройства"},
            {"name": "ESET NOD32", "price": 800, "desc": "5 устройств"},
            {"name": "Avast Premium", "price": 600, "desc": "10 устройств"},
            {"name": "Norton 360", "price": 750, "desc": "3 устройства"},
            {"name": "Bitdefender", "price": 700, "desc": "Total Security, год"},
        ]},
        {"name": "Игровые ключи", "products": [
            {"name": "Cyberpunk 2077", "price": 2800, "desc": "GOG/Steam"},
            {"name": "Hogwarts Legacy", "price": 3500, "desc": "Steam"},
            {"name": "Baldur's Gate 3", "price": 4000, "desc": "Steam"},
            {"name": "Starfield", "price": 3800, "desc": "Steam"},
            {"name": "Diablo 4", "price": 4200, "desc": "Battle.net"},
        ]},
        {"name": "Другой софт", "products": [
            {"name": "Adobe Photoshop лиц.", "price": 1200, "desc": "Бессрочно"},
            {"name": "WinRAR", "price": 300, "desc": "Бессрочно"},
            {"name": "VMware Workstation", "price": 800, "desc": "Pro, ключ"},
            {"name": "Parallels Desktop", "price": 2000, "desc": "Mac, год"},
        ]},
    ]},
    {"id": 3, "name": "📱 Софт", "subcategories": [
        {"name": "Мобильные приложения", "products": [
            {"name": "Nova Launcher Prime", "price": 300, "desc": "Лицензия"},
            {"name": "Tasker", "price": 400, "desc": "Автоматизация Android"},
            {"name": "PicsArt Gold", "price": 350, "desc": "Премиум, год"},
            {"name": "VSCO Premium", "price": 300, "desc": "Фильтры, год"},
        ]},
        {"name": "Десктоп программы", "products": [
            {"name": "Adobe Master Collection", "price": 3000, "desc": "Все программы Adobe"},
            {"name": "CorelDRAW", "price": 1500, "desc": "Graphics Suite, ключ"},
            {"name": "3ds Max", "price": 2000, "desc": "Autodesk, ключ"},
            {"name": "AutoCAD", "price": 1800, "desc": "Лицензия, бессрочно"},
            {"name": "MatLab", "price": 2500, "desc": "Полная версия, ключ"},
        ]},
        {"name": "Скрипты и Боты", "products": [
            {"name": "Скрипт парсинга", "price": 2000, "desc": "Python, любой сайт"},
            {"name": "SEO скрипт", "price": 1500, "desc": "Семантика, анализ"},
            {"name": "Скрипт рассылок", "price": 1800, "desc": "Telegram/Email"},
            {"name": "Торговый скрипт", "price": 3000, "desc": "Крипто-арбитраж"},
            {"name": "Бот для Telegram", "price": 5000, "desc": "Готовый с админкой"},
            {"name": "Discord бот", "price": 4000, "desc": "Модерация, музыка"},
            {"name": "Магазин бот", "price": 6000, "desc": "С базой и платежами"},
        ]},
        {"name": "Плагины и Темы", "products": [
            {"name": "WordPress плагин", "price": 1000, "desc": "Премиум, nulled"},
            {"name": "Chrome расширение", "price": 1200, "desc": "Готовое"},
            {"name": "Figma плагин", "price": 600, "desc": "Премиум"},
            {"name": "Windows тема", "price": 200, "desc": "10/11 тёмная"},
            {"name": "WordPress тема", "price": 800, "desc": "Премиум, nulled"},
        ]},
        {"name": "Графика и Шрифты", "products": [
            {"name": "Коллекция шрифтов 1000+", "price": 500, "desc": "Все стили"},
            {"name": "Кириллические шрифты 500+", "price": 300, "desc": "Дизайн"},
            {"name": "Иконки для сайта 1000+", "price": 400, "desc": "SVG, PNG"},
            {"name": "Текстуры 500+", "price": 350, "desc": "Высокое разрешение"},
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
            {"name": "NFT Sapphire", "price": 17000, "desc": "Сапфир, редкий"},
            {"name": "NFT Birthday Cake", "price": 5000, "desc": "Торт на день рождения"},
            {"name": "NFT Fireworks", "price": 6000, "desc": "Фейерверк"},
            {"name": "NFT Balloons", "price": 4000, "desc": "Воздушные шары"},
            {"name": "NFT Gift Box", "price": 3000, "desc": "Подарочная коробка"},
            {"name": "NFT Teddy Bear", "price": 4500, "desc": "Плюшевый мишка"},
            {"name": "NFT Heart", "price": 3500, "desc": "Сердце"},
            {"name": "NFT Kiss", "price": 3800, "desc": "Поцелуй"},
            {"name": "NFT Love Letter", "price": 3200, "desc": "Любовное письмо"},
        ]},
        {"name": "Telegram Stars", "products": [
            {"name": "1000 Telegram Stars", "price": 1800, "desc": "Звёзды для поддержки"},
            {"name": "2500 Telegram Stars", "price": 4200, "desc": "2500 звёзд"},
            {"name": "5000 Telegram Stars", "price": 8000, "desc": "5000 звёзд"},
            {"name": "10000 Telegram Stars", "price": 15000, "desc": "10000 звёзд"},
            {"name": "25000 Telegram Stars", "price": 35000, "desc": "25000 звёзд"},
        ]},
        {"name": "Telegram Premium", "products": [
            {"name": "Premium 1 месяц", "price": 350, "desc": "Telegram Premium"},
            {"name": "Premium 3 месяца", "price": 950, "desc": "Экономия"},
            {"name": "Premium 6 месяцев", "price": 1700, "desc": "Полгода"},
            {"name": "Premium 1 год", "price": 3000, "desc": "Год, максимальная экономия"},
            {"name": "Premium + 500 Stars", "price": 2000, "desc": "Комбо"},
        ]},
        {"name": "Telegram Аккаунты", "products": [
            {"name": "Аккаунт 2015 года", "price": 3500, "desc": "Старый, хорошая история"},
            {"name": "Аккаунт 2018 года", "price": 1800, "desc": "Без блокировок, чистый"},
            {"name": "Аккаунт 2020 года", "price": 1000, "desc": "Чистый"},
            {"name": "Аккаунт с Premium", "price": 2500, "desc": "С активным Premium"},
        ]},
        {"name": "Telegram Каналы", "products": [
            {"name": "Канал 10k подписчиков", "price": 15000, "desc": "Живые, активные"},
            {"name": "Канал 5k подписчиков", "price": 8000, "desc": "Высокая активность"},
            {"name": "Канал 1k подписчиков", "price": 2000, "desc": "Живая аудитория"},
            {"name": "VIP закрытый канал", "price": 5000, "desc": "500 подписчиков"},
        ]},
        {"name": "Telegram Username", "products": [
            {"name": "@rare 4 символа", "price": 5000, "desc": "Редкое короткое имя"},
            {"name": "@brand имя бренда", "price": 3000, "desc": "Под компанию"},
            {"name": "@beauty 6 символов", "price": 2000, "desc": "Красивое звучное"},
            {"name": "@old с 2015 года", "price": 4000, "desc": "Старый юзернейм"},
        ]},
        {"name": "NFT Username (TON)", "products": [
            {"name": "@crypto NFT", "price": 5000, "desc": "Крипто-нейм, TON"},
            {"name": "@nft NFT", "price": 8000, "desc": "Для коллекционера"},
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
            {"name": "Пустой TON кошелек", "price": 600, "desc": "Чистый"},
            {"name": "TON с историей транзакций", "price": 1500, "desc": "Много операций"},
        ]},
        {"name": "BTC / ETH / USDT", "products": [
            {"name": "BTC кошелек 0.01 BTC", "price": 45000, "desc": "~$400"},
            {"name": "BTC кошелек 0.05 BTC", "price": 225000, "desc": "~$2000"},
            {"name": "ETH кошелек 0.1 ETH", "price": 18000, "desc": "Ethereum"},
            {"name": "ETH кошелек 0.5 ETH", "price": 90000, "desc": "Ethereum"},
            {"name": "USDT 100 USDT", "price": 10000, "desc": "TRC20"},
            {"name": "USDT 500 USDT", "price": 49000, "desc": "TRC20"},
            {"name": "USDT 1000 USDT", "price": 97000, "desc": "TRC20"},
        ]},
        {"name": "NFT Коллекции", "products": [
            {"name": "CryptoPunks", "price": 15000, "desc": "Коллекция"},
            {"name": "Bored Ape Yacht Club", "price": 55000, "desc": "Изображение"},
            {"name": "Azuki", "price": 25000, "desc": "Аниме стиль"},
            {"name": "CloneX", "price": 20000, "desc": "Японский стиль"},
            {"name": "Moonbirds", "price": 18000, "desc": "Коллекция"},
        ]},
        {"name": "Облачный майнинг", "products": [
            {"name": "1 TH/s на месяц", "price": 5000, "desc": "Договор"},
            {"name": "5 TH/s на месяц", "price": 22000, "desc": "Выгодный контракт"},
            {"name": "Контракт на год", "price": 10000, "desc": "Долгосрочный"},
        ]},
        {"name": "Крипто-карты", "products": [
            {"name": "Binance Card", "price": 2000, "desc": "Виртуальная"},
            {"name": "Crypto.com Card", "price": 2500, "desc": "Металлическая"},
            {"name": "Bybit Card", "price": 2000, "desc": "Виртуальная"},
            {"name": "Coinbase Card", "price": 2200, "desc": "Физическая"},
        ]},
    ]},
    {"id": 6, "name": "📚 Базы", "subcategories": [
        {"name": "Email базы", "products": [
            {"name": "Email база 100k", "price": 3000, "desc": "100к свежих"},
            {"name": "Email база 500k", "price": 12000, "desc": "500к целевых"},
            {"name": "Email база 1M", "price": 20000, "desc": "1 миллион"},
            {"name": "Email база РФ 200k", "price": 5000, "desc": "Россия, регионы"},
        ]},
        {"name": "Telegram базы", "products": [
            {"name": "Telegram база 50k", "price": 2500, "desc": "50к активных"},
            {"name": "Telegram база 100k", "price": 4500, "desc": "100к"},
            {"name": "Telegram база 500k", "price": 18000, "desc": "500к"},
            {"name": "Telegram крипто-база", "price": 3000, "desc": "Крипто-инвесторы"},
        ]},
        {"name": "Базы компаний", "products": [
            {"name": "База компаний РФ 500k", "price": 5000, "desc": "Юрлица, контакты"},
            {"name": "База ИП", "price": 3000, "desc": "Предприниматели"},
            {"name": "База компаний EU 200k", "price": 10000, "desc": "Европа"},
            {"name": "База CEO контакты", "price": 4000, "desc": "Email руководителей"},
        ]},
        {"name": "Instagram / WhatsApp", "products": [
            {"name": "Instagram база 10k", "price": 2000, "desc": "10к аккаунтов"},
            {"name": "Instagram база 50k", "price": 8000, "desc": "50к"},
            {"name": "WhatsApp база 10k", "price": 1500, "desc": "10к номеров"},
            {"name": "WhatsApp база 50k", "price": 6000, "desc": "50к"},
        ]},
        {"name": "Курсы и Книги", "products": [
            {"name": "Курс по Python", "price": 2000, "desc": "50 часов, полный"},
            {"name": "Курс по SMM", "price": 1500, "desc": "Продвижение в соцсетях"},
            {"name": "Курс по трейдингу", "price": 3000, "desc": "Крипто, стратегии"},
            {"name": "Курс по дизайну", "price": 2500, "desc": "Figma, Photoshop"},
            {"name": "Коллекция IT-книг 100шт", "price": 1500, "desc": "Программирование"},
            {"name": "Коллекция бизнес-книг 50шт", "price": 1000, "desc": "PDF"},
        ]},
    ]},
    {"id": 7, "name": "💼 Услуги", "subcategories": [
        {"name": "Разработка", "products": [
            {"name": "Telegram бот под ключ", "price": 6000, "desc": "Любая сложность"},
            {"name": "Discord бот", "price": 5000, "desc": "Модерация, музыка, игры"},
            {"name": "Торговый бот", "price": 10000, "desc": "Авто-торговля"},
            {"name": "Сайт-визитка", "price": 8000, "desc": "Одностраничный, адаптивный"},
            {"name": "Интернет-магазин", "price": 20000, "desc": "Полноценный"},
            {"name": "Лендинг", "price": 5000, "desc": "Посадочная страница"},
            {"name": "Корпоративный сайт", "price": 15000, "desc": "5 страниц"},
        ]},
        {"name": "Дизайн", "products": [
            {"name": "Логотип", "price": 1500, "desc": "Уникальный, 3 варианта"},
            {"name": "Фирменный стиль", "price": 5000, "desc": "Полный брендбук"},
            {"name": "Дизайн сайта в Figma", "price": 3000, "desc": "Макет"},
            {"name": "Дизайн упаковки", "price": 2500, "desc": "Дизайн товара"},
        ]},
        {"name": "SMM / SEO", "products": [
            {"name": "Раскрутка Instagram", "price": 3000, "desc": "1000 живых подписчиков"},
            {"name": "Раскрутка Telegram", "price": 2500, "desc": "500 подписчиков"},
            {"name": "Таргетолог FB/IG", "price": 4000, "desc": "Настройка рекламы"},
            {"name": "Ведение соцсетей", "price": 5000, "desc": "Месяц, постинг"},
            {"name": "SEO аудит сайта", "price": 2000, "desc": "Полный аудит"},
            {"name": "Продвижение сайта", "price": 5000, "desc": "Вывод в топ"},
        ]},
        {"name": "Копирайтинг / Переводы", "products": [
            {"name": "SEO-текст 1000 знаков", "price": 300, "desc": "Уникальный"},
            {"name": "Пост для соцсетей", "price": 200, "desc": "Вовлекающий"},
            {"name": "Продающий текст", "price": 400, "desc": "Для лендинга"},
            {"name": "Перевод 1000 знаков", "price": 300, "desc": "С/на английский"},
            {"name": "Технический перевод", "price": 500, "desc": "Документация"},
            {"name": "Юридический перевод", "price": 600, "desc": "Договоры, контракты"},
        ]},
        {"name": "Обучение / Консультации", "products": [
            {"name": "Урок Python 1 час", "price": 500, "desc": "Онлайн"},
            {"name": "Курс Python 5 занятий", "price": 5000, "desc": "10 часов, практика"},
            {"name": "Наставничество месяц", "price": 10000, "desc": "Индивидуально"},
            {"name": "Консультация 1 час", "price": 1000, "desc": "По вашему вопросу"},
            {"name": "Разбор бизнеса", "price": 3000, "desc": "Полный разбор"},
        ]},
    ]},
    {"id": 8, "name": "🎨 NFT", "subcategories": [
        {"name": "NFT Арт", "products": [
            {"name": "Цифровая картина", "price": 2000, "desc": "Уникальный авторский арт"},
            {"name": "Анимированный NFT", "price": 4000, "desc": "GIF/видео"},
            {"name": "Генеративное искусство", "price": 3000, "desc": "Алгоритмическое"},
            {"name": "Пиксель-арт 8bit", "price": 1500, "desc": "Ретро стиль"},
        ]},
        {"name": "NFT Фоны и Модели", "products": [
            {"name": "Cyberpunk City фон 4K", "price": 2000, "desc": "Киберпанк"},
            {"name": "Space Galaxy фон", "price": 2500, "desc": "Космос, звёзды"},
            {"name": "Neon Dreams фон", "price": 1800, "desc": "Неон, ретро"},
            {"name": "3D Cyberpunk модель", "price": 5000, "desc": "3D киберпанк"},
            {"name": "Anime Character 3D", "price": 3500, "desc": "Аниме персонаж"},
            {"name": "Fantasy Dragon 3D", "price": 4500, "desc": "Фэнтези дракон"},
        ]},
        {"name": "NFT Игры / Метавселенные", "products": [
            {"name": "Игровой NFT скин CS2/Dota", "price": 2000, "desc": "Редкий скин"},
            {"name": "Игровой персонаж RPG", "price": 3000, "desc": "Уникальный"},
            {"name": "Игровая земля", "price": 5000, "desc": "Метавселенная"},
            {"name": "Земля в Decentraland", "price": 10000, "desc": "Участок"},
            {"name": "Аватар для VR", "price": 2000, "desc": "Уникальный"},
        ]},
        {"name": "NFT Коллекции", "products": [
            {"name": "CryptoPunks", "price": 15000, "desc": "Копия"},
            {"name": "Bored Ape Yacht Club", "price": 55000, "desc": "Изображение"},
            {"name": "Azuki", "price": 25000, "desc": "Аниме стиль"},
            {"name": "CloneX", "price": 20000, "desc": "Японский стиль"},
            {"name": "Moonbirds", "price": 18000, "desc": "Коллекция"},
        ]},
    ]},
    {"id": 9, "name": "🔞 Другое", "subcategories": [
        {"name": "Эксклюзив", "products": [
            {"name": "VIP доступ", "price": 5000, "desc": "Закрытый контент"},
            {"name": "Эксклюзивный товар", "price": 10000, "desc": "Только для избранных"},
            {"name": "Ранний доступ", "price": 2000, "desc": "Доступ к новинкам"},
            {"name": "Случайный товар-сюрприз", "price": 100, "desc": "Что-то интересное"},
            {"name": "Подарочный набор", "price": 1000, "desc": "Набор разных товаров"},
        ]},
        {"name": "Коллекционное", "products": [
            {"name": "Лимитированная серия", "price": 5000, "desc": "Ограниченный тираж"},
            {"name": "С подписью автора", "price": 7000, "desc": "Цифровой автограф"},
            {"name": "Уникальный экземпляр", "price": 8000, "desc": "В единственном экземпляре"},
            {"name": "Артефакт", "price": 15000, "desc": "Историческая ценность"},
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
    return USER_STATUSES.get(status, USER_STATUSES['new']).get(f'name_{lang}', USER_STATUSES['new']['name_ru'])

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
                    'id': pid,
                    'name': prod['name'],
                    'description': prod['desc'],
                    'price': prod['price'],
                    'category': cat['id'],
                    'category_name': cat['name'],
                    'subcategory': sub['name'],
                    'stock': random.randint(3, 10),
                }
    print(f"Загружено {len(products)} товаров")

# ============ ОТПРАВКА СООБЩЕНИЯ С/БЕЗ БАННЕРА ============

async def send_or_edit_with_banner(target, text: str, keyboard, is_callback: bool = True):
    """
    Универсальная функция: если есть баннер — отправляем новое фото-сообщение,
    старое удаляем. Если баннера нет — редактируем текущее (callback) или шлём новое (message).
    """
    global BANNER_FILE_ID, BANNER_BYTES

    if is_callback:
        call = target
        # Пробуем отправить с баннером
        if BANNER_FILE_ID or BANNER_BYTES:
            try:
                await call.message.delete()
            except Exception:
                pass
            try:
                if BANNER_FILE_ID:
                    await call.message.chat.send_photo(
                        photo=BANNER_FILE_ID,
                        caption=text,
                        reply_markup=keyboard
                    )
                else:
                    buf = BufferedInputFile(BANNER_BYTES, filename="banner.jpg")
                    msg = await call.message.chat.send_photo(
                        photo=buf,
                        caption=text,
                        reply_markup=keyboard
                    )
                    # Сохраняем file_id для следующих отправок
                    if msg.photo:
                        BANNER_FILE_ID = msg.photo[-1].file_id
                return
            except Exception as e:
                print(f"Баннер ошибка: {e}")
        # Без баннера — обычное редактирование
        try:
            await call.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await call.message.answer(text, reply_markup=keyboard)
    else:
        message = target
        if BANNER_FILE_ID or BANNER_BYTES:
            try:
                if BANNER_FILE_ID:
                    msg = await message.answer_photo(
                        photo=BANNER_FILE_ID,
                        caption=text,
                        reply_markup=keyboard
                    )
                else:
                    buf = BufferedInputFile(BANNER_BYTES, filename="banner.jpg")
                    msg = await message.answer_photo(
                        photo=buf,
                        caption=text,
                        reply_markup=keyboard
                    )
                    if msg.photo:
                        BANNER_FILE_ID = msg.photo[-1].file_id
                return
            except Exception as e:
                print(f"Баннер ошибка: {e}")
        await message.answer(text, reply_markup=keyboard)


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
            text = (
                f"📋 Детали сделки\n\n"
                f"ID: {deal_id}\n"
                f"👤 Создатель: @{deal['buyer_username']}\n"
                f"💰 Сумма: {deal.get('amount_display', str(deal['amount']))}\n"
                f"🏷️ Тип: {deal['type']}\n"
                f"📝 Описание: {deal['description']}\n\n"
                f"Статус: {deal['status']}"
            )
            await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Присоединиться", callback_data=f"join_deal_{deal_id}")],
                [InlineKeyboardButton(text="🔙 В меню", callback_data="back_to_menu")],
            ]))
            return
        else:
            await message.answer("❌ Сделка не найдена или удалена")
            return

    if user_id not in users:
        users[user_id] = {
            'username': message.from_user.username or "нет",
            'reg_date': datetime.now().strftime("%d.%m.%Y"),
            'reputation': 0,
        }
        user_language[user_id] = 'ru'
        user_stats[user_id] = {'deals_total': 0, 'deals_success': 0, 'deals_failed': 0, 'status': 'new'}
        await log_event('join', user_id, f"Новый пользователь @{message.from_user.username or 'unknown'} (id={user_id})")

    text = get_welcome_text(user_id)
    await send_or_edit_with_banner(message, text, main_keyboard(user_id), is_callback=False)

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа")
        return
    await message.answer("👑 Админ-панель", reply_markup=admin_keyboard())

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "ℹ️ Помощь\n\n"
        "/start — главное меню\n"
        "/admin — панель администратора\n"
        "/getchatid — ID чата и темы\n\n"
        f"Поддержка: @{SUPPORT_USERNAME}"
    )

@dp.message(Command("getchatid"))
async def cmd_getchatid(message: Message):
    chat_id = message.chat.id
    thread_id = message.message_thread_id
    text = f"ID чата: {chat_id}"
    if thread_id:
        text += f"\nID темы: {thread_id}"
    else:
        text += "\n(это не тема супергруппы)"
    await message.answer(text)

# ============ НАЗАД В МЕНЮ ============

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    await state.clear()
    temp_deal_data.pop(user_id, None)
    user_states.pop(user_id, None)
    text = get_welcome_text(user_id)
    await send_or_edit_with_banner(call, text, main_keyboard(user_id), is_callback=True)

# ============ ЯЗЫК ============

@dp.callback_query(F.data == "language")
async def language_callback(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
         InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton(text="🇪🇸 Español", callback_data="lang_es"),
         InlineKeyboardButton(text="🇫🇷 Français", callback_data="lang_fr")],
        [InlineKeyboardButton(text="🇩🇪 Deutsch", callback_data="lang_de")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")],
    ])
    try:
        await call.message.edit_text("🌐 Choose language / Выбери язык:", reply_markup=kb)
    except Exception:
        await call.message.answer("🌐 Choose language / Выбери язык:", reply_markup=kb)

@dp.callback_query(F.data.in_({"lang_ru", "lang_en", "lang_es", "lang_fr", "lang_de"}))
async def set_language(call: CallbackQuery):
    user_id = call.from_user.id
    lang = call.data.split("_")[1]
    user_language[user_id] = lang
    lang_names = {
        'ru': '✅ Язык изменён на Русский',
        'en': '✅ Language changed to English',
        'es': '✅ Idioma cambiado a Español',
        'fr': '✅ Langue changée en Français',
        'de': '✅ Sprache zu Deutsch geändert',
    }
    msg = lang_names.get(lang, '✅ Язык изменён')
    # Сразу показываем меню на новом языке
    text = get_welcome_text(user_id)
    await send_or_edit_with_banner(call, text, main_keyboard(user_id), is_callback=True)
    await call.answer(msg)

# ============ ТОП ПРОДАВЦОВ ============

@dp.callback_query(F.data == "top_sellers")
async def top_sellers_callback(call: CallbackQuery):
    text = "⭐ Топ продавцов\n\n"
    for i, s in enumerate(TOP_SELLERS, 1):
        text += f"{i}. {s['name']} — {s['deals']} сделок, рейтинг {s['rating']}\n"
    try:
        await call.message.edit_text(text, reply_markup=back_kb())
    except Exception:
        await call.message.answer(text, reply_markup=back_kb())

# ============ ПРОФИЛЬ ============

@dp.callback_query(F.data == "profile")
async def profile_callback(call: CallbackQuery):
    user_id = call.from_user.id
    user = users.get(user_id, {})
    stats = user_stats.get(user_id, {'deals_total': 0, 'deals_success': 0, 'deals_failed': 0, 'status': 'new'})
    rating = get_user_rating(user_id)
    reviews_count = len(reviews_db.get(user_id, []))
    req = user_requisites.get(user_id, {})
    req_text = req.get('card', 'не указаны')
    text = (
        f"👤 Профиль\n\n"
        f"ID: {user_id}\n"
        f"Username: @{user.get('username', 'нет')}\n"
        f"Регистрация: {user.get('reg_date', '—')}\n"
        f"Статус: {get_user_status(user_id)}\n"
        f"Рейтинг: {rating:.1f}/5 ({reviews_count} отзывов)\n"
        f"Реквизиты: {req_text}\n\n"
        f"Сделки:\n"
        f"  Всего: {stats['deals_total']}\n"
        f"  Успешных: {stats['deals_success']}\n"
        f"  Провалено: {stats['deals_failed']}"
    )
    try:
        await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Оставить отзыв", callback_data="leave_review")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")],
        ]))
    except Exception:
        await call.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Оставить отзыв", callback_data="leave_review")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")],
        ]))

@dp.callback_query(F.data == "leave_review")
async def leave_review_callback(call: CallbackQuery):
    user_id = call.from_user.id
    user_states[user_id] = {'action': 'review_select_user'}
    try:
        await call.message.edit_text(
            "👤 Кому оставить отзыв?\n\nВведи ID пользователя или @username:",
            reply_markup=back_kb("profile")
        )
    except Exception:
        await call.message.answer(
            "👤 Кому оставить отзыв?\n\nВведи ID пользователя или @username:",
            reply_markup=back_kb("profile")
        )

@dp.callback_query(F.data.startswith("rating_"))
async def rating_callback(call: CallbackQuery):
    user_id = call.from_user.id
    rating = int(call.data.split("_")[1])
    target_id = user_states.get(user_id, {}).get('target_id', user_id)
    user_states[user_id] = {'action': 'review_text', 'rating': rating, 'target_id': target_id}
    try:
        await call.message.edit_text(
            f"Рейтинг: {rating}/5\n\nНапиши отзыв (максимум 500 символов):",
            reply_markup=back_kb("profile")
        )
    except Exception:
        await call.message.answer(
            f"Рейтинг: {rating}/5\n\nНапиши отзыв (максимум 500 символов):",
            reply_markup=back_kb("profile")
        )

# ============ РЕКВИЗИТЫ ============

@dp.callback_query(F.data == "my_requisites")
async def my_requisites_callback(call: CallbackQuery):
    user_id = call.from_user.id
    req = user_requisites.get(user_id, {})
    text = (
        f"💰 Мои реквизиты\n\n"
        f"Карта/СБП: {req.get('card', 'не указаны')}\n"
        f"TON: {req.get('ton', 'не указан')}\n"
        f"USDT: {req.get('usdt', 'не указан')}\n\n"
        "Выбери что изменить:"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Карта / СБП", callback_data="set_req_card")],
        [InlineKeyboardButton(text="💎 TON кошелёк", callback_data="set_req_ton")],
        [InlineKeyboardButton(text="💵 USDT кошелёк", callback_data="set_req_usdt")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")],
    ])
    try:
        await call.message.edit_text(text, reply_markup=kb)
    except Exception:
        await call.message.answer(text, reply_markup=kb)

@dp.callback_query(F.data.in_({"set_req_card", "set_req_ton", "set_req_usdt"}))
async def set_req_callback(call: CallbackQuery):
    user_id = call.from_user.id
    field_map = {"set_req_card": "card", "set_req_ton": "ton", "set_req_usdt": "usdt"}
    label_map = {"set_req_card": "номер карты или СБП", "set_req_ton": "TON адрес", "set_req_usdt": "USDT (TRC20) адрес"}
    field = field_map[call.data]
    user_states[user_id] = {'action': 'set_req', 'field': field}
    try:
        await call.message.edit_text(
            f"Введи {label_map[call.data]}:",
            reply_markup=back_kb("my_requisites")
        )
    except Exception:
        await call.message.answer(
            f"Введи {label_map[call.data]}:",
            reply_markup=back_kb("my_requisites")
        )

# ============ КАТАЛОГ ============

@dp.callback_query(F.data == "catalog")
async def catalog_callback(call: CallbackQuery):
    buttons = []
    for cat in categories:
        buttons.append([InlineKeyboardButton(text=cat["name"], callback_data=f"cat_{cat['id']}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
    try:
        await call.message.edit_text("🛒 Каталог — выбери категорию:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        await call.message.answer("🛒 Каталог — выбери категорию:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("cat_"))
async def category_callback(call: CallbackQuery):
    cat_id = int(call.data.split("_")[1])
    cat = next((c for c in categories if c["id"] == cat_id), None)
    if not cat:
        await call.answer("Категория не найдена")
        return
    buttons = []
    for sub_idx, sub in enumerate(cat["subcategories"]):
        buttons.append([InlineKeyboardButton(text=sub["name"], callback_data=f"sub_{cat_id}_{sub_idx}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="catalog")])
    try:
        await call.message.edit_text(f"{cat['name']}\n\nВыбери подкатегорию:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        await call.message.answer(f"{cat['name']}\n\nВыбери подкатегорию:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("sub_"))
async def subcategory_callback(call: CallbackQuery):
    parts = call.data.split("_")
    cat_id = int(parts[1])
    sub_idx = int(parts[2])
    cat = next((c for c in categories if c["id"] == cat_id), None)
    if not cat or sub_idx >= len(cat["subcategories"]):
        await call.answer()
        return
    sub = cat["subcategories"][sub_idx]
    sub_products = [(pid, p) for pid, p in products.items()
                    if p['category'] == cat_id and p['subcategory'] == sub['name']]
    buttons = []
    for pid, p in sub_products[:20]:
        buttons.append([InlineKeyboardButton(
            text=f"{p['name']} — {p['price']}₽",
            callback_data=f"prod_{pid}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"cat_{cat_id}")])
    try:
        await call.message.edit_text(
            f"📦 {sub['name']}\n\nВыбери товар:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    except Exception:
        await call.message.answer(
            f"📦 {sub['name']}\n\nВыбери товар:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )

@dp.callback_query(F.data.startswith("prod_"))
async def product_callback(call: CallbackQuery):
    pid = call.data[5:]
    p = products.get(pid)
    if not p:
        await call.answer("Товар не найден")
        return
    text = (
        f"📦 {p['name']}\n\n"
        f"📝 {p['description']}\n\n"
        f"💰 Цена: {p['price']}₽\n"
        f"📊 В наличии: {p['stock']} шт."
    )
    cat = next((c for c in categories if c["id"] == p['category']), None)
    sub_idx = 0
    if cat:
        for i, s in enumerate(cat["subcategories"]):
            if s["name"] == p['subcategory']:
                sub_idx = i
                break
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Купить", callback_data=f"buy_{pid}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"sub_{p['category']}_{sub_idx}")],
    ])
    try:
        await call.message.edit_text(text, reply_markup=kb)
    except Exception:
        await call.message.answer(text, reply_markup=kb)

@dp.callback_query(F.data.startswith("buy_"))
async def buy_callback(call: CallbackQuery):
    pid = call.data[4:]
    p = products.get(pid)
    if not p:
        await call.answer()
        return
    text = (
        f"🛒 Покупка: {p['name']}\n\n"
        f"💰 Сумма: {p['price']}₽\n\n"
        "Выбери способ оплаты:"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Карта / СБП", callback_data=f"pay_card_{pid}")],
        [InlineKeyboardButton(text="💎 TON", callback_data=f"pay_ton_{pid}")],
        [InlineKeyboardButton(text="💵 USDT", callback_data=f"pay_usdt_{pid}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"prod_{pid}")],
    ])
    try:
        await call.message.edit_text(text, reply_markup=kb)
    except Exception:
        await call.message.answer(text, reply_markup=kb)

@dp.callback_query(F.data.startswith("pay_"))
async def pay_callback(call: CallbackQuery):
    parts = call.data.split("_", 2)
    method = parts[1]
    pid = parts[2]
    p = products.get(pid)
    if not p:
        await call.answer()
        return
    if method == "card":
        details = f"💳 Карта / СБП:\n{MANAGER_CARD}"
    elif method == "ton":
        details = f"💎 TON кошелёк:\n{TON_WALLET}"
    else:
        details = f"💵 USDT (TRC20):\n{USDT_WALLET}"
    text = (
        f"💰 Оплата: {p['name']}\n\n"
        f"Сумма: {p['price']}₽\n\n"
        f"{details}\n\n"
        f"После оплаты нажми «Оплатил» и дождись подтверждения.\n"
        f"По вопросам: @{MANAGER_USERNAME}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"paid_{pid}_{method}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"buy_{pid}")],
    ])
    try:
        await call.message.edit_text(text, reply_markup=kb)
    except Exception:
        await call.message.answer(text, reply_markup=kb)

@dp.callback_query(F.data.startswith("paid_"))
async def paid_callback(call: CallbackQuery):
    parts = call.data.split("_", 2)
    pid = parts[1]
    method = parts[2]
    p = products.get(pid)
    user_id = call.from_user.id
    username = call.from_user.username or str(user_id)

    # Создаём заявку на подтверждение
    req_id = generate_id()
    payment_requests[req_id] = {
        'id': req_id,
        'deal_id': None,
        'product_id': pid,
        'product_name': p['name'] if p else '?',
        'buyer_id': user_id,
        'buyer_username': username,
        'amount': p['price'] if p else 0,
        'method': method,
        'type': 'catalog',
        'description': f"Покупка: {p['name']}" if p else "Покупка товара",
        'status': 'pending',
        'created': datetime.now().strftime("%d.%m.%Y %H:%M"),
    }

    try:
        await call.message.edit_text(
            f"Заявка отправлена!\n\n"
            f"Менеджер @{MANAGER_USERNAME} проверит оплату и свяжется с тобой.\n"
            "Обычно это занимает до 15 минут.",
            reply_markup=back_kb()
        )
    except Exception:
        await call.message.answer(
            f"Заявка отправлена!\n\n"
            f"Менеджер @{MANAGER_USERNAME} проверит оплату и свяжется с тобой.\n"
            "Обычно это занимает до 15 минут.",
            reply_markup=back_kb()
        )

    await log_event('deal_paid', user_id, f"@{username} заявил оплату: {p['name'] if p else '?'} за {p['price'] if p else '?'}₽ ({method})")

    # Уведомление админу с кнопками подтверждения
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Оплата получена / Товар передан", callback_data=f"payment_confirm_{req_id}"),],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"payment_reject_{req_id}")],
    ])
    try:
        await bot.send_message(
            ADMIN_ID,
            f"🛒 Новая заявка на оплату!\n\n"
            f"ID заявки: {req_id}\n"
            f"👤 @{username} (id={user_id})\n"
            f"📦 {p['name'] if p else '?'}\n"
            f"💰 {p['price'] if p else '?'}₽\n"
            f"💳 Метод: {method}",
            reply_markup=kb
        )
    except Exception:
        pass

# ============ СОЗДАТЬ СДЕЛКУ ============

@dp.callback_query(F.data == "create_deal")
async def create_deal_callback(call: CallbackQuery):
    text = "🤝 Создать сделку\n\nВыбери тип сделки:"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 Игры / Аккаунты", callback_data="deal_type_game")],
        [InlineKeyboardButton(text="🎁 NFT / Подарки Telegram", callback_data="deal_type_nft")],
        [InlineKeyboardButton(text="🔗 NFT Username (TON)", callback_data="deal_type_nft_username")],
        [InlineKeyboardButton(text="💼 Услуги", callback_data="deal_type_service")],
        [InlineKeyboardButton(text="⭐ Telegram Stars", callback_data="deal_type_stars")],
        [InlineKeyboardButton(text="💎 Крипто (TON/BTC/ETH...)", callback_data="deal_type_crypto")],
        [InlineKeyboardButton(text="📦 Товары / Другое", callback_data="deal_type_goods")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")],
    ])
    try:
        await call.message.edit_text(text, reply_markup=kb)
    except Exception:
        await call.message.answer(text, reply_markup=kb)

CURRENCY_SYMBOLS = {
    'RUB': '₽', 'USD': '$', 'EUR': '€', 'GBP': '£', 'UAH': '₴', 'KZT': '₸',
    'TON': 'TON', 'BTC': '₿', 'ETH': 'Ξ', 'USDT': 'USDT', 'USDC': 'USDC',
    'SOL': 'SOL', 'DOGE': 'DOGE', 'XRP': 'XRP', 'LTC': 'LTC', 'ADA': 'ADA',
    'STARS': '⭐',
}

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
             InlineKeyboardButton(text="₽ Рубли", callback_data=f"cur_{deal_type}_RUB"),
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
             InlineKeyboardButton(text="₽ Рубли", callback_data=f"cur_{deal_type}_RUB"),
             InlineKeyboardButton(text="$ USD", callback_data=f"cur_{deal_type}_USD")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="create_deal")],
        ])
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="₽ Рубли", callback_data=f"cur_{deal_type}_RUB"),
             InlineKeyboardButton(text="$ USD", callback_data=f"cur_{deal_type}_USD"),
             InlineKeyboardButton(text="€ EUR", callback_data=f"cur_{deal_type}_EUR")],
            [InlineKeyboardButton(text="£ GBP", callback_data=f"cur_{deal_type}_GBP"),
             InlineKeyboardButton(text="₴ UAH", callback_data=f"cur_{deal_type}_UAH"),
             InlineKeyboardButton(text="₸ KZT", callback_data=f"cur_{deal_type}_KZT")],
            [InlineKeyboardButton(text="💎 TON", callback_data=f"cur_{deal_type}_TON"),
             InlineKeyboardButton(text="₮ USDT", callback_data=f"cur_{deal_type}_USDT")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="create_deal")],
        ])

    try:
        await call.message.edit_text("💱 Выбери валюту для сделки:", reply_markup=kb)
    except Exception:
        await call.message.answer("💱 Выбери валюту для сделки:", reply_markup=kb)

@dp.callback_query(F.data.startswith("cur_"))
async def currency_callback(call: CallbackQuery):
    user_id = call.from_user.id
    # cur_{deal_type}_{CURRENCY}
    parts = call.data.split("_", 2)
    deal_type = parts[1]
    currency = parts[2]

    temp_deal_data.setdefault(user_id, {})['currency'] = currency
    temp_deal_data[user_id]['currency_symbol'] = CURRENCY_SYMBOLS.get(currency, currency)
    user_states[user_id] = {'action': 'deal_amount'}

    if currency in ['TON', 'BTC', 'ETH', 'USDT', 'USDC', 'SOL', 'DOGE', 'XRP', 'LTC', 'ADA']:
        prompt = f"💰 Введи сумму в {currency}:\n\nПример: 1.5"
    elif currency == 'STARS':
        prompt = "⭐ Введи количество Telegram Stars:\n\nПример: 500"
    else:
        sym = CURRENCY_SYMBOLS.get(currency, currency)
        prompt = f"💰 Введи сумму в {sym}:\n\nПример: 5000"

    try:
        await call.message.edit_text(prompt, reply_markup=back_kb("create_deal"))
    except Exception:
        await call.message.answer(prompt, reply_markup=back_kb("create_deal"))

# ============ ПРИСОЕДИНЕНИЕ К СДЕЛКЕ ============

@dp.callback_query(F.data.startswith("join_deal_"))
async def join_deal_callback(call: CallbackQuery):
    deal_id = call.data.replace("join_deal_", "")
    deal = deals.get(deal_id)
    user_id = call.from_user.id

    if not deal:
        await call.answer("❌ Сделка не найдена")
        return
    if user_id == deal['buyer_id'] or user_id == deal.get('seller_id'):
        await call.answer("✅ Вы уже участник этой сделки", show_alert=True)
        return

    if deal.get('seller_id') is None:
        deal['seller_id'] = user_id
        deal['seller_username'] = call.from_user.username or str(user_id)
        await call.answer("✅ Вы присоединились к сделке!", show_alert=True)

        try:
            await bot.send_message(
                deal['buyer_id'],
                f"✅ К вашей сделке присоединился участник!\n\n"
                f"ID: {deal_id}\n"
                f"Участник: @{deal['seller_username']}\n"
                f"Сумма: {deal.get('amount_display', deal['amount'])}\n\n"
                "Сделка готова к подтверждению менеджером!"
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
                f"🤝 Участник присоединился к сделке!\n\n"
                f"ID: {deal_id}\n"
                f"Создатель: @{deal['buyer_username']} (id={deal['buyer_id']})\n"
                f"Участник: @{deal['seller_username']} (id={user_id})\n"
                f"Сумма: {deal.get('amount_display', deal['amount'])}\n"
                f"Описание: {deal['description']}",
                reply_markup=deal_markup
            )
        except Exception:
            pass

        try:
            await call.message.edit_text(
                f"✅ Вы присоединились к сделке!\n\n"
                f"ID: {deal_id}\n"
                f"Создатель: @{deal['buyer_username']}\n"
                f"Сумма: {deal.get('amount_display', deal['amount'])}\n\n"
                "Ожидайте подтверждения менеджера...",
                reply_markup=back_kb()
            )
        except Exception:
            await call.message.answer(
                f"✅ Вы присоединились к сделке!",
                reply_markup=back_kb()
            )
    else:
        await call.answer("❌ К этой сделке уже присоединился второй участник", show_alert=True)

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
    try:
        await bot.send_message(deal['buyer_id'],
            f"✅ Сделка {deal_id} подтверждена!\n\n"
            f"Сумма: {deal.get('amount_display', deal['amount'])}\n"
            f"Продавец: @{deal.get('seller_username', '?')}\n\n"
            f"Менеджер @{MANAGER_USERNAME} свяжется с вами."
        )
    except Exception:
        pass
    seller_id = deal.get('seller_id')
    if seller_id:
        try:
            await bot.send_message(seller_id,
                f"✅ Сделка {deal_id} подтверждена!\n\n"
                f"Сумма: {deal.get('amount_display', deal['amount'])}\n"
                f"Покупатель: @{deal['buyer_username']}\n"
                f"Передайте товар. Менеджер @{MANAGER_USERNAME} проверит сделку."
            )
        except Exception:
            pass
    await log_event('payment_confirmed', deal['buyer_id'], f"Сделка {deal_id} подтверждена")
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
    try:
        await bot.send_message(deal['buyer_id'],
            f"❌ Сделка {deal_id} отклонена.\n\n"
            f"Свяжитесь с менеджером @{MANAGER_USERNAME} для уточнений."
        )
    except Exception:
        pass
    seller_id = deal.get('seller_id')
    if seller_id:
        try:
            await bot.send_message(seller_id,
                f"❌ Сделка {deal_id} отклонена.\n\n"
                f"Сумма: {deal.get('amount_display', deal['amount'])}\n"
                f"Свяжитесь с менеджером @{MANAGER_USERNAME}."
            )
        except Exception:
            pass
    await log_event('payment_rejected', deal['buyer_id'], f"Сделка {deal_id} отклонена")
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
        await call.answer("❌ Сделка не найдена")
        return
    text = (
        f"📋 Детали сделки {deal_id}\n\n"
        f"Статус: {deal['status']}\n"
        f"Дата: {deal['created']}\n\n"
        f"Покупатель: @{deal['buyer_username']} (id={deal['buyer_id']})\n"
        f"Продавец: @{deal.get('seller_username', '?')} (id={deal.get('seller_id', '?')})\n\n"
        f"Сумма: {deal.get('amount_display', deal['amount'])}\n"
        f"Тип: {deal['type']}\n\n"
        f"Описание:\n{deal['description']}"
    )
    try:
        await call.message.edit_text(text, reply_markup=back_kb("admin_deals"))
    except Exception:
        await call.message.answer(text, reply_markup=back_kb("admin_deals"))

# ============ ПРОДАТЬ ТОВАР ============

@dp.callback_query(F.data == "sell_product")
async def sell_product_callback(call: CallbackQuery):
    user_id = call.from_user.id
    user_states[user_id] = {'action': 'sell_name'}
    try:
        await call.message.edit_text("📤 Продать товар\n\nВведи название товара:", reply_markup=back_kb())
    except Exception:
        await call.message.answer("📤 Продать товар\n\nВведи название товара:", reply_markup=back_kb())

# ============ АДМИН-ПАНЕЛЬ ============

@dp.callback_query(F.data == "admin_panel")
async def admin_panel_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ Нет доступа", show_alert=True)
        return
    try:
        await call.message.edit_text("👑 Админ-панель", reply_markup=admin_keyboard())
    except Exception:
        await call.message.answer("👑 Админ-панель", reply_markup=admin_keyboard())

@dp.callback_query(F.data == "admin_stats")
async def admin_stats_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer()
        return
    active = len([d for d in deals.values() if d.get('status') not in ('confirmed', 'rejected')])
    log_status = f"включены (чат {LOG_CHAT_ID})" if LOG_CHAT_ID else "отключены"
    pending_pay = len([r for r in payment_requests.values() if r.get('status') == 'pending'])
    text = (
        f"📊 Статистика\n\n"
        f"Пользователей: {len(users)}\n"
        f"Товаров: {len(products)}\n"
        f"Всего сделок: {len(deals)}\n"
        f"Активных сделок: {active}\n"
        f"Заявок на оплату (ожидают): {pending_pay}\n"
        f"Логи: {log_status}"
    )
    try:
        await call.message.edit_text(text, reply_markup=admin_keyboard())
    except Exception:
        await call.message.answer(text, reply_markup=admin_keyboard())

@dp.callback_query(F.data == "admin_users")
async def admin_users_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer()
        return
    text = f"👥 Пользователи ({len(users)} чел.)\n\n"
    for uid, u in list(users.items())[:15]:
        stats = user_stats.get(uid, {})
        status = USER_STATUSES.get(stats.get('status', 'new'), USER_STATUSES['new'])['name_ru']
        text += f"• @{u.get('username','нет')} (id={uid}) — {status}\n"
    try:
        await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
        ]))
    except Exception:
        await call.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
        ]))

@dp.callback_query(F.data == "admin_deals")
async def admin_deals_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer()
        return
    text = f"🤝 Сделки ({len(deals)} всего)\n\n"
    for did, d in list(deals.items())[:10]:
        text += f"• #{did} — {d.get('type','?')} — {d.get('amount_display', d.get('amount','?'))} — {d.get('status','?')}\n"
    if not deals:
        text += "Сделок пока нет."
    try:
        await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
        ]))
    except Exception:
        await call.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
        ]))

@dp.callback_query(F.data == "admin_statuses")
async def admin_statuses_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer()
        return
    user_states[call.from_user.id] = {'action': 'admin_set_status_id'}
    try:
        await call.message.edit_text(
            "🚦 Изменить статус пользователя\n\nВведи ID пользователя:",
            reply_markup=back_kb("admin_panel")
        )
    except Exception:
        await call.message.answer(
            "🚦 Изменить статус пользователя\n\nВведи ID пользователя:",
            reply_markup=back_kb("admin_panel")
        )

# --- Выдать репутацию из адм. панели ---

@dp.callback_query(F.data == "admin_give_rep")
async def admin_give_rep_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer()
        return
    user_states[call.from_user.id] = {'action': 'admin_give_reputation'}
    try:
        await call.message.edit_text(
            "⭐ Выдать репутацию\n\nВведи ID пользователя или @username:",
            reply_markup=back_kb("admin_panel")
        )
    except Exception:
        await call.message.answer(
            "⭐ Выдать репутацию\n\nВведи ID пользователя или @username:",
            reply_markup=back_kb("admin_panel")
        )

@dp.callback_query(F.data.startswith("give_rep_"))
async def give_reputation_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ Только администратор", show_alert=True)
        return
    parts = call.data.split("_")
    rating = int(parts[2])
    target_id = int(parts[3])
    reviews_db.setdefault(target_id, []).append({
        'author_id': ADMIN_ID,
        'author_username': 'АДМИНИСТРАТОР',
        'rating': rating,
        'text': 'Репутация выдана администратором',
        'created': datetime.now().strftime("%d.%m.%Y %H:%M"),
    })
    try:
        await bot.send_message(
            target_id,
            f"⭐ Репутация выдана!\n\nРейтинг: {rating}/5\nСпасибо за хорошую работу!"
        )
    except Exception:
        pass
    await call.answer("✅ Репутация выдана!", show_alert=True)
    try:
        await call.message.edit_text(f"✅ Репутация {rating}/5 выдана пользователю {target_id}", reply_markup=back_kb("admin_panel"))
    except Exception:
        pass

@dp.callback_query(F.data == "admin_reviews_panel")
async def admin_reviews_panel_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer()
        return
    count = sum(len(v) for v in reviews_db.values())
    text = f"📝 Отзывы\n\nВсего: {count}\nНа модерации: {len(moderation_queue)}"
    try:
        await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
        ]))
    except Exception:
        await call.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
        ]))

@dp.callback_query(F.data == "admin_moderation")
async def admin_moderation_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer()
        return
    if not moderation_queue:
        try:
            await call.message.edit_text("✅ Очередь модерации пуста.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
            ]))
        except Exception:
            await call.message.answer("✅ Очередь модерации пуста.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
            ]))
        return
    item = moderation_queue[0]
    text = (
        f"Модерация ({len(moderation_queue)} в очереди)\n\n"
        f"@{item.get('username','?')}\n"
        f"Товар: {item.get('name','?')}\n"
        f"Цена: {item.get('price','?')}₽\n"
        f"Описание: {item.get('desc','?')}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Одобрить", callback_data="mod_approve"),
         InlineKeyboardButton(text="❌ Отклонить", callback_data="mod_reject")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")],
    ])
    try:
        await call.message.edit_text(text, reply_markup=kb)
    except Exception:
        await call.message.answer(text, reply_markup=kb)

@dp.callback_query(F.data.in_({"mod_approve", "mod_reject"}))
async def mod_action_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer()
        return
    if moderation_queue:
        item = moderation_queue.pop(0)
        if call.data == "mod_approve":
            pid = generate_id()
            products[pid] = {
                'id': pid, 'name': item['name'], 'description': item.get('desc', ''),
                'price': item['price'], 'category': 9, 'category_name': '🔞 Другое',
                'subcategory': 'Эксклюзив', 'stock': 1,
            }
            await call.answer("✅ Одобрено", show_alert=True)
            await log_event('product_added', item.get('seller_id', 0),
                f"Товар одобрен: {item['name']} за {item['price']}₽")
        else:
            await call.answer("❌ Отклонено", show_alert=True)
    try:
        await call.message.edit_text("👑 Админ-панель", reply_markup=admin_keyboard())
    except Exception:
        await call.message.answer("👑 Админ-панель", reply_markup=admin_keyboard())

@dp.callback_query(F.data == "admin_products")
async def admin_products_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer()
        return
    cat_counts = {}
    for p in products.values():
        cn = p.get('category_name', '?')
        cat_counts[cn] = cat_counts.get(cn, 0) + 1
    text = f"📦 Товары ({len(products)} шт.)\n\n"
    for cn, cnt in cat_counts.items():
        text += f"• {cn}: {cnt} шт.\n"
    try:
        await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
        ]))
    except Exception:
        await call.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
        ]))

# ============ БАННЕР ============

@dp.callback_query(F.data == "admin_banner")
async def admin_banner_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer()
        return
    text = (
        "📸 Баннер\n\n"
        "Текущий баннер: " + ("загружен ✅" if (BANNER_FILE_ID or BANNER_BYTES) else "не загружен ❌") +
        "\n\nОтправь команду /admin_upload и сразу после — фото для загрузки нового баннера."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑️ Удалить баннер", callback_data="delete_banner")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")],
    ])
    try:
        await call.message.edit_text(text, reply_markup=kb)
    except Exception:
        await call.message.answer(text, reply_markup=kb)

@dp.callback_query(F.data == "delete_banner")
async def delete_banner_callback(call: CallbackQuery):
    global BANNER_FILE_ID, BANNER_BYTES
    if call.from_user.id != ADMIN_ID:
        await call.answer()
        return
    BANNER_FILE_ID = None
    BANNER_BYTES = None
    await call.answer("✅ Баннер удалён", show_alert=True)
    try:
        await call.message.edit_text("📸 Баннер удалён.", reply_markup=back_kb("admin_panel"))
    except Exception:
        pass

@dp.message(Command("admin_upload"))
async def admin_upload_banner(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Только администратор")
        return
    user_states[message.from_user.id] = {'action': 'upload_banner'}
    await message.answer("📸 Отправь фото для баннера:")

@dp.message(F.photo)
async def handle_photo(message: Message):
    global BANNER_FILE_ID, BANNER_BYTES
    user_id = message.from_user.id
    state_data = user_states.get(user_id, {})

    if state_data.get('action') == 'upload_banner' and user_id == ADMIN_ID:
        try:
            # Сохраняем file_id Telegram (не скачиваем — просто используем ID)
            BANNER_FILE_ID = message.photo[-1].file_id
            BANNER_BYTES = None  # Сбрасываем байты если были
            del user_states[user_id]
            await message.answer("✅ Баннер загружен и будет показываться в главном меню!")
            await log_event('product_added', user_id, "Баннер обновлён администратором")
        except Exception as e:
            await message.answer(f"❌ Ошибка: {str(e)[:100]}")

# ============ ЛОГИ ============

@dp.callback_query(F.data == "admin_logs")
async def admin_logs_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ Нет доступа", show_alert=True)
        return
    if LOG_CHAT_ID:
        thread_info = f"\nТема: {LOG_THREAD_ID}" if LOG_THREAD_ID else "\n(общий чат)"
        text = f"📋 Логирование включено\n\nЧат: {LOG_CHAT_ID}{thread_info}"
    else:
        text = "📋 Логирование отключено"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Установить чат / тему", callback_data="set_log_chat")],
        [InlineKeyboardButton(text="❌ Отключить логи", callback_data="disable_logs")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")],
    ])
    try:
        await call.message.edit_text(text, reply_markup=kb)
    except Exception:
        await call.message.answer(text, reply_markup=kb)

@dp.callback_query(F.data == "set_log_chat")
async def set_log_chat_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ Нет доступа", show_alert=True)
        return
    user_states[call.from_user.id] = {'action': 'set_log_chat_id'}
    try:
        await call.message.edit_text(
            "Введи ID чата (например -1001234567890):",
            reply_markup=back_kb("admin_logs")
        )
    except Exception:
        await call.message.answer(
            "Введи ID чата (например -1001234567890):",
            reply_markup=back_kb("admin_logs")
        )

@dp.callback_query(F.data == "disable_logs")
async def disable_logs_callback(call: CallbackQuery):
    global LOG_CHAT_ID, LOG_THREAD_ID
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ Нет доступа", show_alert=True)
        return
    LOG_CHAT_ID = None
    LOG_THREAD_ID = None
    await call.answer("✅ Логирование отключено", show_alert=True)
    try:
        await call.message.edit_text("👑 Админ-панель", reply_markup=admin_keyboard())
    except Exception:
        pass

# ============ ЗАЯВКИ НА ОПЛАТУ ============

@dp.callback_query(F.data == "admin_payments")
async def admin_payments_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer()
        return
    pending = [r for r in payment_requests.values() if r.get('status') == 'pending']
    if not pending:
        try:
            await call.message.edit_text(
                f"💰 Заявки на оплату\n\nНет ожидающих заявок.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
                ])
            )
        except Exception:
            pass
        return
    req = pending[0]
    text = (
        f"💰 Заявки на оплату ({len(pending)} ожидают)\n\n"
        f"ID: {req['id']}\n"
        f"Пользователь: @{req['buyer_username']} (id={req['buyer_id']})\n"
        f"Сумма: {req['amount']}\n"
        f"Тип: {req.get('type','?')}\n"
        f"Описание: {req['description']}\n"
        f"Метод: {req.get('method','?')}\n\n"
        f"Создано: {req['created']}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Оплата получена / Товар передан", callback_data=f"payment_confirm_{req['id']}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"payment_reject_{req['id']}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")],
    ])
    try:
        await call.message.edit_text(text, reply_markup=kb)
    except Exception:
        await call.message.answer(text, reply_markup=kb)

@dp.callback_query(F.data.startswith("payment_confirm_"))
async def payment_confirm_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ Только администратор", show_alert=True)
        return
    req_id = call.data.replace("payment_confirm_", "")
    if req_id not in payment_requests:
        await call.answer("❌ Заявка не найдена")
        return
    payment_requests[req_id]['status'] = 'paid'
    buyer_id = payment_requests[req_id]['buyer_id']
    amount = payment_requests[req_id]['amount']
    try:
        await bot.send_message(
            buyer_id,
            f"✅ ОПЛАТА ПОДТВЕРЖДЕНА!\n\n"
            f"Сумма: {amount}\n"
            f"Товар/услуга получены. Менеджер @{MANAGER_USERNAME} свяжется с вами если нужна помощь."
        )
    except Exception:
        pass
    await call.answer("✅ Подтверждено!", show_alert=True)
    await log_event('payment_confirmed', buyer_id, f"Оплата по заявке {req_id} подтверждена")
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
    if req_id not in payment_requests:
        await call.answer("❌ Заявка не найдена")
        return
    payment_requests[req_id]['status'] = 'rejected'
    buyer_id = payment_requests[req_id]['buyer_id']
    try:
        await bot.send_message(
            buyer_id,
            f"❌ Оплата отклонена.\n\n"
            f"Свяжитесь с менеджером @{MANAGER_USERNAME} для уточнений."
        )
    except Exception:
        pass
    await call.answer("❌ Отклонено!", show_alert=True)
    await log_event('payment_rejected', buyer_id, f"Оплата по заявке {req_id} отклонена")
    try:
        await call.message.edit_text("❌ Оплата отклонена.", reply_markup=back_kb("admin_payments"))
    except Exception:
        pass

# ============ ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ ============

@dp.message(F.text)
async def handle_text(message: Message, state: FSMContext):
    global LOG_CHAT_ID, LOG_THREAD_ID
    user_id = message.from_user.id
    state_data = user_states.get(user_id, {})
    action = state_data.get('action')
    if not action:
        return
    text = message.text.strip()

    # ===== Сумма сделки =====
    if action == 'deal_amount':
        currency = temp_deal_data.get(user_id, {}).get('currency', 'RUB')
        currency_symbol = temp_deal_data.get(user_id, {}).get('currency_symbol', '₽')
        try:
            if currency in ['TON', 'BTC', 'ETH', 'USDT', 'USDC', 'SOL', 'DOGE', 'XRP', 'LTC', 'ADA']:
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
            await message.answer(
                f"Сумма: {display}\n\n📝 Опиши что продаётся/покупается:",
                reply_markup=back_kb("create_deal")
            )
        except ValueError:
            await message.answer(f"❌ Введи сумму числом, например: 5000")
        return

    # ===== Описание сделки =====
    if action == 'deal_description':
        deal_data = temp_deal_data.get(user_id, {})
        deal_id = generate_id()
        buyer_id = deal_data.get('buyer_id', user_id)
        buyer_username = message.from_user.username or str(buyer_id)
        amount_display = deal_data.get('amount_display', str(deal_data.get('amount', 0)))

        deals[deal_id] = {
            'id': deal_id,
            'buyer_id': buyer_id,
            'seller_id': None,
            'buyer_username': buyer_username,
            'seller_username': '?',
            'type': deal_data.get('type', '?'),
            'amount': deal_data.get('amount', 0),
            'amount_display': amount_display,
            'description': text,
            'status': 'pending',
            'created': datetime.now().strftime("%d.%m.%Y %H:%M"),
        }
        user_stats.setdefault(buyer_id, {'deals_total': 0, 'deals_success': 0, 'deals_failed': 0, 'status': 'new'})
        user_stats[buyer_id]['deals_total'] += 1
        temp_deal_data.pop(user_id, None)
        del user_states[user_id]

        deal_link = f"https://t.me/{BOT_USERNAME}?start=deal_{deal_id}"

        await message.answer(
            f"✅ Сделка создана!\n\n"
            f"ID: {deal_id}\n"
            f"Сумма: {amount_display}\n"
            f"Описание: {text}\n\n"
            f"Ссылка на сделку для второго участника:\n{deal_link}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔗 Открыть сделку", url=deal_link)],
                [InlineKeyboardButton(text="🔙 Меню", callback_data="back_to_menu")],
            ])
        )
        await log_event('deal_created', buyer_id, f"Сделка @{buyer_username} — {amount_display}")
        # НАМЕРЕННО НЕ отправляем уведомление администратору при создании сделки
        return

    # ===== Выбор пользователя для отзыва =====
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
            for uid, user in users.items():
                if user.get('username', '').lower() == target_text:
                    target_id = uid
                    break
        if not target_id:
            await message.answer("❌ Пользователь не найден. Введи ID или @username")
            return
        target_user = users.get(target_id, {})
        target_username = target_user.get('username', f"id{target_id}")
        user_states[user_id] = {'action': 'review_rating', 'target_id': target_id}
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐", callback_data="rating_1"),
             InlineKeyboardButton(text="⭐⭐", callback_data="rating_2"),
             InlineKeyboardButton(text="⭐⭐⭐", callback_data="rating_3")],
            [InlineKeyboardButton(text="⭐⭐⭐⭐", callback_data="rating_4"),
             InlineKeyboardButton(text="⭐⭐⭐⭐⭐", callback_data="rating_5")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="profile")],
        ])
        await message.answer(f"Оцени @{target_username}:", reply_markup=kb)
        return

    # ===== Текст отзыва =====
    if action == 'review_text':
        rating = state_data.get('rating', 5)
        target_id = state_data.get('target_id', user_id)
        review_text = message.text[:500]
        reviews_db.setdefault(target_id, []).append({
            'author_id': user_id,
            'author_username': message.from_user.username,
            'rating': rating,
            'text': review_text,
            'created': datetime.now().strftime("%d.%m.%Y %H:%M"),
        })
        del user_states[user_id]
        target_user = users.get(target_id, {})
        target_username = target_user.get('username', f"id{target_id}")
        await message.answer(
            f"✅ Отзыв добавлен!\n\n"
            f"Для: @{target_username}\n"
            f"Рейтинг: {rating}/5\n"
            f"Текст: {review_text}",
            reply_markup=back_kb()
        )
        await log_event('review_left', user_id, f"@{message.from_user.username} оставил отзыв ({rating}/5) для {target_id}")
        return

    # ===== Реквизиты =====
    if action == 'set_req':
        field = state_data['field']
        user_requisites.setdefault(user_id, {})[field] = text
        del user_states[user_id]
        await message.answer("✅ Реквизиты сохранены!", reply_markup=back_kb("my_requisites"))
        await log_event('requisites', user_id, f"@{message.from_user.username} обновил реквизиты ({field})")
        return

    # ===== Лог: ID чата =====
    if action == 'set_log_chat_id':
        try:
            LOG_CHAT_ID = int(text)
            user_states[user_id] = {'action': 'set_log_thread_id'}
            await message.answer(
                f"Чат сохранён: {LOG_CHAT_ID}\n\n"
                "Введи ID темы или 0 для общего чата:"
            )
        except ValueError:
            await message.answer("❌ Введи число (например -1001234567890)")
        return

    if action == 'set_log_thread_id':
        try:
            tid = int(text)
            LOG_THREAD_ID = tid if tid != 0 else None
            del user_states[user_id]
            try:
                await bot.send_message(
                    LOG_CHAT_ID, "✅ Логирование активировано!",
                    message_thread_id=LOG_THREAD_ID
                )
                await message.answer(f"✅ Логи включены!\n\nЧат: {LOG_CHAT_ID}\nТема: {LOG_THREAD_ID or 'нет'}")
            except Exception as e:
                await message.answer(f"❌ Не могу отправить сообщение: {e}\n\nПроверь что бот добавлен как администратор в чат.")
                LOG_CHAT_ID = None
                LOG_THREAD_ID = None
        except ValueError:
            await message.answer("❌ Введи число (или 0)")
        return

    # ===== Продажа: название =====
    if action == 'sell_name':
        temp_deal_data.setdefault(user_id, {})['name'] = text
        user_states[user_id] = {'action': 'sell_price'}
        await message.answer("💰 Введи цену (в рублях):")
        return

    # ===== Продажа: цена =====
    if action == 'sell_price':
        try:
            price = int(text.replace(' ', ''))
            temp_deal_data.setdefault(user_id, {})['price'] = price
            user_states[user_id] = {'action': 'sell_desc'}
            await message.answer("📝 Введи описание товара:")
        except ValueError:
            await message.answer("❌ Введи цену числом")
        return

    # ===== Продажа: описание =====
    if action == 'sell_desc':
        sell_data = temp_deal_data.get(user_id, {})
        sell_data['desc'] = text
        sell_data['seller_id'] = user_id
        sell_data['username'] = message.from_user.username or str(user_id)
        moderation_queue.append(sell_data)
        temp_deal_data.pop(user_id, None)
        del user_states[user_id]
        await message.answer(
            f"✅ Товар отправлен на модерацию!\n\n"
            f"Название: {sell_data['name']}\n"
            f"Цена: {sell_data['price']}₽\n\n"
            "Ждите одобрения администратором.",
            reply_markup=back_kb()
        )
        await log_event('product_added', user_id,
            f"@{sell_data['username']} отправил на модерацию: {sell_data['name']} за {sell_data['price']}₽")
        try:
            await bot.send_message(ADMIN_ID,
                f"Товар на модерации!\n\n"
                f"@{sell_data['username']}\n"
                f"Название: {sell_data['name']}\n"
                f"Цена: {sell_data['price']}₽\n"
                f"Описание: {text}")
        except Exception:
            pass
        return

    # ===== Адм: поиск пользователя для репутации =====
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
            await message.answer("❌ Пользователь не найден. Введи ID или @username")
            return
        target_user = users.get(target_id, {})
        target_username = target_user.get('username', f"id{target_id}")
        user_states[user_id] = {'action': 'admin_set_reputation_rating', 'target_id': target_id}
        await message.answer(
            f"Выдать репутацию @{target_username}\n\nВыбери количество звезд:",
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

    # ===== Адм: изменить статус шаг 1 =====
    if action == 'admin_set_status_id':
        try:
            target_id = int(text)
            user_states[user_id] = {'action': 'admin_set_status_val', 'target_id': target_id}
            statuses_list = "\n".join([f"• {k} — {v['name_ru']}" for k, v in USER_STATUSES.items()])
            await message.answer(f"Введи статус для id={target_id}:\n\n{statuses_list}")
        except ValueError:
            await message.answer("❌ Введи числовой ID")
        return

    # ===== Адм: изменить статус шаг 2 =====
    if action == 'admin_set_status_val':
        target_id = state_data.get('target_id')
        if text in USER_STATUSES:
            user_stats.setdefault(target_id, {'deals_total': 0, 'deals_success': 0, 'deals_failed': 0, 'status': 'new'})
            user_stats[target_id]['status'] = text
            del user_states[user_id]
            await message.answer(f"✅ Статус id={target_id} изменён на {USER_STATUSES[text]['name_ru']}")
            await log_event('status_changed', target_id, f"Статус изменён на {USER_STATUSES[text]['name_ru']}")
        else:
            await message.answer(f"❌ Неизвестный статус. Варианты: {', '.join(USER_STATUSES.keys())}")
        return

# ============ ЗАПУСК ============

async def main():
    load_products()
    print(f"LOLZ MARKET запущен! Товаров: {len(products)}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
