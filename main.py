import os
import time
import random
from flask import Flask
from threading import Thread
from telebot import TeleBot, types
from pymongo import MongoClient

# Render Port Binding & Server keep-alive setup
app = Flask('')

@app.route('/')
def home():
    return "Bot is running perfectly!"

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- CONFIGURATION ---
TOKEN = '8615856288:AAGaV1qttSwXx_RogiQxPh43VLZEdo2OsUE' 
WHATSAPP_LINK = 'https://wa.me/qr/TLGSBEYHL74LD1'
SUPPORT_GROUP = 'https://t.me/allinoneg1'
ADMIN_USERNAME = '@akadmin02'
ADMIN_ID = 8615856288 

# পাবলিক চ্যানেল ইউজারনেম (বটকে চ্যানেলে Admin বানিয়ে রাখবেন)
PAYMENT_CHANNEL = '@myearningall' 
REQUIRED_CHANNELS = ['@allinoneg1', '@myearningall']

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

user_last_click = {}
user_withdraw_step = {}
bot = TeleBot(TOKEN)

# --- MONGODB CONNECTION ---
MONGO_URI = os.environ.get('MONGO_URI')
client = MongoClient(MONGO_URI)
db = client['telegram_bot']
users_col = db['users']

# --- FORCE JOIN CHECKER ---
def check_user_channels(user_id):
    for ch in REQUIRED_CHANNELS:
        try:
            member = bot.get_chat_member(ch, user_id)
            if member.status in ['left', 'kicked']:
                return False
        except Exception as e:
            print(f"Channel Check Error ({ch}):", e)
            return False
    return True

def send_force_join_msg(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn1 = types.InlineKeyboardButton("📢 Channel 1 Join", url="https://t.me/allinoneg1")
    btn2 = types.InlineKeyboardButton("📢 Channel 2 Join", url="https://t.me/myearningall")
    btn_check = types.InlineKeyboardButton("✅ Joined / Verified", callback_data="check_channels")
    markup.add(btn1, btn2, btn_check)

    text = (
        "🛑 **আমাদের বটের সার্ভিস ব্যবহার করতে হলে নিচের ২টি চ্যানেলে জয়েন থাকা বাধ্যতামুলক:**\n\n"
        "১. https://t.me/allinoneg1\n"
        "২. https://t.me/myearningall\n\n"
        "জয়েন করার পর নিচে **'✅ Joined / Verified'** বাটনে ক্লিক করুন।"
    )
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

# --- DATABASE FUNCTIONS ---
def is_user_banned(user_id):
    user = users_col.find_one({'user_id': user_id})
    return True if user and user.get('is_banned', 0) == 1 else False

def get_user(user_id, first_name):
    user = users_col.find_one({'user_id': user_id})
    if not user:
        new_user = {
            'user_id': user_id,
            'first_name': first_name,
            'balance': 0.0,
            'referred_by': 0,
            'referrals_count': 0,
            'is_banned': 0
        }
        users_col.insert_one(new_user)
        return 0.0, 0
    return user.get('balance', 0.0), user.get('referrals_count', 0)

def add_balance(user_id, amount):
    users_col.update_one({'user_id': user_id}, {'$inc': {'balance': amount}})

def deduct_balance(user_id, amount):
    users_col.update_one({'user_id': user_id}, {'$inc': {'balance': -amount}})

def add_referral(referrer_id):
    users_col.update_one(
        {'user_id': referrer_id},
        {'$inc': {'balance': 0.003, 'referrals_count': 1}}
    )

def get_total_users():
    return users_col.count_documents({})

# --- MAIN KEYBOARD ---
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_start = types.KeyboardButton("🚀 Start")
    btn_ad = types.KeyboardButton("📺 Watch Ad")
    btn_acc = types.KeyboardButton("🖥️ Account")
    btn_ref = types.KeyboardButton("✨ Referral")
    btn_with = types.KeyboardButton("💸 Withdraw")
    btn_rules = types.KeyboardButton("🛑 Rule's")
    btn_wa = types.KeyboardButton("🔰 Whatsapp")
    btn_sup = types.KeyboardButton("📤 Support")
    btn_stat = types.KeyboardButton("📊 Status")
    
    markup.add(btn_start)
    markup.add(btn_ad, btn_acc, btn_ref, btn_with, btn_rules, btn_wa, btn_sup, btn_stat)
    return markup

# --- AUTO FAKE PAYMENT SENDER THREAD ---
def auto_payment_poster():
    hex_chars = "0123456789abcdefABCDEF"
    methods = ["bKash (Personal)", "Nagad (Personal)", "BSC (BEP20)", "Binance USDT", "Payeer"]
    
    while True:
        try:
            amount = round(random.uniform(5.5, 35.0), 3)
            method = random.choice(methods)
            
            if "BSC" in method:
                start_hex = ''.join(random.choices(hex_chars, k=3))
                end_hex = ''.join(random.choices(hex_chars, k=4))
                address = f"0x{start_hex}****{end_hex}"
            elif "bKash" in method or "Nagad" in method:
                prefix = random.choice(["017", "018", "019", "013", "014", "016", "015"])
                digits = ''.join(random.choices("0123456789", k=2))
                last = ''.join(random.choices("0123456789", k=2))
                address = f"{prefix}{digits}***{last}"
            else:
                address = f"P10{''.join(random.choices('0123456789', k=6))}"

            text = (
                f"✅ **Withdrawal Paid**\n\n"
                f"💵 **{amount:.3f} USDT**\n"
                f"🌐 **{method}**\n"
                f"👛 `{address}`"
            )
            
            bot.send_message(PAYMENT_CHANNEL, text, parse_mode="Markdown")
        except Exception as e:
            print("Auto post error:", e)
            
        time.sleep(60)

def start_auto_post():
    t = Thread(target=auto_payment_poster)
    t.daemon = True
    t.start()

# --- ADMIN COMMANDS ---
@bot.message_handler(commands=['ban'])
def ban_user_cmd(message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        target_id = int(args[1])
        users_col.update_one({'user_id': target_id}, {'$set': {'is_banned': 1}})
        bot.reply_to(message, f"❌ ইউজার `{target_id}` কে ব্যান করা হয়েছে।", parse_mode="Markdown")

@bot.message_handler(commands=['unban'])
def unban_user_cmd(message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        target_id = int(args[1])
        users_col.update_one({'user_id': target_id}, {'$set': {'is_banned': 0}})
        bot.reply_to(message, f"✅ ইউজার `{target_id}` এর ব্যান তুলে নেওয়া হয়েছে।", parse_mode="Markdown")

@bot.message_handler(commands=['addbalance'])
def add_balance_cmd(message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) == 3 and args[1].isdigit():
        target_id = int(args[1])
        try:
            amount = float(args[2])
            add_balance(target_id, amount)
            bot.reply_to(message, f"✅ `{target_id}` একাউন্টে **${amount}** যোগ করা হয়েছে।", parse_mode="Markdown")
        except ValueError:
            bot.reply_to(message, "⚠️ সঠিক পরিমাণ লিখুন।")

@bot.message_handler(commands=['cutbalance'])
def cut_balance_cmd(message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) == 3 and args[1].isdigit():
        target_id = int(args[1])
        try:
            amount = float(args[2])
            deduct_balance(target_id, amount)
            bot.reply_to(message, f"✂️ `{target_id}` একাউন্ট থেকে **${amount}** কাটা হয়েছে।", parse_mode="Markdown")
        except ValueError:
            bot.reply_to(message, "⚠️ সঠিক পরিমাণ লিখুন।")

# --- MAIN BOT HANDLERS ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    
    if is_user_banned(user_id):
        bot.send_message(message.chat.id, "🚫 **আপনার অ্যাকাউন্টটি ব্যান করা হয়েছে!**", parse_mode="Markdown")
        return

    # Check Channel Subscription First
    if not check_user_channels(user_id):
        send_force_join_msg(message.chat.id)
        return

    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        referrer_id = int(args[1])
        if referrer_id != user_id:
            existing_user = users_col.find_one({'user_id': user_id})
            if not existing_user:
                new_user = {
                    'user_id': user_id,
                    'first_name': first_name,
                    'balance': 0.0,
                    'referred_by': referrer_id,
                    'referrals_count': 0,
                    'is_banned': 0
                }
                users_col.insert_one(new_user)
                add_referral(referrer_id)
                try:
                    bot.send_message(referrer_id, "🎉 আপনার রেফারে নতুন একজন জয়েন করেছে! আপনি $0.003 বোনাস পেয়েছেন।")
                except: pass

    balance, ref_count = get_user(user_id, first_name)
    text = f"👋 **স্বাগতম, {first_name}!**\n\nআমাদের বটে কাজ করে আপনি সহজেই ইনকাম করতে পারবেন। নিচের বাটনগুলো ব্যবহার করে কাজ শুরু করুন:"
    bot.send_message(message.chat.id, text, reply_markup=main_keyboard(), parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    text_input = message.text.strip()

    if is_user_banned(user_id):
        bot.send_message(message.chat.id, "🚫 **আপনার অ্যাকাউন্টটি ব্যান করা হয়েছে!**", parse_mode="Markdown")
        return

    # Check Channel Subscription for every message
    if not check_user_channels(user_id):
        send_force_join_msg(message.chat.id)
        return

    if "Start" in text_input:
        send_welcome(message)
        return

    if user_id in user_withdraw_step:
        method = user_withdraw_step[user_id]['method']
        acc_details = text_input
        balance, _ = get_user(user_id, first_name)
        
        if balance < 2.0:
            bot.send_message(message.chat.id, "⚠️ আপনার পর্যাপ্ত ব্যালেন্স নেই! সর্বনিম্ন উইথড্র $2.00 USDT।", reply_markup=main_keyboard())
            del user_withdraw_step[user_id]
            return

        deduct_balance(user_id, balance)
        
        channel_post = (
            f"✅ **Withdrawal Paid**\n\n"
            f"💵 **{balance:.3f} USDT**\n"
            f"🌐 **{method}**\n"
            f"👛 `{acc_details}`"
        )

        admin_post = (
            f"📥 **REAL WITHDRAW REQUEST!**\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Name:** {first_name}\n"
            f"🆔 **User ID:** `{user_id}`\n"
            f"💰 **Amount:** ${balance:.4f} USDT\n"
            f"⚡ **Method:** {method}\n"
            f"📱 **Account:** `{acc_details}`"
        )

        try:
            bot.send_message(PAYMENT_CHANNEL, channel_post, parse_mode="Markdown")
            bot.send_message(ADMIN_ID, admin_post, parse_mode="Markdown")
        except Exception as e:
            print("Withdraw Notification Error:", e)

        bot.send_message(
            message.chat.id, 
            f"✅ **আপনার উইথড্র রিকোয়েস্ট জমা হয়েছে!**\n\n"
            f"💳 **পরিমাণ:** ${balance:.4f} USDT\n"
            f"🔹 **মেথড:** {method}\n"
            f"📱 **ডিটেইলস:** {acc_details}\n\n"
            f"পেমেন্ট প্রুফ চ্যানেলে চেক করুন। ধন্যবাদ!",
            reply_markup=main_keyboard()
        )
        del user_withdraw_step[user_id]
        return

    if "Watch Ad" in text_input:
        user_last_click[user_id] = time.time()
        inline_markup = types.InlineKeyboardMarkup(row_width=2)
        
        m_btns = [types.InlineKeyboardButton(text=f"📺 Monetag {i}", url=link) for i, link in enumerate(MONETAG_LINKS, 1)]
        a_btns = [types.InlineKeyboardButton(text=f"⭐ Adsterra {i}", url=link) for i, link in enumerate(ADSTERRA_LINKS, 1)]
            
        for i in range(0, 10, 2):
            inline_markup.add(m_btns[i], m_btns[i+1])
        for i in range(0, 10, 2):
            inline_markup.add(a_btns[i], a_btns[i+1])
            
        btn_claim = types.InlineKeyboardButton(text="✅ Claim Reward ($0.001)", callback_data="claim_reward")
        inline_markup.add(btn_claim)

        bot.send_message(
            message.chat.id,
            "🎯 **যে কোনো বিজ্ঞাপনে ক্লিক করুন!**\n\n"
            "১. নিচের যেকোনো বিজ্ঞাপনে ক্লিক করে **১৫ সেকেন্ড** অপেক্ষা করুন।\n"
            "২. সময় শেষ হলে **Claim Reward** বাটনে চাপ দিয়ে $0.001 পয়েন্ট যোগ করে নিন!",
            reply_markup=inline_markup,
            parse_mode="Markdown"
        )

    elif "Account" in text_input or "My Balance" in text_input:
        balance, ref_count = get_user(user_id, first_name)
        text = (
            f"👤 **ইউজার প্রোফাইল**\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 **ID:** `{user_id}`\n"
            f"📛 **নাম:** {first_name}\n"
            f"💳 **মোট ব্যালেন্স:** ${balance:.4f} USDT\n"
            f"👥 **মোট রেফার:** {ref_count} জন"
        )
        bot.send_message(message.chat.id, text, parse_mode="Markdown")

    elif "Referral" in text_input:
        bot_info = bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
        text = (
            f"✨ **আপনার রেফারেল লিঙ্ক:**\n`{ref_link}`\n\n"
            f"🎁 প্রতি সফল রেফারে আপনি পাবেন: **$0.003 USDT**!\n"
            f"লিঙ্কটি বন্ধুদের সাথে শেয়ার করুন এবং বেশি ইনকাম করুন।"
        )
        bot.send_message(message.chat.id, text, parse_mode="Markdown")

    elif "Withdraw" in text_input:
        balance, _ = get_user(user_id, first_name)
        if balance < 2.0:
            bot.send_message(
                message.chat.id,
                f"💸 **উইথড্র ইনফরমেশন**\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"💳 **আপনার বর্তমান ব্যালেন্স:** ${balance:.4f} USDT\n"
                f"📌 **সর্বনিম্ন উইথড্র:** **$2.00 USDT**\n\n"
                f"⚠️ আপনার অ্যাকাউন্টে পর্যাপ্ত ব্যালেন্স নেই।",
                parse_mode="Markdown"
            )
        else:
            inline_markup = types.InlineKeyboardMarkup(row_width=2)
            inline_markup.add(
                types.InlineKeyboardButton("bKash", callback_data="with_bKash"),
                types.InlineKeyboardButton("Nagad", callback_data="with_Nagad"),
                types.InlineKeyboardButton("Binance USDT", callback_data="with_Binance"),
                types.InlineKeyboardButton("Payeer", callback_data="with_Payeer")
            )
            bot.send_message(
                message.chat.id,
                f"💳 **আপনার ব্যালেন্স:** ${balance:.4f} USDT\n\nপেমেন্ট মেথড সিলেক্ট করুন:",
                reply_markup=inline_markup
            )

    elif "Rule" in text_input:
        text = (
            f"🛑 **বটের নিয়মাবলী:**\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"১. কোনো প্রকার অটো-ক্লিক বা বট ব্যবহার করা যাবে না।\n"
            f"২. ভিপিএন (VPN) ব্যবহার করে কাজ করা সম্পূর্ণ নিষেধ।\n"
            f"৩. ফেক বা ভুয়া রেফারেল করলে অ্যাকাউন্ট পার্মানেন্ট ব্যান করা হবে।"
        )
        bot.send_message(message.chat.id, text, parse_mode="Markdown")

    elif "Whatsapp" in text_input:
        inline_markup = types.InlineKeyboardMarkup()
        btn_wa = types.InlineKeyboardButton(text="💬 WhatsApp-এ যোগাযোগ করুন", url=WHATSAPP_LINK)
        inline_markup.add(btn_wa)
        bot.send_message(
            message.chat.id,
            "🔰 **অফিসিয়াল হোয়াটসঅ্যাপ সাপোর্ট**",
            reply_markup=inline_markup,
            parse_mode="Markdown"
        )

    elif "Support" in text_input:
        inline_markup = types.InlineKeyboardMarkup(row_width=1)
        btn_group = types.InlineKeyboardButton(text="🖇️ সাপোর্ট গ্রুপে জয়েন করুন", url=SUPPORT_GROUP)
        btn_admin_wa = types.InlineKeyboardButton(text="✅ WhatsApp এডমিন", url=WHATSAPP_LINK)
        inline_markup.add(btn_group, btn_admin_wa)

        text = (
            f"🌐 **ALL IN ONE SUPPORT CENTER** 🌐\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ **টেলিগ্রাম এডমিন:** {ADMIN_USERNAME}\n"
            f"🖇️ **সাপোর্ট গ্রুপ:** {SUPPORT_GROUP}"
        )
        bot.send_message(message.chat.id, text, reply_markup=inline_markup, parse_mode="Markdown")

    elif "Status" in text_input:
        total_users = get_total_users()
        text = (
            f"📊 **বট লাইভ স্ট্যাটিস্টিকস**\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 **মোট রেজিস্ট্রেশন ইউজার:** {total_users} জন\n"
            f"🟢 **সার্ভার স্ট্যাটাস:** ১০০% অনলাইন ও নিরাপদ"
        )
        bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    user_id = call.from_user.id
    
    if is_user_banned(user_id):
        bot.answer_callback_query(call.id, "🚫 আপনার অ্যাকাউন্টটি ব্যান করা হয়েছে!", show_alert=True)
        return

    if call.data == "check_channels":
        if check_user_channels(user_id):
            bot.answer_callback_query(call.id, "✅ ভেরিফিকেশন সফল হয়েছে! এবার কাজ শুরু করুন।", show_alert=True)
            bot.delete_message(call.message.chat.id, call.message.message_id)
            get_user(user_id, call.from_user.first_name)
            bot.send_message(
                call.message.chat.id,
                f"👋 **স্বাগতম {call.from_user.first_name}!**\n\nআপনি সফলভাবে চ্যানেলগুলোতে জয়েন করেছেন। নিচের বাটনগুলো ব্যবহার করে ইনকাম শুরু করুন:",
                reply_markup=main_keyboard(),
                parse_mode="Markdown"
            )
        else:
            bot.answer_callback_query(call.id, "❌ আপনি এখনও ২টি চ্যানেলে জয়েন করেননি!", show_alert=True)

    elif call.data == "claim_reward":
        if not check_user_channels(user_id):
            bot.answer_callback_query(call.id, "⚠️ আগে চ্যানেলগুলোতে জয়েন করুন!", show_alert=True)
            send_force_join_msg(call.message.chat.id)
            return

        current_time = time.time()
        last_click = user_last_click.get(user_id, 0)
        time_passed = current_time - last_click

        if time_passed < 15:
            remaining = int(15 - time_passed)
            bot.answer_callback_query(call.id, f"⚠️ অন্তত ১৫ সেকেন্ড থাকুন (আর {remaining} সেকেন্ড বাকি)।", show_alert=True)
        else:
            add_balance(user_id, 0.001)
            user_last_click[user_id] = current_time + 10
            bot.answer_callback_query(call.id, "🎉 $0.001 আপনার অ্যাকাউন্টে যোগ করা হয়েছে।", show_alert=True)
            
            balance, _ = get_user(user_id, call.from_user.first_name)
            bot.send_message(
                call.message.chat.id,
                f"✅ **রিওয়ার্ড সফলভাবে যোগ হয়েছে!**\nবর্তমান ব্যালেন্স: ${balance:.4f} USDT",
                parse_mode="Markdown"
            )

    elif call.data.startswith("with_"):
        method = call.data.split("_")[1]
        user_withdraw_step[user_id] = {'method': method}
        bot.send_message(
            call.message.chat.id,
            f"📝 আপনার **{method}** নম্বর বা এড্রেসটি লিখে মেসেজ পাঠান:"
        )

if __name__ == "__main__":
    keep_alive()
    start_auto_post()
    print("Bot is running...")
    bot.infinity_polling(skip_pending=True)
