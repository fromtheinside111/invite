import telebot
import sqlite3
from datetime import datetime

bot = telebot.TeleBot('7313879608:AAFgL1bJxl-KftmioFK6KtR37v5-sOPfpOE')
ADMIN_ID = 7153648951

db = sqlite3.connect('base.db', check_same_thread=False)
sql = db.cursor()

sql.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    answer TEXT,
    answer2 TEXT,
    answer3 TEXT,
    username TEXT,
    status INTEGER
)
''')
db.commit()

chat = []

@bot.message_handler(commands=['start'])
def start(message):
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(telebot.types.InlineKeyboardButton(text='📩 Подать заявку', callback_data='application'))
    bot.send_message(message.chat.id,
                     '🎉 <b>Добро пожаловать в <u>Raspberry Team</u>!</b>\n\n'
                     '🚀 <b>Мы команда амбициозных и целеустремлённых людей, зарабатывающих онлайн.</b>\n\n'
                     '📝 <b>Подай заявку, ответив на несколько простых вопросов.</b>\n\n'
                     '👇 Нажми кнопку ниже 👇',
                     parse_mode='HTML', reply_markup=keyboard)

    sql.execute('SELECT * FROM users WHERE user_id = ?', (message.chat.id,))
    if sql.fetchone() is None:
        sql.execute('INSERT INTO users VALUES (NULL, ?, ?, ?, ?, ?, ?)',
                    (message.chat.id, 'none', 'none', 'none', message.from_user.username, 0))
        db.commit()

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.chat.id != ADMIN_ID:
        return

    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(
        telebot.types.InlineKeyboardButton(text='✅ Одобрить всех', callback_data='approve_all'),
        telebot.types.InlineKeyboardButton(text='❌ Отклонить всех', callback_data='reject_all')
    )

    sql.execute('SELECT * FROM users WHERE status = 1')  # 1 = на рассмотрении
    pending_users = sql.fetchall()

    if not pending_users:
        bot.send_message(message.chat.id, "📭 Нет заявок на рассмотрении.")
        return

    text = '📋 <b>Заявки на рассмотрении:</b>\n\n'
    for user in pending_users:
        text += f'🆔 <code>{user[1]}</code> | @{user[5]}\n🔹 {user[2]} | {user[3]} | {user[4]}\n\n'

    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: True)
def question(call):
    if call.data == 'application':
        sql.execute('SELECT * FROM users WHERE user_id = ?', (call.message.chat.id,))
        ans = sql.fetchone()
        status = ans[6]
        if status == 0:
            msg = bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="🧠 <b>Анкета участника:</b>\n\n"
                     "1️⃣ <b>Сколько тебе лет?</b>",
                parse_mode='HTML'
            )
            bot.register_next_step_handler(msg, question2)
        else:
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="❗ <b>Вы уже отправили заявку.</b>", parse_mode='HTML')

    elif call.data == 'sent':
        sql.execute('UPDATE users SET status = 1 WHERE user_id = ?', (call.message.chat.id,))
        db.commit()
        if call.message.chat.id not in chat:
            chat.append(call.message.chat.id)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text="✅ <b>Заявка отправлена на рассмотрение!</b>", parse_mode='HTML')

        sql.execute('SELECT * FROM users WHERE user_id = ?', (call.message.chat.id,))
        anss = sql.fetchone()
        ans1, ans2, ans3, username = anss[2], anss[3], anss[4], anss[5]
        key = telebot.types.InlineKeyboardMarkup()
        key.add(
            telebot.types.InlineKeyboardButton(text='✅ Принять', callback_data='accepted'),
            telebot.types.InlineKeyboardButton(text='❌ Отклонить', callback_data='reject')
        )
        bot.send_message(ADMIN_ID,
                         f'📥 <b>Новая заявка от @{username}</b>\n\n'
                         f'🗓 <b>Возраст:</b> {ans1}\n'
                         f'⏰ <b>Время для работы:</b> {ans2}\n'
                         f'📈 <b>Опыт:</b> {ans3}',
                         parse_mode='HTML', reply_markup=key)

    elif call.data == 'accepted':
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text="✅ <b>Вы приняли заявку!</b>", parse_mode='HTML')
        msm = chat[0]
        bot.send_message(msm, '🎉 <b>Поздравляем! Вы приняты в команду.</b>', parse_mode='HTML')
        sql.execute('UPDATE users SET status = 2 WHERE user_id = ?', (msm,))
        db.commit()
        del chat[0]

    elif call.data == 'reject':
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text="❌ <b>Вы отклонили заявку.</b>", parse_mode='HTML')
        msm = chat[0]
        bot.send_message(msm, '😞 <b>Извините, вы нам не подходите.</b>', parse_mode='HTML')
        sql.execute('UPDATE users SET status = -1 WHERE user_id = ?', (msm,))
        db.commit()
        del chat[0]

    elif call.data == 'approve_all' and call.message.chat.id == ADMIN_ID:
        sql.execute('SELECT user_id FROM users WHERE status = 1')
        users = sql.fetchall()
        for user in users:
            uid = user[0]
            sql.execute('UPDATE users SET status = 2 WHERE user_id = ?', (uid,))
            bot.send_message(uid, '🎉 <b>Ваша заявка одобрена! Добро пожаловать.</b>', parse_mode='HTML')
        db.commit()
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text="✅ Все заявки были одобрены.", parse_mode='HTML')

    elif call.data == 'reject_all' and call.message.chat.id == ADMIN_ID:
        sql.execute('SELECT user_id FROM users WHERE status = 1')
        users = sql.fetchall()
        for user in users:
            uid = user[0]
            sql.execute('UPDATE users SET status = -1 WHERE user_id = ?', (uid,))
            bot.send_message(uid, '❌ <b>Ваша заявка была отклонена.</b>', parse_mode='HTML')
        db.commit()
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text="❌ Все заявки были отклонены.", parse_mode='HTML')

def question2(message):
    question1 = message.text
    sql.execute('UPDATE users SET answer = ? WHERE user_id = ?', (question1, message.chat.id))
    db.commit()
    msg = bot.send_message(message.chat.id, "2️⃣ <b>Сколько времени готов уделять работе?</b>", parse_mode='HTML')
    bot.register_next_step_handler(msg, question3)

def question3(message):
    question2 = message.text
    sql.execute('UPDATE users SET answer2 = ? WHERE user_id = ?', (question2, message.chat.id))
    db.commit()
    msg = bot.send_message(message.chat.id, "3️⃣ <b>Был ли у тебя опыт в похожих проектах?</b>", parse_mode='HTML')
    bot.register_next_step_handler(msg, finish)

def finish(message):
    keyboards = telebot.types.InlineKeyboardMarkup()
    keyboards.add(
        telebot.types.InlineKeyboardButton(text='📤 Отправить', callback_data='sent'),
        telebot.types.InlineKeyboardButton(text='🔁 Заполнить заново', callback_data='application')
    )
    question3 = message.text
    sql.execute('UPDATE users SET answer3 = ? WHERE user_id = ?', (question3, message.chat.id))
    db.commit()
    sql.execute('SELECT * FROM users WHERE user_id = ?', (message.chat.id,))
    ans = sql.fetchone()
    bot.send_message(message.chat.id,
                     f'📝 <b>Ваши ответы:</b>\n\n'
                     f'1️⃣ {ans[2]}\n'
                     f'2️⃣ {ans[3]}\n'
                     f'3️⃣ {ans[4]}',
                     parse_mode='HTML', reply_markup=keyboards)

bot.polling()
