import asyncio
import os
import json
import html
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.session.aiohttp import AiohttpSession
import pymongo
from pymongo import MongoClient

# === MongoDB ক্লাউড কানেকশন ===
MONGO_URI = "mongodb+srv://Admin:Task%26Earn@botrun.ciiuuca.mongodb.net/?appName=botRun"
client = MongoClient(MONGO_URI)
db = client["botRun"]
users_collection = db["users"]

API_TOKEN = '8798494739:AAHylK8iD8jRnD-HNirC3lUB6CaAJVpgb58'
ADMIN_CHAT_ID = -1003709372848

# 📢 চ্যানেল ১
CHANNEL_1_ID = -1003997407290
CHANNEL_1_LINK = "https://t.me/Taskk_Earn"

# 📢 চ্যানেল ২
CHANNEL_2_LINK = "https://t.me/aielevate_27"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# লোকাল ফাইলের পরিবর্তে সরাসরি MongoDB থেকে ডাটা লোড করার ফাংশন
def load_data():
    data = {}
    try:
        for doc in users_collection.find():
            uid = doc.get("user_id")
            if uid:
                user_info = {k: v for k, v in doc.items() if k != "_id"}
                data[str(uid)] = user_info
    except Exception as e:
        print("Database Load Error:", e)
    return data

# ডাটা সেভ বা আপডেট করার ফাংশন (সরাসরি MongoDB ক্লাউডে সেভ হবে)
def save_data(data):
    for uid, info in data.items():
        user_doc = info.copy()
        user_doc["user_id"] = str(uid)
        users_collection.update_one(
            {"user_id": str(uid)},
            {"$set": user_doc},
            upsert=True
        )

user_data = load_data()

used_facebooks = set()
for uid, info in user_data.items():
    if info.get("facebook"):
        used_facebooks.add(info["facebook"])

pending_rejects = {}

main_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎯 Earn Money"), KeyboardButton(text="💳 Withdraw")],
        [KeyboardButton(text="📊 Check Balance")]
    ],
    resize_keyboard=True
)

async def check_user_subscription(user_id: int) -> bool:
    try:
        # চ্যানেল ১ ভেরিফিকেশন
        m1 = await bot.get_chat_member(chat_id=CHANNEL_1_ID, user_id=user_id)
        c1_joined = m1.status in ["member", "creator", "administrator"]

        # চ্যানেল ২ ভেরিফিকেশন
        m2 = await bot.get_chat_member(chat_id=CHANNEL_2_USERNAME, user_id=user_id)
        c2_joined = m2.status in ["member", "creator", "administrator"]

        return c1_joined and c2_joined
    except Exception as e:
        print(f"Subscription Check Error: {e}")
    return False

async def send_join_request(event):
    join_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 চ্যানেল ১-এ জয়েন করুন", url=CHANNEL_1_LINK)],
            [InlineKeyboardButton(text="📢 চ্যানেল ২-এ জয়েন করুন", url=CHANNEL_2_LINK)],
            [InlineKeyboardButton(text="✅ জয়েন ভেরিফাই করুন", callback_data="check_join")]
        ]
    )
    warning_text = (
        "⚠️ <b>অত্যন্ত গুরুত্বপূর্ণ নোটিশ!</b> ⚠️\n\n"
        "বটটি ব্যবহার করতে এবং আপনার ইনকাম সচল রাখতে আমাদের <b>২টি অফিশিয়াল চ্যানেলেই</b> অবশ্যই জয়েন থাকতে হবে। চ্যানেল থেকে লিভ নিলে বট কাজ করবে না! ❌\n\n"
        "📢 <b>আমাদের চ্যানেল দুটি:</b>\n"
        f"১. {CHANNEL_1_LINK}\n"
        f"২. {CHANNEL_2_LINK}\n\n"
        "দুটি চ্যানেলে জয়েন করার পর নিচের <b>\"✅ জয়েন ভেরিফাই করুন\"</b> বাটনে ক্লিক করুন।"
    )
    if isinstance(event, types.Message):
        await event.reply(warning_text, reply_markup=join_keyboard, parse_mode="HTML")
    elif isinstance(event, types.CallbackQuery):
        await event.message.answer(warning_text, reply_markup=join_keyboard, parse_mode="HTML")

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    
    if not await check_user_subscription(user_id):
        await send_join_request(message)
        return

    args = message.text.split()
    referred_by = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            ref_id = int(args[1].split("_")[1])
            if ref_id != user_id:
                referred_by = ref_id
        except ValueError:
            pass

    if user_id not in user_data:
        user_data[user_id] = {
            "facebook": None,
            "balance": 0.00,
            "withdrawn": 0.00,
            "admin_added_bal": 0.00,
            "bkash": None,
            "nagad": None,
            "binance": None,
            "screenshots": [],
            "referred_by": referred_by,
            "referrals_count": 0,
            "is_approved": False,
            "is_banned": False,
            "name": message.from_user.full_name,
            "username": message.from_user.username or "NoUsername",
            "waiting_for": None
        }
        save_data()
    else:
        user_data[user_id]["name"] = message.from_user.full_name
        user_data[user_id]["username"] = message.from_user.username or "NoUsername"
        save_data()

    if user_data[user_id].get("is_banned", False):
        await message.reply("❌ আপনার অ্যাকাউন্টটি ব্যান করা হয়েছে!")
        return

    welcome_text = (
        "✨ <b>স্বাগতম! এক্সক্লুসিভ আর্নিং বটে আপনাকে স্বাগতম।</b> ✨\n\n"
        "🚀 ঘরে বসে সহজে টাস্ক কমপ্লিট করে এবং বন্ধুদের রেফার করে আনলিমিটেড ইনকাম করুন!\n\n"
        "👇 নিচ থেকে আপনার পছন্দমতো অপশন সিলেক্ট করুন:"
    )

    await message.reply(welcome_text, reply_markup=main_menu_keyboard, parse_mode="HTML")

@dp.callback_query(F.data == "check_join")
async def verify_user_join(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    if await check_user_subscription(user_id):
        await callback_query.answer("✅ ধন্যবাদ! আপনার জয়েন ভেরিফাই হয়েছে।", show_alert=True)
        try:
            await callback_query.message.delete()
        except Exception:
            pass
        await send_welcome(callback_query.message)
    else:
        await callback_query.answer("❌ আপনি এখনো ২টি চ্যানেলে জয়েন করেননি! দয়া করে জয়েন করুন।", show_alert=True)

@dp.message(F.text == "🎯 Earn Money")
async def earn_money(message: types.Message):
    user_id = message.from_user.id
    if not await check_user_subscription(user_id):
        await send_join_request(message)
        return

    if user_id in user_data and user_data[user_id].get("is_banned", False):
        await message.reply("❌ আপনার অ্যাকাউন্টটি ব্যান করা হয়েছে!")
        return

    if user_id not in user_data:
        user_data[user_id] = {"facebook": None, "balance": 0.00, "withdrawn": 0.00, "admin_added_bal": 0.00, "bkash": None, "nagad": None, "binance": None, "screenshots": [], "referred_by": None, "referrals_count": 0, "is_approved": False, "is_banned": False, "name": message.from_user.full_name, "username": message.from_user.username or "NoUsername", "waiting_for": None}
        save_data()

    if user_data[user_id]["is_approved"]:
        bot_info = await bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
        ref_msg = (
            "🎉 <b>আপনার টাস্ক ইতিমধ্যে সফলভাবে সম্পন্ন ও এপ্রুভ করা হয়েছে!</b>\n\n"
            "🔗 <b>আপনার রেফারেল লিংক:</b>\n"
            f"<code>{ref_link}</code>\n\n"
            "📌 প্রতি রেফারে আপনি পাবেন <b>৳৫.০০</b> করে!\n"
            "💳 সর্বনিম্ন উইথড্র করতে পারবেন <b>৳৩০.০০</b> টাকা।\n"
            "📌 <b>শর্ত:</b> রেফারকৃত ইউজারের টাস্ক কমপ্লিট এবং এপ্রুভ হতে হবে।"
        )
        await message.reply(ref_msg, parse_mode="HTML")
        return

    if user_data[user_id]["facebook"]:
        task_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📌 Task 1: Follow Page", url="https://facebook.com/unithingszone.bd")],
                [InlineKeyboardButton(text="❤️ Task 2: Like Reel", url="https://facebook.com/reel/1805022833955729")],
                [InlineKeyboardButton(text="🔍 Verify & Check Screenshots", callback_data="verify_tasks")]
            ]
        )
        msg = (
            "⚠️ <b>জরুরী সতর্কবার্তা:</b>\n"
            "ফেক স্ক্রিনশট দিলে অ্যাকাউন্ট স্থায়ীভাবে <b>Ban</b> করা হবে এবং সমস্ত ব্যালেন্স কেটে নেওয়া হবে।\n\n"
            "⚠️ <b>বিশেষ সতর্কীকরণ:</b> ফেক অ্যাকাউন্ট দিয়ে লাইক বা ফলো দিলে টাস্ক সাথে সাথে ক্যানসেল করা হবে, তাই অবশ্যই <b>রিয়েল আইডি</b> ব্যবহার করতে হবে!\n\n"
            "📋 Task ১ এবং ২ কমপ্লিট করে পরপর দুটি স্ক্রিনশট এখানে আপলোড করুন।"
        )
        await message.reply(msg, reply_markup=task_keyboard, parse_mode="HTML")
    else:
        user_data[user_id]["waiting_for"] = "facebook"
        save_data()
        text = (
            "📌 <b>ফেসবুক প্রোফাইল বাইন্ড করুন!</b>\n\n"
            "ইনকাম শুরু করতে আপনার ফেসবুক প্রোফাইল লিংক বা ইউজারনেম দিন:\n"
            "(উদাহরণ: <code>https://www.facebook.com/yourprofile</code>)\n\n"
            "👉 লিংকটি চ্যাটে টাইপ করে সেন্ড করুন:"
        )
        await message.reply(text, parse_mode="HTML")

@dp.message(F.photo)
async def handle_screenshot(message: types.Message):
    user_id = message.from_user.id
    if not await check_user_subscription(user_id):
        await send_join_request(message)
        return

    if user_id in user_data and user_data[user_id].get("is_banned", False):
        return

    if user_id not in user_data:
        user_data[user_id] = {"facebook": None, "balance": 0.00, "withdrawn": 0.00, "admin_added_bal": 0.00, "bkash": None, "nagad": None, "binance": None, "screenshots": [], "referred_by": None, "referrals_count": 0, "is_approved": False, "is_banned": False, "name": message.from_user.full_name, "username": message.from_user.username or "NoUsername", "waiting_for": None}

    photo_id = message.photo[-1].file_id
    user_data[user_id]["screenshots"].append(photo_id)
    save_data()
    
    await message.react([types.ReactionTypeEmoji(emoji="👍")])

@dp.callback_query(F.data == "verify_tasks")
async def verify_screenshots_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    if not await check_user_subscription(user_id):
        await send_join_request(callback_query)
        return

    user_name = html.escape(callback_query.from_user.full_name)
    
    if user_id not in user_data or len(user_data[user_id]["screenshots"]) < 2:
        await callback_query.answer("❌ সর্বনিম্ন ২টি স্ক্রিনশট আপলোড করতে হবে!", show_alert=True)
        return

    await callback_query.answer("ভেরিফিকেশনের জন্য পাঠানো হয়েছে!")
    
    checking_msg = "⏳ <b>আপনার স্ক্রিনশটগুলো আপলোড করা হয়েছে। আমরা ২৪ ঘণ্টার ভিতর চেক করে আপনার ইনকাম Active করে দিবো।</b>"
    await callback_query.message.answer(checking_msg, parse_mode="HTML")

    admin_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_{user_id}"),
                InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{user_id}")
            ]
        ]
    )
    
    fb_profile = html.escape(str(user_data[user_id].get("facebook", "N/A")))
    caption = f"🔔 <b>নতুন টাস্ক সাবমিশন!</b>\n👤 ইউজার: {user_name} (ID: <code>{user_id}</code>)\n🔗 ফেসবুক: {fb_profile}\n📸 স্ক্রিনশট নিচে দেওয়া হলো:"
    
    await bot.send_message(chat_id=ADMIN_CHAT_ID, text=caption, parse_mode="HTML")
    for photo in user_data[user_id]["screenshots"][-2:]:
        await bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=photo)

    await bot.send_message(chat_id=ADMIN_CHAT_ID, text="👇 সিদ্ধান্ত নিন:", reply_markup=admin_keyboard)

@dp.callback_query(F.data.startswith('approve_'))
async def process_approval(callback_query: types.CallbackQuery):
    user_id = int(callback_query.data.split('_')[1])
    await callback_query.answer("সফলভাবে এপ্রুভ করা হয়েছে!")
    
    if user_id in user_data:
        user_data[user_id]["is_approved"] = True
        save_data()

    if callback_query.message.text:
        try:
            await callback_query.message.edit_text(callback_query.message.text + "\n\n✅ <b>[স্ট্যাটাস: এপ্রুভড]</b>", parse_mode="HTML")
        except Exception:
            pass
    
    msg1 = (
        "🎉 <b>অভিনন্দন! আপনার স্ক্রিনশটটি সফলভাবে সম্পন্ন হয়েছে।</b>\n\n"
        "আপনার জমা দেওয়া স্ক্রিনশটগুলো সফলভাবে ভেরিফাই করা হয়েছে। আপনার <b>রেফার ইনকাম লিংক</b> সফলভাবে চালু হয়েছে! ✅"
    )
    await bot.send_message(chat_id=user_id, text=msg1, parse_mode="HTML")

    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    msg2 = (
        "🔗 <b>আপনার রেফারেল লিংক:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        "📌 প্রতি রেফারে আপনি পাবেন <b>৳৫.০০</b> করে!\n"
        "💳 সর্বনিম্ন উইথড্র করতে পারবেন <b>৳৩০.০০</b> টাকা।"
    )
    await bot.send_message(chat_id=user_id, text=msg2, parse_mode="HTML")

    if user_id in user_data and user_data[user_id]["referred_by"]:
        referrer_id = user_data[user_id]["referred_by"]
        if referrer_id in user_data:
            user_data[referrer_id]["balance"] += 5.00
            user_data[referrer_id]["referrals_count"] += 1
            save_data()
            
            ref_user_name = html.escape(str(user_data[user_id].get("name", "User")))
            ref_success_msg = (
                f"🎉 <b>অভিনন্দন! রেফার সম্পন্ন।</b>\n\n"
                f"💰 আপনার একাউন্টে ৳৫.০০ ব্যালেন্স যোগ করা হয়েছে।\n"
                f"👤 <b>রেফারেড ইউজার:</b> {ref_user_name}"
            )
            await bot.send_message(chat_id=referrer_id, text=ref_success_msg, parse_mode="HTML")

@dp.callback_query(F.data.startswith('reject_'))
async def process_reject(callback_query: types.CallbackQuery):
    user_id = int(callback_query.data.split('_')[1])
    await callback_query.answer()
    
    msg = await callback_query.message.reply(
        f"✍️ <b>টাস্ক রিজেক্ট করার নোট/কারণ লিখুন:</b>\n"
        f"এই মেসেজের রিপ্লাইতে কারণটি লিখুন (ইউজার আইডি: <code>{user_id}</code>)।",
        parse_mode="HTML"
    )
    pending_rejects[msg.message_id] = {"user_id": user_id, "amount": 0.0, "type": "task", "main_msg": callback_query.message}

@dp.callback_query(F.data.startswith('wapprove_'))
async def process_withdraw_approval(callback_query: types.CallbackQuery):
    data_parts = callback_query.data.split('_')
    user_id = int(data_parts[1])
    amount = float(data_parts[2])
    
    if amount <= 99:
        final_payout = amount - 5.0
        fee_label = "-৳৫"
    else:
        final_payout = amount - (amount * 0.05)
        fee_label = "-৫%"

    await callback_query.answer("উইথড্র এপ্রুভ করা হয়েছে!")
    if callback_query.message.text:
        try:
            await callback_query.message.edit_text(callback_query.message.text + "\n\n✅ <b>[উইথড্র স্ট্যাটাস: পেইড/এপ্রুভড]</b>", parse_mode="HTML")
        except Exception:
            pass
            
    success_msg = (
        f"🎉 <b>আপনার উত্তোলন সফল হয়েছে!</b>\n\n"
        f"💰 অ্যামাউন্ট: ৳{amount:.2f}\n"
        f"💸 ফি বাবদ ({fee_label}): ৳{final_payout:.2f}\n"
        f"✅ আপনার পেমেন্ট সফলভাবে পাঠানো হয়েছে।"
    )
    await bot.send_message(chat_id=user_id, text=success_msg, parse_mode="HTML")

@dp.callback_query(F.data.startswith('wreject_'))
async def process_withdraw_reject(callback_query: types.CallbackQuery):
    data_parts = callback_query.data.split('_')
    user_id = int(data_parts[1])
    amount = float(data_parts[2])
    
    await callback_query.answer()
    
    msg = await callback_query.message.reply(
        f"✍️ <b>উইথড্র রিজেক্ট করার নোট/কারণ লিখুন:</b>\n"
        f"এই মেসেজের রিপ্লাইতে কারণটি লিখুন (ইউজার আইডি: <code>{user_id}</code>, অ্যামাউন্ট: ৳{amount})।",
        parse_mode="HTML"
    )
    pending_rejects[msg.message_id] = {"user_id": user_id, "amount": amount, "type": "withdraw", "main_msg": callback_query.message}

@dp.message(F.text == "📊 Check Balance")
async def check_balance(message: types.Message):
    user_id = message.from_user.id
    if not await check_user_subscription(user_id):
        await send_join_request(message)
        return

    if user_id in user_data and user_data[user_id].get("is_banned", False):
        await message.reply("❌ আপনার অ্যাকাউন্টটি ব্যান করা হয়েছে!")
        return

    if user_id not in user_data:
        user_data[user_id] = {"facebook": None, "balance": 0.00, "withdrawn": 0.00, "admin_added_bal": 0.00, "bkash": None, "nagad": None, "binance": None, "screenshots": [], "referred_by": None, "referrals_count": 0, "is_approved": False, "is_banned": False, "name": message.from_user.full_name, "username": message.from_user.username or "NoUsername", "waiting_for": None}
        save_data()
    
    bal = user_data[user_id]["balance"]
    withdrawn = user_data[user_id]["withdrawn"]
    refs = user_data[user_id]["referrals_count"]
    
    text = (
        f"📊 <b>অ্যাকাউন্ট ব্যালেন্স বিবরণী:</b>\n\n"
        f"💰 বর্তমান ব্যালেন্স: BDT {bal:.2f}\n"
        f"💸 মোট উত্তোলন: BDT {withdrawn:.2f}\n"
        f"👥 মোট রেফারেল: {refs}\n\n"
        f"✨ এক্সেলের মতো স্বয়ংক্রিয় হিসাব ব্যবস্থা।"
    )
    await message.reply(text, parse_mode="HTML")

@dp.message(F.text == "💳 Withdraw")
async def withdraw_menu(message: types.Message):
    user_id = message.from_user.id
    if not await check_user_subscription(user_id):
        await send_join_request(message)
        return

    if user_id in user_data and user_data[user_id].get("is_banned", False):
        await message.reply("❌ আপনার অ্যাকাউন্টটি ব্যান করা হয়েছে!")
        return

    if user_id not in user_data:
        user_data[user_id] = {"facebook": None, "balance": 0.00, "withdrawn": 0.00, "admin_added_bal": 0.00, "bkash": None, "nagad": None, "binance": None, "screenshots": [], "referred_by": None, "referrals_count": 0, "is_approved": False, "is_banned": False, "name": message.from_user.full_name, "username": message.from_user.username or "NoUsername", "waiting_for": None}
        save_data()

    withdraw_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📱 বিকাশ (Bkash)", callback_data="pay_bkash"),
                InlineKeyboardButton(text="📱 নগদ (Nagad)", callback_data="pay_nagad")
            ],
            [
                InlineKeyboardButton(text="🌐 বাইন্যান্স পে (Binance Pay)", callback_data="pay_binance")
            ]
        ]
    )
    text = "💳 <b>সর্বনিম্ন উত্তোলন ৩০ টাকা</b>\n\n👇 আপনার পেমেন্ট মেথড সিলেক্ট করুন:"
    await message.reply(text, reply_markup=withdraw_keyboard, parse_mode="HTML")

@dp.callback_query(F.data.startswith('pay_'))
async def select_payment_method(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    if not await check_user_subscription(user_id):
        await send_join_request(callback_query)
        return

    method = callback_query.data.split('_')[1]
    
    if user_id not in user_data:
        user_data[user_id] = {"facebook": None, "balance": 0.00, "withdrawn": 0.00, "admin_added_bal": 0.00, "bkash": None, "nagad": None, "binance": None, "screenshots": [], "referred_by": None, "referrals_count": 0, "is_approved": False, "is_banned": False, "name": callback_query.from_user.full_name, "username": callback_query.from_user.username or "NoUsername", "waiting_for": None}
        save_data()

    user_data[user_id]["temp_method"] = method
    bound_num = user_data[user_id].get(method)
    
    if bound_num:
        user_data[user_id]["waiting_for"] = f"amount_{method}"
        save_data()
        await callback_query.message.answer(f"✅ আপনার পূর্বে বাইন্ড করা অ্যাকাউন্ট ({method.upper()}): <code>{html.escape(str(bound_num))}</code> পাওয়া গেছে।\n\nকত টাকা উইথড্র করতে চান? অ্যামাউন্ট লিখে সেন্ড করুন (যেমন: <code>30</code>)", parse_mode="HTML")
    else:
        user_data[user_id]["waiting_for"] = f"bind_{method}"
        save_data()
        await callback_query.message.answer(f"📌 আপনি <b>{method.upper()}</b> সিলেক্ট করেছেন।\n\n👉 আপনার পেমেন্ট নম্বর বা বাইন্যান্স আইডি এই চ্যাটে টাইপ করে সেন্ড করুন:", parse_mode="HTML")
    
    await callback_query.answer()

@dp.message(F.chat.id == ADMIN_CHAT_ID)
async def group_admin_commands(message: types.Message):
    if not message.text:
        return
        
    text = message.text.strip()

    if message.reply_to_message and message.reply_to_message.message_id in pending_rejects:
        reject_info = pending_rejects.pop(message.reply_to_message.message_id)
        target_uid = reject_info["user_id"]
        amount = reject_info["amount"]
        reject_type = reject_info["type"]
        reason = html.escape(text)
        
        main_msg = reject_info.get("main_msg")

        if reject_type == "withdraw":
            if target_uid in user_data:
                user_data[target_uid]["balance"] += amount
                user_data[target_uid]["withdrawn"] -= amount
                save_data()
            
            if main_msg:
                try:
                    await main_msg.edit_text(main_msg.text + f"\n\n❌ <b>[উইথড্র স্ট্যাটাস: রিজেক্টেড]</b>\n📝 কারণ: {reason}", parse_mode="HTML")
                except Exception:
                    pass
            
            try:
                await bot.send_message(
                    chat_id=target_uid,
                    text=f"⚠️ <b>আপনার ৳{amount:.2f} টাকার উইথড্র রিকোয়েস্ট বাতিল করা হয়েছে!</b>\n\n📝 <b>কারণ:</b> {reason}\n💰 টাকা আপনার একাউন্ট ব্যালেন্সে ফেরত দেওয়া হয়েছে।",
                    parse_mode="HTML"
                )
            except Exception:
                pass
        else:
            if main_msg:
                try:
                    await main_msg.edit_text(main_msg.text + f"\n\n❌ <b>[টাস্ক স্ট্যাটাস: রিজেক্টেড]</b>\n📝 কারণ: {reason}", parse_mode="HTML")
                except Exception:
                    pass
                
            try:
                await bot.send_message(
                    chat_id=target_uid,
                    text=f"⚠️ <b>আপনার টাস্ক স্ক্রিনশট বাতিল করা হয়েছে!</b>\n\n📝 <b>কারণ:</b> {reason}\n📌 দয়া করে সঠিক নিয়মে আবার চেষ্টা করুন।",
                    parse_mode="HTML"
                )
            except Exception:
                pass

        try:
            await message.reply("✅ কাস্টম নোট/কারণ সহ রিজেক্ট সম্পন্ন হয়েছে!")
        except Exception:
            await message.answer("✅ কাস্টম নোট/কারণ সহ রিজেক্ট সম্পন্ন হয়েছে!")
        return

    if not text.startswith('/'):
        return

    parts = text.split(maxsplit=1)
    cmd = parts[0].lower()

    if cmd == "/notice":
        if len(parts) < 2:
            await message.reply("❌ নোটিশের লেখা দিন!\nউদাহরণ: `/notice আপনার নোটিশের টেক্সট`", parse_mode="HTML")
            return
        
        notice_text = html.escape(parts[1])
        success_count = 0
        fail_count = 0
        
        for uid in user_data.keys():
            try:
                await bot.send_message(
                    chat_id=int(uid),
                    text=f"📢 <b>অফিশিয়াল নোটিশ:</b>\n\n{notice_text}",
                    parse_mode="HTML"
                )
                success_count += 1
            except Exception:
                fail_count += 1
                
        await message.reply(f"✅ নোটিশ সফলভাবে ব্রডকাস্ট করা হয়েছে!\n👥 সফল: {success_count} জন\n⚠️ ব্যর্থ: {fail_count} জন", parse_mode="HTML")
        return

    target_uid = None
    if len(parts) > 1:
        target_input = parts[1].split()[0].strip()
        if target_input.startswith('@'):
            target_username = target_input.lstrip('@').lower()
            for uid, info in user_data.items():
                if info.get("username", "").lower() == target_username:
                    target_uid = uid
                    break
        elif target_input.isdigit():
            target_uid = int(target_input)

    if not target_uid and message.reply_to_message and message.reply_to_message.from_user:
        target_uid = message.reply_to_message.from_user.id

    if target_uid and target_uid not in user_data:
        user_data[target_uid] = {"facebook": None, "balance": 0.00, "withdrawn": 0.00, "admin_added_bal": 0.00, "bkash": None, "nagad": None, "binance": None, "screenshots": [], "referred_by": None, "referrals_count": 0, "is_approved": False, "is_banned": False, "name": "User", "username": "NoUsername", "waiting_for": None}
        save_data()

    if "balance" in cmd:
        if not target_uid:
            await message.reply("❌ সঠিক ইউজার আইডি/ইউজারনেম দিন!")
            return
        try:
            val = float(cmd.replace("/balance", ""))
            user_data[target_uid]["balance"] += val
            user_data[target_uid]["admin_added_bal"] += val
            save_data()
            await message.reply(f"✅ ব্যালেন্স আপডেট হয়েছে! বর্তমান ব্যালেন্স: ৳{user_data[target_uid]['balance']:.2f}", parse_mode="HTML")
        except Exception:
            await message.reply("❌ উদাহরণ: <code>/balance+20 @username</code> অথবা <code>/balance-10 123456</code>", parse_mode="HTML")

    elif "ref" in cmd:
        if not target_uid:
            await message.reply("❌ সঠিক ইউজার আইডি/ইউজারনেম দিন!")
            return
        try:
            val = int(cmd.replace("/ref", ""))
            user_data[target_uid]["referrals_count"] += val
            save_data()
            await message.reply(f"✅ রেফার সংখ্যা আপডেট হয়েছে! মোট রেফার: {user_data[target_uid]['referrals_count']}", parse_mode="HTML")
        except Exception:
            await message.reply("❌ উদাহরণ: <code>/ref+5 @username</code> অথবা <code>/ref-3 123456</code>", parse_mode="HTML")

    elif cmd == "/ban":
        if not target_uid:
            await message.reply("❌ সঠিক ইউজার আইডি/ইউজারনেম দিন!")
            return
        user_data[target_uid]["is_banned"] = True
        save_data()
        await message.reply(f"🚫 ইউজার (ID: <code>{target_uid}</code>) কে ব্যান করা হয়েছে।", parse_mode="HTML")

    elif cmd == "/unban":
        if not target_uid:
            await message.reply("❌ সঠিক ইউজার আইডি/ইউজারনেম দিন!")
            return
        user_data[target_uid]["is_banned"] = False
        save_data()
        await message.reply(f"✅ ইউজার (ID: <code>{target_uid}</code>) কে আনব্যান করা হয়েছে।", parse_mode="HTML")

@dp.message(F.text)
async def handle_text_inputs(message: types.Message):
    user_id = message.from_user.id
    if message.chat.id == ADMIN_CHAT_ID:
        return

    if not await check_user_subscription(user_id):
        await send_join_request(message)
        return

    if user_id in user_data and user_data[user_id].get("is_banned", False):
        return

    if user_id not in user_data:
        user_data[user_id] = {"facebook": None, "balance": 0.00, "withdrawn": 0.00, "admin_added_bal": 0.00, "bkash": None, "nagad": None, "binance": None, "screenshots": [], "referred_by": None, "referrals_count": 0, "is_approved": False, "is_banned": False, "name": message.from_user.full_name, "username": message.from_user.username or "NoUsername", "waiting_for": None}
        save_data()

    text = message.text.strip()
    waiting = user_data[user_id].get("waiting_for")

    if waiting == "facebook" or ("facebook.com" in text or "profile" in text or "http" in text):
        if user_data[user_id]["is_approved"]:
            await message.reply("❌ আপনার একাউন্ট ইতিমধ্যে ভেরিফাই সম্পন্ন হয়েছে!")
            return

        if user_data[user_id]["facebook"]:
            await message.reply("❌ আপনার ফেসবুক অ্যাকাউন্ট ইতিমধ্যে বাইন্ড করা আছে!")
            return

        if text in used_facebooks:
            await message.reply("⚠️ এই ফেসবুক আইডি ইতিমধ্যে অন্য কেউ ব্যবহার করেছে!")
            return

        used_facebooks.add(text)
        user_data[user_id]["facebook"] = text
        user_data[user_id]["waiting_for"] = None
        save_data()

        await message.reply("🎉 অভিনন্দন! আপনার ফেসবুক প্রোফাইল বাইন্ড হয়েছে।")

        task_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📌 Task 1: Follow Page", url="https://facebook.com/unithingszone.bd")],
                [InlineKeyboardButton(text="❤️ Task 2: Like Reel", url="https://facebook.com/reel/1805022833955729")],
                [InlineKeyboardButton(text="🔍 Verify & Check Screenshots", callback_data="verify_tasks")]
            ]
        )
        
        instructions = (
            "⚠️ <b>জরুরী সতর্কবার্তা:</b>\n"
            "ফেক স্ক্রিনশট দিলে অ্যাকাউন্ট <b>Ban</b> করা হবে।\n\n"
            "⚠️ <b>বিশেষ সতর্কীকরণ:</b> ফেক অ্যাকাউন্ট দিয়ে লাইক বা ফলো দিলে টাস্ক সাথে সাথে ক্যানসেল করা হবে, তাই অবশ্যই <b>রিয়েল আইডি</b> ব্যবহার করতে হবে!\n\n"
            "📋 Task ১ ও ২ এর ২টি স্ক্রিনশট পরপর আপলোড করুন।"
        )
        await message.answer(instructions, reply_markup=task_keyboard, parse_mode="HTML")
        return

    if waiting and waiting.startswith("bind_"):
        method = waiting.split("_")[1]
        user_data[user_id][method] = text
        user_data[user_id]["waiting_for"] = f"amount_{method}"
        save_data()
        
        await message.reply(f"✅ আপনার <b>{method.upper()}</b> নম্বর (<code>{html.escape(text)}</code>) বাইন্ড হয়েছে!\n\nএখন অ্যামাউন্ট লিখে পাঠান (সর্বনিম্ন ৩০ টাকা)।", parse_mode="HTML")
        return

    if waiting and waiting.startswith("amount_"):
        method = waiting.split("_")[1]
        if not text.replace('.', '', 1).isdigit():
            await message.reply("❌ দয়া করে সঠিক অ্যামাউন্ট লিখুন!")
            return
            
        amount = float(text)
        current_bal = user_data[user_id]["balance"]
        
        if amount < 30.00:
            await message.reply("❌ সর্বনিম্ন উত্তোলন <b>৳৩০.০০</b> টাকা।", parse_mode="HTML")
            return
            
        if current_bal < 30.00 or amount > current_bal:
            await message.reply("⚠️ আপনার একাউন্ট ব্যালেন্স পর্যাপ্ত নয়!")
            return
            
        user_data[user_id]["balance"] -= amount
        user_data[user_id]["withdrawn"] += amount
        user_data[user_id]["waiting_for"] = None
        save_data()
        
        if amount <= 99:
            fee_text = "💸 <b>আপনার উত্তোলন পরিমাণ থেকে ৫ টাকা সেন্ড মানি চার্জ কাটা হবে।</b>"
            final_payout = amount - 5.0
            fee_label = "-৳৫"
        else:
            fee_text = "📉 <b>আপনার উত্তোলন পরিমাণ থেকে ৫% ফি কাটা হবে।</b>"
            final_payout = amount - (amount * 0.05)
            fee_label = "-৫%"

        await message.reply(f"✅ আপনার উইথড্র রিকোয়েস্ট জমা হয়েছে! ২৪ ঘণ্টার ভেতর পেমেন্ট পেয়ে যাবেন।\n\n{fee_text}", parse_mode="HTML")

        user_name = html.escape(str(user_data[user_id]["name"]))
        bound_number = html.escape(str(user_data[user_id][method]))
        refs_count = user_data[user_id]["referrals_count"]
        withdrawn_total = user_data[user_id]["withdrawn"]
        admin_added = user_data[user_id].get("admin_added_bal", 0.0)
        
        expected_balance = 0.0 + (refs_count * 5.0) + admin_added - withdrawn_total
        actual_balance = user_data[user_id]["balance"]

        is_fraud = abs(expected_balance - actual_balance) > 0.01
        security_status = "⚠️ <b>সন্দেহজনক / অমিল পাওয়া গেছে!</b>" if is_fraud else "✅ <b>সঠিক ও ভেরিফাইড ইউজার</b>"

        w_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Approve", callback_data=f"wapprove_{user_id}_{amount}"),
                    InlineKeyboardButton(text="❌ Reject", callback_data=f"wreject_{user_id}_{amount}")
                ]
            ]
        )
        w_caption = (
            f"💳 <b>নতুন উত্তোলন রিকোয়েস্ট!</b>\n\n"
            f"👤 ইউজার: {user_name} (ID: <code>{user_id}</code>)\n"
            f"📱 মেথড: {method.upper()}\n"
            f"📞 নম্বর/আইডি: <code>{bound_number}</code>\n"
            f"💰 আবেদনের পরিমাণ: ৳{amount:.2f}\n"
            f"💸 প্রদানের পরিমাণ ({fee_label}): ৳{final_payout:.2f}\n\n"
            f"-----------------------------\n"
            f"📊 <b>ইউজার অডিট ও জালিয়াতি সিকিউরিটি রিপোর্ট:</b>\n"
            f"👥 মোট রেফারেল: {refs_count} টি\n"
            f"💵 রেফার থেকে অর্জিত: ৳{refs_count * 5.00:.2f}\n"
            f"➕ অ্যাডমিন কাস্টম যোগ: ৳{admin_added:.2f}\n"
            f"💸 সর্বমোট এ যাবত উত্তোলন: ৳{withdrawn_total:.2f}\n"
            f"👛 অবশিষ্ট বর্তমান ব্যালেন্স: ৳{actual_balance:.2f}\n"
            f"🔒 নিরাপত্তা স্ট্যাটাস: {security_status}"
        )
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=w_caption, reply_markup=w_keyboard, parse_mode="HTML")
        return

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
