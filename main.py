import os
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

# আপনার বট কনফিগারেশন
TOKEN = '8615856288:AAHxmLU-JVNut0cBy-86sSMjeMVsT-b8luM' 
MONETAG_LINK = 'https://omg10.com/4/11516146' 
WHATSAPP_LINK = 'https://wa.me/qr/TLGSBEYHL74LD1'
SUPPORT_GROUP = 'https://t.me/allinoneg1'
ADMIN_USERNAME = '@akadmin02'

bot = TeleBot(TOKEN)

# ড্যাটাবেজ তৈরি ও আপডেট (সিকিউরড)
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

# প্রধান কিবোর্ড (আপনার স্ক্রিনশটের কিবোর্ড অনুযায়ী হুবহু মেলানো হয়েছে)
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

# /start দিলে যা দেখাবে
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    
    # রেফারেল হ্যান্ডলিং
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
                    bot.send_message(referrer_id, f"🎉 আপনার রেফারে নতুন একজন জয়েন করেছে! আপনি $0.003 বোনাস পেয়েছেন।")
                except:
                    pass

    balance, ref_count = get_user(user_id, first_name)

    text = f"👋 **স্বাগতম, {first_name}!**\n\nআমাদের বটে কাজ করে আপনি সহজেই ইনকাম করতে পারবেন। নিচের বাটনগুলো ব্যবহার করে কাজ শুরু করুন:"
    bot.send_message(message.chat.id, text, reply_markup=main_keyboard(), parse_mode="Markdown")

# বাটনে চাপ দিলে যা ঘটবে (ইমোজি সহ এবং ছাড়া দুইভাবেই হ্যান্ডেল করা হয়েছে)
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    text_input = message.text.strip()

    if "Watch Ad" in text_input:
        add_balance(user_id, 0.001)
        
        inline_markup = types.InlineKeyboardMarkup()
        btn_link = types.InlineKeyboardButton(text="👉 বিজ্ঞাপনে ক্লিক করুন", url=MONETAG_LINK)
        inline_markup.add(btn_link)

        bot.send_message(
            message.chat.id,
            "নিচের বোতামে চাপ দিয়ে বিজ্ঞাপনটি দেখুন। দেখার পর আপনার অ্যাকাউন্টে **$0.001** যোগ হয়ে যাবে!",
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
            f"লিঙ্কটি বন্ধুদের সাথে শেয়ার করুন এবং বেশি ইনকাম করুন।"
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
            f"🛑 **বটের নিয়মাবলী:**\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"১. কোনো প্রকার অটো-ক্লিক বা বট ব্যবহার করা যাবে না।\n"
            f"২. ভিপিএন (VPN) ব্যবহার করে কাজ করা সম্পূর্ণ নিষেধ।\n"
            f"৩. ফেক বা ভুয়া রেফারেল করলে অ্যাকাউন্ট পার্মানেন্ট ব্যান করা হবে।\n"
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
        btn_group = types.InlineKeyboardButton(text="🖇️ সাপোর্ট গ্রুপে জয়েন করুন", url=SUPPORT_GROUP)
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

if __name__ == "__main__":
    keep_alive()
    print("Bot is running securely...")
    bot.infinity_polling()
