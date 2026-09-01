import telebot
from telebot.types import ReplyKeyboardRemove, MenuButtonWebApp, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading

BOT_TOKEN = "8615856288:AAFhhFONNIB56invYKb00GfUxkExtuU0C3k"
WEB_APP_URL = "https://ariful013152.github.io/My-Earning-All/"
ADMIN_IDS = [8414665404, 5034445579]

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
CORS(app)

# ডাটাবেজ অপশন (মেমোরিতে স্টোর করা হচ্ছে)
device_map = {}  # { device_id: primary_telegram_user_id }
banned_users = set()

try:
    bot.remove_webhook()
except Exception as e:
    print(f"Error removing webhook: {e}")

# ১. বট স্টার্ট মেসেজ
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    
    if user_id in banned_users:
        bot.send_message(message.chat.id, "🚫 **আপনার অ্যাকাউন্টটি ব্যান (Ban) করা হয়েছে!**", parse_mode="Markdown")
        return

    bot.set_chat_menu_button(
        message.chat.id,
        MenuButtonWebApp(type="web_app", text="Open App", web_app=WebAppInfo(url=WEB_APP_URL))
    )

    bot.send_message(
        message.chat.id,
        "👋 **স্বাগতম!**\n\nকাজ করতে নিচে থাকা **'Open App'** বাটনে চাপ দিন।",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )

# ২. WebApp থেকে ডিভাইস চেক করার API endpoint
@app.route('/check-device', methods=['POST'])
def check_device():
    data = request.json
    device_id = data.get('device_id')
    user_id = data.get('user_id')
    user_name = data.get('first_name', 'Unknown')
    username = data.get('username', 'নাই')

    if not device_id or not user_id:
        return jsonify({"status": "error", "message": "Invalid data"}), 400

    # ব্যানড চেক
    if int(user_id) in banned_users:
        return jsonify({"status": "banned"}), 403

    # ডিভাইস চেকিং লজিক
    if device_id in device_map:
        existing_user_id = device_map[device_id]
        
        # যদি একই ডিভাইসে অন্য কোনো টেলিগ্রাম আইডি পাওয়া যায়
        if str(existing_user_id) != str(user_id):
            admin_msg = (
                f"🚨 **মাল্টিপল অ্যাকাউন্ট সতর্কতা!** 🚨\n\n"
                f"একটি ফোন থেকে একাধিক টেলিগ্রাম আইডিতে ঢোকার চেষ্টা করা হয়েছে!\n\n"
                f"📱 **ডিভাইস ID:** `{device_id}`\n"
                f"👤 **বর্তমান ইউজার:** {user_name} (`{user_id}`)\n"
                f"🏷 **ইউজারনেম:** @{username}\n"
                f"🆔 **প্রথম রেজিস্টার্ড ID:** `{existing_user_id}`"
            )

            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("🚫 Ban User", callback_data=f"ban_{user_id}"),
                InlineKeyboardButton("✅ Unban User", callback_data=f"unban_{user_id}")
            )

            for admin_id in ADMIN_IDS:
                try:
                    bot.send_message(admin_id, admin_msg, parse_mode="Markdown", reply_markup=markup)
                except Exception as e:
                    print(f"Admin message error ({admin_id}): {e}")

            return jsonify({"status": "multi_account_detected"}), 200
    else:
        # নতুন ফোন হলে ডিভাইস এবং ইউজার আইডি সেভ করা হলো
        device_map[device_id] = user_id

    return jsonify({"status": "ok"}), 200

# ৩. এডমিন Ban / Unban হ্যান্ডলার
@bot.callback_query_handler(func=lambda call: call.data.startswith(('ban_', 'unban_')))
def handle_ban_unban(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "আপনি এডমিন নন!", show_alert=True)
        return

    action, target_id = call.data.split('_')
    target_id = int(target_id)

    if action == "ban":
        banned_users.add(target_id)
        bot.answer_callback_query(call.id, f"ইউজার {target_id} ব্যান হয়েছে!", show_alert=True)
        bot.edit_message_text(
            f"{call.message.text}\n\n❌ **স্ট্যাটাস: ইউজারের অ্যাকাউন্ট ব্যান করা হয়েছে।**",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
    elif action == "unban":
        banned_users.discard(target_id)
        bot.answer_callback_query(call.id, f"ইউজার {target_id} আনব্যান হয়েছে!", show_alert=True)
        bot.edit_message_text(
            f"{call.message.text}\n\n✅ **স্ট্যাটাস: ইউজারকে আনব্যান করা হয়েছে।**",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )

# Flask API এবং Telegram Bot একসাথে রান করানো
def run_flask():
    app.run(host='0.0.0.0', port=5000)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    print("Bot and Server are running...")
    bot.infinity_polling(skip_pending=True)
