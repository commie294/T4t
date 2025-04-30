import sqlite3
import random
import os
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN_MEET")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
if not BOT_TOKEN or not ADMIN_CHAT_ID:
    print("Ошибка: Не найден BOT_TOKEN_MEET или ADMIN_CHAT_ID.")
    exit()

DATABASE_NAME = 't4t_meet.db'

REGISTER, GET_NAME, GET_AGE, GET_GENDER, GET_GENDER_OTHER, GET_PHOTO, GET_BIO = range(7)
REPORT, GET_REPORT_REASON = range(7, 9)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rules = (
        "Добро пожаловать в T4t Meet!\n\n"
        "Пожалуйста, ознакомьтесь с нашими правилами:\n"
        "1. Будьте уважительны к другим участникам.\n"
        "2. Запрещены оскорбления, дискриминация и нетерпимость. Анкеты цисгендеров будут блокироваться.\n"
        "3. Не публикуйте контент 18+ и другой неприемлемый материал.\n"
        "4. Соблюдайте конфиденциальность личной информации других пользователей.\n"
        "5. Администрация оставляет за собой право удалять профили и блокировать пользователей за нарушения.\n\n"
        "Основные команды:\n"
        "/register - Зарегистрировать свой профиль.\n"
        "/browse - Просмотр анкет других пользователей.\n"
        "/matches - Просмотр ваших мэтчей.\n"
        "/profile - Просмотр вашего профиля (реализуем позже).\n"
    )

    keyboard = [
        [KeyboardButton("/register")],
        [KeyboardButton("/browse"), KeyboardButton("/matches")],
        [KeyboardButton("/profile")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(rules, reply_markup=reply_markup)

async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Как вас будут видеть другие пользователи?")
    return GET_NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['name'] = update.message.text
    await update.message.reply_text(f"Отлично, ваше имя будет '{context.user_data['name']}'. Теперь скажите, сколько вам лет?")
    return GET_AGE

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        age = int(update.message.text)
        if 16 <= age <= 100:
            context.user_data['age'] = age
            keyboard = [["Транс-женщина"], ["Транс-мужчина"], ["Небинарная персона"], ["Другое"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text("Кем вы себя идентифицируете?", reply_markup=reply_markup)
            return GET_GENDER
        else:
            await update.message.reply_text("Пожалуйста, введите корректный возраст (от 16 до 100 лет).")
            return GET_AGE
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите ваш возраст цифрами.")
        return GET_AGE

async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['gender'] = update.message.text
    if context.user_data['gender'] == "Другое":
        await update.message.reply_text("Пожалуйста, уточните вашу гендерную идентичность.")
        return GET_GENDER_OTHER
    await update.message.reply_text("Отлично. Теперь, пожалуйста, загрузите вашу фотографию профиля.")
    return GET_PHOTO

async def get_gender_other(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['gender'] = update.message.text
    await update.message.reply_text("Спасибо. Теперь, пожалуйста, загрузите вашу фотографию профиля.")
    return GET_PHOTO

async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.photo:
        photo = update.message.photo[-1]
        context.user_data['photo_id'] = photo.file_id
        await update.message.reply_text("Отлично, фото получено. Теперь расскажите немного о себе (ваши интересы, что вы ищете и т.д.).")
        return GET_BIO
    else:
        await update.message.reply_text("Пожалуйста, отправьте фотографию.")
        return GET_PHOTO

async def get_bio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['bio'] = update.message.text
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (user_id, name, age, gender, bio, photo_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (update.message.from_user.id, context.user_data['name'], context.user_data['age'],
          context.user_data['gender'], context.user_data['bio'], context.user_data['photo_id']))
    conn.commit()
    conn.close()
    await update.message.reply_text("Спасибо за регистрацию! Ваш профиль создан.")
    context.user_data.clear()
    return ConversationHandler.END

async def browse_profiles(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id != ? ORDER BY RANDOM() LIMIT 1", (user_id,))
    profile = cursor.fetchone()
    conn.close()

    if profile:
        user_id_browse, name, age, gender, bio, photo_id, _, _ = profile
        keyboard = [
            [InlineKeyboardButton("👍 Лайк", callback_data=f'like_{user_id_browse}')],
            [InlineKeyboardButton("➡️ Следующая анкета", callback_data='next')],
            [InlineKeyboardButton("⚠️ Пожаловаться", callback_data=f'report_{user_id_browse}')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        media = InputMediaPhoto(media=photo_id, caption=f"Имя: {name}\nВозраст: {age}\nПол: {gender}\nО себе: {bio}")
        await context.bot.send_media_group(chat_id=update.message.chat_id, media=[media], reply_markup=reply_markup)
    else:
        await update.message.reply_text("Пока нет доступных анкет для просмотра.")

async def like_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    liked_user_id = int(query.data.split('_')[1])
    liking_user_id = query.from_user.id

    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO matches (user_id_1, user_id_2) VALUES (?, ?)", (liking_user_id, liked_user_id))
    conn.commit()

    cursor.execute("SELECT id FROM matches WHERE user_id_1 = ? AND user_id_2 = ?", (liked_user_id, liking_user_id))
    if cursor.fetchone():
        cursor.execute("UPDATE matches SET is_match = TRUE WHERE user_id_1 = ? AND user_id_2 = ?", (liking_user_id, liked_user_id))
        cursor.execute("UPDATE matches SET is_match = TRUE WHERE user_id_1 = ? AND user_id_2 = ?", (liked_user_id, liking_user_id))
        conn.commit()
        user_info_liked = get_user_info(liked_user_id)
        user_info_liking = get_user_info(liking_user_id)
        if user_info_liked and user_info_liking:
            await context.bot.send_message(chat_id=liked_user_id, text=f"У вас мэтч с {user_info_liking[0]}!")
            await context.bot.send_message(chat_id=liking_user_id, text=f"У вас мэтч с {user_info_liked[0]}!")

    conn.close()
    keyboard = [[InlineKeyboardButton("➡️ Следующая анкета", callback_data='next')],
                [InlineKeyboardButton("⚠️ Пожаловаться", callback_data=f'report_{liked_user_id}')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_caption(caption=query.message.caption_text + "\n\n❤️ Вы поставили лайк!", reply_markup=reply_markup)

async def next_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id != ? ORDER BY RANDOM() LIMIT 1", (user_id,))
    profile = cursor.fetchone()
    conn.close()

    if profile:
        user_id_browse, name, age, gender, bio, photo_id, _, _ = profile
        keyboard = [
            [InlineKeyboardButton("👍 Лайк", callback_data=f'like_{user_id_browse}')],
            [InlineKeyboardButton("➡️ Следующая анкета", callback_data='next')],
            [InlineKeyboardButton("⚠️ Пожаловаться", callback_data=f'report_{user_id_browse}')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        media = InputMediaPhoto(media=photo_id, caption=f"Имя: {name}\nВозраст: {age}\nПол: {gender}\nО себе: {bio}")
        await context.bot.edit_message_media(media=media, chat_id=query.message.chat_id, message_id=query.message.message_id, reply_markup=reply_markup)
    else:
        await query.edit_message_text("Пока нет доступных анкет для просмотра.", reply_markup=None)

async def report_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    reported_user_id = int(query.data.split('_')[1])
    context.user_data['reported_user_id'] = reported_user_id
    await context.bot.send_message(query.message.chat_id, "Пожалуйста, укажите причину жалобы.")
    return GET_REPORT_REASON

async def get_report_reason(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reason = update.message.text
    reporter_user_id = update.message.from_user.id
    reported_user_id = context.user_data.get('reported_user_id')

    if reported_user_id:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO reports (reporter_user_id, reported_user_id, reason) VALUES (?, ?, ?)",
                       (reporter_user_id, reported_user_id, reason))
        conn.commit()
        conn.close()

        await update.message.reply_text("Ваша жалоба принята и будет рассмотрена.")

        if ADMIN_CHAT_ID:
            try:
                user_info_reporter = get_user_info(reporter_user_id)
                user_info_reported = get_user_info(reported_user_id)
                if user_info_reporter and user_info_reported:
                    await context.bot.send_message(
                        chat_id=ADMIN_CHAT_ID,
                        text=f"Новая жалоба:\nОт пользователя ID {reporter_user_id} ({user_info_reporter[0]})\nНа пользователя ID {reported_user_id} ({user_info_reported[0]})\nПричина: {reason}"
                    )
            except Exception as e:
                print(f"Ошибка при отправке уведомления администратору: {e}")

        return ConversationHandler.END
    else:
        await update.message.reply_text("Произошла ошибка при обработке жалобы. Пожалуйста, попробуйте еще раз.")
        return ConversationHandler.END

async def show_matches(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.name, u.user_id
        FROM matches m
        JOIN users u ON (m.user_id_1 = u.user_id OR m.user_id_2 = u.user_id) AND u.user_id != ?
        WHERE m.is_match = TRUE AND (m.user_id_1 = ? OR m.user_id_2 = ?)
    """, (user_id, user_id, user_id))
    matches = cursor.fetchall()
    conn.close()

    if matches:
        message = "Ваши мэтчи:\n"
        keyboard = []
        for name, matched_user_id in matches:
            message += f"- {name}\n"
            keyboard.append([InlineKeyboardButton(f"Начать чат с {name}", callback_data=f'chat_{matched_user_id}')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, reply_markup=reply_markup)
    else:
        await update.message.reply_text("У вас пока нет мэтчей.")

async def start_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    matched_user_id = int(query.data.split('_')[1])
    await query.message.reply_text(f"Вы выбрали пользователя с ID {matched_user_id}. Вы можете попробовать найти его в Telegram и написать ему.")

def get_user_info(user_id: int) -> tuple or None:
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM users WHERE user_id = ?", (user_id,))
    user_info = cursor.fetchone()
    conn.close()
    return user_info

def setup_registration_conversation():
    return ConversationHandler(
        entry_points=[CommandHandler("register", register_start)],
        states={
            REGISTER: [MessageHandler(filters.COMMAND, register_start)],
            GET_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            GET_AGE: [MessageHandler(filters.TEXT & ~filters.TEXT, get_age)],
            GET_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gender)],
            GET_GENDER_OTHER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gender_other)],
            GET_PHOTO: [MessageHandler(filters.PHOTO, get_photo)],
            GET_BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_bio)],
        },
        fallbacks=[],
    )

def setup_browsing(application):
    application.add_handler(CommandHandler("browse", browse_profiles))
    application.add_handler(CallbackQueryHandler(like_profile, pattern='^like_'))
    application.add_handler(CallbackQueryHandler(next_profile, pattern='^next$'))
    application.add_handler(CallbackQueryHandler(report_profile, pattern='^report_'))

def setup_matches(application):
    application.add_handler(CommandHandler("matches", show_matches))
    application.add_handler(CallbackQueryHandler(start_chat, pattern='^chat_'))

def setup_report_conversation():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(report_profile, pattern='^report_')],
        states={
            GET_REPORT_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_report_reason)],
        },
        fallbacks=[],
    )

def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()
    reg_handler = setup_registration_conversation()
    browse_handler = setup_browsing(application)
    matches_handler = setup_matches(application)
    report_handler = setup_report_conversation()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(reg_handler)
    application.add_handler(browse_handler)
    application.add_handler(matches_handler)
    application.add_handler(report_handler)

    application.run_polling()

if __name__ == "__main__":
    # Убедитесь, что файл базы данных существует и таблицы созданы
    if not os.path.exists(DATABASE_NAME):
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                gender TEXT NOT NULL,
                bio TEXT,
                interests TEXT,
                seeking_gender TEXT,
                seeking_age_min INTEGER,
                seeking_age_max INTEGER,
                photo_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id_1 INTEGER NOT NULL,
                user_id_2 INTEGER NOT NULL,
                is_match BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id_1) REFERENCES users(user_id),
                FOREIGN KEY (user_id_2) REFERENCES users(user_id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter_user_id INTEGER NOT NULL,
                reported_user_id INTEGER NOT NULL,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (reporter_user_id) REFERENCES users(user_id),
                FOREIGN KEY (reported_user_id) REFERENCES users(user_id)
            )
        """)
        conn.commit()
        conn.close()

    main()
