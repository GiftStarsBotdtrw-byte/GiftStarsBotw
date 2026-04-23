import telebot
from telebot import types
from datetime import datetime
import requests
import os
import sqlite3
from flask import Flask
from threading import Thread
import time

# --- RENDER SERVER (24/7 UYG'OQ SAQLASH) ---
app = Flask('')
@app.route('/')
def home():
    return "Bot is Live and Permanent!"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- SQLITE DATABASE (DOIMIY XOTIRA) ---
DB_NAME = "users.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, 
        name TEXT, 
        orders INTEGER DEFAULT 0, 
        total_spent INTEGER DEFAULT 0, 
        reg_date TEXT)''')
    conn.commit()
    conn.close()

def get_user_data(uid, name="Foydalanuvchi"):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name, orders, total_spent, reg_date FROM users WHERE user_id = ?", (uid,))
    row = cursor.fetchone()
    if not row:
        reg_date = datetime.now().strftime("%d.%m.%Y")
        cursor.execute("INSERT INTO users VALUES (?, ?, 0, 0, ?)", (uid, name, reg_date))
        conn.commit()
        res = {'name': name, 'orders': 0, 'total_spent': 0, 'reg_date': reg_date}
    else:
        res = {'name': row[0], 'orders': row[1], 'total_spent': row[2], 'reg_date': row[3]}
    conn.close()
    return res

# --- ASOSIY SOZLAMALAR ---
TOKEN = "8609066317:AAHy2380eKGF9auvYlYkg40tgVtz_6PNKH8"
bot = telebot.TeleBot(TOKEN, threaded=False)
MY_USERNAME = "@Saidrasulovv_s"

pending_orders = {} 
user_states = {} 

# --- MENYULAR DIZAYNI ---
def main_menu(first_name):
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("⭐ Stars olish", callback_data="buy_stars"))
    markup.row(types.InlineKeyboardButton("🎁 Gift olish", callback_data="buy_gift"))
    markup.add(types.InlineKeyboardButton("🏆 Top", callback_data="top_all"),
               types.InlineKeyboardButton("📊 Statistikam", callback_data="stats"))
    markup.row(types.InlineKeyboardButton("👤 Profil", callback_data="profile"))
    
    text = (f"🐥 <b>Assalom alaykum, {first_name} botga xush kelibsiz!</b>\n\n"
            f"🛍 <i>Bot orqali «⭐ Telegram Stars» va turli xil sovg'alarni xarid qilishingiz mumkin</i>\n\n"
            f"<b>Quyidagi menyudan keraklisini tanlang 👇</b>")
    return text, markup

@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    user_states[uid] = "IDLE"
    get_user_data(uid, message.from_user.first_name)
    text, markup = main_menu(message.from_user.first_name)
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    uid, cid, mid = call.from_user.id, call.message.chat.id, call.message.message_id
    user = get_user_data(uid, call.from_user.first_name)

    # --- STARS BO'LIMI ---
    if call.data == "buy_stars":
        user_states[uid] = "WAITING_STARS_AMOUNT"
        text = (f"<b>⭐ Telegram Stars</b>\n\n"
                f"Siz qanchalik ko'p Stars olsangiz,\nshunchalik afzalliklarga ega bo'lasiz!\n\n"
                f"⚠️ <b><u>Cheklovlar</u></b>\n"
                f"<blockquote>■ Minimal: 50 ta\n"
                f"■ Maksimal: 9685 ta</blockquote>\n\n"
                f"🌀 <b>Kerakli miqdorni tanlang yoki raqam bilan yuboring 👇</b>")
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        stars_list = [("50", 10250), ("75", 15375), ("100", 20500), ("150", 30750),
                      ("250", 51250), ("350", 71750), ("500", 102500), ("750", 153750),
                      ("1000", 205000), ("1500", 307500), ("2500", 512500), ("5000", 1025000)]
        btns = [types.InlineKeyboardButton(f"⭐ {s[0]} - {int(s[1]):,} so'm", callback_data=f"ord_STARS_{s[0]}_{s[1]}") for s in stars_list]
        markup.add(*btns)
        markup.row(types.InlineKeyboardButton("⬅️ Ortga", callback_data="back_to_main"))
        bot.edit_message_text(text, cid, mid, reply_markup=markup, parse_mode="HTML")

    # --- GIFT BO'LIMI ---
    elif call.data == "buy_gift":
        text = (f"<b>🎁 Telegram Gift xarid qilish</b>\n\n"
                f"<blockquote>ℹ️ Giftni yuborish jarayoni\n"
                f"{MY_USERNAME} profili orqali anonim amalga oshiriladi</blockquote>\n\n"
                f"🌐 <b>Iltimos, yuborish uchun kerakli Giftni tanlang 👇</b>")
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        gifts = [("💝", 3000), ("🧸", 3000), ("🎁", 5000), ("🌹", 5000), ("🎂", 10000), ("💐", 10000),
                 ("🚀", 10000), ("🍾", 10000), ("🏆", 20000), ("💍", 20000), ("💎", 20000), ("🎈", 10000)]
        btns = [types.InlineKeyboardButton(f"{g[0]} | {g[1]:,} so'm", callback_data=f"ord_GIFT_{g[0]}_{g[1]}") for g in gifts]
        markup.add(*btns)
        markup.row(types.InlineKeyboardButton("⬅️ Ortga", callback_data="back_to_main"))
        bot.edit_message_text(text, cid, mid, reply_markup=markup, parse_mode="HTML")

    # --- STATISTIKA ---
    elif call.data == "stats":
        conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users ORDER BY total_spent DESC")
        ranks = [r[0] for r in cursor.fetchall()]; conn.close()
        rank = ranks.index(uid) + 1 if uid in ranks else 0
        text = (f"📊 <b>Statistika</b>\n\n"
                f"<blockquote>▫️ Barcha buyurtmalar: {user['orders']} ta\n"
                f"▫️ Jami kiritilgan pul: {user['total_spent']:,} so'm\n"
                f"▫️ Bot bo'yicha o'rningiz: {rank}</blockquote>")
        bot.edit_message_text(text, cid, mid, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Ortga", callback_data="back_to_main")), parse_mode="HTML")

    # --- TOP RO'YXATI ---
    elif call.data == "top_all":
        conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
        cursor.execute("SELECT name, total_spent FROM users ORDER BY total_spent DESC LIMIT 10")
        top_list = cursor.fetchall(); conn.close()
        text = "🏆 <b>Eng faol foydalanuvchilar (Top 10)</b>\n\n"
        for i, (name, spent) in enumerate(top_list):
            text += f"{i+1}. {name} — {spent:,} so'm\n"
        bot.edit_message_text(text, cid, mid, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Ortga", callback_data="back_to_main")), parse_mode="HTML")

    # --- PROFIL ---
    elif call.data == "profile":
        text = (f"👤 <b>Sizning profilingiz</b>\n\n"
                f"🆔 <b>ID:</b> <code>{uid}</code>\n"
                f"📅 <b>Ro'yxatdan o'tgan sana:</b> {user['reg_date']}\n"
                f"💰 <b>Jami sarf:</b> {user['total_spent']:,} so'm")
        bot.edit_message_text(text, cid, mid, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Ortga", callback_data="back_to_main")), parse_mode="HTML")

    # --- BUYURTMA BOSHQARUVI ---
    elif call.data.startswith("ord_"):
        parts = call.data.split("_")
        p_type, p_name, p_price = parts[1], parts[2], int(parts[3])
        pending_orders[uid] = {'type': p_type, 'name': p_name, 'price': p_price, 'msg_id': mid}
        user_states[uid] = "WAITING_USERNAME"
        
        # Qaytish manzili (Stars yoki Gift bo'limiga)
        back_to = "buy_stars" if p_type == "STARS" else "buy_gift"
        
        u_own = f"@{call.from_user.username}" if call.from_user.username else "mavjud emas"
        text = (f"<b>@ Foydalanuvchi nomi</b>\n\n"
                f"<blockquote>📌 Biz {p_type}ni qaysi profilga yuborishimizni aniqlashtirib olishimiz kerak\n\n"
                f"👤 <b>Masalan:</b> {MY_USERNAME}</blockquote>\n\n"
                f"💡 <b>Sizning username:</b> <code>{u_own}</code>\n"
                f"🖋 <b>Foydalanuvchi nomini yuboring</b>")
        bot.edit_message_text(text, cid, mid, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Ortga", callback_data=back_to)), parse_mode="HTML")

    # --- TO'LOVNI TASDIQLASH ---
    elif call.data == "payment_done":
        order = pending_orders.get(uid)
        if order:
            conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
            cursor.execute("UPDATE users SET orders = orders + 1, total_spent = total_spent + ? WHERE user_id = ?", (order['price'], uid))
            conn.commit(); conn.close()
            bot.answer_callback_query(call.id, "✅ Tasdiqlandi!")
            bot.edit_message_text("✅ <b>To'lov tasdiqlandi!</b>\n\nSizning statistikangiz yangilandi.", cid, mid, 
                                  reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Menyu", callback_data="back_to_main")), parse_mode="HTML")
            pending_orders.pop(uid, None)

    elif call.data == "back_to_main":
        user_states[uid] = "IDLE"
        text, markup = main_menu(call.from_user.first_name)
        bot.edit_message_text(text, cid, mid, reply_markup=markup, parse_mode="HTML")

# --- XABARLARNI QABUL QILISH VA TAHLIL ---
@bot.message_handler(func=lambda m: True)
def message_handler(message):
    uid, cid = message.from_user.id, message.chat.id
    state = user_states.get(uid, "IDLE")

    if state == "WAITING_STARS_AMOUNT" and message.text.isdigit():
        amount = int(message.text)
        if 50 <= amount <= 9685:
            price = amount * 205
            u_own = f"@{message.from_user.username}" if message.from_user.username else "mavjud emas"
            text = (f"<b>@ Foydalanuvchi nomi</b>\n\n"
                    f"<blockquote>📌 Biz STARS ({amount} ta)ni qaysi profilga yuborishimizni aniqlashtirib olishimiz kerak</blockquote>\n\n"
                    f"💡 <b>Sizning username:</b> <code>{u_own}</code>\n"
                    f"🖋 <b>Foydalanuvchi nomini yuboring</b>")
            sent_msg = bot.send_message(cid, text, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Ortga", callback_data="buy_stars")), parse_mode="HTML")
            pending_orders[uid] = {'type': "STARS", 'name': str(amount), 'price': price, 'msg_id': sent_msg.message_id}
            user_states[uid] = "WAITING_USERNAME"

    elif state == "WAITING_USERNAME":
        order = pending_orders.get(uid)
        clean_name = message.text.replace('@', '').lower().strip()
        
        # Username mavjudligini tekshirish logicasi
        exists = False
        try:
            res = requests.get(f"https://api.telegram.org/bot{TOKEN}/getChat?chat_id=@{clean_name}", timeout=5).json()
            if res.get("ok"): exists = True
            else:
                tg_page = requests.get(f"https://t.me/{clean_name}", headers={'User-Agent': 'Mozilla/5.0'}).text
                if 'tgme_page_title' in tg_page: exists = "SHUBHA"
        except: exists = "XATO"

        if exists is False:
            bot.send_message(cid, f"❌ <b>@{clean_name}</b> topilmadi. Qaytadan urinib ko'ring.", parse_mode="HTML")
            return

        user_states[uid] = "IDLE"
        res_text = (f"🏪 <b>Buyurtma yaratildi</b>\n\n"
                    f"<blockquote>■ <b>Turi:</b> {order['type']} ({order['name']})\n"
                    f"■ <b>Username:</b> @{clean_name}\n"
                    f"■ <b>Summa:</b> {order['price']:,} so'm</blockquote>\n\n"
                    f"💳 <b>To'lov usulini tanlang:</b>")
        
        pay_markup = types.InlineKeyboardMarkup()
        pay_markup.add(types.InlineKeyboardButton("🔹 Click orqali to'lash", url="https://click.uz/"))
        pay_markup.add(types.InlineKeyboardButton("✅ To'lovni qildim", callback_data="payment_done"))
        pay_markup.add(types.InlineKeyboardButton("⬅️ Ortga", callback_data="back_to_main"))
        bot.edit_message_text(res_text, cid, order['msg_id'], reply_markup=pay_markup, parse_mode="HTML")

# --- ISHGA TUSHIRISH ---
if __name__ == "__main__":
    init_db()
    Thread(target=run).start()
    print("🚀 Bot Database bilan ishga tushdi...")
    while True:
        try:
            bot.infinity_polling(timeout=90, long_polling_timeout=10)
        except Exception as e:
            time.sleep(10)
        
