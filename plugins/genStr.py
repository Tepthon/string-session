import os
import json
import time
import asyncio

from asyncio.exceptions import TimeoutError

from pyrogram import filters, Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import (
    SessionPasswordNeeded, FloodWait,
    PhoneNumberInvalid, ApiIdInvalid,
    PhoneCodeInvalid, PhoneCodeExpired
)


API_TEXT = """🙋‍♂أهلاً {},

انا بوت اساعدك على استخراج جلسة بايروجرام او تليثون 

لإنشاء جلسة الاستخراج قم بإرسال الايبي ايدي الخاص بك `API_ID` 🐿
"""
HASH_TEXT = "الان قم بإرسال الايبي هاش الخاص بك `API_HASH` to Continue.\n\nPress /cancel to Cancel.🐧"
PHONE_NUMBER_TEXT = (
    "📞__  الآن أرسل رقم هاتفك للمتابعة"
    " الرجاء إرسال رقم هاتفك مع رمز الدولة.__\n**Eg:** `+13124562345`\n\n"
    "Press /cancel to Cancel."
)



@Client.on_message(filters.private & filters.command("start"))
async def generate_str(c, m):
    get_api_id = await c.ask(
        chat_id=m.chat.id,
        text=API_TEXT.format(m.from_user.mention(style='md')),
        filters=filters.text
    )
    api_id = get_api_id.text
    if await is_cancel(m, api_id):
        return

    await get_api_id.delete()
    await get_api_id.request.delete()
    try:
        check_api = int(api_id)
    except Exception:
        await m.reply("**--🛑 الايبي ايدي الخاص بك غير صالح 🛑--**\nPress /الرجاء إعادة المحاولة مجددا.")
        return

    get_api_hash = await c.ask(
        chat_id=m.chat.id, 
        text=HASH_TEXT,
        filters=filters.text
    )
    api_hash = get_api_hash.text
    if await is_cancel(m, api_hash):
        return

    await get_api_hash.delete()
    await get_api_hash.request.delete()

    if not len(api_hash) >= 30:
        await m.reply("--**🛑 الايبي هاش الخاص بك غير صالح🛑**--\nPress / الرجاء إعادة المحاولة مجددا.")
        return

    try:
        client = Client(":memory:", api_id=api_id, api_hash=api_hash)
    except Exception as e:
        await c.send_message(m.chat.id ,f"**🛑 خطأ: 🛑** `{str(e)}`\nPress / الرجاء إعادة المحاولة مجددا.")
        return

    try:
        await client.connect()
    except ConnectionError:
        await client.disconnect()
        await client.connect()
    while True:
        get_phone_number = await c.ask(
            chat_id=m.chat.id,
            text=PHONE_NUMBER_TEXT
        )
        phone_number = get_phone_number.text
        if await is_cancel(m, phone_number):
            return
        await get_phone_number.delete()
        await get_phone_number.request.delete()

        confirm = await c.ask(
            chat_id=m.chat.id,
            text=f'🤔 هل هذا الرقم الخاص بك `{phone_number}` correct? (y/n): \n\ntype: `y` (If Yes)\ntype: `n` (If No)'
        )
        if await is_cancel(m, confirm.text):
            return
        if "y" in confirm.text.lower():
            await confirm.delete()
            await confirm.request.delete()
            break
    try:
        code = await client.send_code(phone_number)
        await asyncio.sleep(1)
    except FloodWait as e:
        await m.reply(f"__عذرًا أن أقول لك إن لديك فترة انتظار فيضان تبلغ {e.x} ثانية 😞__")
        return
    except ApiIdInvalid:
        await m.reply("🕵‍♂ الايبي ايدي والايبي هاش الخاص بك غير صالح.\n\nPress / الرجاء إعادة المحاولة مجددا.")
        return
    except PhoneNumberInvalid:
        await m.reply("☎ رقم هاتفك غير صالح.`\n\nPress / الرجاء إعادة المحاولة مجددا.")
        return

    try:
        sent_type = {"تطبيق": "تليجرام 💌",
            "sms": "الرسائل القصيرة 💬",
            "call": "مكالمة هاتفية 📱",
            "flash_call": "مكالمة هاتفية فلاش📲"
        }[code.type]
        otp = await c.ask(
            chat_id=m.chat.id,
            text=(f"لقد أرسلت OTP إلى الرقم `{phone_number}` through {sent_type}\n\n"
                  "يرجى إدخال OTP في الشكل `1 2 3 4 5` __(provied white space between numbers)__\n\n"
                  "إذا لم يرسل الروبوت OTP ، فحاول /start the Bot.\n"
                  "Press /cancel to Cancel."), timeout=300)
    except TimeoutError:
        await m.reply("**⏰ خطأ TimeOut: ** لقد وصلت إلى الحد الزمني 5 دقائق\nPress / الرجاء إعادة المحاولة مجددا.")
        return
    if await is_cancel(m, otp.text):
        return
    otp_code = otp.text
    await otp.delete()
    await otp.request.delete()
    try:
        await client.sign_in(phone_number, code.phone_code_hash, phone_code=' '.join(str(otp_code)))
    except PhoneCodeInvalid:
        await m.reply("**📵 رمز غير صالح**\n\nPress / الرجاء إعادة المحاولة مجددا.")
        return 
    except PhoneCodeExpired:
        await m.reply("**⌚ الكود منتهي الصلاحية**\n\nPress / الرجاء إعادة المحاولة مجددا.")
        return
    except SessionPasswordNeeded:
        try:
            two_step_code = await c.ask(
                chat_id=m.chat.id, 
                text="`🔐 يحتوي هذا الحساب على رمز تحقق من خطوتين.\nPlease enter your second factor authentication code.`\nPress /cancel to Cancel.",
                timeout=300
            )
        except TimeoutError:
            await m.reply("**⏰ خطأ TimeOut: ** لقد وصلت إلى الحد الزمني 5 دقائق.\nPress / الرجاء إعادة المحاولة مجددا.")
            return
        if await is_cancel(m, two_step_code.text):
            return
        new_code = two_step_code.text
        await two_step_code.delete()
        await two_step_code.request.delete()
        try:
            await client.check_password(new_code)
        except Exception as e:
            await m.reply(f"**⚠️ خطأ:** `{str(e)}`")
            return
    except Exception as e:
        await c.send_message(m.chat.id ,f"**⚠️ خطأ:** `{str(e)}`")
        return
    try:
        session_string = await client.export_session_string()
        await client.send_message("me", f"**Your String Session 👇**\n\n`{session_string}`\n\nThanks For using {(await c.get_me()).mention(style='md')}")
        text = "✅ تم الدخول بنجاح الى الحساب اذهب إلى الرسائل المحفوظة وقم بنسخ الكود."
        reply_markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton(text="String Session ↗️", url=f"tg://openmessage?user_id={m.chat.id}")]]
        )
        await c.send_message(m.chat.id, text, reply_markup=reply_markup)
    except Exception as e:
        await c.send_message(m.chat.id ,f"**⚠️ خطأ:** `{str(e)}`")
        return
    try:
        await client.stop()
    except:
        pass


@Client.on_message(filters.private & filters.command("help"))
async def help(c, m):
    await help_cb(c, m, cb=False)


@Client.on_callback_query(filters.regex('^help$'))
async def help_cb(c, m, cb=True):
    help_text = """**مهلا تحتاج مساعدة ؟؟ 👨‍✈️**


>>>> اضغط على زر البداية >>>> أرسل API_ID الخاص بك عندما يطلب البوت. >>>> ثم أرسل API_HASH عندما يطلب البوت. >>>> أرسل رقم هاتفك المحمول. >>>> أرسل كلمة المرور لمرة واحدة (OTP) المستلمة إلى رقمك بالتنسيق `1 2 3 4 5` (أعط مسافة b / w لكل رقم) >>>> (إذا كان لديك تحقق من خطوتين ، فأرسل إلى bot إذا طلب bot.)
**ملاحظة:**

إذا قمت بأي خطأ في أي مكان اضغط /cancel and then press /start
"""

    buttons = [[
        InlineKeyboardButton('📕 حول', callback_data='about'),
        InlineKeyboardButton('❌ إغلاق', callback_data='close')
    ]]
    if cb:
        await m.answer()
        await m.message.edit(text=help_text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
    else:
        await m.reply_text(text=help_text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True, quote=True)


@Client.on_message(filters.private & filters.command("about"))
async def about(c, m):
    await about_cb(c, m, cb=False)


@Client.on_callback_query(filters.regex('^about$'))
async def about_cb(c, m, cb=True):
    me = await c.get_me()
    about_text = f"""**MY DETAILS:**

__🤖 اسمي:__ {me.mention(style='md')}
    
__📝 لغة البوت:__ [Python3](https://www.python.org/)

__🧰 برمجة البوت:__ [Pyrogram](https://github.com/pyrogram/pyrogram)

__👨‍💻 المطور:__ [𝐌𝐎𝐇𝐀𝐌𝐌𝐀𝐃](https://t.me/P17_12)

__🖥️|قناة السورس:__ [TEPTHON](https://t.me/Tepthon)

__👥|كروب الدعم:__ [Tepthon_Support](https://t.me/Tepthon_Support)

__🚀 |قناة اليوتيوب:__ [سورس تيبثون العربي](https://youtube.com/channel/UCbLdgVNSQ9aVmRuttZ7p_8Q)
"""

    buttons = [[
        InlineKeyboardButton('💡 حول', callback_data='help'),
        InlineKeyboardButton('❌ إغلاق', callback_data='close')
    ]]
    if cb:
        await m.answer()
        await m.message.edit(about_text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
    else:
        await m.reply_text(about_text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True, quote=True)


@Client.on_callback_query(filters.regex('^close$'))
async def close(c, m):
    await m.message.delete()
    await m.message.reply_to_message.delete()


async def is_cancel(msg: Message, text: str):
    if text.startswith("/cancel"):
        await msg.reply("⛔ تم إلغاء العملية.")
        return True
    return False


