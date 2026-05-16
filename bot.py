
import os
import json
import time
import threading
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# ═══════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════

TOKEN = os.environ.get("BOT_TOKEN")

METALPRICE_API_KEY = os.environ.get("METALPRICE_API_KEY")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))
SCRAPER_SECRET = os.environ.get("SCRAPER_SECRET", "change_this_secret")

RATE_FILE = "rates.json"
PRICE_FILE = "prices.json"
WORLD_PRICE_FILE = "world_prices.json"
METALS_FILE = "metals_prices.json"
FACTORY_PRICE_FILE = "factory_prices.json"

_file_lock = threading.Lock()

# ═══════════════════════════════════════════════════════════════════
# Default Data
# ═══════════════════════════════════════════════════════════════════

DEFAULT_FACTORY_DATA = {
    "rebar": {
        "اصفهان": {
            "ذوب آهن": {"price": 49000, "unit": "تومان"},
            "فولاد مبارکه": {"price": 48500, "unit": "تومان"}
        },

        "خوزستان": {
            "فولاد خوزستان": {"price": 49500, "unit": "تومان"}
        },
        "خراسان": {
            "فولاد خراسان": {"price": 50000, "unit": "تومان"}
        }
    },
    "billet": {
        "اصفهان": {
            "ذوب آهن": {"price": 44000, "unit": "تومان"},
            "فولاد مبارکه": {"price": 44500, "unit": "تومان"}
        },
        "خوزستان": {
            "فولاد خوزستان": {"price": 45000, "unit": "تومان"}
        },
        "خراسان": {
            "فولاد خراسان": {"price": 45500, "unit": "تومان"}
        }
    },
    "dri": {
        "اصفهان": {
            "ذوب آهن": {"price": 14200, "unit": "تومان"},
            "فولاد مبارکه": {"price": 14100, "unit": "تومان"}
        }
    },
    "pellet": {
        "کرمان": {
            "گلگهر": {"price": 6500000, "unit": "تومان"}
        }

    },
    "concentrate": {
        "کرمان": {
            "گلگهر": {"price": 4800000, "unit": "تومان"}
        }
    }
}

# ═══════════════════════════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════════════════════════

def to_persian(num):
    """تبدیل اعداد انگلیسی به فارسی"""
    return str(num).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))

def format_number(num):
    """فرمت عدد صحیح با جداکننده هزارگان"""
    if num is None:
        return "نامشخص"
    try:
        num = int(num)
        return to_persian(f"{num:,}".replace(",", "،"))
    except (ValueError, TypeError):

        return "نامشخص"

def format_float(num, decimals=2):
    """فرمت عدد اعشاری"""
    if num is None:
        return "نامشخص"
    try:
        num = float(num)
        return to_persian(f"{num:,.{decimals}f}".replace(",", "،"))
    except (ValueError, TypeError):
        return "نامشخص"

def save_json(filepath, data):
    """ذخیره داده در فایل JSON"""
    with _file_lock:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"خطا در ذخیره {filepath}: {e}")

def load_json(filepath, default=None):
    """بارگذاری داده از فایل JSON"""
    with _file_lock:
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:

                    return json.load(f)
            else:
                if default is not None:
                    save_json(filepath, default)
                    return default
                return {}
        except Exception as e:
            print(f"خطا در بارگذاری {filepath}: {e}")
            if default is not None:
                save_json(filepath, d
                return default
            return {}

def is_admin(update: Update) -> bool:
    return update.effective_user.id == ADMIN_ID

# ═══════════════════════════════════════════════════════════════════
# Load Functions
# ═══════════════════════════════════════════════════════════════════

def load_rates():
    return load_json(RATE_FILE, {"free": 183000, "secondary": 140000})

def load_prices():

    return load_json(PRICE_FILE, {
        "concentrate": 4800000,
        "pellet": 6500000,
        "dri": 14200,
        "billet": 42500,
        "rebar": 58000,
        "last_update": datetime.now().isoformat()
    })

def load_world_prices():
    return load_json(WORLD_PRICE_FILE, {
        "iron_ore_base": 104,
        "concentrate_fob": 31,
        "pellet_fob": 41,
        "dri_fob": 350,
        "billet_fob": 500,
        "rebar_fob": 550,
        "last_update": datetime.now().isoformat()
    })

def load_factory_prices():
    return load_json(FACTORY_PRICE_FILE, DEFAULT_FACTORY_DATA)

# ═══════════════════════════════════════════════════════════════════
# Keyboards
# 

# ═══════════════════════════════════════════════════════════════════

def main_keyboard():
    keyboard = [
        [InlineKeyboardButton("🌍 جهانی", callback_data='world')],
        [InlineKeyboardButton("🏭 کارخانه", callback_data='factory')],
        [InlineKeyboardButton("📊 بورس کالا", callback_data='ice')],
        [InlineKeyboardButton("💵 ارز", callback_data='rate')]
    ]
    return InlineKeyboardMarkup(keyboard)

def factory_products_keyboard():
    keyboard = [
        [InlineKeyboardButton("میلگرد", callback_data='fact_rebar')],
        [InlineKeyboardButton("بیلت", callback_data='fact_billet')],
        [InlineKeyboardButton("آهن اسفنجی", callback_data='fact_dri')],
        [InlineKeyboardButton("گندله", callback_data='fact_pellet')],
        [InlineKeyboardButton("کنسانتره", callback_data='fact_concentrate')],
        [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]

    ]
    return InlineKeyboardMarkup(keyboard)

# ═══════════════════════════════════════════════════════════════════
# Commands
# ═══════════════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏠 منوی اصلی",
        reply_markup=main_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "راهنمای ربات:\n\n"
        "🌍 قیمت‌های جهانی\n"
        "🏭 قیمت کارخانه\n"
        "📊 بورس کالا\n"
        "💵 نرخ ارز\n\n"
        "برای شروع /start را بزنید."
    )
    await update.message.reply_text(text)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔️ شما دسترسی ادمین ندارید.")
        return

    rates = load_rates()
    prices = load_prices()
    world = load_world_prices()

    text = (
        "📊 وضعیت سیستم:\n\n"
        f"💲 دلار آزاد: {format_number(rates.get('free'))} تومان\n"
        f"🏭 میلگرد داخلی: {format_number(prices.get('rebar'))} تومان\n"
        f"🌍 سنگ آهن جهانی: ${format_float(world.get('iron_ore_base'))}\n"
        f"🕒 آخرین بروزرسانی: {world.get('last_update','-')}"
    )

    await update.message.reply_text(text)

# ═══════════════════════════════════════════════════════════════════
# Callback Handlers

# ═══════════════════════════════════════════════════════════════════

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "world":
        world = load_world_prices()
        text = (
            "🌍 قیمت‌های جهانی:\n\n"
            f"🔹 سنگ آهن: ${format_float(world.get('iron_ore_base'))}\n"
            f"🔹 کنسانتره FOB: ${format_float(world.get('concentrate_fob'))}\n"
            f"🔹 گندله FOB: ${format_float(world.get('pellet_fob'))}\n"
            f"🔹 آهن اسفنجی FOB: ${format_float(world.get('dri_fob'))}\n"
            f"🔹 بیلت FOB: ${format_float(world.get('billet_fob'))}\n"
            f"🔹 میلگرد FOB: ${format_float(world.get('rebar_fob'))}\n\n"
            f"🕒 آخرین بروزرسانی: {world.get('last_update','-')}"
        )
        await query.edit_message_text(text, 

reply_markup=main_keyboard())

    elif data == "rate":
        rates = load_rates()
        text = (
            "💵 نرخ ارز:\n\n"
            f"💲 دلار آزاد: {format_number(rates.get('free'))} تومان\n"
            f"🏦 دلار نیمایی: {format_number(rates.get('secondary'))} تومان"
        )
        await query.edit_message_text(text, reply_markup=main_keyboard())

    elif data == "ice":
        prices = load_prices()
        text = (
            "📊 قیمت داخلی:\n\n"
            f"🔹 کنسانتره: {format_number(prices.get('concentrate'))} تومان\n"
            f"🔹 گندله: {format_number(prices.get('pellet'))} تومان\n"
            f"🔹 آهن اسفنجی: {format_number(prices.get('dri'))} تومان\n"
            f"🔹 بیلت: {format_number(prices.get('billet'))} تومان\n"
            f"🔹 میلگرد: {format_number(prices.get('rebar'))} تومان\n\n"
            f"🕒 بروزرسانی: {prices.get('last_update','-')}"

        )
        await query.edit_message_text(text, reply_markup=main_keyboard())

    elif data == "factory":
        await query.edit_message_text(
            "🏭 انتخاب محصول:",
            reply_markup=factory_products_keyboard()
        )

    elif data == "back":
        await query.edit_message_text(
            "🏠 منوی اصلی",
            reply_markup=main_keyboard()
        )

# ═══════════════════════════════════════════════════════════════════
# Factory Handler
# ═══════════════════════════════════════════════════════════════════

async def factory_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    mapping = {
        "fact_rebar": ("میلگرد", "rebar"),
        "fact_billet": ("بیلت", "billet"),
        "fact_dri": ("آهن اسفنجی", "dri"),
        "fact_pellet": ("گندله", "pellet"),
        "fact_concentrate": ("کنسانتره", "concentrate"),
    }

    title, key = mapping.get(query.data, (None, None))
    if not key:
        return

    data = load_factory_prices().get(key, {})
    text = f"🏭 قیمت کارخانه - {title}\n\n"

    if not data:
        text += "❌ داده‌ای موجود نیست"
    else:
        for province, factories in data.items():
            text += f"📍 {province}\n"
            for factory, info in factories.items():
                text += f"  - {factory}: {format_number(info['price'])} {info['unit']}\n"
            text += "\n"

    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت", callback_data="factory")]
    ]


    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

def main():
    if not TOKEN:
        print("❌ خطا: TOKEN تنظیم نشده است")
        return

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))

    app.add_handler(CallbackQueryHandler(button_handler,

                                         pattern="^(world|rate|ice|factory|back)$"))
    app.add_handler(CallbackQueryHandler(factory_handler,
                                         pattern="^fact_"))

    print("✅ ربات با موفقیت راه‌اندازی شد.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
