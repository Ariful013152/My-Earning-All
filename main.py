import os
import random
import threading
import time
import pymongo
import telebot
from flask import Flask
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

# --- CONFIGURATION ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
MONGO_URI = os.environ.get("MONGO_URI", "YOUR_MONGO_URI_HERE")

REQUIRED_CHANNELS = ["@myearningall", "@earningdesh0"]

# Task / Ad Links
TASK_LINKS = [
    "https://poawooptugpoup.com/4/8991730",
    "https://poawooptugpoup.com/4/8991732",
    "https://poawooptugpoup.com/4/8991734",
    "https://poawooptugpoup.com/4/8991735",
    "https://poawooptugpoup.com/4/8991736",
    "https://poawooptugpoup.com/4/8991737",
    "https://poawooptugpoup.com/4/8991738",
    "https://poawooptugpoup.com/4/8991739",
    "https://poawooptugpoup.com/4/8991740",
    "https://poawooptugpoup.com/4/8991741",
]

# --- DATABASE SETUP ---
client = pymongo.MongoClient(MONGO_URI)
db = client["earning_bot_db"]
users_col = db["users"]

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# --- MEMORY TRACKING FOR RATE LIMITING & STATES ---
user_last_action = {}  # {user_id: timestamp}
user_states = {}       # {user_id: "waiting_for_bkash" / "waiting_for_nagad"}

# --- DATABASE HELPERS WITH SECURITY ---
def get_user(user_id, first_name="User"):
    user = users_col.find_one({"user_id": user_id})
    if not user:
        user = {
            "user_id": user_id, 
            "first_name": str(first_name)[:30], # Payload attack prevention
            "balance": 0.0, 
            "daily_count": 0,
            "last_reset": time.time(),
            "last_task_time": 0,
            "is_banned": False
        }
        users_col.insert_one(user)
    return user

def update_user_field(user_id, field_dict):
    users_col.update_one({"user_id": user_id}, {"$set": field_dict}, upsert=True)

def add_balance(user_id, amount):
    users_col.update_one({"user_id": user_id}, {"$inc": {"balance": amount}})

# --- SECURITY & VALIDATION FUNCTIONS ---
def rate_limit_check(user_id, cooldown_seconds=2):
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
        "⚠️ **বটটি ব্যবহার করতে আপনাকে নিচের সকল চ্যানেলে জয়েন করতে হবে:**",
        reply_markup=markup,
        parse_mode="Markdown"
    )

def is_valid_bd_number(number_str):
    number_str = str(number_str).strip()
    if len(number_str) == 11 and number_str.isdigit():
        if number_str.startswith(("017", "018", "019", "016", "015", "013", "014")):
            return True
    return False

# --- MAIN MENU KEYBOARD ---
def main_menu_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("💰 Balance", callback_data="menu_balance"),
        InlineKeyboardButton("🚀 Start Task", callback_data="menu_task"),
        InlineKeyboardButton("💳 Withdraw", callback_data="menu_withdraw"),
        InlineKeyboardButton("📊 Stats", callback_data="menu_stats")
    )
    return markup

# --- BOT COMMAND HANDLERS ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    
    user = get_user(user_id, first_name)
    if user.get("is_banned", False):
        bot.send_message(message.chat.id, "🚫 আপনার অ্যাকাউন্টটি অ্যাক্টিভিটি লঙ্ঘনের জন্য স্থায়ীভাবে ব্যান করা হয়েছে!")
        return

    if not check_user_channels(user_id):
        send_force_join_msg(message.chat.id)
    else:
        bot.send_message(
            message.chat.id,
            f"👋 **হ্যালো {first_name}!**\n\nআমাদের আনিং বটে আপনাকে স্বাগতম। কাজ শুরু করতে নিচের মেনু ব্যবহার করুন:",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )

# --- TEXT MESSAGE HANDLER FOR WITHDRAW NUMBER VALIDATION ---
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    text = message.text.strip() if message.text else ""

    user = get_user(user_id, message.from_user.first_name)
    if user.get("is_banned", False):
        return

    if not rate_limit_check(user_id, 2):
        return

    if user_id in user_states:
        state = user_states[user_id]
        
        # মোবাইল নম্বর ফিল্টারিং ও কড়া ভ্যালিডেশন
        if not is_valid_bd_number(text):
            bot.reply_to(
                message,
                "❌ **ভুল ইনপুট!**\n\nঅনুগ্যহ করে সঠিক ১১ ডিজিটের মোবাইল নম্বর লিখুন (যেমন: 01712345678)। অন্য কোনো লেখা বা সংকেত সিস্টেম গ্রহণ করবে না।",
                parse_mode="Markdown"
            )
            return

        method_name = "bKash" if state == "waiting_for_bkash" else "Nagad"
        del user_states[user_id]

        current_balance = user.get("balance", 0.0)
        if current_balance < 0.5:
            bot.send_message(message.chat.id, "❌ আপনার পর্যাপ্ত ব্যালেন্স নেই। মিনিমাম উইথড্র $0.50 USDT।")
            return

        # সেফ ব্যালেন্স কাটা
        update_user_field(user_id, {"balance": current_balance - 0.5})

        bot.send_message(
            message.chat.id,
            f"✅ **উইথড্র রিকোয়েস্ট সফল হয়েছে!**\n\n"
            f"💳 **মেথড:** {method_name}\n"
            f"📱 **নম্বর:** `{text}`\n"
            f"💵 **পরিমাণ:** $0.50 USDT\n\n"
            f"⏳ আগামী ২৪ ঘণ্টার মধ্যে অ্যাডমিন রিভিউ করে পেমেন্ট পাঠিয়ে দেবে।",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )
        return

    if not check_user_channels(user_id):
        send_force_join_msg(message.chat.id)
    else:
        bot.send_message(message.chat.id, "নিচের মেনু থেকে অপশন নির্বাচন করুন:", reply_markup=main_menu_keyboard())

# --- CALLBACK QUERY HANDLER ---
@bot.message_handler(func=lambda call: True)
def callback_inline(call):
    user_id = call.from_user.id
    first_name = call.from_user.first_name

    # স্প্যাম প্রটেকশন
    if not rate_limit_check(user_id, 2):
        bot.answer_callback_query(call.id, "⚠️ খুব দ্রুত চাপছেন! একটু ধীরে চেষ্টা করুন।", show_alert=False)
        return

    user = get_user(user_id, first_name)
    if user.get("is_banned", False):
        bot.answer_callback_query(call.id, "🚫 আপনার অ্যাকাউন্ট ব্যান করা রয়েছে!", show_alert=True)
        return

    if call.data == "check_join":
        if check_user_channels(user_id):
            bot.answer_callback_query(call.id, "✅ ধন্যবাদ! আপনি সব চ্যানেলে জয়েন আছেন।", show_alert=True)
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except Exception:
                pass
            bot.send_message(call.message.chat.id, "🎉 স্বাগতম! মেনু সিলেক্ট করুন:", reply_markup=main_menu_keyboard())
        else:
            bot.answer_callback_query(call.id, "❌ আপনি এখনো সব চ্যানেলে জয়েন করেননি!", show_alert=True)

    elif call.data == "menu_balance":
        balance = user.get("balance", 0.0)
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            f"👤 **ইউজার:** {first_name}\n💰 **বর্তমান ব্যালেন্স:** `${balance:.4f} USDT`",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )

    elif call.data == "menu_task":
        if not check_user_channels(user_id):
            send_force_join_msg(call.message.chat.id)
            return

        # টাস্ক শুরুর টাইম ডাটাবেজে স্টোর
        update_user_field(user_id, {"last_task_time": time.time()})

        random_url = random.choice(TASK_LINKS)
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("🌐 Visit Ad / Link", url=random_url),
            InlineKeyboardButton("✅ Claim Reward", callback_data="claim_reward")
        )
        
        bot.send_message(
            call.message.chat.id,
            "📌 **টাস্ক নিয়মাবলী:**\n1. নিচের লিংকে ক্লিক করে কমপক্ষে **১৫ সেকেন্ড** ওয়েবসাইট বা অ্যাডে অপেক্ষা করুন।\n2. ১৫ সেকেন্ড পর **Claim Reward** বাটনে ক্লিক করুন।",
            reply_markup=markup,
            parse_mode="Markdown"
        )

    elif call.data == "claim_reward":
        if not check_user_channels(user_id):
            bot.answer_callback_query(call.id, "⚠️ আগে চ্যানেলগুলোতে জয়েন করুন!", show_alert=True)
            send_force_join_msg(call.message.chat.id)
            return

        current_time = time.time()
        last_task_time = user.get("last_task_time", 0)

        # ⏱️ ১৫ সেকেন্ড বাধ্যবাধকতা চেক
        elapsed_time = current_time - last_task_time
        if elapsed_time < 15:
            remaining_sec = int(15 - elapsed_time)
            bot.answer_callback_query(
                call.id, 
                f"⚠️ খুব দ্রুত ক্লেইম করার চেষ্টা করছেন!\nঅনুগ্যহ করে অ্যাডে আরও {remaining_sec} সেকেন্ড অপেক্ষা করুন।", 
                show_alert=True
            )
            return

        daily_count = user.get("daily_count", 0)
        last_reset = user.get("last_reset", current_time)

        # ২৪ ঘণ্টা পর পর কাউন্টার ০ তে রিসেট
        if current_time - last_reset >= 86400:
            daily_count = 0
            last_reset = current_time
            update_user_field(user_id, {"daily_count": 0, "last_reset": current_time})

        # প্রতিদিন সর্বোচ্চ ৩০ বার দেখার সীমা
        if daily_count >= 30:
            remaining_hours = max(1, int((86400 - (current_time - last_reset)) / 3600))
            bot.answer_callback_query(
                call.id, 
                f"❌ আজকের দেখার সীমা (৩০/৩০) পূর্ণ হয়েছে!\nআবার {remaining_hours} ঘণ্টা পর চেষ্টা করুন।", 
                show_alert=True
            )
            return

        # ক্লেইম সাকসেসফুল হলে টাইম জিরো করা ও পয়েন্ট যোগ করা
        daily_count += 1
        update_user_field(user_id, {"daily_count": daily_count, "last_reset": last_reset, "last_task_time": 0})
        add_balance(user_id, 0.001)

        clicks_left = 30 - daily_count
        bot.answer_callback_query(call.id, f"🎉 $0.001 যোগ হয়েছে! আজকের বাকি: {clicks_left}টি", show_alert=True)

        updated_user = get_user(user_id)
        bot.send_message(
            call.message.chat.id,
            f"✅ **রিওয়ার্ড সফলভাবে যোগ হয়েছে!**\n"
            f"💰 **বর্তমান ব্যালেন্স:** `${updated_user.get('balance', 0.0):.4f} USDT`\n"
            f"📊 **আজকের লিমিট:** {daily_count}/৩০",
            parse_mode="Markdown"
        )

    elif call.data == "menu_withdraw":
        balance = user.get("balance", 0.0)
        if balance < 0.5:
            bot.answer_callback_query(call.id, f"❌ মিনিমাম উইথড্র $0.50 USDT! আপনার আছে ${balance:.4f}", show_alert=True)
            return

        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("বিকাশ (bKash)", callback_data="withdraw_bkash"),
            InlineKeyboardButton("নগদ (Nagad)", callback_data="withdraw_nagad")
        )
        bot.send_message(
            call.message.chat.id,
            f"💳 **পেমেন্ট মেথড সিলেক্ট করুন:**\n\nবর্তমান ব্যালেন্স: `${balance:.4f} USDT`\nমিনিমাম উইথড্র: `$0.50 USDT`",
            reply_markup=markup,
            parse_mode="Markdown"
        )

    elif call.data == "withdraw_bkash":
        user_states[user_id] = "waiting_for_bkash"
        bot.send_message(
            call.message.chat.id,
            "📝 **আপনার bKash নম্বর 01********* টি লিখে পাঠান:**",
            parse_mode="Markdown"
        )

    elif call.data == "withdraw_nagad":
        user_states[user_id] = "waiting_for_nagad"
        bot.send_message(
            call.message.chat.id,
            "📝 **আপনার Nagad নম্বর 01********* টি লিখে পাঠান:**",
            parse_mode="Markdown"
        )

    elif call.data == "menu_stats":
        total_users = users_col.count_documents({})
        bot.send_message(
            call.message.chat.id,
            f"📊 **বট স্ট্যাটাস্টিকস:**\n\n👥 মোট সক্রিয় ইউজার: `{total_users}` জন",
            parse_mode="Markdown"
        )

# --- AUTO FAKE WITHDRAW NOTIFICATION TO CHANNELS ---
def send_fake_withdraw_loop():
    while True:
        try:
            amount = round(random.uniform(0.50, 2.50), 2)
            digits = "".join([str(random.randint(0, 9)) for _ in range(6)])
            fake_num = f"017{digits}***"
            method = random.choice(["bKash", "Nagad"])

            msg = (
                f"🎉 **New Successful Withdrawal!**\n\n"
                f"👤 **User ID:** `{random.randint(10000000, 99999999)}`\n"
                f"💵 **Amount:** `${amount} USDT`\n"
                f"📱 **Method:** {method} (`{fake_num}`)\n"
                f"✅ **Status:** Paid\n\n"
                f"🤖 **Bot:** @myearningall"
            )

            for ch in REQUIRED_CHANNELS:
                try:
                    bot.send_message(ch, msg, parse_mode="Markdown")
                except Exception as e:
                    print(f"Error sending to {ch}: {e}")

            time.sleep(300) # প্রতি ৫ মিনিট পরপর
        except Exception as e:
            print(f"Fake withdraw error: {e}")
            time.sleep(60)

# --- FLASK WEB SERVER ---
@app.route('/')
def home():
    return "Fully secured Telegram Bot is running continuously!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# --- MAIN STARTUP ---
if __name__ == "__main__":
    t_flask = threading.Thread(target=run_flask)
    t_flask.daemon = True
    t_flask.start()

    t_fake = threading.Thread(target=send_fake_withdraw_loop)
    t_fake.daemon = True
    t_fake.start()

    print("Secure bot startup complete. Polling active...")
    bot.infinity_polling(skip_pending=True)
