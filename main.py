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
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8615856288:AAHsdARNnr1J4IEK_RodW0_xiLqnftct1C8")
MONGO_URI = os.environ.get("MONGO_URI", "YOUR_MONGO_URI_HERE")

BOT_USERNAME = "myearningall01_bot"
REQUIRED_CHANNELS = ["@myearningall", "@allinoneg1"]  # জয়েন করার জন্য বাধ্যতামূলক চ্যানেল
PROOF_CHANNEL = "@myearningall"  # অটো পোস্ট প্রুফ চ্যানেল

MIN_WITHDRAW = 2.0  # মিনিমাম উইথড্র $2.00 USDT
REFERRAL_BONUS = 0.005  # রেফার কমিশন $0.005 USDT

# --- ADMIN IDS ---
ADMIN_IDS = [8414665404, 5034445579]

# --- MONETAG & ADSTERRA LINKS ---
MONETAG_LINKS = [
    'https://omg10.com/4/11522087',
    'https://omg10.com/4/11522086',
    'https://omg10.com/4/11522081',
    'https://omg10.com/4/11522080',
    'https://omg10.com/4/11522079',
    'https://omg10.com/4/11522078',
    'https://omg10.com/4/11522077',
    'https://omg10.com/4/11522076',
    'https://omg10.com/4/11522074',
    'https://omg10.com/4/11516146'
]

ADSTERRA_LINKS = [
    'https://www.effectivecpmnetwork.com/nx2nqegj3p?key=8fb4f6d68a89919faeee5ec3846d4292',
    'https://www.effectivecpmnetwork.com/bbjq6k48?key=4707c2aa3827755848d5332b72a9c955',
    'https://www.effectivecpmnetwork.com/hqrjr5jzm?key=fe9a5012689a62a78d579d93d0864575',
    'https://www.effectivecpmnetwork.com/nqch6m5jc?key=3eecd9428d8b55066d6cfdcadeda271c',
    'https://www.effectivecpmnetwork.com/ie1pgkmbcc?key=1298a27dc3477c9aef05ead4c6778088',
    'https://www.effectivecpmnetwork.com/wg9r001v7?key=4f2213d1fb414c2e0c9ac7dde1c72402',
    'https://www.effectivecpmnetwork.com/m36r7xvy?key=e8b267b7b19cae2daee8f96118e5326e',
    'https://www.effectivecpmnetwork.com/jwsp4r2rtr?key=63a26410a1f920c6de29b0e73bf69055',
    'https://www.effectivecpmnetwork.com/dwja24niv?key=6a9552e41b528897598e4eec709d5115',
    'https://www.effectivecpmnetwork.com/aqap5tdu?key=292364b4c9161a24064eaf503e245724'
]

ALL_TASK_LINKS = MONETAG_LINKS + ADSTERRA_LINKS

# --- DATABASE SETUP ---
client = pymongo.MongoClient(MONGO_URI)
db = client["earning_bot_db"]
users_col = db["users"]

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# --- MEMORY TRACKING ---
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

# --- HELPER FUNCTIONS ---
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

# --- MAIN MENU KEYBOARD ---
def main_menu_keyboard():
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        KeyboardButton("📺 Watch Ad"),
        KeyboardButton("🖥 Account"),
        KeyboardButton("✨ Referral"),
        KeyboardButton("💸 Withdraw"),
        KeyboardButton("🛑 Rule's"),
        KeyboardButton("🔰 Whatsapp"),
        KeyboardButton("📩 Support"),
        KeyboardButton("📊 Status")
    )
    return markup

# --- ADMIN COMMAND HANDLERS ---
@bot.message_handler(commands=['ban'])
def ban_user_cmd(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        bot.reply_to(message, "❌ ব্যবহার: `/ban USER_ID`", parse_mode="Markdown")
        return
    
    target_id = int(args[1])
    update_user_field(target_id, {"is_banned": True})
    bot.reply_to(message, f"✅ ইউজার `{target_id}` সফলভাবে ব্যান করা হয়েছে।", parse_mode="Markdown")

@bot.message_handler(commands=['unban'])
def unban_user_cmd(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        bot.reply_to(message, "❌ ব্যবহার: `/unban USER_ID`", parse_mode="Markdown")
        return
    
    target_id = int(args[1])
    update_user_field(target_id, {"is_banned": False})
    bot.reply_to(message, f"✅ ইউজার `{target_id}` সফলভাবে আনব্যান করা হয়েছে।", parse_mode="Markdown")

@bot.message_handler(commands=['addbalance'])
def add_balance_cmd(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    args = message.text.split()
    if len(args) < 3 or not args[1].isdigit():
        bot.reply_to(message, "❌ ব্যবহার: `/addbalance USER_ID AMOUNT`", parse_mode="Markdown")
        return
    
    target_id = int(args[1])
    try:
        amount = float(args[2])
    except ValueError:
        bot.reply_to(message, "❌ সঠিক অ্যামাউন্ট লিখুন।")
        return

    add_balance(target_id, amount)
    bot.reply_to(message, f"✅ ইউজার `{target_id}`-এর অ্যাকাউন্টে `${amount}` যোগ করা হয়েছে।", parse_mode="Markdown")

@bot.message_handler(commands=['cutbalance'])
def cut_balance_cmd(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    args = message.text.split()
    if len(args) < 3 or not args[1].isdigit():
        bot.reply_to(message, "❌ ব্যবহার: `/cutbalance USER_ID AMOUNT`", parse_mode="Markdown")
        return
    
    target_id = int(args[1])
    try:
        amount = float(args[2])
    except ValueError:
        bot.reply_to(message, "❌ সঠিক অ্যামাউন্ট লিখুন।")
        return

    add_balance(target_id, -amount)
    bot.reply_to(message, f"✅ ইউজার `{target_id}`-এর অ্যাকাউন্ট থেকে `${amount}` কাটা হয়েছে।", parse_mode="Markdown")

# --- USER COMMAND HANDLERS ---
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
            f"👋 **স্বাগতম, 👤 {first_name}!**\n\nআমাদের বটে কাজ করে আপনি সহজেই ইনকাম করতে পারবেন। নিচের বাটনগুলো ব্যবহার করে কাজ শুরু করুন:",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )

# --- TEXT MESSAGE HANDLER ---
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

    # 1. Withdraw Process Number Entry
    if user_id in user_withdraw_step:
        method = user_withdraw_step[user_id].get('method', 'bKash')
        del user_withdraw_step[user_id]

        if not is_valid_bd_number(text):
            bot.reply_to(
                message,
                "❌ **ভুল ইনপুট!**\n\nঅনুরোধ করে সঠিক ১১ ডিজিটের মোবাইল নম্বর লিখুন (যেমন: 01712345678)।",
                parse_mode="Markdown"
            )
            return

        if balance < MIN_WITHDRAW:
            bot.send_message(message.chat.id, f"❌ আপনার পর্যাপ্ত ব্যালেন্স নেই। মিনিমাম উইথড্র ${MIN_WITHDRAW:.2f} USDT।")
            return

        withdraw_amount = balance
        update_user_field(user_id, {"balance": 0.0})

        msg = (
            f"📥 **REAL WITHDRAW REQUEST!**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Name:** 👤 `{first_name}`\n"
            f"🆔 **User ID:** `{user_id}`\n"
            f"💰 **Amount:** `${withdraw_amount:.4f} USDT`\n"
            f"⚡ **Method:** {method}\n"
            f"📱 **Account:** `{text}`\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"✅ **আপনার উইথড্র রিকোয়েস্ট জমা হয়েছে!**\n\n"
            f"💳 **পরিমাণ:** `${withdraw_amount:.4f} USDT`\n"
            f"🔷 **মেথড:** {method}\n"
            f"📱 **ডিটেইলস:** `{text}`\n\n"
            f"পেমেন্ট প্রুফ চ্যানেলে চেক করুন। ধন্যবাদ!"
        )

        bot.send_message(message.chat.id, msg, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
        return

    # Check required channels
    if not check_user_channels(user_id):
        send_force_join_msg(message.chat.id)
        return

    # 2. Reply Keyboard Routing
    if text == "📺 Watch Ad":
        update_user_field(user_id, {"last_task_time": time.time()})
        random_url = random.choice(ALL_TASK_LINKS)
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("🌐 Visit Ad / Link", url=random_url),
            InlineKeyboardButton("✅ Claim Reward", callback_data="claim_reward")
        )
        bot.send_message(
            message.chat.id,
            "📌 **টাস্ক নিয়মাবলী:**\n1. নিচের লিংকে ক্লিক করে কমপক্ষে **১৫ সেকেন্ড** অপেক্ষা করুন।\n2. ১৫ সেকেন্ড পর **Claim Reward** বাটনে চাপ দিন।",
            reply_markup=markup,
            parse_mode="Markdown"
        )

    elif text == "🖥 Account":
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
            f"👥 **আপনার রেফারেল লিংক**\n\n"
            f"🔗 `{ref_link}`\n\n"
            f"📊 **মোট সফল রেফারেল:** `{ref_count}` জন\n"
            f"🎁 **রেফার কমিশন:** `${REFERRAL_BONUS:.3f} USDT`",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )

    elif text == "💸 Withdraw":
        if balance < MIN_WITHDRAW:
            msg = (
                f"💸 **উইথড্র ইনফরমেশন**\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"💳 **আপনার বর্তমান ব্যালেন্স:** `${balance:.4f} USDT`\n"
                f"📌 **সর্বনিম্ন উইথড্র:** `${MIN_WITHDRAW:.2f} USDT`\n\n"
                f"⚠️ **আপনার অ্যাকাউন্টে পর্যাপ্ত ব্যালেন্স নেই।**"
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
                f"💳 **পেমেন্ট মেথড সিলেক্ট করুন:**\n\nবর্তমান ব্যালেন্স: `${balance:.4f} USDT`\nমিনিমাম উইথড্র: `${MIN_WITHDRAW:.2f} USDT`",
                reply_markup=markup,
                parse_mode="Markdown"
            )

    elif text == "🛑 Rule's":
        rules = (
            "📌 **বট নিয়মাবলী:**\n\n"
            "১. প্রতিদিন সর্বোচ্চ ৩০টি অ্যাড দেখতে পারবেন।\n"
            "২. অ্যাড লিংকে অন্তত ১৫ সেকেন্ড অপেক্ষা করতে হবে।\n"
            "৩. ফেক রেফারেল করলে অ্যাকাউন্ট ব্যান করা হবে।\n"
            "৪. সর্বনিম্ন উইথড্র $২.০০ USDT।"
        )
        bot.send_message(message.chat.id, rules, reply_markup=main_menu_keyboard(), parse_mode="Markdown")

    elif text == "🔰 Whatsapp":
        msg = (
            "🌐 **ALL IN ONE** 🌐\n\n"
            "✅ **Whatsapp এডমিন লিংক:**\n"
            "https://wa.me/qr/TLGSBEYHL74LD1"
        )
        bot.send_message(message.chat.id, msg, reply_markup=main_menu_keyboard(), disable_web_page_preview=True)

    elif text == "📩 Support":
        msg = (
            "🌐 **ALL IN ONE** 🌐\n\n"
            "🖇️ **আমাদের সাপোর্ট গ্রুপ লিংক:** https://t.me/allinoneg1\n\n"
            "✅ **টেলেগ্রাম এডমিন লিংক:** @akadmin02\n\n"
            "✅ **Whatsapp এডমিন লিংক:**\nhttps://wa.me/qr/TLGSBEYHL74LD1"
        )
        bot.send_message(message.chat.id, msg, reply_markup=main_menu_keyboard(), disable_web_page_preview=True)

    elif text == "📊 Status":
        total_users = users_col.count_documents({})
        bot.send_message(
            message.chat.id,
            f"📊 **বট স্ট্যাটাস্টিকস:**\n\n👥 মোট সক্রিয় ইউজার: `{total_users}` জন",
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
            bot.answer_callback_query(call.id, "✅ ধন্যবাদ! আপনি সব চ্যানেলে জয়েন আছেন।", show_alert=True)
            
            if user.get("referred_by") and not user.get("ref_reward_given", False):
                referrer_id = user.get("referred_by")
                referrer = users_col.find_one({"user_id": referrer_id})
                if referrer and not referrer.get("is_banned", False):
                    add_balance(referrer_id, REFERRAL_BONUS)
                    users_col.update_one({"user_id": referrer_id}, {"$inc": {"referrals_count": 1}})
                    update_user_field(user_id, {"ref_reward_given": True})

            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except Exception:
                pass
            bot.send_message(call.message.chat.id, "🎉 স্বাগতম! কাজ শুরু করতে নিচের বাটন ব্যবহার করুন:", reply_markup=main_menu_keyboard())
        else:
            bot.answer_callback_query(call.id, "❌ আপনি এখনো সব চ্যানেলে জয়েন করেননি!", show_alert=True)

    elif call.data == "claim_reward":
        if not check_user_channels(user_id):
            bot.answer_callback_query(call.id, "⚠️ আগে চ্যানেলগুলোতে জয়েন করুন!", show_alert=True)
            send_force_join_msg(call.message.chat.id)
            return

        current_time = time.time()
        last_task_time = user.get("last_task_time", 0)
        elapsed_time = current_time - last_task_time

        if elapsed_time < 15:
            remaining = int(15 - elapsed_time)
            bot.answer_callback_query(call.id, f"⚠️ অন্তত ১৫ সেকেন্ড থাকুন (আর {remaining} সেকেন্ড বাকি)।", show_alert=True)
        else:
            daily_count = user.get("daily_count", 0)
            last_reset = user.get("last_reset", current_time)

            if current_time - last_reset >= 86400:
                daily_count = 0
                last_reset = current_time

            if daily_count >= 30:
                bot.answer_callback_query(call.id, "❌ আজকের কাজের সীমা (৩০/৩০) পূর্ণ হয়েছে!", show_alert=True)
                return

            add_balance(user_id, 0.001)
            update_user_field(user_id, {"daily_count": daily_count + 1, "last_reset": last_reset, "last_task_time": 0})

            bot.answer_callback_query(call.id, "🎉 $0.001 আপনার অ্যাকাউন্টে যোগ করা হয়েছে।", show_alert=True)

            updated_balance, _ = get_user(user_id, first_name)
            bot.send_message(
                call.message.chat.id,
                f"✅ রিওয়ার্ড সফলভাবে যোগ হয়েছে!\nবর্তমান ব্যালেন্স: ${updated_balance:.4f} USDT",
                reply_markup=main_menu_keyboard(),
                parse_mode="Markdown"
            )

    elif call.data.startswith("with_"):
        method = call.data.split("_")[1]
        user_withdraw_step[user_id] = {'method': method}
        bot.send_message(
            call.message.chat.id,
            f"📝 আপনার {method} নম্বর বা এড্রেসটি লিখে মেসেজ পাঠান:"
        )

# --- AUTO POST TO ONLY ONE CHANNEL (@myearningall) ---
def start_auto_post():
    def loop():
        while True:
            try:
                amount = round(random.uniform(2.00, 5.50), 2)
                digits = "".join([str(random.randint(0, 9)) for _ in range(6)])
                fake_num = f"017{digits}***"
                method = random.choice(["bKash", "Nagad"])

                msg = (
                    f"🎉 **New Successful Withdrawal!**\n\n"
                    f"👤 **User ID:** `{random.randint(10000000, 99999999)}`\n"
                    f"💵 **Amount:** `${amount:.2f} USDT`\n"
                    f"📱 **Method:** {method} (`{fake_num}`)\n"
                    f"✅ **Status:** Paid\n\n"
                    f"🤖 **Bot:** @{BOT_USERNAME}"
                )

                try:
                    bot.send_message(PROOF_CHANNEL, msg, parse_mode="Markdown")
                except Exception as e:
                    print(f"Error sending to {PROOF_CHANNEL}: {e}")

                time.sleep(300)
            except Exception as e:
                print(f"Auto post error: {e}")
                time.sleep(60)

    t = threading.Thread(target=loop)
    t.daemon = True
    t.start()

# --- FLASK WEB SERVER ---
def keep_alive():
    @app.route('/')
    def home():
        return "Bot is running continuously!"

    def run():
        port = int(os.environ.get("PORT", 10000))
        app.run(host="0.0.0.0", port=port)

    t = threading.Thread(target=run)
    t.daemon = True
    t.start()

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    keep_alive()
    start_auto_post()
    print("Bot is running...")
    bot.infinity_polling(skip_pending=True)
