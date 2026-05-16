
# bot.py - Telegram Price Bot (Complete & Fixed)

import os
import json
import time
import threading
import requests
import re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    MessageHandler, 
    filters, 
    ConversationHandler,
    ContextTypes
)
from datetime import datetime
from bs4 import BeautifulSoup

# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════

════════════════════════════════

TOKEN = os.environ.get("BOT_TOKEN")
METALPRICE_API_KEY = os.environ.get("METALPRICE_API_KEY")
ADMIN_ID = 715854466
SCRAPER_SECRET = os.environ.get("SCRAPER_SECRET", "change_this_secret")

# File paths
RATE_FILE = "rates.json"
PRICE_FILE = "prices.json"
WORLD_PRICE_FILE = "world_prices.json"
METALS_FILE = "metals_prices.json"
FACTORY_PRICE_FILE = "factory_prices.json"

# Conversation states
WAITING_VALUE = 1

# Thread-safe file access
_file_lock = threading.Lock()

# Default factory data
DEFAULT_FACTORY_DATA = {
    "rebar": {
        "اصفهان": {"ذوبآهن": 58000, "فولاد مبارکه": 57500},
        "خوزستان": {"فولاد خوزستان": 58200}
    },

    "billet": {
        "اصفهان": {"ذوبآهن": 42500, "فولاد مبارکه": 42000},
        "خوزستان": {"فولاد خوزستان": 42800}
    },
    "dri": {
        "خراسان": {"فولاد خراسان": 14166}
    },
    "pellet": {
        "خراسان": {"گلگهر": 6500000}
    },
    "concentrate": {
        "کرمان": {"گلگهر": 4800000}
    }
}

# ═══════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def to_persian(num):
    """Convert English digits to Persian"""
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    return "".join(persian_digits[int(d)] if d.isdigit() else d for d in str(num))

def format_number(num):
    """Format number with commas and Persian digits"""
    try:
        formatted = f"{int(num):,}"
        return to_persian(formatted)
    except:
        return to_persian(str(num))

def format_float(num, decimals=2):
    """Format float with Persian digits"""
    try:
        formatted = f"{float(num):.{decimals}f}"
        return to_persian(formatted)
    except:

        return to_persian(str(num))

def save_json(filepath, data):
    """Thread-safe JSON save"""
    with _file_lock:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

def load_json(filepath, default):
    """Thread-safe JSON load with fallback"""
    with _file_lock:
        if not os.path.exists(filepath):
            return default
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return default

def is_admin(update: Update) -> bool:
    """Check if user is admin"""
    return update.effective_user.id == ADMIN_ID

# ═══════════════════════════════════════════════════════════════════
# DATA UPDATE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def update_rates():
    """Update exchange rates from Nobitex"""
    try:
        response = requests.get(
            "https://api.nobitex.ir/v2/orderbook/USDTIRT",
            timeout=10
        )
        data = response.json()
        free_rate = int(float(data["asks"][0][0]))
        
        rates = {
            "free": free_rate,
            "secondary": 140000,
            "last_update": datetime.now().isoformat()
        }
        save_json(RATE_FILE, rates)
        print(f"✓ Rates updated: {free_rate}")
    except Exception as e:
        print(f"✗ Rate update failed: {e}")
        save_json(RATE_FILE, {

            "free": 183000,
            "secondary": 140000,
            "last_update": datetime.now().isoformat()

def scrape_billet_from_ahanmelal():
    try:
        response = requests.get(
            "https://ahanmelal.com/steel-ingots/steel-ingot-price",
            timeout=15
        )

        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text()

        prices = re.findall(r"\d{5}", text)

        for price in prices:
            price_int = int(price)
            if 40000 < price_int < 60000:
                return price_int

    except Exception as e:
        print(f"Billet scrape error: {e}")

    return None

def scrape_rebar_from_ahanmelal():
    try:
        response = requests.get(
            "https://ahanmelal.com/steel-products/rebar-price",

            timeout=15
        )

        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text()

        prices = re.findall(r"\d{5}", text)

        for price in prices:
            price_int = int(price)
            if 50000 < price_int < 80000:
                return price_int

    except Exception as e:
        print(f"Rebar scrape error: {e}")

    return None

def update_all_prices():
    prices = {
        "concentrate": 4800000,
        "pellet": 6500000,
        "dri": 14166,
        "billet": 42500,
        "rebar": 58000,
    }

    billet = scrape_billet_from_ahanmelal()
    if billet:

        prices["billet"] = billet

    rebar = scrape_rebar_from_ahanmelal()
    if rebar:
        prices["rebar"] = rebar

    prices["last_update"] = datetime.now().isoformat()

    save_json(PRICE_FILE, prices)

def update_world_prices():
    iron_ore = 104.0

    world = {
        "iron_ore_base": iron_ore,

        "concentrate_fob": round(iron_ore * 0.42, 2),
        "concentrate_north": round(iron_ore * 0.46, 2),
        "concentrate_south": round(iron_ore * 0.44, 2),

        "pellet_fob": round(iron_ore * 1.25, 2),
        "pellet_north": round(iron_ore * 1.31, 2),
        "pellet_south": round(iron_ore * 1.28, 2),

        "dri_fob": round(iron_ore * 3.2, 2),
        "dri_north": round(iron_ore * 3.4, 2),
        "dri_south": round(iron_ore * 3.3, 2),

        "billet_fob": round(iron_ore * 5.1, 2),

        "billet_north": round(iron_ore * 5.3, 2),
        "billet_south": round(iron_ore * 5.2, 2),

        "rebar_fob": round(iron_ore * 5.8, 2),
        "rebar_north": round(iron_ore * 6.0, 2),
        "rebar_south": round(iron_ore * 5.9, 2),

        "source": "MetalPriceAPI",
        "last_update": datetime.now().isoformat()
    }

    save_json(WORLD_PRICE_FILE, world)

# ═══════════════════════════════════════════════════════════════════
# DATA LOADERS
# ═══════════════════════════════════════════════════════════════════

def load_rates():
    return load_json(RATE_FILE, {
        "free": 183000,
        "secondary": 140000
    })

def load_prices():
    return load_json(PRICE_FILE, {
        "concentrate": 4800000,
        "pellet": 6500000,
        "dri": 14166,
        "billet": 42500,
        "rebar": 58000
    })

def load_world_prices():
    return load_json(WORLD_PRICE_FILE, {})

def load_factory_prices():
    return load_json(FACTORY_PRICE_FILE, 

DEFAULT_FACTORY_DATA)

# ═══════════════════════════════════════════════════════════════════
# KEYBOARDS
# ═══════════════════════════════════════════════════════════════════

def main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🌍 جهانی", callback_data="world"),
            InlineKeyboardButton("🏭 کارخانه", callback_data="factory")
        ],
        [
            InlineKeyboardButton("📈 بورس کالا", callback_data="ice"),
            InlineKeyboardButton("💵 ارز", callback_data="rate")
        ]
    ]

    return InlineKeyboardMarkup(keyboard)

def factory_products_keyboard():

    keyboard = [
        [InlineKeyboardButton("میلگرد", callback_data="fact_rebar")],
        [InlineKeyboardButton("بیلت", callback_data="fact_billet")],
        [InlineKeyboardButton("آهن اسفنجی", callback_data="fact_dri")],
        [InlineKeyboardButton("گندله", callback_data="fact_pellet")],
        [InlineKeyboardButton("کنسانتره", callback_data="fact_concentrate")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back")]
    ]

    return InlineKeyboardMarkup(keyboard)

# ═══════════════════════════════════════════════════════════════════
# COMMAND HANDLERS
# ═══════════════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    welcome_text = (
        "🔹 به ربات قیمتیابی فولاد خوش آمدید\n\n"
        "📊 این ربات قیمتهای زیر را ارائه میدهد:\n"
        "• قیمت جهانی محصولات فولادی\n"
        "• قیمت کارخانههای داخلی\n"
        "• نرخ ارز\n"
        "• قیمت بورس کالا\n\n"
        "لطفاً یکی از گزینههای زیر را انتخاب کنید:"
    )
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=main_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    """Handle /help command"""
    help_text = (
        "📖 راهنمای استفاده:\n\n"
        "🌍 جهانی: قیمتهای جهانی محصولات\n"
        "🏭 کارخانه: قیمت کارخانههای داخلی\n"
        "💵 ارز: نرخ دلار آزاد و نیمایی\n"
        "📈 بورس کالا: قیمتهای بورس\n\n"
        "برای شروع از دستور /start استفاده کنید."
    )
    
    await update.message.reply_text(help_text)

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin command"""
    if not is_admin(update):
        await update.message.reply_text("⛔️ شما دسترسی ادمین ندارید.")
        return
    
    admin_text = (
        "🔧 پنل مدیریت\n\n"
        "دستورات موجود:\n"
        "/update_rates - بهروزرسانی نرخ ارز\n"
        "/update_prices - بهروزرسانی قیمتها\n"
        "/update_world - بهروزرسانی قیمت جهانی\n"
        "/status - وضعیت سیستم"
    )
    

    await update.message.reply_text(admin_text)

async def update_rates_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /update_rates command"""
    if not is_admin(update):
        await update.message.reply_text("⛔️ شما دسترسی ادمین ندارید.")
        return
    
    await update.message.reply_text("⏳ در حال بهروزرسانی نرخ ارز...")
    update_rates()
    await update.message.reply_text("✅ نرخ ارز بهروزرسانی شد.")

async def update_prices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /update_prices command"""
    if not is_admin(update):
        await update.message.reply_text("⛔️ شما دسترسی ادمین ندارید.")
        return
    
    await update.message.reply_text("⏳ در حال بهروزرسانی قیمتها...")
    update_all_prices()
    await update.message.reply_text("✅ قیمتها بهروزرسانی شد.")


async def update_world_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /update_world command"""
    if not is_admin(update):
        await update.message.reply_text("⛔️ شما دسترسی ادمین ندارید.")
        return
    
    await update.message.reply_text("⏳ در حال بهروزرسانی قیمت جهانی...")
    update_world_prices()
    await update.message.reply_text("✅ قیمت جهانی بهروزرسانی شد.")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command"""
    if not is_admin(update):
        await update.message.reply_text("⛔️ شما دسترسی ادمین ندارید.")
        return
    
    rates = load_rates()
    prices = load_prices()
    world = load_world_prices()
    
    status_text = (
        "📊 وضعیت سیستم:\n\n"

        f"💵 نرخ ارز: {format_number(rates.get('free', 0))} تومان\n"
        f"🏭 میلگرد: {format_number(prices.get('rebar', 0))} تومان\n"
        f"🏭 بیلت: {format_number(prices.get('billet', 0))} تومان\n"
        f"🌍 سنگآهن: ${format_float(world.get('iron_ore_base', 0))}\n\n"
        f"آخرین بهروزرسانی ارز: {rates.get('last_update', 'نامشخص')}\n"
        f"آخرین بهروزرسانی قیمت: {prices.get('last_update', 'نامشخص')}"
    )
    
    await update.message.reply_text(status_text)

# ═══════════════════════════════════════════════════════════════════
# CALLBACK HANDLERS - MAIN MENU
# ═══════════════════════════════════════════════════════════════════

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard buttons"""
    
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    # 🌍 World Prices
    if data == "world":
        world = load_world_prices()
        
        text = (
            "🌍 قیمتهای جهانی فولاد\n\n"
            
            f"🪨 سنگ آهن: ${format_float(world.get('iron_ore_base', 0))}\n\n"
            
            f"🔹 کنسانتره FOB: $

{format_float(world.get('concentrate_fob', 0))}\n"
            f"🔹 گندله FOB: ${format_float(world.get('pellet_fob', 0))}\n"
            f"🔹 آهن اسفنجی FOB: ${format_float(world.get('dri_fob', 0))}\n"
            f"🔹 بیلت FOB: ${format_float(world.get('billet_fob', 0))}\n"
            f"🔹 میلگرد FOB: ${format_float(world.get('rebar_fob', 0))}\n\n"
            
            f"🕒 آخرین بروزرسانی:\n"
            f"{world.get('last_update', 'نامشخص')}"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back")]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # 🏭 Factory Prices
    elif data == "factory":
        await query.edit_message_text(
            "🏭 انتخاب محصول:",
            reply_markup=factory_products_keyboard()

        )
    
    # 💵 Currency Rates
    elif data == "rate":
        rates = load_rates()
        
        text = (
            "💵 نرخ ارز\n\n"
            
            f"💲 دلار آزاد: "
            f"{format_number(rates.get('free', 0))} تومان\n\n"
            
            f"🏦 دلار نیمایی: "
            f"{format_number(rates.get('secondary', 0))} تومان\n\n"
            
            f"🕒 آخرین بروزرسانی:\n"
            f"{rates.get('last_update', 'نامشخص')}"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back")]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    
    # 📈 ICE Prices
    elif data == "ice":
        prices = load_prices()
        
        text = (
            "📈 قیمتهای بازار داخلی\n\n"
            
            f"🔹 کنسانتره: "
            f"{format_number(prices.get('concentrate', 0))}\n\n"
            
            f"🔹 گندله: "
            f"{format_number(prices.get('pellet', 0))}\n\n"
            
            f"🔹 آهن اسفنجی: "
            f"{format_number(prices.get('dri', 0))}\n\n"
            
            f"🔹 بیلت: "
            f"{format_number(prices.get('billet', 0))}\n\n"
            
            f"🔹 میلگرد: "
            f"{format_number(prices.get('rebar', 0))}\n\n"
            
            f"🕒 آخرین بروزرسانی:\n"
            f"{prices.get('last_update', 'نامشخص')}"
        )
        
        keyboard = [

            [InlineKeyboardButton("🔙 بازگشت", callback_data="back")]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # 🔙 Back
    elif data == "back":
        await query.edit_message_text(
            "🏠 منوی اصلی",
            reply_markup=main_keyboard()
        )

# ═══════════════════════════════════════════════════════════════════
# FACTORY PRODUCT HANDLER
# ═══════════════════════════════════════════════════════════════════

async def factory_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle factory product selection"""

    query = update.callback_query
    await query.answer()

    data = query.data

    mapping = {
        "fact_rebar": ("میلگرد", "rebar"),
        "fact_billet": ("بیلت", "billet"),
        "fact_dri": ("آهن اسفنجی", "dri"),
        "fact_pellet": ("گندله", "pellet"),
        "fact_concentrate": ("کنسانتره", "concentrate")
    }

    if data not in mapping:
        return

    title, key = mapping[data]

    factory_data = load_factory_prices()
    product_data = factory_data.get(key, {})

    text = f"🏭 قیمت کارخانه - {title}\n\n"

    if not product_data:
        text += "❌ دادهای موجود نیست"
    else:
        for province, factories in product_data.items():

            text += f"📍 {province}\n"

            for factory, price in factories.items():
                text += (
                    f"• {factory}: "
                    f"{format_number(price)} تومان\n"
                )

            text += "\n"

    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت", callback_data="factory")]
    ]

    await query.edit_message_text(
        text,

        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ═══════════════════════════════════════════════════════════════════
# MAIN FUNCTION
# ═══════════════════════════════════════════════════════════════════

def main():
    """Start the bot"""
    
    if not TOKEN:
        print("❌ خطا: TOKEN تنظیم نشده است")
        return
    
    # Start all background updaters
    start_all_updaters()
    
    # Create application
    app = Application.builder().token(TOKEN).build()
    
    # ✅ FIX: Use 'app' instead of 'application'
    
    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("admin", 

admin_panel))
    app.add_handler(CommandHandler("update_rates", update_rates_command))
    app.add_handler(CommandHandler("update_prices", update_prices_command))
    app.add_handler(CommandHandler("update_world", update_world_command))
    app.add_handler(CommandHandler("status", status_command))
    
    # Callback handlers - Main menu
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(world|rate|ice|back)$"))
    
    # Callback handlers - Factory menu
    app.add_handler(CallbackQueryHandler(factory_handler, pattern="^factory$"))
    app.add_handler(CallbackQueryHandler(factory_handler, pattern="^factory_"))
    
    # Start polling
    print("✅ ربات راهاندازی شد...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":

    main()
