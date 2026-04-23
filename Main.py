import telebot
from telebot import types
from datetime import datetime, timedelta
import requests
import os
import sqlite3
from flask import Flask
from threading import Thread
import time

# --- RENDER SERVER ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online!"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- SQLITE DATABASE (Reyting va Vaqt bilan) ---
DB_NAME = "users.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # last_order_date qo'shildi - haftalik/oylik filtr uchun
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, 
        name TEXT, 
        orders INTEGER DEFAULT 0,
        total_spent INTEGER DEFAULT 0, 
        reg_date TEXT,
        last_order_date TEXT)''')
    conn.commit(); conn.close()

def get_user_data(uid, name="Foydalanuvchi"):
    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
    cursor.execute("SELECT name, orders, total_spent, reg_date FROM users WHERE user_id = ?", (uid,))
    row = cursor.fetchone()
    if not row:
        reg_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO users (user_id, name, reg_date) VALUES (?, ?, ?)", (uid, name, reg_date))
        conn.commit()
        res = {'name': name, 'orders': 0, 'total_spent': 0, 'reg_date': reg_date}
    else:
        res = {'name': row[0], 'orders': row[1], 'total_spent': row[2], 'reg_date': row[3]}
    conn.close(); return res

# --- SETTINGS ---
TOKEN = "8609066317:AAHy2380eKGF9auvYlYkg40tgVtz_6PNKH8"
bot = telebot.TeleBot(TOKEN, threaded=False)
MY_USERNAME = "@Saidrasulovv_s"

pending_orders = {} 
user_states = {} 

# --- ASOSIY MENYU ---
def main_menu(first_name):
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("⭐ Stars olish", callback_data="buy_stars"))
    markup.row(types.InlineKeyboardButton("🎁 Gift olish", callback_data="buy_gift"))
    markup.add(types.InlineKeyboardButton("🏆 Top Reyting", callback_data="top_menu"),
               types.InlineKeyboardButton("📊 Statistikam", callback_data="stats"))
    markup.add(types.InlineKeyboardButton("👤 Profil", callback_data="profile"),
               types.InlineKeyboardButton("📞 Murojaat", callback_data="murojaat"))
    
    text = (f"🐥 <b>Assalom alaykum, {first_name} botga xush kelibsiz!</b>\n\n"
            f"🛍 <i>Bot orqali «⭐ Telegram Stars» va turli xil sovg'alarni xarid qilishingiz mumkin</i>\n\n"
            f"<b>Quyidagi menyudan keraklisini tanlang 👇</b>")
    return text, markup

@bot.message_handler(commands=['start'])
def start_cmd(message):
    get_user_data(message.from_user.id, message.from_user.first_name)
    user_states[message.from_user.id] = "IDLE"
    text, markup = main_menu(message.from_user.first_name)
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    uid, cid, mid = call.from_user.id, call.message.chat.id, call.message.message_id
    user = get_user_data(uid, call.from_user.first_name)

    # --- TOP MENU (HAFTALIK / OYLIK TANLOV) ---
    if call.data == "top_menu":
        text = "🏆 <b>Reyting bo'limiga xush kelibsiz!</b>\n\nQaysi vaqt oralig'idagi eng faol foydalanuvchilarni ko'rmoqchisiz?"
        markup = types.InlineKeyboardMarkup()
        markup.row(types.InlineKeyboardButton("📅 Haftalik Top", callback_data="top_week"),
                   types.InlineKeyboardButton("🗓 Oylik Top", callback_data="top_month"))
        markup.row(types.InlineKeyboardButton("⬅️ Ortga", callback_data="back_to_main"))
        bot.edit_message_text(text, cid, mid, reply_markup=markup, parse_mode="HTML")

    elif call.data.startswith("top_"):
        period = call.data.split("_")[1]
        days = 7 if period == "week" else 30
        title = "Haftalik" if period == "week" else "Oylik"
        
        date_limit = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        
        conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
        # Faqat belgilangan vaqtdan keyin buyurtma berganlarni chiqarish
        cursor.execute("SELECT name, total_spent FROM users WHERE last_order_date >= ? ORDER BY total_spent DESC LIMIT 10", (date_limit,))
        top_list = cursor.fetchall(); conn.close()
        
        res_text = f"🏆 <b>{title} Top 10 Faollar</b>\n\n"
        if not top_list:
            res_text += "<i>Hozircha ushbu davrda faol foydalanuvchilar yo'q.</i>"
        else:
            for i, (name, spent) in enumerate(top_list):
                res_text += f"{i+1}. {name} — {spent:,} so'm\n"
        
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Ortga", callback_data="top_menu"))
        bot.edit_message_text(res_text, cid, mid, reply_markup=markup, parse_mode="HTML")

    # --- STARS (12 TA VARIANT) ---
    elif call.data == "buy_stars":
        user_states[uid] = "WAITING_STARS_AMOUNT"
        text = (f"<b>⭐ Telegram Stars</b>\n\n⚠️ <b><u>Cheklovlar</u></b>\n"
                f"<blockquote>■ Minimal: 50 ta\n■ Maksimal: 9685 ta</blockquote>\n\n"
                f"🌀 <b>Kerakli miqdorni tanlang yoki raqam bilan yuboring 👇</b>")
        markup = types.InlineKeyboardMarkup(row_width=2)
        stars_list = [("50", 10250), ("75", 15375), ("100", 20500), ("150", 30750),
                      ("250", 51250), ("350", 71750), ("500", 102500), ("750", 153750),
                      ("1000", 205000), ("1500", 307500), ("2500", 512500), ("5000", 1025000)]
        btns = [types.InlineKeyboardButton(f"⭐ {s[0]} - {int(s[1]):,} so'm", callback_data=f"ord_STARS_{s[0]}_{s[1]}") for s in stars_list]
        markup.add(*btns)
        markup.row(types.InlineKeyboardButton("⬅️ Ortga", callback_data="back_to_main"))
        bot.edit_message_text(text, cid, mid, reply_markup=markup, parse_mode="HTML")

    # --- GIFT ---
    elif call.data == "buy_gift":
        text = (f"<b>🎁 Telegram Gift xarid qilish</b>\n\n"
                f"<blockquote>ℹ️ Giftni yuborish jarayoni\n{MY_USERNAME} orqali amalga oshiriladi</blockquote>")
        markup = types.InlineKeyboardMarkup(row_width=2)
        gifts = [("💝", 3000), ("🧸", 3000), ("🎁", 5000), ("🌹", 5000), ("🎂", 10000), ("💐", 10000),
                 ("🚀", 10000), ("🍾", 10000), ("🏆", 20000), ("💍", 20000), ("💎", 20000), ("🎈", 10000)]
        btns = [types.InlineKeyboardButton(f"{g[0]} | {g[1]:,} so'm", callback_data=f"ord_GIFT_{g[0]}_{g[1]}") for g in gifts]
        markup.add(*btns)
        markup.row(types.InlineKeyboardButton("⬅️ Ortga", callback_data="back_to_main"))
        bot.edit_message_text(text, cid, mid, reply_markup=markup, parse_mode="HTML")

    elif call.data == "murojaat":
        text = (f"📞 <b>Murojaat uchun ma'lumotlar:</b>\n\n"
                f"📱 Tel 1: +998939438014 \n"
                f"📱 Tel 2: +998935417516 \n\n"
                f"💬 Telegram: {MY_USERNAME}, @ndrbkvvc")
        bot.edit_message_text(text, cid, mid, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Ortga", callback_data="back_to_main")), parse_mode="HTML")

    elif call.data == "profile":
        text = (f"👤 <b>Sizning profilingiz</b>\n\n🆔 <b>ID:</b> <code>{uid}</code>\n"
                f"📅 <b>Sana:</b> {user['reg_date']}\n💰 <b>Sarf:</b> {user['total_spent']:,} so'm")
        bot.edit_message_text(text, cid, mid, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Ortga", callback_data="back_to_main")), parse_mode="HTML")

    elif call.data.startswith("ord_"):
        parts = call.data.split("_")
        pending_orders[uid] = {'type': parts[1], 'name': parts[2], 'price': int(parts[3]), 'msg_id': mid}
        user_states[uid] = "WAITING_USERNAME"
        u_own = f"@{call.from_user.username}" if call.from_user.username else "mavjud emas"
        text = (f"<b>@ Foydalanuvchi nomi</b>\n\n"
                f"<blockquote>📌 Biz {parts[1]}ni qaysi profilga yuborishimizni aniqlashtirib olishimiz kerak</blockquote>\n"
                f"💡 <b>Sizning username:</b> <code>{u_own}</code>\n"
                f"🖋 <b>Foydalanuvchi nomini yuboring</b>")
        back_call = "buy_stars" if parts[1] == "STARS" else "buy_gift"
        bot.edit_message_text(text, cid, mid, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Ortga", callback_data=back_call)), parse_mode="HTML")

    elif call.data == "payment_done":
        order = pending_orders.get(uid)
        if order:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
            cursor.execute("UPDATE users SET orders = orders + 1, total_spent = total_spent + ?, last_order_date = ? WHERE user_id = ?", 
                           (order['price'], now, uid))
            conn.commit(); conn.close()
            bot.answer_callback_query(call.id, "✅ Tasdiqlandi!")
            bot.edit_message_text("✅ <b>To'lov tasdiqlandi!</b>", cid, mid, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Menyu", callback_data="back_to_main")), parse_mode="HTML")
            pending_orders.pop(uid, None)

    elif call.data == "stats":
        conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users ORDER BY total_spent DESC")
        ranks = [r[0] for r in cursor.fetchall()]; conn.close()
        rank = ranks.index(uid) + 1 if uid in ranks else 0
        msg = f"📊 <b>Statistika</b>\n\n<blockquote>▫️ Buyurtmalar: {user['orders']} ta\n▫️ Sarf: {user['total_spent']:,} so'm\n▫️ O'rningiz: {rank}</blockquote>"
        bot.edit_message_text(msg, cid, mid, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Ortga", callback_data="back_to_main")), parse_mode="HTML")

    elif call.data == "back_to_main":
        user_states[uid] = "IDLE"
        text, markup = main_menu(call.from_user.first_name)
        bot.edit_message_text(text, cid, mid, reply_markup=markup, parse_mode="HTML")

# --- MESSAGE HANDLER (XATOLIKLAR BILAN) ---
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
                    f"<blockquote>📌 Biz STARS ({amount} ta)ni qaysi profilga yuborishimizni aniqlashtirib olishimiz kerak</blockquote>\n"
                    f"💡 <b>Sizning username:</b> <code>{u_own}</code>\n"
                    f"🖋 <b>Foydalanuvchi nomini yuboring</b>")
            sent = bot.send_message(cid, text, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Ortga", callback_data="buy_stars")), parse_mode="HTML")
            pending_orders[uid] = {'type': "STARS", 'name': str(amount), 'price': price, 'msg_id': sent.message_id}
            user_states[uid] = "WAITING_USERNAME"

    elif state == "WAITING_USERNAME":
        order = pending_orders.get(uid)
        clean_name = message.text.replace('@', '').lower().strip()
        u_own = f"@{message.from_user.username}" if message.from_user.username else "mavjud emas"
        try: bot.delete_message(cid, message.message_id)
        except: pass

        exists = False
        try:
            res = requests.get(f"https://api.telegram.org/bot{TOKEN}/getChat?chat_id=@{clean_name}", timeout=5).json()
            if res.get("ok"): exists = True
            else:
                tg_page = requests.get(f"https://t.me/{clean_name}", headers={'User-Agent': 'Mozilla/5.0'}).text
                if 'tgme_page_title' in tg_page: exists = "SHUBHA"
        except: exists = "XATO"

        if exists is False:
            err_text = (f"<b>❌ Foydalanuvchi topilmadi: @{clean_name}</b>\n\n"
                        f"<blockquote> Ushbu foydalanuvchi nomi orqali hech qanday profilni topa olmadik.</blockquote>\n\n"
                        f"💡 <b>Sizning username:</b> <code>{u_own}</code>\n"
                        f"🖋 <b>Foydalanuvchi nomini yuboring</b>")
            bot.edit_message_text(err_text, cid, order['msg_id'], reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Ortga", callback_data="back_to_main")), parse_mode="HTML")
            return

        user_states[uid] = "IDLE"
        res_text = (f"🏪 <b>Buyurtma yaratildi</b>\n\n<blockquote>■ {order['type']} ({order['name']})\n■ @{clean_name}\n■ {order['price']:,} so'm</blockquote>")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔹 Click orqali to'lash", url="https://click.uz/"))
        markup.add(types.InlineKeyboardButton("✅ To'lovni qildim", callback_data="payment_done"))
        markup.add(types.InlineKeyboardButton("⬅️ Ortga", callback_data="back_to_main"))
        bot.edit_message_text(res_text, cid, order['msg_id'], reply_markup=markup, parse_mode="HTML")

if __name__ == "__main__":
    init_db()
    Thread(target=run).start()
    while True:
        try: bot.infinity_polling(timeout=90)
        except: time.sleep(10)
    
        
