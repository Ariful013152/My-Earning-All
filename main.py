import os
import time
import sqlite3
from flask import Flask
from threading import Thread
from telebot import TeleBot, types

# Flask Web Server setup for Render Port Binding
app = Flask('')

@app.route('/')
def home():
    return "Bot is running perfectly!"

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Config
TOKEN = '8615856288:AAHxmLU-JVNut0cBy-86sSMjeMVsT-b8luM' 
WHATSAPP_LINK = 'https://wa.me/qr/TLGSBEYHL74LD1'
SUPPORT_GROUP = 'https://t.me/allinoneg1'
ADMIN_USERNAME = '@akadmin02'

# --- 10 MONETAG LINKS ---
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

# --- 10 ADSTERRA LINKS ---
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

# Security Trackers (In-Memory)
user_last_click = {}

bot = TeleBot(TOKEN)

# Database Setup
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            balance REAL DEFAULT 0.0,
            referred_by INTEGER DEFAULT 0,
            referrals_count INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_user(user_id, first_name):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT balance, referrals_count FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    
    if row is None:
        cursor.execute('INSERT INTO users (user_id, first_name, balance, referred_by, referrals_count) VALUES (?, ?, 0.0, 0, 0)', (user_id, first_name))
        conn.commit()
        data = (0.0, 0)
    else:
        data = (row[0], row[1])
        
    conn.close()
    return data

def add_balance(user_id, amount):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def add_referral(referrer_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance = balance + 0.003, referrals_count = referrals_count + 1 WHERE user_id = ?', (referrer_id,))
    conn.commit()
    conn.close()

def get_total_users():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    total = cursor.fetchone()[0]
    conn.close()
    return total

def main_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_ad = types.KeyboardButton("📺 Watch Ad")
    btn_acc = types.KeyboardButton("🖥️ Account")
    btn_ref = types.KeyboardButton("✨ Referral")
    btn_with = types.KeyboardButton("💸 Withdraw")
    btn_rules = types.KeyboardButton("🛑 Rule's")
    btn_wa = types.KeyboardButton("🔰 Whatsapp")
    btn_sup = types.KeyboardButton("📤 Support")
    btn_stat = types.KeyboardButton("📊 Status")
    markup.add(btn_ad, btn_acc, btn_ref, btn_with, btn_rules, btn_wa, btn_sup, btn_stat)
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        referrer_id = int(args[1])
        if referrer_id != user_id:
            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
            if cursor.fetchone() is None:
                cursor.execute('INSERT INTO users (user_id, first_name, balance, referred_by, referrals_count) VALUES (?, ?, 0.0, ?, 0)', (user_id, first_name, referrer_id))
                conn.commit()
                conn.close()
                add_referral(referrer_id)
                try:
                    bot.send_message(referrer_id, f"🎉 আপনার রেফারে নতুন একজন জয়েন করেছে! আপনি $0.003 বোনাস পেয়েছেন।")
                except:
                    pass

    balance, ref_count = get_user(user_id, first_name)
    text = f"👋 **স্বাগতম, {first_name}!**\n\nআমাদের বটে কাজ করে আপনি সহজেই ইনকাম করতে পারবেন। নিচের বাটনগুলো ব্যবহার করে কাজ শুরু করুন:"
    bot.send_message(message.chat.id, text, reply_markup=main_keyboard(), parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    text_input = message.text.strip()

    if "Watch Ad" in text_input:
        user_last_click[user_id] = time.time()
        
        inline_markup = types.InlineKeyboardMarkup(row_width=2)
        
        # Adding 10 Monetag Links
        m_btns = []
        for i, link in enumerate(MONETAG_LINKS, 1):
            m_btns.append(types.InlineKeyboardButton(text=f"📺 Monetag {i}", url=link))
        
        # Adding 10 Adsterra Links
        a_btns = []
        for i, link in enumerate(ADSTERRA_LINKS, 1):
            a_btns.append(types.InlineKeyboardButton(text=f"⭐ Adsterra {i}", url=link))
            
        # Grouping in pairs
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
            "২. সময় শেষ হলে **Claim Reward** বাটনে চাপ দিয়ে $0.001 পয়েন্ট যোগ করে নিন!",
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
        text = (
            f"💸 **উইথড্র ইনফরমেশন**\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"💳 **আপনার বর্তমান ব্যালেন্স:** ${balance:.4f} USDT\n"
            f"📌 **সর্বনিম্ন উইথড্র:** **$2.00 USDT**\n\n"
            f"⚡ **পেমেন্ট মেথডসমূহ:**\n"
            f"🔹 বিকাশ (bKash)\n"
            f"🔹 নগদ (Nagad)\n"
            f"🔹 বাইনান্স (Binance USDT)\n"
            f"🔹 পায়ার (Payeer)\n\n"
            f"📝 **নোট:** আপনার ব্যালেন্স $2.00 USDT পূর্ণ হলে টাকা তুলতে সরাসরি অ্যাডমিন সাপোর্টে যোগাযোগ করুন।"
        )
        bot.send_message(message.chat.id, text, parse_mode="Markdown")

    elif "Rule" in text_input:
        text = (
            f"🛑 **বটের নিয়মাবলী:**\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"১. কোনো প্রকার অটো-ক্লিক বা বট ব্যবহার করা যাবে না।\n"
            f"২. ভিপিএন (VPN) ব্যবহার করে কাজ করা সম্পূর্ণ নিষেধ।\n"
            f"৩. ফেক বা ভুয়া রেফারেল করলে অ্যাকাউন্ট পার্মানেন্ট ব্যান করা হবে।\n"
            f"৪. সততার সাথে কাজ করলে ১০০% পেমেন্ট গ্যারান্টি।"
        )
        bot.send_message(message.chat.id, text, parse_mode="Markdown")

    elif "Whatsapp" in text_input:
        inline_markup = types.InlineKeyboardMarkup()
        btn_wa = types.InlineKeyboardButton(text="💬 WhatsApp-এ যোগাযোগ করুন", url=WHATSAPP_LINK)
        inline_markup.add(btn_wa)
        bot.send_message(
            message.chat.id,
            "🔰 **অফিসিয়াল হোয়াটসঅ্যাপ সাপোর্ট**\n\nআমাদের সাথে সরাসরি হোয়াটসঅ্যাপে কথা বলতে নিচের বোতামে চাপ দিন:",
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
            f"আপনার যেকোনো সমস্যা বা পেমেন্ট সংক্রান্ত তথ্যের জন্য যোগাযোগ করুন:\n\n"
            f"✅ **টেলিগ্রাম এডমিন:** {ADMIN_USERNAME}\n"
            f"🖇️ **সাপোর্ট গ্রুপ:** {SUPPORT_GROUP}\n"
            f"✅ **Whatsapp এডমিন:** {WHATSAPP_LINK}\n\n"
            f"সহযোগিতার জন্য নিচের বোতামগুলো ব্যবহার করুন 👇"
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

# Callback Handler for Secure Reward Verification
@bot.callback_query_handler(func=lambda call: call.data == "claim_reward")
def claim_reward_callback(call):
    user_id = call.from_user.id
    current_time = time.time()
    last_click = user_last_click.get(user_id, 0)

    time_passed = current_time - last_click

    if time_passed < 15:
        remaining = int(15 - time_passed)
        bot.answer_callback_query(call.id, f"⚠️ ভুয়া দাবি গ্রহণ করা হবে না! বিজ্ঞাপনে অন্তত ১৫ সেকেন্ড থাকুন (আর {remaining} সেকেন্ড বাকি)।", show_alert=True)
    else:
        add_balance(user_id, 0.001)
        user_last_click[user_id] = current_time + 10 # reset timer with cooldown
        bot.answer_callback_query(call.id, "🎉 অভিনন্দন! $0.001 আপনার অ্যাকাউন্টে যোগ করা হয়েছে।", show_alert=True)
        
        balance, _ = get_user(user_id, call.from_user.first_name)
        bot.send_message(
            call.message.chat.id,
            f"✅ **রিওয়ার্ড সফলভাবে যোগ হয়েছে!**\n"
            f"বর্তমান মোট ব্যালেন্স: ${balance:.4f} USDT",
            parse_mode="Markdown"
        )

if __name__ == "__main__":
    keep_alive()
    print("Bot is running securely with 20 ad links...")
    bot.infinity_polling()
