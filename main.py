import os
import telebot
from telebot import types
from pymongo import MongoClient
from flask import Flask
import threading

# Web Server Configuration for Keeping Alive
app = Flask('')

@app.route('/')
def home():
    return "Bot is running live!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# Bot Configuration
TOKEN = '8615856288:AAHsdARNnr1J4IEK_RodW0_xiLqnftct1C8'
ADMIN_ID = 5034445579

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

# Database Setup (MongoDB)
# Render Environment-এ MONGO_URI থাকলে সেটা নেবে, না থাকলে ডিফল্ট URI ব্যবহার করবে
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb+srv://test:test@cluster0.example.mongodb.net/?retryWrites=true&w=majority')
client = MongoClient(MONGO_URI)
db = client['telegram_bot']
users_collection = db['users']

SIGNUP_BONUS = 0.0010
REFERRAL_BONUS = 0.0030

# /start Command & Referral System
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    
    # ডাটাবেজে ইউজার আছে কিনা চেক
    user = users_collection.find_one({"user_id": user_id})
    
    if not user:
        # রেফারার বের করা
        args = message.text.split()
        referrer_id = None
        
        if len(args) > 1 and args[1].isdigit():
            referrer_id = int(args[1])
        
        # নতুন ইউজার হিসেবে সেভ
        users_collection.insert_one({
            "user_id": user_id,
            "name": first_name,
            "balance": SIGNUP_BONUS,
            "total_referrals": 0,
            "referred_by": referrer_id
        })
        
        # রেফারারের ব্যালেন্স এবং রেফারাল সংখ্যা বাড়ানো
        if referrer_id and referrer_id != user_id:
            referrer = users_collection.find_one({"user_id": referrer_id})
            if referrer:
                users_collection.update_one(
                    {"user_id": referrer_id},
                    {"$inc": {"balance": REFERRAL_BONUS, "total_referrals": 1}}
                )
                try:
                    bot.send_message(
                        referrer_id, 
                        f"🎉 **নতুন রেফারেল ইনকাম!**\n\n👤 **{first_name}** আপনার লিংকে জয়েন করেছেন।\n🎁 আপনি পেয়েছেন **${REFERRAL_BONUS} USDT**!"
                    )
                except Exception as e:
                    print(f"Referral Notification Error: {e}")

    # কিবোর্ড বাটন সেটআপ
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        types.KeyboardButton('📺 Watch Ad'),
        types.KeyboardButton('💻 Account'),
        types.KeyboardButton('✨ Referral'),
        types.KeyboardButton('💸 Withdraw'),
        types.KeyboardButton('🔴 Rule\'s'),
        types.KeyboardButton('🟢 Whatsapp'),
        types.KeyboardButton('📨 Support'),
        types.KeyboardButton('📊 Status')
    )
    
    bot.send_message(
        message.chat.id, 
        f"👋 **স্বাগতম, {first_name}!**\n\nআমাদের বটে কাজ করতে নিচের বাটনগুলো ব্যবহার করুন:", 
        reply_markup=markup
    )

# Button Handlers
@bot.message_handler(func=lambda message: message.text == '💻 Account')
def account_info(message):
    user_id = message.from_user.id
    user = users_collection.find_one({"user_id": user_id})
    
    if user:
        bal = user.get('balance', 0.0)
        refs = user.get('total_referrals', 0)
        bot.reply_to(
            message, 
            f"👤 **ইউজার প্রোফাইল**\n\n🆔 **ID:** `{user_id}`\n📛 **নাম:** {message.from_user.first_name}\n💳 **মোট ব্যালেন্স:** ${bal:.4f} USDT\n👥 **মোট রেফার:** {refs} জন"
        )

@bot.message_handler(func=lambda message: message.text == '✨ Referral')
def referral_info(message):
    user_id = message.from_user.id
    try:
        bot_username = bot.get_me().username
    except:
        bot_username = "myearningall01_bot"
        
    ref_link = f"https://t.me/{bot_username}?start={user_id}"
    
    bot.reply_to(
        message, 
        f"✨ **আপনার রেফারেল লিংক:**\n`{ref_link}`\n\n🎁 **প্রতি সফল রেফারারে পাবেন:** ${REFERRAL_BONUS} USDT!\nলিংকটি বন্ধুদের সাথে শেয়ার করুন।"
    )

# Admin Commands
@bot.message_handler(commands=['ban'])
def ban_user(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        tid = int(message.text.split()[1])
        users_collection.update_one({"user_id": tid}, {"$set": {"is_banned": True}})
        bot.reply_to(message, f"✅ ইউজার `{tid}` ব্যান করা হয়েছে।")
    except:
        bot.reply_to(message, "⚠️ ব্যবহার: `/ban USER_ID`")

@bot.message_handler(commands=['unban'])
def unban_user(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        tid = int(message.text.split()[1])
        users_collection.update_one({"user_id": tid}, {"$set": {"is_banned": False}})
        bot.reply_to(message, f"✅ ইউজার `{tid}` এর ব্যান তোলা হয়েছে।")
    except:
        bot.reply_to(message, "⚠️ ব্যবহার: `/unban USER_ID`")

@bot.message_handler(commands=['addbalance'])
def add_balance(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        _, tid, amt = message.text.split()
        users_collection.update_one({"user_id": int(tid)}, {"$inc": {"balance": float(amt)}})
        bot.reply_to(message, f"✅ ইউজার `{tid}` এর অ্যাকাউন্টে ${amt} যোগ করা হয়েছে।")
    except:
        bot.reply_to(message, "⚠️ ব্যবহার: `/addbalance USER_ID AMOUNT`")

@bot.message_handler(commands=['cutbalance'])
def cut_balance(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        _, tid, amt = message.text.split()
        users_collection.update_one({"user_id": int(tid)}, {"$inc": {"balance": -float(amt)}})
        bot.reply_to(message, f"✅ ইউজার `{tid}` এর অ্যাকাউন্ট থেকে ${amt} কাটা হয়েছে।")
    except:
        bot.reply_to(message, "⚠️ ব্যবহার: `/cutbalance USER_ID AMOUNT`")

# Start Flask Web Server
threading.Thread(target=run_flask, daemon=True).start()

# Clear Webhooks & Start Polling
if __name__ == '__main__':
    try:
        bot.remove_webhook()
    except Exception as e:
        print(f"Webhook Removal Error: {e}")
        
    bot.infinity_polling(timeout=60, long_polling_timeout=30)
