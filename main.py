import sqlite3
from telebot import TeleBot, types

# আপনার বট টোকেন এবং মনিট্যাগ লিংক বসানো সম্পন্ন
TOKEN = '8615856288:AAHxmLU-JVNut0cBy-86sSMjeMVsT-b8luM' 
MONETAG_LINK = 'https://omg10.com/4/11516146' 

bot = TeleBot(TOKEN)

# ড্যাটাবেজ তৈরি
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            balance REAL DEFAULT 0.0
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_user(user_id, first_name):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    
    if row is None:
        cursor.execute('INSERT INTO users (user_id, first_name, balance) VALUES (?, ?, ?)', (user_id, first_name, 0.0))
        conn.commit()
        balance = 0.0
    else:
        balance = row[0]
        
    conn.close()
    return balance

def add_balance(user_id, amount):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (user_id, user_id))
    conn.commit()
    conn.close()

# /start দিলে যা দেখাবে
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    balance = get_user(user_id, first_name)

    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_ad = types.KeyboardButton("📺 Watch Ad")
    btn_bal = types.KeyboardButton("💰 My Balance")
    markup.add(btn_ad, btn_bal)

    text = f"👋 স্বাগতম, {first_name}!\n\nআপনার বর্তমান ব্যালেন্স: ${balance:.2f} USDT"
    bot.send_message(message.chat.id, text, reply_markup=markup)

# বাটনে চাপ দিলে যা ঘটবে
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name

    if message.text == "📺 Watch Ad":
        add_balance(user_id, 0.05) 
        
        inline_markup = types.InlineKeyboardMarkup()
        btn_link = types.InlineKeyboardButton(text="👉 বিজ্ঞাপনে ক্লিক করুন", url=MONETAG_LINK)
        inline_markup.add(btn_link)

        bot.send_message(
            message.chat.id,
            "নিচের বোতামে চাপ দিয়ে বিজ্ঞাপনটি দেখুন। দেখার পর আপনার অ্যাকাউন্টে $0.05 যোগ হয়ে যাবে!",
            reply_markup=inline_markup
        )

    elif message.text == "💰 My Balance":
        balance = get_user(user_id, first_name)
        bot.send_message(message.chat.id, f"👤 ইউজার: {first_name}\n💳 মোট ব্যালেন্স: ${balance:.2f} USDT")

print("Bot is running...")
bot.infinity_polling()
