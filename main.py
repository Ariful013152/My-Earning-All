import os
import time
import random
import datetime
import requests
import threading
import hashlib
import hmac
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

app = Flask(__name__, template_folder='.', static_folder='.')

# Restricted CORS configuration for production security
CORS(app, origins=[RENDER_EXTERNAL_URL, "https://web.telegram.org"])

bot = telebot.TeleBot(BOT_TOKEN) if BOT_TOKEN else None

db = None
users_collection = None
devices_collection = None
withdraws_collection = None
referrals_collection = None

if MONGO_URI:
    try:
        mongo_client = MongoClient(MONGO_URI)
        db = mongo_client.get_database()
        users_collection = db["users"]
        devices_collection = db["devices"]
        withdraws_collection = db["withdraws"]
        referrals_collection = db["referrals"]
        print("✅ MongoDB Connected Successfully")
    except Exception as e:
        print(f"❌ MongoDB Connection Error: {e}")


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
            bot.reply_to(message, "❌ <b>আপনি এই বট থেকে ব্যান হয়েছেন!</b>", parse_mode="HTML")
            return

        if not check_user_joined_channels(message.from_user.id):
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("📢 Channel 1", url="https://t.me/myearningall"))
            markup.add(InlineKeyboardButton("📢 Channel 2", url="https://t.me/allinoneg1"))
            markup.add(InlineKeyboardButton("📢 Channel 3", url="https://t.me/allinoneg2"))
            markup.add(InlineKeyboardButton("✅ Check Verification", callback_data="check_join"))
            
            join_msg = (
                "⚠️ <b>বট ব্যবহার করতে আপনাকে অবশ্যই আমাদের ৩টি চ্যানেলেই জয়েন করতে হবে!</b>\n\n"
                "নিচের ৩টি চ্যানেলে জয়েন করে <b>Check Verification</b> বাটনে ক্লিক করুন।"
            )
            bot.reply_to(message, join_msg, parse_mode="HTML", reply_markup=markup)
            return

        # নতুন ইউজার চেক করা এবং চ্যানেলে মেসেজ পাঠানো
        if users_collection is not None:
            existing_user = users_collection.find_one({"user_id": user_id})
            
            if not existing_user:
                try:
                    new_user_msg = (
                        f"🎉 <b>নতুন ইউজার জয়েন করেছেন!</b>\n\n"
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
                 "$setOnInsert": {"user_id": user_id, "balance": 0.0, "total_refers": 0, "monetag_count": 0, "adsterra_count": 0, "gigapub_count": 0, "gigapub_first_view_at": None, "last_reset_date": datetime.datetime.utcnow().strftime("%Y-%m-%d")}},
                upsert=True
            )

        args = message.text.split()
        referrer_id = args[1] if len(args) > 1 else None

        if referrer_id and str(referrer_id) != user_id:
            if users_collection is not None:
                try:
                    current_user = users_collection.find_one({"user_id": user_id})
                    if current_user and not current_user.get("referred_by"):
                        users_collection.update_one(
                            {"user_id": user_id},
                            {"$set": {"referred_by": str(referrer_id)}}
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

        welcome_text = "👋 <b>স্বাগতম!</b>\n\nআপনি সকল চ্যানেলে জয়েন করেছেন। আমাদের অ্যাপে ঢুকতে নিচে থাকা <b>Open App</b> বাটনে চাপ দিন।"
        
        markup = InlineKeyboardMarkup()
        web_app_btn = InlineKeyboardButton("🚀 Open App 🚀", web_app=WebAppInfo(url=RENDER_EXTERNAL_URL))
        markup.add(web_app_btn)

        bot.reply_to(message, welcome_text, parse_mode="HTML", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data == "check_join")
    def handle_check_join(call):
        user_id = call.from_user.id
        if check_user_joined_channels(user_id):
            bot.answer_callback_query(call.id, "✅ ভেরিফিকেশন সফল হয়েছে!")
            bot.delete_message(call.message.chat.id, call.message.message_id)
            send_welcome(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ আপনি এখনো সবগুলো চ্যানেলে জয়েন করেননি!", show_alert=True)

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
            bot.answer_callback_query(call.id, "উইথড্র রিকোয়েস্টটি পাওয়া যায়নি!", show_alert=True)
            return

        if req.get("status") != "pending":
            bot.answer_callback_query(call.id, "এই রিকোয়েস্টটি আগেই প্রসেস করা হয়েছে!", show_alert=True)
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
                bot.send_message(user_id, f"🎉 <b>আপনার ৳{amount:.2f} ({method}) উইথড্র রিকোয়েস্টটি অ্যাপ্রুভ হয়েছে এবং টাকা পাঠানো হয়েছে!</b>", parse_mode="HTML")
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
                bot.send_message(user_id, f"❌ <b>আপনার ৳{amount:.2f} ({method}) উইথড্র রিকোয়েস্টটি রিজেক্ট করা হয়েছে এবং ব্যালেন্স ওয়ালেটে ফেরত দেওয়া হয়েছে।</b>", parse_mode="HTML")
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
                    {"$inc": {"balance": 0.50, "total_refers": 1}},
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
            bot.edit_message_text(f"🚫 <b>ইউজার ID: {target_user_id} ব্যান করা হয়েছে!</b>", 
                                  chat_id=call.message.chat.id, 
                                  message_id=call.message.message_id, parse_mode="HTML")
        elif action == 'unban':
            if users_collection is not None:
                users_collection.update_one({"user_id": target_user_id}, {"$set": {"banned": False}})
            bot.answer_callback_query(call.id, f"User {target_user_id} Unbanned!")
            bot.edit_message_text(f"✅ <b>ইউজার ID: {target_user_id} আনব্যান করা হয়েছে!</b>", 
                                  chat_id=call.message.chat.id, 
                                  message_id=call.message.message_id, parse_mode="HTML")

    @bot.message_handler(commands=['admin'])
    def handle_admin_panel(message):
        if message.from_user.id not in ADMIN_CHAT_IDS:
            bot.reply_to(message, "❌ আপনি এই বটের অ্যাডমিন নন।")
            return

        markup = InlineKeyboardMarkup(row_width=2)
        btn_ban = InlineKeyboardButton("🚫 Ban User", callback_data="admin_ban_prompt")
        btn_unban = InlineKeyboardButton("✅ Unban User", callback_data="admin_unban_prompt")
        btn_add_bal = InlineKeyboardButton("➕ Add Balance", callback_data="admin_addbal_prompt")
        btn_cut_bal = InlineKeyboardButton("➖ Cut Balance", callback_data="admin_cutbal_prompt")
        btn_stats = InlineKeyboardButton("📊 Total Users", callback_data="admin_stats")
        btn_broadcast = InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast_prompt")
        
        markup.add(btn_ban, btn_unban, btn_add_bal, btn_cut_bal, btn_stats, btn_broadcast)
        
        bot.send_message(
            message.chat.id, 
            "<b>⚙️ অ্যাডমিন কন্ট্রোল প্যানেল</b>\n\nনিচের যেকোনো বাটনে ক্লিক করে সরাসরি কাজ সম্পন্ন করুন:", 
            parse_mode="HTML", 
            reply_markup=markup
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
                "➕ <b>USER_ID এবং AMOUNT স্পেস দিয়ে লিখে এই মেসেজে রিপ্লাই দিন:</b>\n(যেমন: <code>8530140256 50</code>)", 
                parse_mode="HTML", 
                reply_markup=ForceReply(selective=True)
            )
            bot.register_next_step_handler(msg, process_addbal_input)

        elif call.data == "admin_cutbal_prompt":
            msg = bot.send_message(
                call.message.chat.id, 
                "➖ <b>USER_ID এবং AMOUNT স্পেস দিয়ে লিখে এই মেসেজে রিপ্লাই দিন:</b>\n(যেমন: <code>8530140256 20</code>)", 
                parse_mode="HTML", 
                reply_markup=ForceReply(selective=True)
            )
            bot.register_next_step_handler(msg, process_cutbal_input)
            
        elif call.data == "admin_stats":
            total_db_users = users_collection.count_documents({}) if users_collection is not None else 0
            total_banned = users_collection.count_documents({"banned": True}) if users_collection is not None else 0
            
            msg = f"<b>📊 ইউজার স্ট্যাটিস্টিক্স:</b>\n\n"
            msg += f"👤 মোট রেজিস্টার্ড ইউজার: {total_db_users}\n"
            msg += f"🚫 মোট ব্যানড ইউজার: {total_banned}"
            
            bot.send_message(call.message.chat.id, msg, parse_mode="HTML")
            
        elif call.data == "admin_broadcast_prompt":
            msg = bot.send_message(
                call.message.chat.id, 
                "📢 <b>সকল ইউজারের কাছে যে মেসেজটি পাঠাতে চান তা লিখে রিপ্লাই দিন:</b>", 
                parse_mode="HTML", 
                reply_markup=ForceReply(selective=True)
            )
            bot.register_next_step_handler(msg, process_broadcast_input)
            
        bot.answer_callback_query(call.id)

    def process_ban_input(message):
        if message.from_user.id not in ADMIN_CHAT_IDS:
            return
        target_user_id = message.text.strip()
        if users_collection is not None:
            users_collection.update_one({"user_id": target_user_id}, {"$set": {"banned": True}})
        bot.reply_to(message, f"🚫 <b>ইউজার ID: {target_user_id} ব্যান করা হয়েছে!</b>", parse_mode="HTML")

    def process_unban_input(message):
        if message.from_user.id not in ADMIN_CHAT_IDS:
            return
        target_user_id = message.text.strip()
        if users_collection is not None:
            users_collection.update_one({"user_id": target_user_id}, {"$set": {"banned": False}})
        bot.reply_to(message, f"✅ <b>ইউজার ID: {target_user_id} সফলভাবে আনব্যান করা হয়েছে!</b>", parse_mode="HTML")

    def process_addbal_input(message):
        if message.from_user.id not in ADMIN_CHAT_IDS:
            return
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "⚠️ <b>সঠিক নিয়ম:</b> USER_ID এবং AMOUNT স্পেস দিয়ে লিখুন।", parse_mode="HTML")
            return
        target_user_id = args[0].strip()
        try:
            amount = float(args[1].strip())
        except ValueError:
            bot.reply_to(message, "❌ টাকার পরিমাণ সংখ্যায় লিখুন।")
            return

        if users_collection is not None:
            users_collection.update_one({"user_id": target_user_id}, {"$inc": {"balance": amount}}, upsert=True)
            bot.reply_to(message, f"💰 <b>ইউজার ID {target_user_id} এর অ্যাকাউন্টে ৳{amount:.2f} যোগ করা হয়েছে!</b>", parse_mode="HTML")
            try:
                bot.send_message(target_user_id, f"🎉 অ্যাডমিন আপনার ওয়ালেটে <b>৳{amount:.2f}</b> যুক্ত করেছেন!", parse_mode="HTML")
            except Exception:
                pass

    def process_cutbal_input(message):
        if message.from_user.id not in ADMIN_CHAT_IDS:
            return
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "⚠️ <b>সঠিক নিয়ম:</b> USER_ID এবং AMOUNT স্পেস দিয়ে লিখুন।", parse_mode="HTML")
            return
        target_user_id = args[0].strip()
        try:
            amount = float(args[1].strip())
        except ValueError:
            bot.reply_to(message, "❌ টাকার পরিমাণ সংখ্যায় লিখুন।")
            return

        if users_collection is not None:
            users_collection.update_one({"user_id": target_user_id}, {"$inc": {"balance": -amount}}, upsert=True)
            bot.reply_to(message, f"✂️ <b>ইউজার ID {target_user_id} এর অ্যাকাউন্ট থেকে ৳{amount:.2f} কেটে নেওয়া হয়েছে!</b>", parse_mode="HTML")
            try:
                bot.send_message(target_user_id, f"⚠️ অ্যাডমিন আপনার ওয়ালেট থেকে <b>৳{amount:.2f}</b> কেটে নিয়েছেন।", parse_mode="HTML")
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
            
            status_msg = bot.reply_to(message, "⏳ ব্রডকাস্ট মেসেজ পাঠানো শুরু হয়েছে...")
            
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
            bot.reply_to(message, "⚠️ <b>নিয়ম:</b> <code>/unban USER_ID</code>", parse_mode="HTML")
            return
        target_user_id = args[1].strip()
        if users_collection is not None:
            users_collection.update_one({"user_id": target_user_id}, {"$set": {"banned": False}})
        bot.reply_to(message, f"✅ <b>ইউজার ID: {target_user_id} সফলভাবে আনব্যান করা হয়েছে!</b>", parse_mode="HTML")

    @bot.message_handler(commands=['ban'])
    def handle_ban_command(message):
        if message.from_user.id not in ADMIN_CHAT_IDS:
            return
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "⚠️ <b>নিয়ম:</b> <code>/ban USER_ID</code>", parse_mode="HTML")
            return
        target_user_id = args[1].strip()
        if users_collection is not None:
            users_collection.update_one({"user_id": target_user_id}, {"$set": {"banned": True}})
        bot.reply_to(message, f"🚫 <b>ইউজার ID: {target_user_id} ব্যান করা হয়েছে!</b>", parse_mode="HTML")

    @bot.message_handler(commands=['addbalance'])
    def handle_addbalance_command(message):
        if message.from_user.id not in ADMIN_CHAT_IDS:
            return
        args = message.text.split()
        if len(args) < 3:
            bot.reply_to(message, "⚠️ <b>নিয়ম:</b> <code>/addbalance USER_ID AMOUNT</code>", parse_mode="HTML")
            return
        target_user_id = args[1].strip()
        try:
            amount = float(args[2].strip())
        except ValueError:
            bot.reply_to(message, "❌ টাকার পরিমাণ সংখ্যায় লিখুন।")
            return

        if users_collection is not None:
            users_collection.update_one({"user_id": target_user_id}, {"$inc": {"balance": amount}}, upsert=True)
            bot.reply_to(message, f"💰 <b>ইউজার ID {target_user_id} এর অ্যাকাউন্টে ৳{amount:.2f} যোগ করা হয়েছে!</b>", parse_mode="HTML")
            try:
                bot.send_message(target_user_id, f"🎉 অ্যাডমিন আপনার ওয়ালেটে <b>৳{amount:.2f}</b> যুক্ত করেছেন!", parse_mode="HTML")
            except Exception:
                pass

    @bot.message_handler(commands=['cutbalance'])
    def handle_cutbalance_command(message):
        if message.from_user.id not in ADMIN_CHAT_IDS:
            return
        args = message.text.split()
        if len(args) < 3:
            bot.reply_to(message, "⚠️ <b>নিয়ম:</b> <code>/cutbalance USER_ID AMOUNT</code>", parse_mode="HTML")
            return
        target_user_id = args[1].strip()
        try:
            amount = float(args[2].strip())
        except ValueError:
            bot.reply_to(message, "❌ টাকার পরিমাণ সংখ্যায় লিখুন।")
            return

        if users_collection is not None:
            users_collection.update_one({"user_id": target_user_id}, {"$inc": {"balance": -amount}}, upsert=True)
            bot.reply_to(message, f"✂️ <b>ইউজার ID {target_user_id} এর অ্যাকাউন্ট থেকে ৳{amount:.2f} কেটে নেওয়া হয়েছে!</b>", parse_mode="HTML")
            try:
                bot.send_message(target_user_id, f"⚠️ অ্যাডমিন আপনার ওয়ালেট থেকে <b>৳{amount:.2f}</b> কেটে নিয়েছেন।", parse_mode="HTML")
            except Exception:
                pass

    @bot.message_handler(commands=['broadcast'])
    def handle_broadcast_command(message):
        if message.from_user.id not in ADMIN_CHAT_IDS:
            return
        text_to_send = message.text.replace("/broadcast", "").strip()
        if not text_to_send:
            bot.reply_to(message, "⚠️ <b>নিয়ম:</b> <code>/broadcast আপনার মেসেজ</code>", parse_mode="HTML")
            return
        if users_collection is not None:
            all_users = list(users_collection.find({}, {"user_id": 1}))
            success_count = 0
            status_msg = bot.reply_to(message, "⏳ ব্রডকাস্ট মেসেজ পাঠানো শুরু হয়েছে...")
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
            return jsonify({"status": "not_joined", "message": "আপনি সকল চ্যানেলে জয়েন নেই!"}), 200
    except Exception:
        pass

    if users_collection is not None:
        user_data = users_collection.find_one({"user_id": str(user_id)})
        if user_data:
            if user_data.get("banned", False):
                return jsonify({"status": "banned"}), 200
            
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

            return jsonify({
                "status": "success",
                "balance": float(user_data.get("balance", 0.00)),
                "total_refers": int(user_data.get("total_refers", 0)),
                "first_name": user_data.get("first_name", "User"),
                "monetag_count": monetag_count,
                "adsterra_count": adsterra_count,
                "gigapub_count": gigapub_count,
                "completed_channel_tasks": user_data.get("completed_channel_tasks", []),
                "withdraws": user_withdraws
            }), 200

    return jsonify({"status": "success", "balance": 0.00, "total_refers": 0, "first_name": "User", "monetag_count": 0, "adsterra_count": 0, "gigapub_count": 0, "completed_channel_tasks": [], "withdraws": []}), 200

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
                    return jsonify({"status": "not_joined", "message": "আপনি এখনো চ্যানেলে জয়েন করেননি!"}), 200
            except Exception as e:
                print(f"Task verification error: {e}")
                return jsonify({"status": "error", "message": "ভেরিফিকেশনে সমস্যা হয়েছে!"}), 500

        users_collection.update_one(
            {"user_id": str(user_id)},
            {
                "$inc": {"balance": reward},
                "$push": {"completed_channel_tasks": channel}
            },
            upsert=True
        )
        return jsonify({"status": "success", "message": f"🎉 সফল হয়েছে! ৳{reward:.2f} ব্যালেন্সে যোগ করা হয়েছে।"}), 200

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

    reward = 0.10

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
            update_fields = {"$inc": {"balance": gigapub_reward, "gigapub_count": 1}}
        else:
            update_fields = {
                "$inc": {"balance": gigapub_reward},
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
            {"$inc": {"balance": reward, "monetag_count": 1}}
        )
        return jsonify({"status": "success", "reward": reward, "new_count": monetag_count + 1}), 200

    elif task_type == 'adsterra':
        if adsterra_count >= 20:
            return jsonify({"status": "limit_reached", "message": "আজকের Adsterra টাস্ক লিমিট শেষ!"}), 400
        
        users_collection.update_one(
            {"user_id": user_id},
            {"$inc": {"balance": reward, "adsterra_count": 1}}
        )
        return jsonify({"status": "success", "reward": reward, "new_count": adsterra_count + 1}), 200

@app.route('/request-withdraw', methods=['POST'])
def request_withdraw():
    data = request.json or {}
    user_id = str(data.get('user_id'))
    amount = float(data.get('amount', 0.0))
    account = str(data.get('account', ''))
    method = str(data.get('method', 'bKash'))

    if not user_id or amount < 100 or len(account) < 11:
        return jsonify({"status": "error", "message": "Invalid request parameters"}), 400

    if is_user_banned(user_id):
        return jsonify({"status": "banned"}), 200

    if users_collection is not None and withdraws_collection is not None:
        user_data = users_collection.find_one({"user_id": user_id})
        if not user_data or float(user_data.get("balance", 0)) < amount:
            return jsonify({"status": "error", "message": "পর্যাপ্ত ব্যালেন্স নেই!"}), 400

        users_collection.update_one({"user_id": user_id}, {"$inc": {"balance": -amount}})

        req_doc = {
            "user_id": user_id,
            "amount": amount,
            "account": account,
            "method": method,
            "status": "pending",
            "date": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        }
        res = withdraws_collection.insert_one(req_doc)
        req_id = str(res.inserted_id)

        admin_msg = (
            f"📥 <b>নতুন উইথড্র রিকোয়েস্ট!</b>\n\n"
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
    
    if RENDER_EXTERNAL_URL:
        threading.Thread(target=keep_alive, daemon=True).start()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
