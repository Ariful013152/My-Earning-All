import telebot
from telebot.types import ReplyKeyboardRemove, MenuButtonWebApp, WebAppInfo

BOT_TOKEN = "8615856288:AAFhhFONNIB56invYKb00GfUxkExtuU0C3k"
WEB_APP_URL = "https://ariful013152.github.io/My-Earning-All/"

bot = telebot.TeleBot(BOT_TOKEN)

# পুরোনো Webhook মুছে ফেলে সেশন ক্লিয়ার করা
try:
    bot.remove_webhook()
except Exception as e:
    print(f"Error removing webhook: {e}")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        # বটের নিচে বাম কোণায় 'Open App' বাটন সেট করা
        bot.set_chat_menu_button(
            message.chat.id,
            MenuButtonWebApp(type="web_app", text="Open App", web_app=WebAppInfo(url=WEB_APP_URL))
        )
    except Exception as e:
        print(f"Error setting menu button: {e}")

    # পুরোনো চ্যাট বাটন মুছে ফেলা এবং স্বাগতম মেসেজ দেওয়া
    bot.send_message(
        message.chat.id,
        "👋 **স্বাগতম!**\n\nআমাদের অ্যাপ থেকে আয় করতে নিচে থাকা **'Open App'** বাটনে চাপ দিন।",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )

if __name__ == "__main__":
    print("Bot is running...")
    # skip_pending=True দিলে আগের সব আটকা পড়া মেসেজ এড়িয়ে বট কাজ শুরু করবে
    bot.infinity_polling(skip_pending=True)
