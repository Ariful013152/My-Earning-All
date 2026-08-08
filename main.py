import os
import random
import threading
import time
import pymongo
import telebot
from flask import Flask
from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

# --- CONFIGURATION ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
MONGO_URI = os.environ.get("MONGO_URI", "YOUR_MONGO_URI_HERE")

BOT_USERNAME = "myearningall01_bot"
REQUIRED_CHANNELS = ["@myearningall", "@allinoneg1"]
NOTIFICATION_CHANNEL = "@myearningall"

MIN_WITHDRAW = 2.0
REFERRAL_BONUS = 0.005

ADMIN_IDS = [8414665404, 5034445579]

# --- DATABASE SETUP ---
client = pymongo.MongoClient(MONGO_URI)
db = client["telegram_bot"]
users_col = db["users"]

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

user_last_action = {}
user_withdraw_step = {}

# --- DATABASE HELPERS ---
def get_user(user_id, first_name="User", referred_by=None):
    user = users_col.find_one({"user_id": user_id})
    if not user:
        user = {
            "user_id": user_id, 
            "first_name": str(first_name)[:30],
            "balance": 0.0, 
            "daily_count": 0,
            "last_reset": time.time(),
            "last_task_time": 0,
            "referred_by": referred_by,
            "referrals_count": 0,
            "ref_reward_given": False,
            "is_banned": False
        }
        users_col.insert_one(user)
    return user.get("balance", 0.0), user

def update_user_field(user_id, field_dict):
    users_col.update_one({"user_id": user_id}, {"$set": field_dict}, upsert=True)

def add_balance(user_id, amount):
    users_col.update_one({"user_id": user_id}, {"$inc": {"balance": amount}})

def rate_limit_check(user_id, cooldown_seconds=1):
    current = time.time()
    last = user_last_action.get(user_id, 0)
    if current - last < cooldown_seconds:
        return False
    user_last_action[user_id] = current
    return True

def check_user_channels(user_id):
    for channel in REQUIRED_CHANNELS:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status in ['left', 'kicked']:
                return False
        except Exception:
            return False
    return True

def send_force_join_msg(chat_id):
    markup = InlineKeyboardMarkup(row_width=1)
    for channel in REQUIRED_CHANNELS:
        markup.add(InlineKeyboardButton(f"🔗 Join {channel}", url=f"https://t.me/{channel.replace('@', '')}"))
    markup.add(InlineKeyboardButton("✅ Checked / Verified", callback_data="check_join"))
    
    bot.send_message(
        chat_id,
        "⚠️ **বটটি ব্যবহার করতে আপনাকে নিচের সকল চ্যানেলগুলোতে জয়েন করতে হবে:**",
        reply_markup=markup,
        parse_mode="Markdown"
    )

def is_valid_bd_number(number_str):
    number_str = str(number_str).strip()
    if len(number_str) == 11 and number_str.isdigit():
        if number_str.startswith(("017", "018", "019", "016", "015", "013", "014")):
            return True
    return False

def main_menu_keyboard():
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        KeyboardButton("📺 Task"),
        KeyboardButton("🖥 Account"),
        KeyboardButton("✨ Referral"),
        KeyboardButton("💸 Withdraw"),
        KeyboardButton("🛑 Rule's"),
        KeyboardButton("🔰 Whatsapp"),
        KeyboardButton("📩 Support"),
        KeyboardButton("📊 Status")
    )
    return markup

# --- COMMAND HANDLERS ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    
    args = message.text.split()
    referred_by = None
    if len(args) > 1 and args[1].isdigit():
        ref_id = int(args[1])
        if ref_id != user_id:
            referred_by = ref_id

    _, user = get_user(user_id, first_name, referred_by=referred_by)
    if user.get("is_banned", False):
        bot.send_message(message.chat.id, "🚫 আপনার অ্যাকাউন্টটি ব্যান করা হয়েছে!")
        return

    if not check_user_channels(user_id):
        send_force_join_msg(message.chat.id)
    else:
        bot.send_message(
            message.chat.id,
            f"👋 **স্বাগতম, 👤 {first_name}!**\n\nনিচের অপশনগুলো ব্যবহার করে কাজ শুরু করুন:",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )

# --- MESSAGE HANDLER ---
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    text = message.text.strip() if message.text else ""
    first_name = message.from_user.first_name

    balance, user = get_user(user_id, first_name)
    if user.get("is_banned", False):
        return

    if not rate_limit_check(user_id, 1):
        return

    # Withdraw Process Handling
    if user_id in user_withdraw_step:
        method = user_withdraw_step[user_id].get('method', 'bKash')
        del user_withdraw_step[user_id]

        if not is_valid_bd_number(text):
            bot.reply_to(
                message,
                "❌ **ভুল ইনপুট!**\n\nঅনুরোধ করে সঠিক ১১ ডিজিটের নম্বর প্রদান করুন।",
                parse_mode="Markdown"
            )
            return

        if balance < MIN_WITHDRAW:
            bot.send_message(message.chat.id, f"❌ আপনার পর্যাপ্ত ব্যালেন্স নেই। মিনিমাম উইথড্র ${MIN_WITHDRAW:.2f} USDT।")
            return

        withdraw_amount = balance
        update_user_field(user_id, {"balance": 0.0})

        msg = (
            f"📥 **WITHDRAW REQUEST SUBMITTED**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Name:** `{first_name}`\n"
            f"🆔 **User ID:** `{user_id}`\n"
            f"💰 **Amount:** `${withdraw_amount:.4f} USDT`\n"
            f"⚡ **Method:** {method}\n"
            f"📱 **Account:** `{text}`\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"✅ **আপনার উইথড্র রিকোয়েস্ট জমা হয়েছে।**"
        )

        bot.send_message(message.chat.id, msg, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
        return

    if not check_user_channels(user_id):
        send_force_join_msg(message.chat.id)
        return

    # Menu Buttons
    if text == "🖥 Account":
        bot.send_message(
            message.chat.id,
            f"👤 **ইউজার:** {first_name}\n🆔 **আইডি:** `{user_id}`\n💰 **বর্তমান ব্যালেন্স:** `${balance:.4f} USDT`",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )

    elif text == "✨ Referral":
        ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
        ref_count = user.get("referrals_count", 0)
        bot.send_message(
            message.chat.id,
            f"👥 **আপনার রেফারেল লিংক**\n\n🔗 `{ref_link}`\n\n📊 **মোট রেফারেল:** `{ref_count}` জন",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )

    elif text == "💸 Withdraw":
        if balance < MIN_WITHDRAW:
            msg = (
                f"💳 **আপনার বর্তমান ব্যালেন্স:** `${balance:.4f} USDT`\n"
                f"📌 **সর্বনিম্ন উইথড্র:** `${MIN_WITHDRAW:.2f} USDT`\n\n"
                f"⚠️ **ব্যালেন্স অপর্যাপ্ত।**"
            )
            bot.send_message(message.chat.id, msg, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
        else:
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                InlineKeyboardButton("বিকাশ (bKash)", callback_data="with_bKash"),
                InlineKeyboardButton("নগদ (Nagad)", callback_data="with_Nagad")
            )
            bot.send_message(
                message.chat.id,
                f"💳 **পেমেন্ট মেথড সিলেক্ট করুন:**\n\nবর্তমান ব্যালেন্স: `${balance:.4f} USDT`",
                reply_markup=markup,
                parse_mode="Markdown"
            )

    elif text == "📊 Status":
        total_users = users_col.count_documents({})
        bot.send_message(
            message.chat.id,
            f"📊 **বট স্ট্যাটাস্টিকস:**\n\n👥 মোট ইউজার: `{total_users}` জন",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )

    else:
        bot.send_message(message.chat.id, "নিচের বাটনগুলো ব্যবহার করে অপশন সিলেক্ট করুন:", reply_markup=main_menu_keyboard())

# --- CALLBACK QUERY HANDLER ---
@bot.message_handler(func=lambda call: True)
def callback_inline(call):
    user_id = call.from_user.id
    first_name = call.from_user.first_name

    balance, user = get_user(user_id, first_name)

    if call.data == "check_join":
        if check_user_channels(user_id):
            bot.answer_callback_query(call.id, "✅ ধন্যবাদ! জয়েন নিশ্চিত হয়েছে।", show_alert=True)
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except Exception:
                pass
            bot.send_message(call.message.chat.id, "🎉 স্বাগতম!", reply_markup=main_menu_keyboard())
        else:
            bot.answer_callback_query(call.id, "❌ আপনি এখনো সব চ্যানেলে জয়েন করেননি!", show_alert=True)

    elif call.data.startswith("with_"):
        method = call.data.split("_")[1]
        user_withdraw_step[user_id] = {'method': method}
        bot.send_message(
            call.message.chat.id,
            f"📝 আপনার {method} নম্বর লিখে মেসেজ পাঠান:"
        )

# --- 4-MINUTE AUTOMATED CHANNEL SCHEDULER ---
def start_channel_updates():
    def loop():
        while True:
            try:
                # প্রতি ২৪০ সেকেন্ড (৪ মিনিট) পর পর চ্যানেলে নির্ধারিত আপডেট মেসেজ যাবে
                bot.send_message(
                    NOTIFICATION_CHANNEL, 
                    "📢 **System Update**: Service status is active.", 
                    parse_mode="Markdown"
                )
                time.sleep(240)
            except Exception as e:
                print(f"Channel update error: {e}")
                time.sleep(60)

    t = threading.Thread(target=loop)
    t.daemon = True
    t.start()

# --- FLASK WEB SERVER (FOR RENDER KEEP ALIVE) ---
def keep_alive():
    @app.route('/')
    def home():
        return "Bot service is running!"

    def run():
        port = int(os.environ.get("PORT", 10000))
        app.run(host="0.0.0.0", port=port)

    t = threading.Thread(target=run)
    t.daemon = True
    t.start()

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    keep_alive()
    start_channel_updates()
    print("Bot started successfully...")
    bot.infinity_polling(skip_pending=True)
