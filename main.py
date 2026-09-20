import os
import re
import time
import random
import datetime
import requests
import threading
import hashlib
import hmac
import secrets
import urllib.parse
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, ForceReply
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@myearningall")

# ৩টি বাধ্যতামূলক চ্যানেল
REQUIRED_CHANNELS = ["@myearningall", "@allinoneg1", "@allinoneg2"]

# নতুন ইউজার নোটিফিকেশন পাঠানোর চ্যানেল
NEW_USER_CHANNEL = "@allinoneg2"

PAYMENT_IMAGE_URL = os.environ.get("PAYMENT_IMAGE_URL", "https://i.ibb.co/L8y2pNz/payment-banner.jpg")

ADMIN_IDS_RAW = os.environ.get("ADMIN_CHAT_IDS", "")
ADMIN_CHAT_IDS = [int(admin_id.strip()) for admin_id in ADMIN_IDS_RAW.split(",") if admin_id.strip()]

MONGO_URI = os.environ.get("MONGO_URI")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://my-earning-app.onrender.com")

WITHDRAW_METHOD_MIN = {
    "bKash": 100,
    "Nagad": 100,
    "Recharge": 50,
}

# Deposit payment settings
BKASH_MERCHANT = "01884635078"
BINANCE_USDT_ADDRESS = "0x0998085153541e45e0df0ff23debb0a1c961854d"
USDT_BDT_RATE = 110.0
DEPOSIT_DAILY_RATE = 0.003
DEPOSIT_ALLOWED_AMOUNTS = {100, 200, 300, 400, 500, 1000, 1500, 2000, 3000, 4000, 5000, 10000, 20000, 30000, 40000, 50000}


app = Flask(__name__, template_folder='.', static_folder='.')

# Restricted CORS configuration for production security
CORS(app, origins=[RENDER_EXTERNAL_URL, "https://web.telegram.org"])

bot = telebot.TeleBot(BOT_TOKEN) if BOT_TOKEN else None

db = None
users_collection = None
devices_collection = None
withdraws_collection = None
deposits_collection = None
referrals_collection = None
settings_collection = None

if MONGO_URI:
    try:
        mongo_client = MongoClient(MONGO_URI)
        db = mongo_client.get_database()
        users_collection = db["users"]
        devices_collection = db["devices"]
        withdraws_collection = db["withdraws"]
        deposits_collection = db["deposits"]
        referrals_collection = db["referrals"]
        settings_collection = db["settings"]
        print("✅ MongoDB Connected Successfully")

        # Indexes matter a lot here: users_collection.find_one({"user_id": ...})
        # runs on nearly every request. Without an index Mongo does a full
        # collection scan per lookup, which gets slower as the collection
        # grows and turns into real lag once many users are active at once.
        # These are safe to run every startup — creating an index that
        # already exists is a no-op.
        try:
            users_collection.create_index("user_id", unique=True)
            users_collection.create_index("banned")
            users_collection.create_index("last_active")
            withdraws_collection.create_index("user_id")
            deposits_collection.create_index("user_id")
            deposits_collection.create_index("status")
            deposits_collection.create_index([("user_id", 1), ("status", 1)])
            devices_collection.create_index("device_id")
            print("✅ MongoDB indexes ensured")
        except Exception as e:
            print(f"⚠️ Index creation error (non-fatal): {e}")
    except Exception as e:
        print(f"❌ MongoDB Connection Error: {e}")

BOT_MAINTENANCE_MSG = "\U0001F6E0\uFE0F বটটি বর্তমানে সাময়িকভাবে বন্ধ আছে। একটু পরে আবার চেষ্টা করুন।"


def is_bot_active():
    """Global on/off switch, toggled from the admin panel. Defaults to ON
    if the settings doc doesn't exist yet or the DB is unavailable, so a
    fresh deploy never accidentally starts in a locked-out state."""
    if settings_collection is None:
        return True
    doc = settings_collection.find_one({"_id": "global"})
    if doc is None:
        return True
    return doc.get("bot_enabled", True)


def set_bot_active(active):
    if settings_collection is None:
        return
    settings_collection.update_one({"_id": "global"}, {"$set": {"bot_enabled": active}}, upsert=True)


# -------- TELEGRAM WEBAPP HASH VERIFICATION --------
def verify_telegram_init_data(init_data):
    if not BOT_TOKEN or not init_data:
        return False
    try:
        parsed_data = urllib.parse.parse_qsl(init_data, keep_blank_values=True)
        data_dict = dict(parsed_data)
        received_hash = data_dict.pop('hash', None)
        if not received_hash:
            return False
        
        data_list = [f"{k}={v}" for k, v in sorted(data_dict.items())]
        data_check_string = "\n".join(data_list)
        
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode('utf-8'), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode('utf-8'), hashlib.sha256).hexdigest()
        
        return hmac.compare_digest(calculated_hash, received_hash)
    except Exception as e:
        print(f"Auth verification error: {e}")
        return False

# -------- HELPER: CHECK USER BANNED STATUS FROM DB --------
def is_user_banned(user_id):
    if users_collection is None:
        return False
    user = users_collection.find_one({"user_id": str(user_id)})
    if user and user.get("banned", False):
        return True
    return False


def is_valid_telegram_id(value):
    """Telegram numeric user IDs only — rejects stray commands (e.g. an admin
    accidentally typing '/admin' into a 'send USER ID' prompt), empty input,
    or obvious typos, before it gets used in a DB write or a send_message call."""
    return bool(value) and value.isdigit() and 5 <= len(value) <= 15

# -------- FORCE JOIN CHECKER --------
def check_user_joined_channels(user_id):
    if not bot:
        return False
    try:
        uid = int(user_id)
    except Exception:
        return False

    for ch in REQUIRED_CHANNELS:
        try:
            member = bot.get_chat_member(ch, uid)
            if member.status in ['left', 'kicked']:
                return False
        except Exception as e:
            print(f"Channel check error for {ch}: {e}")
            return False
    return True

# -------- FAKE WITHDRAW AUTO SENDER --------
def send_fake_withdraw_loop():
    while True:
        try:
            if bot:
                methods = ['bKash', 'Nagad']
                selected_method = random.choice(methods)
                random_amount = round(random.uniform(200.0, 850.0), 2)
                
                prefixes = ['017', '018', '019', '013', '014', '016', '015']
                prefix = random.choice(prefixes)
                last_two = random.randint(10, 99)
                fake_acc = f"{prefix}xxxx{last_two}"

                msg = (
                    f"<b>My Earning All Payment</b>\n"
                    f"✅ Withdrawal Paid\n\n"
                    f"💵 <b>{random_amount} BDT</b>\n"
                    f"🌐 <b>{selected_method}</b>\n"
                    f"👛 <b>{fake_acc}</b>"
                )

                markup = InlineKeyboardMarkup()
                bot_username = bot.get_me().username
                markup.add(InlineKeyboardButton("Open App & Earn", url=f"https://t.me/{bot_username}"))

                try:
                    bot.send_photo(CHANNEL_ID, photo=PAYMENT_IMAGE_URL, caption=msg, parse_mode="HTML", reply_markup=markup)
                except Exception as e:
                    bot.send_message(CHANNEL_ID, msg, parse_mode="HTML", reply_markup=markup)

        except Exception as e:
            print(f"⚠️ Fake withdraw error: {e}")
            
        time.sleep(300)

INACTIVITY_REMINDER_HOURS = 24
INACTIVITY_REMINDER_TEXT = (
    "\u23F0 <b>আজকের টাস্ক এখনো বাকি!</b>\n\n"
    "অ্যাপে ফিরে গিয়ে টাস্ক সম্পন্ন করে আয় করুন — ডেইলি লিমিট প্রতিদিন রিসেট হয়, "
    "মিস করবেন না!"
)

def inactivity_reminder_loop():
    """Nudges users who haven't opened the app in 24h+ with a Telegram
    reminder. Sent at most once per 24h window per user (tracked via
    last_reminder_sent) so this never turns into spam. Every user gets a
    last_active value the moment they're created (see send_welcome), so a
    plain last_active < cutoff check covers both "used it once and left"
    and "joined but never opened the app" cases."""
    if not bot:
        return
    while True:
        try:
            if users_collection is not None:
                cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=INACTIVITY_REMINDER_HOURS)
                idle_users = users_collection.find({
                    "banned": {"$ne": True},
                    "last_active": {"$lt": cutoff},
                    "$or": [
                        {"last_reminder_sent": {"$exists": False}},
                        {"last_reminder_sent": {"$lt": cutoff}}
                    ]
                })
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton("\U0001F680 Open App \U0001F680", web_app=WebAppInfo(url=RENDER_EXTERNAL_URL)))
                for u in idle_users:
                    uid = u.get("user_id")
                    if not uid:
                        continue
                    try:
                        bot.send_message(uid, INACTIVITY_REMINDER_TEXT, parse_mode="HTML", reply_markup=markup)
                        users_collection.update_one({"user_id": uid}, {"$set": {"last_reminder_sent": datetime.datetime.utcnow()}})
                        time.sleep(0.05)  # gentle pacing, same as broadcast, to stay under Telegram's rate limits
                    except Exception:
                        # Most common cause: user blocked the bot — nothing to do, just move on.
                        pass
        except Exception as e:
            print(f"Inactivity reminder error: {e}")
        time.sleep(3600)  # check hourly — reminders still only go out once per 24h per user

# -------- KEEP ALIVE --------
def keep_alive():
    if RENDER_EXTERNAL_URL:
        while True:
            time.sleep(840)
            try:
                requests.get(RENDER_EXTERNAL_URL, timeout=10)
            except Exception as e:
                print(f"⚠️ Ping Error: {e}")

# -------- TELEGRAM BOT HANDLERS & REFERRAL --------
if bot:
    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        user_id = str(message.from_user.id)
        first_name = message.from_user.first_name or "User"
        username = message.from_user.username or "No Username"

        if is_user_banned(user_id):
            bot.reply_to(message, "❌ <b>আপনি এই বট থেকে ব্যান হয়েছেন!</b>", parse_mode="HTML")
            return

        if message.from_user.id not in ADMIN_CHAT_IDS and not is_bot_active():
            bot.reply_to(message, BOT_MAINTENANCE_MSG, parse_mode="HTML")
            return

        # Save the referrer id (if present in the /start deep-link) to the DB right away,
        # BEFORE the channel-join gate below. This is critical: when the user later taps
        # "Check Verification", this same function runs again but with the bot's own
        # message object (no "/start <referrer_id>" text), so without this early save the
        # referrer id would be lost for anyone who has to join channels first.
        if message.text and message.text.startswith('/start'):
            start_args = message.text.split()
            incoming_referrer = start_args[1] if len(start_args) > 1 else None
            if incoming_referrer and str(incoming_referrer) != user_id and users_collection is not None:
                users_collection.update_one(
                    {"user_id": user_id, "referred_by": {"$exists": False}},
                    {
                        "$set": {"pending_referrer": str(incoming_referrer)},
                        "$setOnInsert": {
                            "user_id": user_id, "balance": 0.0, "total_refers": 0,
                            "monetag_count": 0, "adsterra_count": 0, "gigapub_count": 0,
                            "gigapub_first_view_at": None,
                            "last_reset_date": datetime.datetime.utcnow().strftime("%Y-%m-%d")
                        }
                    },
                    upsert=True
                )

        if not check_user_joined_channels(message.from_user.id):
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("📢 Channel 1", url="https://t.me/myearningall"))
            markup.add(InlineKeyboardButton("📢 Channel 2", url="https://t.me/allinoneg1"))
            markup.add(InlineKeyboardButton("📢 Channel 3", url="https://t.me/allinoneg2"))
            markup.add(InlineKeyboardButton("✅ Check Verification", callback_data="check_join"))
            
            join_msg = (
                "⚠️ <b>বট ব্যবহার করতে আপনাকে অবশ্যই আমাদের ৩টি চ্যানেলেই জয়েন করতে হবে!</b>\n\n"
                "নিচের ৩টি চ্যানেলে জয়েন করে <b>Check Verification</b> বাটনে ক্লিক করুন।"
            )
            bot.reply_to(message, join_msg, parse_mode="HTML", reply_markup=markup)
            return

        # নতুন ইউজার চেক করা এবং চ্যানেলে মেসেজ পাঠানো
        if users_collection is not None:
            existing_user = users_collection.find_one({"user_id": user_id})
            
            if not existing_user:
                try:
                    new_user_msg = (
                        f"🎉 <b>নতুন ইউজার জয়েন করেছেন!</b>\n\n"
                        f"👤 <b>নাম:</b> {first_name}\n"
                        f"🆔 <b>ইউজার ID:</b> <code>{user_id}</code>\n"
                        f"🔗 <b>ইউজারনেম:</b> @{username}"
                    )
                    bot.send_message(NEW_USER_CHANNEL, new_user_msg, parse_mode="HTML")
                except Exception as e:
                    print(f"Channel notify error: {e}")

            users_collection.update_one(
                {"user_id": user_id},
                {"$set": {"first_name": first_name, "username": username, "banned": False},
                 "$setOnInsert": {"user_id": user_id, "balance": 0.0, "total_refers": 0, "monetag_count": 0, "adsterra_count": 0, "gigapub_count": 0, "gigapub_first_view_at": None, "last_reset_date": datetime.datetime.utcnow().strftime("%Y-%m-%d"), "total_earned": 0.0, "total_tasks_completed": 0, "joined_at": datetime.datetime.utcnow(), "last_active": datetime.datetime.utcnow()}},
                upsert=True
            )

        # Read the referrer id from the DB (saved earlier, before the channel-join gate)
        # instead of re-parsing message.text, since this function can be re-entered via
        # the "Check Verification" button with a message object that has no /start args.
        current_user = users_collection.find_one({"user_id": user_id}) if users_collection is not None else None
        referrer_id = current_user.get("pending_referrer") if current_user else None

        if referrer_id and str(referrer_id) != user_id:
            if users_collection is not None:
                try:
                    if current_user and not current_user.get("referred_by"):
                        users_collection.update_one(
                            {"user_id": user_id},
                            {"$set": {"referred_by": str(referrer_id)}, "$unset": {"pending_referrer": ""}}
                        )

                        if referrals_collection is not None:
                            ref_doc = {
                                "referrer_id": str(referrer_id),
                                "referred_id": user_id,
                                "referred_name": first_name,
                                "referred_username": username,
                                "status": "pending",
                                "date": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M")
                            }
                            res = referrals_collection.insert_one(ref_doc)
                            ref_req_id = str(res.inserted_id)

                            referrer_data = users_collection.find_one({"user_id": str(referrer_id)})
                            referrer_name = referrer_data.get("first_name", "Unknown") if referrer_data else "Unknown"
                            referrer_username = referrer_data.get("username", "No Username") if referrer_data else "No Username"

                            admin_msg = (
                                f"\U0001F465 <b>\u09a8\u09a4\u09c1\u09a8 \u09b0\u09c7\u09ab\u09be\u09b0 \u09b0\u09bf\u0995\u09cb\u09df\u09c7\u09b8\u09cd\u099f!</b>\n\n"
                                f"\U0001F517 <b>\u09b0\u09c7\u09ab\u09be\u09b0\u09be\u09b0:</b> {referrer_name} (@{referrer_username})\n"
                                f"\U0001F194 <b>\u09b0\u09c7\u09ab\u09be\u09b0\u09be\u09b0 ID:</b> <code>{referrer_id}</code>\n\n"
                                f"\U0001F195 <b>\u09a8\u09a4\u09c1\u09a8 \u0987\u0989\u099c\u09be\u09b0:</b> {first_name} (@{username})\n"
                                f"\U0001F194 <b>\u09a8\u09a4\u09c1\u09a8 \u0987\u0989\u099c\u09be\u09b0 ID:</b> <code>{user_id}</code>\n\n"
                                f"\U0001F4B5 <b>\u09ac\u09cb\u09a8\u09be\u09b8:</b> \u09f30.50 (Accept \u0995\u09b0\u09b2\u09c7 \u09a6\u09c7\u0993\u09df\u09be \u09b9\u09ac\u09c7)"
                            )

                            ref_markup = InlineKeyboardMarkup()
                            ref_markup.row(
                                InlineKeyboardButton("\u2705 Accept", callback_data=f"ref_acc_{ref_req_id}"),
                                InlineKeyboardButton("\u274c Reject", callback_data=f"ref_rej_{ref_req_id}")
                            )

                            for admin_id in ADMIN_CHAT_IDS:
                                try:
                                    bot.send_message(admin_id, admin_msg, parse_mode="HTML", reply_markup=ref_markup)
                                except Exception as e:
                                    print(f"Error notifying admin {admin_id} about referral: {e}")
                except Exception as e:
                    print(f"Referral update error: {e}")

        welcome_text = "👋 <b>স্বাগতম!</b>\n\nআপনি সকল চ্যানেলে জয়েন করেছেন। আমাদের অ্যাপে ঢুকতে নিচে থাকা <b>Open App</b> বাটনে চাপ দিন।"
        
        markup = InlineKeyboardMarkup()
        web_app_btn = InlineKeyboardButton("🚀 Open App 🚀", web_app=WebAppInfo(url=RENDER_EXTERNAL_URL))
        markup.add(web_app_btn)

        bot.reply_to(message, welcome_text, parse_mode="HTML", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data == "check_join")
    def handle_check_join(call):
        user_id = call.from_user.id
        if is_user_banned(user_id):
            bot.answer_callback_query(call.id, "❌ আপনি ব্যান হয়েছেন!", show_alert=True)
            return
        if user_id not in ADMIN_CHAT_IDS and not is_bot_active():
            bot.answer_callback_query(call.id, BOT_MAINTENANCE_MSG, show_alert=True)
            return
        if check_user_joined_channels(user_id):
            bot.answer_callback_query(call.id, "✅ ভেরিফিকেশন সফল হয়েছে!")
            bot.delete_message(call.message.chat.id, call.message.message_id)
            send_welcome(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ আপনি এখনো সবগুলো চ্যানেলে জয়েন করেননি!", show_alert=True)

    # -------- WITHDRAW ACTION HANDLER (ACCEPT/REJECT) --------
    @bot.callback_query_handler(func=lambda call: call.data.startswith(('wd_acc_', 'wd_rej_')))
    def handle_withdraw_action(call):
        if call.from_user.id not in ADMIN_CHAT_IDS:
            bot.answer_callback_query(call.id, "❌ আপনি এই কাজের জন্য অনুমোদিত নন!", show_alert=True)
            return

        parts = call.data.split('_')
        action = parts[1]
        req_id = parts[2]

        if withdraws_collection is None:
            bot.answer_callback_query(call.id, "Database Error!", show_alert=True)
            return

        req = withdraws_collection.find_one({"_id": ObjectId(req_id)})
        if not req:
            bot.answer_callback_query(call.id, "উইথড্র রিকোয়েস্টটি পাওয়া যায়নি!", show_alert=True)
            return

        if req.get("status") != "pending":
            bot.answer_callback_query(call.id, "এই রিকোয়েস্টটি আগেই প্রসেস করা হয়েছে!", show_alert=True)
            return

        user_id = req["user_id"]
        amount = req["amount"]
        account = req["account"]
        method = req["method"]

        if action == "acc":
            withdraws_collection.update_one({"_id": ObjectId(req_id)}, {"$set": {"status": "completed"}})
            bot.answer_callback_query(call.id, "✅ Withdraw Approved!")

            bot.edit_message_text(
                f"{call.message.text}\n\n<b>✅ স্ট্যাটাস: Approved by Admin</b>",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode="HTML"
            )

            try:
                bot.send_message(user_id, f"🎉 <b>আপনার ৳{amount:.2f} ({method}) উইথড্র রিকোয়েস্টটি অ্যাপ্রুভ হয়েছে এবং টাকা পাঠানো হয়েছে!</b>", parse_mode="HTML")
            except Exception:
                pass

            hidden_acc = account[:3] + "xxxx" + account[-2:]
            msg = (
                f"<b>My Earning All Payment</b>\n"
                f"✅ Withdrawal Paid\n\n"
                f"💵 <b>{amount:.2f} BDT</b>\n"
                f"🌐 <b>{method}</b>\n"
                f"👛 <b>{hidden_acc}</b>"
            )
            markup = InlineKeyboardMarkup()
            bot_username = bot.get_me().username if bot else ""
            markup.add(InlineKeyboardButton("Open App & Earn", url=f"https://t.me/{bot_username}"))
            try:
                bot.send_photo(CHANNEL_ID, photo=PAYMENT_IMAGE_URL, caption=msg, parse_mode="HTML", reply_markup=markup)
            except Exception:
                bot.send_message(CHANNEL_ID, msg, parse_mode="HTML", reply_markup=markup)

        elif action == "rej":
            withdraws_collection.update_one({"_id": ObjectId(req_id)}, {"$set": {"status": "rejected"}})

            # Rejected withdrawal: restore any deposit principal that was reduced
            # when the withdrawal request was created.
            restore_withdrawal_deposit_principal(req.get("principal_allocations", []))

            if users_collection is not None:
                users_collection.update_one({"user_id": user_id}, {"$inc": {"balance": amount}})

            bot.answer_callback_query(call.id, "❌ Withdraw Rejected!")

            bot.edit_message_text(
                f"{call.message.text}\n\n<b>❌ স্ট্যাটাস: Rejected & Refunded</b>",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode="HTML"
            )

            try:
                bot.send_message(user_id, f"❌ <b>আপনার ৳{amount:.2f} ({method}) উইথড্র রিকোয়েস্টটি রিজেক্ট করা হয়েছে এবং ব্যালেন্স ওয়ালেটে ফেরত দেওয়া হয়েছে।</b>", parse_mode="HTML")
            except Exception:
                pass

    @bot.callback_query_handler(func=lambda call: call.data.startswith(('dep_acc_', 'dep_rej_')))
    def handle_deposit_action(call):
        if call.from_user.id not in ADMIN_CHAT_IDS:
            bot.answer_callback_query(call.id, "❌ আপনি এই কাজের জন্য অনুমোদিত নন!", show_alert=True)
            return

        parts = call.data.split('_')
        action = parts[1]
        req_id = parts[2]

        if deposits_collection is None:
            bot.answer_callback_query(call.id, "Database Error!", show_alert=True)
            return

        try:
            req = deposits_collection.find_one({"_id": ObjectId(req_id)})
        except Exception:
            req = None

        if not req:
            bot.answer_callback_query(call.id, "ডিপোজিট রিকোয়েস্ট পাওয়া যায়নি!", show_alert=True)
            return

        if req.get("status") != "pending":
            bot.answer_callback_query(call.id, "এই রিকোয়েস্টটি আগেই প্রসেস করা হয়েছে!", show_alert=True)
            return

        user_id = str(req.get("user_id"))
        amount = float(req.get("amount", 0))
        today = datetime.datetime.utcnow().strftime("%Y-%m-%d")

        if action == "acc":
            deposits_collection.update_one(
                {"_id": ObjectId(req_id), "status": "pending"},
                {"$set": {
                    "status": "active",
                    "approved_at": datetime.datetime.utcnow(),
                    "started_at": datetime.datetime.utcnow(),
                    "last_profit_date": today,
                    "daily_rate": DEPOSIT_DAILY_RATE
                }}
            )
            bot.answer_callback_query(call.id, "✅ Deposit Approved!")
            try:
                bot.edit_message_text(
                    f"{call.message.text}\n\n<b>✅ স্ট্যাটাস: Approved / Active</b>",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    parse_mode="HTML"
                )
            except Exception:
                pass
            try:
                bot.send_message(
                    user_id,
                    f"🎉 <b>আপনার ৳{amount:.2f} ডিপোজিট অ্যাপ্রুভ হয়েছে!</b>\n\n"
                    f"📈 দৈনিক হিসাব: ৳{amount * DEPOSIT_DAILY_RATE:.2f}\n"
                    f"ℹ️ প্রথম profit claim পরবর্তী UTC দিনে করা যাবে।",
                    parse_mode="HTML"
                )
            except Exception:
                pass

        elif action == "rej":
            deposits_collection.update_one(
                {"_id": ObjectId(req_id), "status": "pending"},
                {"$set": {"status": "rejected", "rejected_at": datetime.datetime.utcnow()}}
            )
            bot.answer_callback_query(call.id, "❌ Deposit Rejected!")
            try:
                bot.edit_message_text(
                    f"{call.message.text}\n\n<b>❌ স্ট্যাটাস: Rejected</b>",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    parse_mode="HTML"
                )
            except Exception:
                pass
            try:
                bot.send_message(
                    user_id,
                    f"❌ <b>আপনার ৳{amount:.2f} ডিপোজিট রিকোয়েস্টটি রিজেক্ট করা হয়েছে।</b>",
                    parse_mode="HTML"
                )
            except Exception:
                pass

    @bot.callback_query_handler(func=lambda call: call.data.startswith(('ref_acc_', 'ref_rej_')))
    def handle_referral_action(call):
        if call.from_user.id not in ADMIN_CHAT_IDS:
            bot.answer_callback_query(call.id, "\u274c \u0986\u09aa\u09a8\u09bf \u098f\u0987 \u0995\u09be\u099c\u09c7\u09b0 \u099c\u09a8\u09cd\u09af \u0985\u09a8\u09c1\u09ae\u09cb\u09a6\u09bf\u09a4 \u09a8\u09a8!", show_alert=True)
            return

        parts = call.data.split('_')
        action = parts[1]
        req_id = parts[2]

        if referrals_collection is None:
            bot.answer_callback_query(call.id, "Database Error!", show_alert=True)
            return

        req = referrals_collection.find_one({"_id": ObjectId(req_id)})
        if not req:
            bot.answer_callback_query(call.id, "\u09b0\u09c7\u09ab\u09be\u09b0 \u09b0\u09bf\u0995\u09cb\u09df\u09c7\u09b8\u09cd\u099f\u099f\u09bf \u09aa\u09be\u0993\u09df\u09be \u09af\u09be\u09df\u09a8\u09bf!", show_alert=True)
            return

        if req.get("status") != "pending":
            bot.answer_callback_query(call.id, "\u098f\u0987 \u09b0\u09bf\u0995\u09cb\u09df\u09c7\u09b8\u09cd\u099f\u099f\u09bf \u0986\u0997\u09c7\u0987 \u09aa\u09cd\u09b0\u09b8\u09c7\u09b8 \u0995\u09b0\u09be \u09b9\u09df\u09c7\u099b\u09c7!", show_alert=True)
            return

        referrer_id = req["referrer_id"]

        if action == "acc":
            referrals_collection.update_one({"_id": ObjectId(req_id)}, {"$set": {"status": "approved"}})
            if users_collection is not None:
                users_collection.update_one(
                    {"user_id": referrer_id},
                    {"$inc": {"balance": 0.50, "total_refers": 1, "total_earned": 0.50}},
                    upsert=True
                )

            bot.answer_callback_query(call.id, "\u2705 Referral Approved!")
            bot.edit_message_text(
                f"{call.message.text}\n\n<b>\u2705 \u09b8\u09cd\u099f\u09cd\u09af\u09be\u099f\u09be\u09b8: Approved by Admin</b>",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode="HTML"
            )

            try:
                bot.send_message(referrer_id, "\U0001F389 \u0986\u09aa\u09a8\u09be\u09b0 \u09b0\u09c7\u09ab\u09be\u09b0 \u09b2\u09bf\u0982\u0995\u09c7 \u09a8\u09a4\u09c1\u09a8 \u098f\u0995\u099c\u09a8 \u099c\u09df\u09c7\u09a8 \u0995\u09b0\u09be\u09df \u0986\u09aa\u09a8\u09bf <b>TK 0.50</b> \u09ac\u09cb\u09a8\u09be\u09b8 \u09aa\u09c7\u09df\u09c7\u099b\u09c7\u09a8!", parse_mode="HTML")
            except Exception:
                pass

        elif action == "rej":
            referrals_collection.update_one({"_id": ObjectId(req_id)}, {"$set": {"status": "rejected"}})
            bot.answer_callback_query(call.id, "\u274c Referral Rejected!")
            bot.edit_message_text(
                f"{call.message.text}\n\n<b>\u274c \u09b8\u09cd\u099f\u09cd\u09af\u09be\u099f\u09be\u09b8: Rejected by Admin</b>",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode="HTML"
            )

    @bot.callback_query_handler(func=lambda call: call.data.startswith(('ban_', 'unban_')))
    def handle_ban_callback(call):
        action, target_user_id = call.data.split('_')
        
        if action == 'ban':
            if users_collection is not None:
                users_collection.update_one({"user_id": target_user_id}, {"$set": {"banned": True}})
            bot.answer_callback_query(call.id, f"User {target_user_id} Banned!")
            bot.edit_message_text(f"🚫 <b>ইউজার ID: {target_user_id} ব্যান করা হয়েছে!</b>", 
                                  chat_id=call.message.chat.id, 
                                  message_id=call.message.message_id, parse_mode="HTML")
        elif action == 'unban':
            if users_collection is not None:
                users_collection.update_one({"user_id": target_user_id}, {"$set": {"banned": False}})
            bot.answer_callback_query(call.id, f"User {target_user_id} Unbanned!")
            bot.edit_message_text(f"✅ <b>ইউজার ID: {target_user_id} আনব্যান করা হয়েছে!</b>", 
                                  chat_id=call.message.chat.id, 
                                  message_id=call.message.message_id, parse_mode="HTML")

    def build_admin_panel_markup():
        markup = InlineKeyboardMarkup(row_width=2)
        bot_status_label = "\U0001F7E2 Bot: ON (চাপ দিলে OFF হবে)" if is_bot_active() else "\U0001F534 Bot: OFF (চাপ দিলে ON হবে)"

        btn_ban = InlineKeyboardButton("\U0001F6AB Ban User", callback_data="admin_ban_prompt")
        btn_unban = InlineKeyboardButton("\u2705 Unban User", callback_data="admin_unban_prompt")
        btn_add_bal = InlineKeyboardButton("\u2795 Add Balance", callback_data="admin_addbal_prompt")
        btn_cut_bal = InlineKeyboardButton("\u2796 Cut Balance", callback_data="admin_cutbal_prompt")
        btn_stats = InlineKeyboardButton("\U0001F4CA Total Users", callback_data="admin_stats")
        btn_broadcast = InlineKeyboardButton("\U0001F4E2 Broadcast", callback_data="admin_broadcast_prompt")
        btn_startall = InlineKeyboardButton("\U0001F504 Start All Users", callback_data="admin_startall_confirm")
        btn_toggle = InlineKeyboardButton(bot_status_label, callback_data="admin_toggle_bot")
        btn_msguser = InlineKeyboardButton("\u2709\uFE0F Message User", callback_data="admin_msguser_prompt")
        btn_bannedlist = InlineKeyboardButton("\U0001F4CB Banned List", callback_data="admin_banned_list")

        markup.add(btn_ban, btn_unban)
        markup.add(btn_add_bal, btn_cut_bal)
        markup.add(btn_stats, btn_broadcast)
        markup.add(btn_msguser, btn_bannedlist)
        markup.add(btn_toggle)
        markup.add(btn_startall)
        return markup

    @bot.message_handler(commands=['admin'])
    def handle_admin_panel(message):
        if message.from_user.id not in ADMIN_CHAT_IDS:
            bot.reply_to(message, "❌ আপনি এই বটের অ্যাডমিন নন।")
            return

        bot.send_message(
            message.chat.id, 
            "<b>⚙️ অ্যাডমিন কন্ট্রোল প্যানেল</b>\n\nনিচের যেকোনো বাটনে ক্লিক করে সরাসরি কাজ সম্পন্ন করুন:", 
            parse_mode="HTML", 
            reply_markup=build_admin_panel_markup()
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
    def handle_admin_callbacks(call):
        if call.from_user.id not in ADMIN_CHAT_IDS:
            bot.answer_callback_query(call.id, "অ্যাক্সেস নেই!", show_alert=True)
            return

        if call.data == "admin_ban_prompt":
            msg = bot.send_message(
                call.message.chat.id, 
                "🚫 <b>যাকে ব্যান করতে চান তার USER ID লিখে এই মেসেজে রিপ্লাই দিন:</b>", 
                parse_mode="HTML", 
                reply_markup=ForceReply(selective=True)
            )
            bot.register_next_step_handler(msg, process_ban_input)
        
        elif call.data == "admin_unban_prompt":
            msg = bot.send_message(
                call.message.chat.id, 
                "✅ <b>যাকে আনব্যান করতে চান তার USER ID লিখে এই মেসেজে রিপ্লাই দিন:</b>", 
                parse_mode="HTML", 
                reply_markup=ForceReply(selective=True)
            )
            bot.register_next_step_handler(msg, process_unban_input)

        elif call.data == "admin_addbal_prompt":
            msg = bot.send_message(
                call.message.chat.id, 
                "➕ <b>USER_ID এবং AMOUNT স্পেস দিয়ে লিখে এই মেসেজে রিপ্লাই দিন:</b>\n(যেমন: <code>8530140256 50</code>)", 
                parse_mode="HTML", 
                reply_markup=ForceReply(selective=True)
            )
            bot.register_next_step_handler(msg, process_addbal_input)

        elif call.data == "admin_cutbal_prompt":
            msg = bot.send_message(
                call.message.chat.id, 
                "➖ <b>USER_ID এবং AMOUNT স্পেস দিয়ে লিখে এই মেসেজে রিপ্লাই দিন:</b>\n(যেমন: <code>8530140256 20</code>)", 
                parse_mode="HTML", 
                reply_markup=ForceReply(selective=True)
            )
            bot.register_next_step_handler(msg, process_cutbal_input)
            
        elif call.data == "admin_stats":
            if users_collection is not None:
                total_db_users = users_collection.count_documents({})
                total_banned = users_collection.count_documents({"banned": True})
                active_cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
                # "Active" = opened the app in the last 24 hours (last_active is
                # stamped by /get-user-data on every app load) and not banned.
                total_active = users_collection.count_documents({
                    "last_active": {"$gte": active_cutoff},
                    "banned": {"$ne": True}
                })
            else:
                total_db_users = total_banned = total_active = 0

            msg = f"<b>\U0001F4CA ইউজার স্ট্যাটিস্টিক্স:</b>\n\n"
            msg += f"\U0001F464 মোট রেজিস্টার্ড ইউজার: {total_db_users}\n"
            msg += f"\U0001F7E2 বর্তমানে একটিভ (২৪ ঘন্টায়): {total_active}\n"
            msg += f"\U0001F6AB মোট ব্যানড ইউজার: {total_banned}"
            
            bot.send_message(call.message.chat.id, msg, parse_mode="HTML")
            
        elif call.data == "admin_broadcast_prompt":
            msg = bot.send_message(
                call.message.chat.id, 
                "📢 <b>সকল ইউজারের কাছে যে মেসেজটি পাঠাতে চান তা লিখে রিপ্লাই দিন:</b>", 
                parse_mode="HTML", 
                reply_markup=ForceReply(selective=True)
            )
            bot.register_next_step_handler(msg, process_broadcast_input)

        elif call.data == "admin_msguser_prompt":
            msg = bot.send_message(
                call.message.chat.id,
                "\u2709\uFE0F <b>যাকে মেসেজ পাঠাতে চান তার USER ID লিখে এই মেসেজে রিপ্লাই দিন:</b>",
                parse_mode="HTML",
                reply_markup=ForceReply(selective=True)
            )
            bot.register_next_step_handler(msg, process_msguser_id_input)

        elif call.data == "admin_banned_list":
            if users_collection is None:
                bot.send_message(call.message.chat.id, "⚠️ ডাটাবেস সংযুক্ত নেই।")
            else:
                banned_docs = list(users_collection.find({"banned": True}, {"user_id": 1, "first_name": 1, "username": 1}).limit(150))
                if not banned_docs:
                    bot.send_message(call.message.chat.id, "\u2705 বর্তমানে কোনো ইউজার ব্যানড নেই।")
                else:
                    lines = [f"<b>\U0001F4CB ব্যানড ইউজার তালিকা ({len(banned_docs)} জন):</b>\n"]
                    for d in banned_docs:
                        uid = d.get("user_id", "?")
                        name = d.get("first_name", "N/A")
                        uname = d.get("username", "N/A")
                        lines.append(f"\u2022 <code>{uid}</code> — {name} (@{uname})")
                    text = "\n".join(lines)
                    if len(text) > 3900:
                        text = text[:3900] + "\n... (আরও আছে)"
                    bot.send_message(call.message.chat.id, text, parse_mode="HTML")

        elif call.data == "admin_toggle_bot":
            new_state = not is_bot_active()
            set_bot_active(new_state)
            status_text = "\U0001F7E2 চালু (ON)" if new_state else "\U0001F534 বন্ধ (OFF)"
            bot.send_message(call.message.chat.id, f"\u2699\uFE0F বট এখন: <b>{status_text}</b>", parse_mode="HTML")
            try:
                bot.edit_message_reply_markup(
                    chat_id=call.message.chat.id, message_id=call.message.message_id,
                    reply_markup=build_admin_panel_markup()
                )
            except Exception:
                pass

        elif call.data == "admin_startall_confirm":
            confirm_markup = InlineKeyboardMarkup()
            confirm_markup.add(
                InlineKeyboardButton("\u2705 হ্যাঁ, সবাইকে পাঠান", callback_data="admin_startall_go"),
                InlineKeyboardButton("\u274C বাতিল", callback_data="admin_startall_cancel")
            )
            total_db_users = users_collection.count_documents({}) if users_collection is not None else 0
            bot.send_message(
                call.message.chat.id,
                f"\u26A0\uFE0F আপনি কি নিশ্চিত? এতে <b>{total_db_users}</b> জন ইউজারের কাছে বট রিস্টার্ট মেসেজ যাবে।",
                parse_mode="HTML",
                reply_markup=confirm_markup
            )

        elif call.data == "admin_startall_cancel":
            bot.edit_message_text("\u274C বাতিল করা হয়েছে।", chat_id=call.message.chat.id, message_id=call.message.message_id)

        elif call.data == "admin_startall_go":
            if users_collection is None:
                bot.send_message(call.message.chat.id, "⚠️ ডাটাবেস সংযুক্ত নেই।")
            else:
                all_users = list(users_collection.find({}, {"user_id": 1}))
                status_msg = bot.send_message(call.message.chat.id, "\u23F3 সকল ইউজারের বট রিস্টার্ট করা হচ্ছে...")
                success_count = 0
                restart_markup = InlineKeyboardMarkup()
                restart_markup.add(InlineKeyboardButton("\U0001F680 Open App \U0001F680", web_app=WebAppInfo(url=RENDER_EXTERNAL_URL)))
                restart_text = "\U0001F504 <b>বট রিস্টার্ট করা হয়েছে!</b>\n\nআমাদের অ্যাপে ঢুকতে নিচে থাকা Open App বাটনে চাপ দিন।"
                for u in all_users:
                    uid = u.get("user_id")
                    if uid:
                        try:
                            bot.send_message(uid, restart_text, parse_mode="HTML", reply_markup=restart_markup)
                            success_count += 1
                            time.sleep(0.05)
                        except Exception:
                            pass
                bot.edit_message_text(
                    f"\u2705 <b>রিস্টার্ট সম্পন্ন!</b>\n\nমোট <b>{success_count}</b> জন ইউজারের কাছে মেসেজ পৌঁছেছে।",
                    chat_id=call.message.chat.id, message_id=status_msg.message_id, parse_mode="HTML"
                )

        bot.answer_callback_query(call.id)

    def process_msguser_id_input(message):
        if message.from_user.id not in ADMIN_CHAT_IDS:
            return
        target_user_id = message.text.strip()
        if not is_valid_telegram_id(target_user_id):
            bot.reply_to(message, "\u274C এটি সঠিক Telegram User ID নয় (শুধু সংখ্যা হতে হবে)। আবার /admin থেকে চেষ্টা করুন।")
            return
        msg = bot.send_message(
            message.chat.id,
            f"\u2709\uFE0F <b>ইউজার {target_user_id} কে যে মেসেজ পাঠাতে চান তা লিখে রিপ্লাই দিন:</b>",
            parse_mode="HTML",
            reply_markup=ForceReply(selective=True)
        )
        bot.register_next_step_handler(msg, process_msguser_text_input, target_user_id)

    def process_msguser_text_input(message, target_user_id):
        if message.from_user.id not in ADMIN_CHAT_IDS:
            return
        text_to_send = message.text.strip() if message.text else ""
        if not text_to_send:
            bot.reply_to(message, "⚠️ খালি মেসেজ পাঠানো যাবে না।")
            return
        try:
            bot.send_message(target_user_id, f"\U0001F4E9 <b>অ্যাডমিন মেসেজ:</b>\n\n{text_to_send}", parse_mode="HTML")
            bot.reply_to(message, f"\u2705 ইউজার <code>{target_user_id}</code> কে মেসেজ পাঠানো হয়েছে।", parse_mode="HTML")
        except Exception as e:
            bot.reply_to(message, f"\u274C মেসেজ পাঠাতে ব্যর্থ হয়েছে (ইউজার হয়তো বটকে ব্লক করেছেন বা ভুল ID): {e}")

    def process_ban_input(message):
        if message.from_user.id not in ADMIN_CHAT_IDS:
            return
        target_user_id = message.text.strip()
        if not is_valid_telegram_id(target_user_id):
            bot.reply_to(message, "\u274C এটি সঠিক Telegram User ID নয় (শুধু সংখ্যা হতে হবে)।")
            return
        if users_collection is not None:
            users_collection.update_one({"user_id": target_user_id}, {"$set": {"banned": True}})
        bot.reply_to(message, f"🚫 <b>ইউজার ID: {target_user_id} ব্যান করা হয়েছে!</b>", parse_mode="HTML")

    def process_unban_input(message):
        if message.from_user.id not in ADMIN_CHAT_IDS:
            return
        target_user_id = message.text.strip()
        if not is_valid_telegram_id(target_user_id):
            bot.reply_to(message, "\u274C এটি সঠিক Telegram User ID নয় (শুধু সংখ্যা হতে হবে)।")
            return
        if users_collection is not None:
            users_collection.update_one({"user_id": target_user_id}, {"$set": {"banned": False}})
        bot.reply_to(message, f"✅ <b>ইউজার ID: {target_user_id} সফলভাবে আনব্যান করা হয়েছে!</b>", parse_mode="HTML")

    def process_addbal_input(message):
        if message.from_user.id not in ADMIN_CHAT_IDS:
            return
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "⚠️ <b>সঠিক নিয়ম:</b> USER_ID এবং AMOUNT স্পেস দিয়ে লিখুন।", parse_mode="HTML")
            return
        target_user_id = args[0].strip()
        if not is_valid_telegram_id(target_user_id):
            bot.reply_to(message, "\u274C এটি সঠিক Telegram User ID নয় (শুধু সংখ্যা হতে হবে)।")
            return
        try:
            amount = float(args[1].strip())
        except ValueError:
            bot.reply_to(message, "❌ টাকার পরিমাণ সংখ্যায় লিখুন।")
            return

        if users_collection is not None:
            users_collection.update_one({"user_id": target_user_id}, {"$inc": {"balance": amount}}, upsert=True)
            bot.reply_to(message, f"💰 <b>ইউজার ID {target_user_id} এর অ্যাকাউন্টে ৳{amount:.2f} যোগ করা হয়েছে!</b>", parse_mode="HTML")
            try:
                bot.send_message(target_user_id, f"🎉 অ্যাডমিন আপনার ওয়ালেটে <b>৳{amount:.2f}</b> যুক্ত করেছেন!", parse_mode="HTML")
            except Exception:
                pass

    def process_cutbal_input(message):
        if message.from_user.id not in ADMIN_CHAT_IDS:
            return
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "⚠️ <b>সঠিক নিয়ম:</b> USER_ID এবং AMOUNT স্পেস দিয়ে লিখুন।", parse_mode="HTML")
            return
        target_user_id = args[0].strip()
        if not is_valid_telegram_id(target_user_id):
            bot.reply_to(message, "\u274C এটি সঠিক Telegram User ID নয় (শুধু সংখ্যা হতে হবে)।")
            return
        try:
            amount = float(args[1].strip())
        except ValueError:
            bot.reply_to(message, "❌ টাকার পরিমাণ সংখ্যায় লিখুন।")
            return

        if users_collection is not None:
            users_collection.update_one({"user_id": target_user_id}, {"$inc": {"balance": -amount}}, upsert=True)
            bot.reply_to(message, f"✂️ <b>ইউজার ID {target_user_id} এর অ্যাকাউন্ট থেকে ৳{amount:.2f} কেটে নেওয়া হয়েছে!</b>", parse_mode="HTML")
            try:
                bot.send_message(target_user_id, f"⚠️ অ্যাডমিন আপনার ওয়ালেট থেকে <b>৳{amount:.2f}</b> কেটে নিয়েছেন।", parse_mode="HTML")
            except Exception:
                pass

    def process_broadcast_input(message):
        if message.from_user.id not in ADMIN_CHAT_IDS:
            return
        text_to_send = message.text.strip()
        if not text_to_send:
            bot.reply_to(message, "⚠️ খালি মেসেজ পাঠানো যাবে না।")
            return
        
        if users_collection is not None:
            all_users = list(users_collection.find({}, {"user_id": 1}))
            success_count = 0
            
            status_msg = bot.reply_to(message, "⏳ ব্রডকাস্ট মেসেজ পাঠানো শুরু হয়েছে...")
            
            for user in all_users:
                u_id = user.get("user_id")
                if u_id:
                    try:
                        bot.send_message(u_id, f"📢 <b>অ্যাডমিন নোটিশ:</b>\n\n{text_to_send}", parse_mode="HTML")
                        success_count += 1
                        time.sleep(0.05)
                    except Exception:
                        pass
            
            bot.edit_message_text(f"✅ <b>ব্রডকাস্ট সম্পন্ন!</b>\n\nমোট <b>{success_count}</b> জন ইউজারের কাছে মেসেজ পৌঁছেছে।", chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="HTML")

    @bot.message_handler(commands=['unban'])
    def handle_unban_command(message):
        if message.from_user.id not in ADMIN_CHAT_IDS:
            return
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "⚠️ <b>নিয়ম:</b> <code>/unban USER_ID</code>", parse_mode="HTML")
            return
        target_user_id = args[1].strip()
        if not is_valid_telegram_id(target_user_id):
            bot.reply_to(message, "\u274C এটি সঠিক Telegram User ID নয় (শুধু সংখ্যা হতে হবে)।")
            return
        if users_collection is not None:
            users_collection.update_one({"user_id": target_user_id}, {"$set": {"banned": False}})
        bot.reply_to(message, f"✅ <b>ইউজার ID: {target_user_id} সফলভাবে আনব্যান করা হয়েছে!</b>", parse_mode="HTML")

    @bot.message_handler(commands=['ban'])
    def handle_ban_command(message):
        if message.from_user.id not in ADMIN_CHAT_IDS:
            return
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "⚠️ <b>নিয়ম:</b> <code>/ban USER_ID</code>", parse_mode="HTML")
            return
        target_user_id = args[1].strip()
        if not is_valid_telegram_id(target_user_id):
            bot.reply_to(message, "\u274C এটি সঠিক Telegram User ID নয় (শুধু সংখ্যা হতে হবে)।")
            return
        if users_collection is not None:
            users_collection.update_one({"user_id": target_user_id}, {"$set": {"banned": True}})
        bot.reply_to(message, f"🚫 <b>ইউজার ID: {target_user_id} ব্যান করা হয়েছে!</b>", parse_mode="HTML")

    @bot.message_handler(commands=['addbalance'])
    def handle_addbalance_command(message):
        if message.from_user.id not in ADMIN_CHAT_IDS:
            return
        args = message.text.split()
        if len(args) < 3:
            bot.reply_to(message, "⚠️ <b>নিয়ম:</b> <code>/addbalance USER_ID AMOUNT</code>", parse_mode="HTML")
            return
        target_user_id = args[1].strip()
        if not is_valid_telegram_id(target_user_id):
            bot.reply_to(message, "\u274C এটি সঠিক Telegram User ID নয় (শুধু সংখ্যা হতে হবে)।")
            return
        try:
            amount = float(args[2].strip())
        except ValueError:
            bot.reply_to(message, "❌ টাকার পরিমাণ সংখ্যায় লিখুন।")
            return

        if users_collection is not None:
            users_collection.update_one({"user_id": target_user_id}, {"$inc": {"balance": amount}}, upsert=True)
            bot.reply_to(message, f"💰 <b>ইউজার ID {target_user_id} এর অ্যাকাউন্টে ৳{amount:.2f} যোগ করা হয়েছে!</b>", parse_mode="HTML")
            try:
                bot.send_message(target_user_id, f"🎉 অ্যাডমিন আপনার ওয়ালেটে <b>৳{amount:.2f}</b> যুক্ত করেছেন!", parse_mode="HTML")
            except Exception:
                pass

    @bot.message_handler(commands=['cutbalance'])
    def handle_cutbalance_command(message):
        if message.from_user.id not in ADMIN_CHAT_IDS:
            return
        args = message.text.split()
        if len(args) < 3:
            bot.reply_to(message, "⚠️ <b>নিয়ম:</b> <code>/cutbalance USER_ID AMOUNT</code>", parse_mode="HTML")
            return
        target_user_id = args[1].strip()
        if not is_valid_telegram_id(target_user_id):
            bot.reply_to(message, "\u274C এটি সঠিক Telegram User ID নয় (শুধু সংখ্যা হতে হবে)।")
            return
        try:
            amount = float(args[2].strip())
        except ValueError:
            bot.reply_to(message, "❌ টাকার পরিমাণ সংখ্যায় লিখুন।")
            return

        if users_collection is not None:
            users_collection.update_one({"user_id": target_user_id}, {"$inc": {"balance": -amount}}, upsert=True)
            bot.reply_to(message, f"✂️ <b>ইউজার ID {target_user_id} এর অ্যাকাউন্ট থেকে ৳{amount:.2f} কেটে নেওয়া হয়েছে!</b>", parse_mode="HTML")
            try:
                bot.send_message(target_user_id, f"⚠️ অ্যাডমিন আপনার ওয়ালেট থেকে <b>৳{amount:.2f}</b> কেটে নিয়েছেন।", parse_mode="HTML")
            except Exception:
                pass

    @bot.message_handler(commands=['broadcast'])
    def handle_broadcast_command(message):
        if message.from_user.id not in ADMIN_CHAT_IDS:
            return
        text_to_send = message.text.replace("/broadcast", "").strip()
        if not text_to_send:
            bot.reply_to(message, "⚠️ <b>নিয়ম:</b> <code>/broadcast আপনার মেসেজ</code>", parse_mode="HTML")
            return
        if users_collection is not None:
            all_users = list(users_collection.find({}, {"user_id": 1}))
            success_count = 0
            status_msg = bot.reply_to(message, "⏳ ব্রডকাস্ট মেসেজ পাঠানো শুরু হয়েছে...")
            for user in all_users:
                u_id = user.get("user_id")
                if u_id:
                    try:
                        bot.send_message(u_id, f"📢 <b>অ্যাডমিন নোটিশ:</b>\n\n{text_to_send}", parse_mode="HTML")
                        success_count += 1
                        time.sleep(0.05)
                    except Exception:
                        pass
            bot.edit_message_text(f"✅ <b>ব্রডকাস্ট সম্পন্ন!</b>\n\nমোট <b>{success_count}</b> জন ইউজারের কাছে মেসেজ পৌঁছেছে।", chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="HTML")

def run_bot():
    if not bot:
        return
    while True:
        try:
            bot.remove_webhook()
            bot.infinity_polling(skip_pending=True, timeout=60)
        except Exception as e:
            print(f"Bot polling restart error: {e}")
            time.sleep(5)

# -------- FLASK ROUTES --------
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get-bot-info', methods=['GET'])
def get_bot_info():
    try:
        bot_username = bot.get_me().username if bot else ""
        return jsonify({"status": "success", "username": bot_username}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get-user-data', methods=['GET'])
def get_user_data():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"status": "error", "message": "User ID required"}), 400

    if is_user_banned(user_id):
        return jsonify({"status": "banned"}), 200

    try:
        if not check_user_joined_channels(user_id):
            return jsonify({"status": "not_joined", "message": "আপনি সকল চ্যানেলে জয়েন নেই!"}), 200
    except Exception:
        pass

    if users_collection is not None:
        user_data = users_collection.find_one({"user_id": str(user_id)})
        if user_data:
            if user_data.get("banned", False):
                return jsonify({"status": "banned"}), 200

            # Stamped on every app load/foreground — powers the "active users"
            # count in the admin panel. Cheap indexed write, not read back here.
            users_collection.update_one(
                {"user_id": str(user_id)},
                {"$set": {"last_active": datetime.datetime.utcnow()}}
            )
            
            today_str = datetime.datetime.utcnow().strftime("%Y-%m-%d")
            if user_data.get("last_reset_date") != today_str:
                users_collection.update_one(
                    {"user_id": str(user_id)},
                    {"$set": {"monetag_count": 0, "adsterra_count": 0, "gigapub_count": 0, "last_reset_date": today_str}}
                )
                monetag_count = 0
                adsterra_count = 0
                gigapub_count = 0
            else:
                monetag_count = user_data.get("monetag_count", 0)
                adsterra_count = user_data.get("adsterra_count", 0)
                gigapub_count = user_data.get("gigapub_count", 0)

            user_withdraws = []
            if withdraws_collection is not None:
                docs = withdraws_collection.find({"user_id": str(user_id)})
                for d in docs:
                    user_withdraws.append({
                        "amount": d.get("amount"),
                        "account": d.get("account"),
                        "method": d.get("method"),
                        "status": d.get("status"),
                        "date": d.get("date")
                    })

            # ---------------------------------------------------------
            # AUTO CREDIT DAILY DEPOSIT PROFIT
            # ---------------------------------------------------------
            # Approved deposits start earning from the next UTC day.
            # Whenever the user opens/refreshes the app, credit one
            # unclaimed day of profit atomically into the main wallet.
            # This keeps the existing /claim-deposit-profit endpoint
            # available, while also making daily profit actually reach
            # the main balance without requiring a separate button.
            if deposits_collection is not None and users_collection is not None:
                today_profit_date = datetime.datetime.utcnow().strftime("%Y-%m-%d")
                auto_profit_total = 0.0

                active_profit_docs = deposits_collection.find({
                    "user_id": str(user_id),
                    "status": "active"
                })

                for dep in active_profit_docs:
                    last_profit_date = dep.get("last_profit_date")

                    # No profit on the approval day. Profit starts the next UTC day.
                    if not last_profit_date:
                        continue
                    if last_profit_date >= today_profit_date:
                        continue

                    dep_amount = float(dep.get("amount", 0) or 0)
                    dep_rate = float(dep.get("daily_rate", DEPOSIT_DAILY_RATE) or DEPOSIT_DAILY_RATE)
                    dep_profit = round(dep_amount * dep_rate, 2)

                    if dep_profit <= 0:
                        continue

                    # Only one request/process can credit this deposit for today.
                    credit_result = deposits_collection.update_one(
                        {
                            "_id": dep["_id"],
                            "status": "active",
                            "last_profit_date": last_profit_date
                        },
                        {
                            "$set": {"last_profit_date": today_profit_date},
                            "$inc": {"total_profit": dep_profit}
                        }
                    )

                    if credit_result.modified_count == 1:
                        auto_profit_total += dep_profit

                if auto_profit_total > 0:
                    users_collection.update_one(
                        {"user_id": str(user_id)},
                        {
                            "$inc": {
                                "balance": round(auto_profit_total, 2),
                                "total_earned": round(auto_profit_total, 2)
                            }
                        }
                    )

                    # Refresh user data after adding today's profit.
                    user_data = users_collection.find_one({"user_id": str(user_id)}) or user_data

            user_deposits = []
            active_deposit_total = 0.0
            active_daily_profit = 0.0
            if deposits_collection is not None:
                for d in deposits_collection.find({"user_id": str(user_id)}).sort("created_at", -1):
                    amount = float(d.get("amount", 0))
                    rate = float(d.get("daily_rate", DEPOSIT_DAILY_RATE))
                    if d.get("status") == "active":
                        active_deposit_total += amount
                        active_daily_profit += amount * rate
                    user_deposits.append({
                        "id": str(d.get("_id")),
                        "amount": amount,
                        "method": d.get("method", ""),
                        "transaction_id": d.get("transaction_id", ""),
                        "status": d.get("status", "pending"),
                        "daily_profit": round(amount * rate, 2),
                        "total_profit": round(float(d.get("total_profit", 0)), 2),
                        "created_at": d.get("date", ""),
                        "last_profit_date": d.get("last_profit_date", "")
                    })

            return jsonify({
                "status": "success",
                "balance": float(user_data.get("balance", 0.00)),
                "total_refers": int(user_data.get("total_refers", 0)),
                "total_earned": float(user_data.get("total_earned", 0.00)),
                "total_tasks_completed": int(user_data.get("total_tasks_completed", 0)),
                "first_name": user_data.get("first_name", "User"),
                "monetag_count": monetag_count,
                "adsterra_count": adsterra_count,
                "gigapub_count": gigapub_count,
                "completed_channel_tasks": user_data.get("completed_channel_tasks", []),
                "withdraws": user_withdraws,
                "deposits": user_deposits,
                "active_deposit_total": round(active_deposit_total, 2),
                "active_daily_profit": round(active_daily_profit, 2)
            }), 200

    return jsonify({"status": "success", "balance": 0.00, "total_refers": 0, "total_earned": 0.00, "total_tasks_completed": 0, "first_name": "User", "monetag_count": 0, "adsterra_count": 0, "gigapub_count": 0, "completed_channel_tasks": [], "withdraws": [], "deposits": [], "active_deposit_total": 0.0, "active_daily_profit": 0.0}), 200

@app.route('/verify-channel-task', methods=['POST'])
def verify_channel_task():
    data = request.json or {}
    user_id = data.get('user_id')
    channel = data.get('channel')
    reward = float(data.get('reward', 0.50))

    if not user_id or not channel:
        return jsonify({"status": "error", "message": "Invalid parameters"}), 400

    if is_user_banned(user_id):
        return jsonify({"status": "banned"}), 200

    if users_collection is not None:
        user = users_collection.find_one({"user_id": str(user_id)})
        completed_tasks = user.get("completed_channel_tasks", []) if user else []

        if channel in completed_tasks:
            return jsonify({"status": "already_completed", "message": "আপনি এই টাস্কটি আগেই সম্পূর্ণ করেছেন!"}), 200

        if not channel.startswith('bot_'):
            try:
                member = bot.get_chat_member(channel, int(user_id)) if bot else None
                if member and member.status in ['left', 'kicked']:
                    return jsonify({"status": "not_joined", "message": "আপনি এখনো চ্যানেলে জয়েন করেননি!"}), 200
            except Exception as e:
                print(f"Task verification error: {e}")
                return jsonify({"status": "error", "message": "ভেরিফিকেশনে সমস্যা হয়েছে!"}), 500

        users_collection.update_one(
            {"user_id": str(user_id)},
            {
                "$inc": {"balance": reward, "total_earned": reward, "total_tasks_completed": 1},
                "$push": {"completed_channel_tasks": channel}
            },
            upsert=True
        )
        return jsonify({"status": "success", "message": f"🎉 সফল হয়েছে! ৳{reward:.2f} ব্যালেন্সে যোগ করা হয়েছে।"}), 200

    return jsonify({"status": "error", "message": "Database connection error"}), 500

@app.route('/verify-ad-task', methods=['POST'])
def verify_ad_task():
    data = request.json or {}
    user_id = str(data.get('user_id'))
    task_type = str(data.get('task_type'))

    if not user_id or task_type not in ['monetag', 'adsterra', 'gigapub']:
        return jsonify({"status": "error", "message": "Invalid task parameters"}), 400

    if is_user_banned(user_id):
        return jsonify({"status": "banned"}), 200

    if users_collection is None:
        return jsonify({"status": "error", "message": "Database offline"}), 500

    user_data = users_collection.find_one({"user_id": user_id})
    if not user_data:
        return jsonify({"status": "error", "message": "User not found"}), 404

    today_str = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    if user_data.get("last_reset_date") != today_str:
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"monetag_count": 0, "adsterra_count": 0, "gigapub_count": 0, "last_reset_date": today_str}}
        )
        monetag_count = 0
        adsterra_count = 0
        gigapub_count = 0
    else:
        monetag_count = user_data.get("monetag_count", 0)
        adsterra_count = user_data.get("adsterra_count", 0)
        gigapub_count = user_data.get("gigapub_count", 0)

    reward = 0.05

    if task_type == 'gigapub':
        gigapub_reward = 0.05
        now = datetime.datetime.utcnow()
        first_view_at = user_data.get("gigapub_first_view_at")

        if first_view_at and (now - first_view_at) < datetime.timedelta(hours=24):
            if gigapub_count >= 20:
                remaining = datetime.timedelta(hours=24) - (now - first_view_at)
                hours_left = int(remaining.total_seconds() // 3600)
                mins_left = int((remaining.total_seconds() % 3600) // 60)
                return jsonify({
                    "status": "limit_reached",
                    "message": f"আজকের Gigapub টাস্ক লিমিট শেষ! আরও {hours_left} ঘন্টা {mins_left} মিনিট পর আবার দেখতে পারবেন।"
                }), 400
            update_fields = {"$inc": {"balance": gigapub_reward, "gigapub_count": 1, "total_earned": gigapub_reward, "total_tasks_completed": 1}}
        else:
            update_fields = {
                "$inc": {"balance": gigapub_reward, "total_earned": gigapub_reward, "total_tasks_completed": 1},
                "$set": {"gigapub_count": 1, "gigapub_first_view_at": now}
            }
            gigapub_count = 0

        users_collection.update_one({"user_id": user_id}, update_fields)
        return jsonify({"status": "success", "reward": gigapub_reward, "new_count": gigapub_count + 1}), 200

    if task_type == 'monetag':
        if monetag_count >= 20:
            return jsonify({"status": "limit_reached", "message": "আজকের Monetag টাস্ক লিমিট শেষ!"}), 400
        
        users_collection.update_one(
            {"user_id": user_id},
            {"$inc": {"balance": reward, "monetag_count": 1, "total_earned": reward, "total_tasks_completed": 1}}
        )
        return jsonify({"status": "success", "reward": reward, "new_count": monetag_count + 1}), 200

    elif task_type == 'adsterra':
        if adsterra_count >= 20:
            return jsonify({"status": "limit_reached", "message": "আজকের Adsterra টাস্ক লিমিট শেষ!"}), 400
        
        users_collection.update_one(
            {"user_id": user_id},
            {"$inc": {"balance": reward, "adsterra_count": 1, "total_earned": reward, "total_tasks_completed": 1}}
        )
        return jsonify({"status": "success", "reward": reward, "new_count": adsterra_count + 1}), 200

@app.route('/request-deposit', methods=['POST'])
def request_deposit():
    data = request.json or {}
    user_id = str(data.get('user_id', '')).strip()
    amount = float(data.get('amount', 0) or 0)
    method = str(data.get('method', 'bKash')).strip()
    transaction_id = str(data.get('transaction_id', '')).strip()

    allowed_amounts = DEPOSIT_ALLOWED_AMOUNTS
    allowed_methods = {'bKash', 'Binance'}
    usdt_amount = data.get('usdt_amount')
    if usdt_amount not in (None, ''):
        try:
            usdt_amount = float(usdt_amount)
        except (TypeError, ValueError):
            usdt_amount = None

    if not user_id or amount not in allowed_amounts or method not in allowed_methods or len(transaction_id) < 4:
        return jsonify({"status": "error", "message": "ডিপোজিটের তথ্য সঠিকভাবে দিন।"}), 400

    expected_usdt = round(amount / USDT_BDT_RATE, 6) if method == 'Binance' else None
    if method == 'Binance' and (usdt_amount is None or abs(usdt_amount - expected_usdt) > 0.00001):
        return jsonify({"status": "error", "message": f"এই প্যাকেজের জন্য {expected_usdt:.2f} USDT প্রয়োজন।"}), 400

    if is_user_banned(user_id):
        return jsonify({"status": "banned"}), 200

    if users_collection is None or deposits_collection is None:
        return jsonify({"status": "error", "message": "Database Connection Error"}), 500

    user = users_collection.find_one({"user_id": user_id})
    if not user:
        return jsonify({"status": "error", "message": "ইউজার পাওয়া যায়নি।"}), 404

    # Same transaction ID cannot be submitted twice.
    if deposits_collection.find_one({"transaction_id": transaction_id}):
        return jsonify({"status": "error", "message": "এই Transaction ID আগে ব্যবহার করা হয়েছে।"}), 400

    now = datetime.datetime.utcnow()
    doc = {
        "user_id": user_id,
        "amount": amount,
        "method": method,
        "transaction_id": transaction_id,
        "payment_destination": BKASH_MERCHANT if method == 'bKash' else BINANCE_USDT_ADDRESS,
        "network": "BEP20" if method == 'Binance' else None,
        "usdt_amount": expected_usdt,
        "usdt_bdt_rate": USDT_BDT_RATE if method == 'Binance' else None,
        "status": "pending",
        "daily_rate": DEPOSIT_DAILY_RATE,
        "daily_profit": round(amount * DEPOSIT_DAILY_RATE, 2),
        "total_profit": 0.0,
        "created_at": now,
        "date": now.strftime("%Y-%m-%d %H:%M"),
        "last_profit_date": None
    }
    res = deposits_collection.insert_one(doc)
    req_id = str(res.inserted_id)

    if method == 'Binance':
        payment_line = (
            f"🌐 <b>মেথড:</b> Binance USDT (BEP20)\n"
            f"💳 <b>Address:</b> <code>{BINANCE_USDT_ADDRESS}</code>\n"
            f"🪙 <b>USDT:</b> {expected_usdt:.6f} (1 USDT = ৳{USDT_BDT_RATE:.0f})\n"
        )
    else:
        payment_line = (
            f"🌐 <b>মেথড:</b> bKash Merchant\n"
            f"💳 <b>Merchant:</b> <code>{BKASH_MERCHANT}</code>\n"
        )

    admin_msg = (
        f"📥 <b>নতুন ডিপোজিট রিকোয়েস্ট!</b>\n\n"
        f"👤 <b>ইউজার:</b> {user.get('first_name', 'User')} (@{user.get('username', 'No Username')})\n"
        f"🆔 <b>ইউজার ID:</b> <code>{user_id}</code>\n"
        f"💵 <b>প্যাকেজ:</b> ৳{amount:.2f}\n"
        + payment_line +
        f"🧾 <b>TXID/Hash:</b> <code>{transaction_id}</code>\n"
        f"📈 <b>Daily হিসাব:</b> ৳{amount * DEPOSIT_DAILY_RATE:.2f}"
    )
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ Approve", callback_data=f"dep_acc_{req_id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"dep_rej_{req_id}")
    )
    if bot:
        for admin_id in ADMIN_CHAT_IDS:
            try:
                bot.send_message(admin_id, admin_msg, parse_mode="HTML", reply_markup=markup)
            except Exception as e:
                print(f"Deposit admin notification error: {e}")

    return jsonify({"status": "success", "message": "ডিপোজিট রিকোয়েস্ট পাঠানো হয়েছে। অ্যাডমিন যাচাই করে Approve করবেন।"}), 200


@app.route('/claim-deposit-profit', methods=['POST'])
def claim_deposit_profit():
    data = request.json or {}
    user_id = str(data.get('user_id', '')).strip()
    if not user_id:
        return jsonify({"status": "error", "message": "User ID required"}), 400
    if is_user_banned(user_id):
        return jsonify({"status": "banned"}), 200
    if users_collection is None or deposits_collection is None:
        return jsonify({"status": "error", "message": "Database Connection Error"}), 500

    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    active = list(deposits_collection.find({"user_id": user_id, "status": "active"}))
    if not active:
        return jsonify({"status": "error", "message": "কোনো Active Deposit নেই।"}), 400

    total_profit = 0.0
    claimed_ids = []
    for d in active:
        last_date = d.get("last_profit_date")
        if last_date == today:
            continue
        amount = float(d.get("amount", 0))
        rate = float(d.get("daily_rate", DEPOSIT_DAILY_RATE))
        profit = round(amount * rate, 2)
        if profit <= 0:
            continue
        # Atomic daily guard prevents double credit if two requests arrive together.
        result = deposits_collection.update_one(
            {"_id": d["_id"], "status": "active", "last_profit_date": {"$ne": today}},
            {"$set": {"last_profit_date": today}, "$inc": {"total_profit": profit}}
        )
        if result.modified_count == 1:
            total_profit += profit
            claimed_ids.append(str(d["_id"]))

    if total_profit <= 0:
        return jsonify({"status": "already_claimed", "message": "আজকের Deposit Profit ইতিমধ্যে নেওয়া হয়েছে।", "profit": 0}), 200

    users_collection.update_one(
        {"user_id": user_id},
        {"$inc": {"balance": total_profit, "total_earned": total_profit}}
    )
    return jsonify({
        "status": "success",
        "profit": round(total_profit, 2),
        "message": f"আজকের Deposit Profit ৳{total_profit:.2f} ওয়ালেটে যোগ হয়েছে।"
    }), 200


def reduce_active_deposit_principal(user_id, withdraw_amount):
    """Allocate a withdrawal against active deposit principal, oldest first.
    Returns a list of allocations so a rejected withdrawal can restore them.
    Any amount above active principal is treated as wallet/profit balance and
    does not reduce deposits further.
    """
    if deposits_collection is None or withdraw_amount <= 0:
        return []

    remaining = round(float(withdraw_amount), 2)
    allocations = []

    deposits = list(deposits_collection.find(
        {"user_id": str(user_id), "status": "active", "amount": {"$gt": 0}}
    ).sort("created_at", 1))

    for d in deposits:
        if remaining <= 0:
            break
        principal = round(float(d.get("amount", 0)), 2)
        if principal <= 0:
            continue

        take = min(principal, remaining)
        new_amount = round(principal - take, 2)

        result = deposits_collection.update_one(
            {"_id": d["_id"], "status": "active", "amount": principal},
            {"$set": {
                "amount": new_amount,
                "daily_profit": round(new_amount * float(d.get("daily_rate", DEPOSIT_DAILY_RATE)), 2)
            }}
        )

        if result.modified_count == 1:
            allocations.append({
                "deposit_id": str(d["_id"]),
                "amount": take
            })
            remaining = round(remaining - take, 2)

            if new_amount <= 0:
                deposits_collection.update_one(
                    {"_id": d["_id"], "status": "active", "amount": 0},
                    {"$set": {"status": "closed", "daily_profit": 0.0}}
                )

    return allocations


def restore_withdrawal_deposit_principal(allocations):
    """Restore principal reductions when an admin rejects a withdrawal."""
    if deposits_collection is None:
        return

    for item in allocations or []:
        try:
            dep_id = ObjectId(item["deposit_id"])
            restore_amount = round(float(item["amount"]), 2)
        except Exception:
            continue
        if restore_amount <= 0:
            continue

        dep = deposits_collection.find_one({"_id": dep_id})
        if not dep:
            continue

        current_amount = round(float(dep.get("amount", 0)), 2)
        new_amount = round(current_amount + restore_amount, 2)
        rate = float(dep.get("daily_rate", DEPOSIT_DAILY_RATE))

        deposits_collection.update_one(
            {"_id": dep_id},
            {"$set": {
                "amount": new_amount,
                "status": "active",
                "daily_profit": round(new_amount * rate, 2)
            }}
        )


@app.route('/request-withdraw', methods=['POST'])
def request_withdraw():
    data = request.json or {}
    user_id = str(data.get('user_id'))
    amount = float(data.get('amount', 0.0))
    account = str(data.get('account', ''))
    method = str(data.get('method', 'bKash'))

    min_amount = WITHDRAW_METHOD_MIN.get(method, 100)
    if not user_id or method not in WITHDRAW_METHOD_MIN or amount < min_amount or len(account) < 11:
        return jsonify({"status": "error", "message": f"সর্বনিম্ন উইথড্র পরিমাণ ৳{min_amount:.0f} অথবা তথ্য সঠিক নয়!"}), 400

    if is_user_banned(user_id):
        return jsonify({"status": "banned"}), 200

    if users_collection is not None and withdraws_collection is not None:
        user_data = users_collection.find_one({"user_id": user_id})
        if not user_data or float(user_data.get("balance", 0)) < amount:
            return jsonify({"status": "error", "message": "পর্যাপ্ত ব্যালেন্স নেই!"}), 400

        # Withdrawal consumes active deposit principal first (oldest deposit first).
        # This immediately reduces the principal used for future daily profit.
        principal_allocations = reduce_active_deposit_principal(user_id, amount)

        users_collection.update_one({"user_id": user_id}, {"$inc": {"balance": -amount}})

        req_doc = {
            "user_id": user_id,
            "amount": amount,
            "account": account,
            "method": method,
            "status": "pending",
            "principal_allocations": principal_allocations,
            "date": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        }
        res = withdraws_collection.insert_one(req_doc)
        req_id = str(res.inserted_id)

        admin_msg = (
            f"📥 <b>নতুন উইথড্র রিকোয়েস্ট!</b>\n\n"
            f"👤 <b>ইউজার:</b> {user_data.get('first_name', 'User')} (@{user_data.get('username', 'No Username')})\n"
            f"🆔 <b>ইউজার ID:</b> <code>{user_id}</code>\n"
            f"💵 <b>পরিমাণ:</b> ৳{amount:.2f}\n"
            f"🌐 <b>মেথড:</b> {method}\n"
            f"📱 <b>অ্যাকাউন্ট:</b> <code>{account}</code>"
        )

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("✅ Accept", callback_data=f"wd_acc_{req_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"wd_rej_{req_id}")
        )

        if bot:
            for admin_id in ADMIN_CHAT_IDS:
                try:
                    bot.send_message(admin_id, admin_msg, parse_mode="HTML", reply_markup=markup)
                except Exception as e:
                    print(f"Error notifying admin {admin_id}: {e}")

        return jsonify({"status": "success"}), 200
    return jsonify({"status": "error", "message": "Database Connection Error"}), 500

@app.route('/check-device', methods=['POST'])
def check_device():
    data = request.json or {}
    if not data:
        return jsonify({"status": "error", "message": "No data"}), 400

    device_id = str(data.get('device_id'))
    user_id = str(data.get('user_id'))
    first_name = data.get('first_name', 'Unknown')
    username = data.get('username', 'No Username')

    if is_user_banned(user_id):
        return jsonify({"status": "banned"}), 200

    if users_collection is not None:
        u_data = users_collection.find_one({"user_id": user_id})
        if u_data and u_data.get("banned", False):
            return jsonify({"status": "banned"}), 200

    if devices_collection is not None:
        device_doc = devices_collection.find_one({"device_id": device_id})

        if not device_doc:
            devices_collection.insert_one({"device_id": device_id, "users": [user_id]})
            return jsonify({"status": "success"}), 200
        else:
            associated_users = device_doc.get("users", [])
            
            if user_id not in associated_users:
                associated_users.append(user_id)
                devices_collection.update_one({"device_id": device_id}, {"$set": {"users": associated_users}})
                
                all_users_str = ", ".join(associated_users)
                alert_msg = (
                    f"<b>⚠️ মাল্টিপল অ্যাকাউন্ট সতর্কবার্তা!</b>\n\n"
                    f"<b>ডিভাইস ID:</b> <code>{device_id}</code>\n"
                    f"<b>নতুন ইউজার:</b> {first_name} (@{username})\n"
                    f"<b>ইউজার ID:</b> <code>{user_id}</code>\n"
                    f"<b>এই ডিভাইসের সকল ID:</b> <code>{all_users_str}</code>"
                )

                markup = InlineKeyboardMarkup()
                markup.row(
                    InlineKeyboardButton("🚫 Ban User", callback_data=f"ban_{user_id}"),
                    InlineKeyboardButton("✅ Unban User", callback_data=f"unban_{user_id}")
                )

                if bot:
                    for admin_id in ADMIN_CHAT_IDS:
                        try:
                            bot.send_message(admin_id, alert_msg, parse_mode="HTML", reply_markup=markup)
                        except Exception as e:
                            print(f"Error sending admin alert: {e}")

                return jsonify({"status": "multi_account_detected"}), 200

    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    if bot:
        threading.Thread(target=run_bot, daemon=True).start()
        threading.Thread(target=send_fake_withdraw_loop, daemon=True).start()
        threading.Thread(target=inactivity_reminder_loop, daemon=True).start()

    if RENDER_EXTERNAL_URL:
        threading.Thread(target=keep_alive, daemon=True).start()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
