import os
import telebot
from telebot import types
from pymongo import MongoClient
from flask import Flask
from threading import Thread

# Web Server Configuration for Keeping Alive
app = Flask('')

@app.route('/')
def home():
    return "Bot is running live!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Bot Setup
TOKEN = '8615856288:AAHsdARNnr1J4IEK_RodW0_xiLqnftct1C8'
ADMIN_ID = 5034445579  # আপনার সঠিক Telegram ID

bot = telebot.TeleBot(TOKEN)

# Database Setup (MongoDB)
MONGO_URI = os.environ.get('MONGO_URI', 'YOUR_MONGO_URI_HERE')  # আপনার আসল Mongo URI থাকলে এখানে দিন বা Render Env-এ রাখুন
client = MongoClient(MONGO_URI)
db = client['telegram_bot']
users_collection = db['users']

# Settings
SIGNUP_BONUS = 0.0010
REFERRAL_BONUS = 0.0030

# /start Command Handler with 100% Working Referral System
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    
    # ইউজার ডাটাবেজে আছে কিনা চেক
    user = users_collection.find_one({"user_id": user_id})
    
    if not user:
        # রেফারেল আইডি হ্যান্ডলিং
        command_args = message.text.split()
        referrer_id = None
        
        if len(command_args) > 1:
            try:
                referrer_id = int(command_args[1])
            except ValueError:
                referrer_id = None
        
        # নতুন ইউজারের তথ্য সেভ করা
        users_collection.insert_one({
            "user_id": user_id,
            "name": first_name,
            "balance": SIGNUP_BONUS,
            "total_referrals": 0,
            "referred_by": referrer_id
        })
        
        # রেফারারকে বোনাস এবং নোটিফিকেশন দেওয়া
        if referrer_id and referrer_id != user_id:
            referrer = users_collection.find_one({"user_id": referrer_id})
            if referrer:
                users_collection.update_one(
                    {"user_id": referrer_id},
                    {
                        "$inc": {
                            "balance": REFERRAL_BONUS,
                            "total_referrals": 1
                        }
                    }
                )
                try:
                    bot.send_message(
                        referrer_id, 
                        f"🎉 **নতুন রেফারেল ইনকাম!**\n\n👤 **{first_name}** আপনার রেফারেল লিংকে জয়েন করেছেন।\n🎁 আপনার অ্যাকাউন্টে **${REFERRAL_BONUS} USDT** যোগ হয়েছে!"
                    )
                except Exception as e:
                    print(f"Referral notice error: {e}")

    # মূল ইন্টারফেস/বাটন মেসেজ
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_watch = types.KeyboardButton('📺 Watch Ad')
    btn_account = types.KeyboardButton('💻 Account')
    btn_referral = types.KeyboardButton('✨ Referral')
    btn_withdraw = types.KeyboardButton('💸 Withdraw')
    btn_rules = types.KeyboardButton('🔴 Rule\'s')
    btn_whatsapp = types.KeyboardButton('🟢 Whatsapp')
    btn_support = types.KeyboardButton('📨 Support')
    btn_status = types.KeyboardButton('📊 Status')
    
    markup.add(btn_watch, btn_account, btn_referral, btn_withdraw, btn_rules, btn_whatsapp, btn_support, btn_status)
    
    bot.send_message(
        message.chat.id, 
        f"👋 **স্বাগতম, {first_name}!**\n\nআমাদের বটে কাজ করে আপনি প্রতিদিন USDT ইনকাম করতে পারবেন। নিচের বাটনগুলো ব্যবহার করুন:", 
        reply_markup=markup
    )

# Admin Commands
@bot.message_handler(commands=['ban'])
def ban_user(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        target_id = int(message.text.split()[1])
        users_collection.update_one({"user_id": target_id}, {"$set": {"is_banned": True}})
        bot.reply_to(message, f"✅ ইউজার {target_id} সফলভাবে ব্যান করা হয়েছে।")
    except Exception as e:
        bot.reply_to(message, "⚠️ ব্যবহার করার সঠিক নিয়ম: `/ban USER_ID`")

@bot.message_handler(commands=['unban'])
def unban_user(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        target_id = int(message.text.split()[1])
        users_collection.update_one({"user_id": target_id}, {"$set": {"is_banned": False}})
        bot.reply_to(message, f"✅ ইউজার {target_id} এর ব্যান তুলে নেওয়া হয়েছে।")
    except Exception as e:
        bot.reply_to(message, "⚠️ ব্যবহার করার সঠিক নিয়ম: `/unban USER_ID`")

@bot.message_handler(commands=['addbalance'])
def add_balance(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        _, target_id, amount = message.text.split()
        target_id = int(target_id)
        amount = float(amount)
        
        users_collection.update_one({"user_id": target_id}, {"$inc": {"balance": amount}})
        bot.reply_to(message, f"✅ ইউজার {target_id} এর অ্যাকাউন্টে ${amount} USDT যোগ করা হয়েছে।")
    except Exception as e:
        bot.reply_to(message, "⚠️ ব্যবহার করার সঠিক নিয়ম: `/addbalance USER_ID AMOUNT`")

@bot.message_handler(commands=['cutbalance'])
def cut_balance(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        _, target_id, amount = message.text.split()
        target_id = int(target_id)
        amount = float(amount)
        
        users_collection.update_one({"user_id": target_id}, {"$inc": {"balance": -amount}})
        bot.reply_to(message, f"✅ ইউজার {target_id} এর অ্যাকাউন্ট থেকে ${amount} USDT কেটে নেওয়া হয়েছে।")
    except Exception as e:
        bot.reply_to(message, "⚠️ ব্যবহার করার সঠিক নিয়ম: `/cutbalance USER_ID AMOUNT`")

# Keep Alive & Bot Polling
if __name__ == '__main__':
    keep_alive()
    bot.infinity_polling(timeout=60, long_polling_timeout=30)
