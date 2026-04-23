import telebot
from telebot import types
from datetime import datetime
import requests
import os
from flask import Flask
from threading import Thread
import time

# --- SERVER QISMI (Render uchun) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is Live!"

def run():
    # Render avtomatik port beradi, bo'lmasa 10000 ishlatiladi
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- ASOSIY SOZLAMALAR ---
TOKEN = "8609066317:AAHy2380eKGF9auvYlYkg40tgVtz_6PNKH8"
bot = telebot.TeleBot(TOKEN, threaded=False)
MY_USERNAME = "@Saidrasulovv_s"

users_db = {} 
pending_orders = {} 
user_states = {} 

def get_user_data(user_id, name="Foydalanuvchi"):
    if user_id not in users_db:
        users_db[user_id] = {
            'name': name, 'orders': 0, 'total_spent': 0,
            'stars_bought': 0, 'reg_date': datetime.now().strftime("%d.%m.%Y")
        }
    return users_db[user_id]

def get_user_rank_data(uid):
    if not users_db: return 1, 0, 0
    all_users = sorted(users_db.items(), key=lambda x: x[1]['total_spent'], reverse=True)
    rank = next((i + 1 for i, (u_id, _) in enumerate(all_users) if u_id == uid), 1)
    next_rank_gap = all_users[rank - 2][1]['total_spent'] - users_db[uid]['total_spent'] if rank > 1 else 0
    lower_user_gap = users_db[uid]['total_spent'] - (all_users[rank][1]['total_spent'] if rank < len(all_users) else 0)
    return rank, next_rank_gap, lower_user_gap

# --- ASOSIY MENYU ---
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

    elif call.data == "stats":
        rank, nxt, low = get_user_rank_data(uid)
        text = (f"📊 <b>Statistika</b>\n\n"
                f"<blockquote>▫️ Barcha buyurtmalar: {user['orders']} ta\n"
                f"▫️ Jami kiritilgan pul: {user['total_spent']:,} so'm\n"
                f"▫️ Bot bo'yicha o'rningiz: {rank}\n"
                f"▫️ Keyingi o'rin uchun: {max(0, nxt):,} so'm\n"
                f"▫️ Sizdan o'tishlari uchun: {max(0, low):,} so'm</blockquote>")
        bot.edit_message_text(text, cid, mid, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Ortga", callback_data="back_to_main")), parse_mode="HTML")

    elif call.data == "top_all":
        all_users = sorted(users_db.items(), key=lambda x: x[1]['total_spent'], reverse=True)[:10]
        text = "🏆 <b>Eng faol foydalanuvchilar (Top 10)</b>\n\n"
        for i, (u_id, data) in enumerate(all_users):
            text += f"{i+1}. {data['name']} — {data['total_spent']:,} so'm\n"
        bot.edit_message_text(text, cid, mid, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Ortga", callback_data="back_to_main")), parse_mode="HTML")

    elif call.data == "profile":
        text = (f"👤 <b>Sizning profilingiz</b>\n\n"
                f"🆔 <b>ID:</b> <code>{uid}</code>\n"
                f"📅 <b>Ro'yxatdan o'tgan sana:</b> {user['reg_date']}\n"
                f"💰 <b>Jami sarf:</b> {user['total_spent']:,} so'm")
        bot.edit_message_text(text, cid, mid, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Ortga", callback_data="back_to_main")), parse_mode="HTML")

    elif call.data.startswith("ord_"):
        parts = call.data.split("_")
        p_type, p_name, p_price = parts[1], parts[2], int(parts[3])
        pending_orders[uid] = {'type': p_type, 'name': p_name, 'price': p_price, 'msg_id': mid}
        user_states[uid] = "WAITING_USERNAME"
        u_own_name = call.from_user.username if call.from_user.username else "mavjud emas"
        text = (f"<b>@ Foydalanuvchi nomi</b>\n\n"
                f"<blockquote>📌 Biz {p_type}ni qaysi profilga yuborishimizni aniqlashtirib olishimiz kerak\n\n"
                f"👤 <b>Masalan:</b> {MY_USERNAME}</blockquote>\n\n"
                f"💡 <b>Keyni sizning username:</b> <code>@{u_own_name}</code>\n"
                f"🖋 <b>Foydalanuvchi nomini yuboring</b>")
        bot.edit_message_text(text, cid, mid, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Ortga", callback_data="back_to_main")), parse_mode="HTML")

    elif call.data == "payment_done":
        order = pending_orders.get(uid)
        if order:
            user['orders'] += 1
            user['total_spent'] += order['price']
            bot.answer_callback_query(call.id, "✅ Tasdiqlandi!")
            bot.edit_message_text("✅ <b>To'lov tasdiqlandi!</b>\n\nStatistikangiz yangilandi va buyurtma navbatga qo'shildi.", cid, mid, 
                                  reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Menyu", callback_data="back_to_main")), parse_mode="HTML")
            pending_orders.pop(uid, None)

    elif call.data == "back_to_main":
        user_states[uid] = "IDLE"
        text, markup = main_menu(call.from_user.first_name)
        bot.edit_message_text(text, cid, mid, reply_markup=markup, parse_mode="HTML")

# --- MESSAGE HANDLER ---
@bot.message_handler(func=lambda m: True)
def message_handler(message):
    uid, cid = message.from_user.id, message.chat.id
    state = user_states.get(uid, "IDLE")

    if state == "WAITING_STARS_AMOUNT" and message.text.isdigit():
        amount = int(message.text)
        if 50 <= amount <= 9685:
            price = amount * 205
            u_own_name = message.from_user.username if message.from_user.username else "mavjud emas"
            text = (f"<b>@ Foydalanuvchi nomi</b>\n\n"
                    f"<blockquote>📌 Biz STARS ({amount} ta)ni qaysi profilga yuborishimizni aniqlashtirib olishimiz kerak\n\n"
                    f"👤 <b>Masalan:</b> {MY_USERNAME}</blockquote>\n\n"
                    f"💡 <b>Keyni sizning username:</b> <code>@{u_own_name}</code>\n"
                    f"🖋 <b>Foydalanuvchi nomini yuboring</b>")
            sent_msg = bot.send_message(cid, text, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Ortga", callback_data="buy_stars")), parse_mode="HTML")
            pending_orders[uid] = {'type': "STARS", 'name': str(amount), 'price': price, 'msg_id': sent_msg.message_id}
            user_states[uid] = "WAITING_USERNAME"

    elif state == "WAITING_USERNAME":
        order = pending_orders.get(uid)
        clean_name = message.text.replace('@', '').lower().strip()
        u_own_name = message.from_user.username if message.from_user.username else "mavjud emas"
        
        try: bot.delete_message(cid, message.message_id)
        except: pass

        exists = False
        try:
            res = requests.get(f"https://api.telegram.org/bot{TOKEN}/getChat?chat_id=@{clean_name}").json()
            if res.get("ok"): exists = True
            else:
                tg_page = requests.get(f"https://t.me/{clean_name}", headers={'User-Agent': 'Mozilla/5.0'}).text
                if 'tgme_page_title' in tg_page: exists = "SHUBHA"
        except: exists = "XATO"

        if exists is False:
            err_text = (f"<b>❌ Foydalanuvchi topilmadi: @{clean_name}</b>\n\n"
                        f"<blockquote> Ushbu foydalanuvchi nomi orqali hech qanday profilni topa olmadik.\n\n"
                        f"👤 <b>Masalan:</b> {MY_USERNAME}</blockquote>\n\n"
                        f"💡 <b>Keyni sizning username:</b> <code>@{u_own_name}</code>\n"
                        f"🖋 <b>Foydalanuvchi nomini yuboring</b>")
            bot.edit_message_text(err_text, cid, order['msg_id'], reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Ortga", callback_data="back_to_main")), parse_mode="HTML")
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
        pay_markup.add(types.InlineKeyboardButton("⬅️ Menyu", callback_data="back_to_main"))
        bot.edit_message_text(res_text, cid, order['msg_id'], reply_markup=pay_markup, parse_mode="HTML")

# --- ISHGA TUSHIRISH (Render barqarorligi uchun) ---
if __name__ == "__main__":
    t = Thread(target=run)
    t.daemon = True
    t.start()
    
    print("🚀 Bot Renderda ishga tushdi...")
    while True:
        try:
            bot.infinity_polling(timeout=90, long_polling_timeout=10)
        except Exception as e:
            print(f"Xato: {e}")
            time.sleep(10)
        

  
