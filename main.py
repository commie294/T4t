import logging
import sqlite3
import os
from dotenv import load_dotenv
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN_MEET")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
if not BOT_TOKEN or not ADMIN_CHAT_ID:
    print("Ошибка: Не найден BOT_TOKEN_MEET или ADMIN_CHAT_ID.")
    exit()

DATABASE_NAME = 't4t_meet.db'

# Состояния для ConversationHandler
REGISTER, GET_NAME, GET_AGE, GET_GENDER, GET_GENDER_OTHER, GET_PHOTO, GET_BIO = range(7)
EDIT_PROFILE, EDIT_NAME, EDIT_AGE, EDIT_GENDER, EDIT_GENDER_OTHER, EDIT_BIO, EDIT_PHOTO = range(7, 14)
REPORT, GET_REPORT_REASON = range(14, 16)

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
        "/profile - Просмотр вашего профиля.\n"
        "/edit_profile - Редактировать свой профиль.\n"
    )

    keyboard = [
        [KeyboardButton("/register")],
        [KeyboardButton("/browse"), KeyboardButton("/matches")],
        [KeyboardButton("/profile"), KeyboardButton("/edit_profile")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(rules, reply_markup=reply_markup)

async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Ваше имя: как вас будут видеть другие пользователи?")
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

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name, age, gender, bio, photo_id FROM users WHERE user_id = ?", (user_id,))
    profile = cursor.fetchone()
    conn.close()

    if profile:
        name, age, gender, bio, photo_id = profile
        await context.bot.send_photo(
            chat_id=update.message.chat_id,
            photo=photo_id,
            caption=f"Ваш профиль:\nИмя: {name}\nВозраст: {age}\nПол: {gender}\nО себе: {bio}"
        )
    else:
        await update.message.reply_text("Ваш профиль не найден. Пожалуйста, зарегистрируйтесь.")

async def edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        ["Изменить имя"],
        ["Изменить возраст"],
        ["Изменить пол"],
        ["Изменить фото"],
        ["Изменить био"],
        ["Отмена"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Что вы хотите изменить в своем профиле?", reply_markup=reply_markup)
    return EDIT_PROFILE

async def edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Пожалуйста, введите новое имя.")
    return EDIT_NAME

async def update_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_name = update.message.text
    user_id = update.message.from_user.id
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET name = ? WHERE user_id = ?", (new_name, user_id))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"Ваше имя обновлено на '{new_name}'.")
    return ConversationHandler.END

async def edit_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Пожалуйста, введите новый возраст.")
    return EDIT_AGE

async def update_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        new_age = int(update.message.text)
        if 16 <= new_age <= 100:
            user_id = update.message.from_user.id
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET age = ? WHERE user_id = ?", (new_age, user_id))
            conn.commit()
            conn.close()
            await update.message.reply_text(f"Ваш возраст обновлен на '{new_age}'.")
            return ConversationHandler.END
        else:
            await update.message.reply_text("Пожалуйста, введите корректный возраст (от 16 до 100 лет).")
            return EDIT_AGE
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите возраст цифрами.")
        return EDIT_AGE

async def edit_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [["Транс-женщина"], ["Транс-мужчина"], ["Небинарная персона"], ["Другое"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Пожалуйста, выберите новый пол.", reply_markup=reply_markup)
    return EDIT_GENDER

async def update_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_gender = update.message.text
    if new_gender == "Другое":
        await update.message.reply_text("Пожалуйста, уточните вашу гендерную идентичность.")
        return EDIT_GENDER_OTHER
    user_id = update.message.from_user.id
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET gender = ? WHERE user_id = ?", (new_gender, user_id))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"Ваш пол обновлен на '{new_gender}'.")
    return ConversationHandler.END

async def edit_gender_other_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_gender = update.message.text
    user_id = update.message.from_user.id
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET gender = ? WHERE user_id = ?", (new_gender, user_id))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"Ваш пол обновлен на '{new_gender}'.")
    return ConversationHandler.END

async def edit_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Пожалуйста, отправьте новую фотографию профиля.")
    return EDIT_PHOTO

async def update_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.photo:
        photo = update.message.photo[-1]
        new_photo_id = photo.file_id
        user_id = update.message.from_user.id
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET photo_id = ? WHERE user_id = ?", (new_photo_id, user_id))
        conn.commit()
        conn.close()
        await update.message.reply_text("Ваша фотография профиля обновлена.")
        return ConversationHandler.END
    else:
        await update.message.reply_text("Пожалуйста, отправьте фотографию.")
        return EDIT_PHOTO

async def edit_bio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Пожалуйста, введите новое описание профиля.")
    return EDIT_BIO

async def update_bio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_bio = update.message.text
    user_id = update.message.from_user.id
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET bio = ? WHERE user_id = ?", (new_bio, user_id))
    conn.commit()
    conn.close()
    await update.message.reply_text("Ваше описание профиля обновлено.")
    return ConversationHandler.END

async def cancel_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Редактирование профиля отменено.")
    return ConversationHandler.END

async def browse_profiles(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT user_id, name, age, gender, bio, photo_id FROM users WHERE user_id != ? ORDER BY RANDOM() LIMIT 1", (user_id,))
        profile = cursor.fetchone()

        if profile:
            user_id_browse, name, age, gender, bio, photo_id = profile
            keyboard = [
                [InlineKeyboardButton("👍 Лайк", callback_data=f'like_{user_id_browse}')],
                [InlineKeyboardButton("➡️ Следующая анкета", callback_data='next')],
                [InlineKeyboardButton("⚠️ Пожаловаться", callback_data=f'report_{user_id_browse}')],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_photo(
                chat_id=update.message.chat_id,
                photo=photo_id,
                caption=f"Имя: {name}\nВозраст: {age}\nПол: {gender}\nО себе: {bio}",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text("Пока нет доступных анкет для просмотра.")
    except Exception as e:
        logger.error(f"Ошибка в browse_profiles: {e}")
        await update.message.reply_text("Произошла ошибка при загрузке анкеты.")
    finally:
        conn.close()

async def like_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    liked_user_id = int(query.data.split('_')[1])
    liking_user_id = query.from_user.id

    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO matches (user_id_1, user_id_2) VALUES (?, ?)", (liking_user_id, liked_user_id))
        conn.commit()

        cursor.execute("SELECT id FROM matches WHERE user_id_1 = ? AND user_id_2 = ?", (liked_user_id, liking_user_id))
        if cursor.fetchone():
            cursor.execute("UPDATE matches SET is_match = TRUE WHERE user_id_1 = ? AND user_id_2 = ?", (liking_user_id, liked_user_id))
            cursor.execute("UPDATE matches SET is_match = TRUE WHERE user_id_1 = ? AND user_id_2 = ?", (liked_user_id, liking_user_id))
            conn.commit()
            cursor.execute("SELECT name FROM users WHERE user_id = ?", (liked_user_id,))
            user_info_liked = cursor.fetchone()
            cursor.execute("SELECT name FROM users WHERE user_id = ?", (liking_user_id,))
            user_info_liking = cursor.fetchone()
            if user_info_liked and user_info_liking:
                await context.bot.send_message(chat_id=liked_user_id, text=f"У вас мэтч с {user_info_liking[0]}!")
                await context.bot.send_message(chat_id=liking_user_id, text=f"У вас мэтч с {user_info_liked[0]}!")

        keyboard = [
            [InlineKeyboardButton("➡️ Следующая анкета", callback_data='next')],
            [InlineKeyboardButton("⚠️ Пожаловаться", callback_data=f'report_{liked_user_id}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_caption(
            caption=f"{query.message.caption}\n\n❤️ Вы поставили лайк!",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Ошибка в like_profile: {e}")
        await query.answer(text="Произошла ошибка при обработке лайка.", show_alert=True)
    finally:
        conn.close()

async def next_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT user_id, name, age, gender, bio, photo_id FROM users WHERE user_id != ? ORDER BY RANDOM() LIMIT 1", (user_id,))
        profile = cursor.fetchone()

        if profile:
            user_id_browse, name, age, gender, bio, photo_id = profile
            keyboard = [
                [InlineKeyboardButton("👍 Лайк", callback_data=f'like_{user_id_browse}')],
                [InlineKeyboardButton("➡️ Следующая анкета", callback_data='next')],
                [InlineKeyboardButton("⚠️ Пожаловаться", callback_data=f'report_{user_id_browse}')],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_media(
                media=InputMediaPhoto(media=photo_id, caption=f"Имя: {name}\nВозраст: {age}\nПол: {gender}\nО себе: {bio}"),
                reply_markup=reply_markup
            )
        else:
            await query.edit_message_text("Пока нет доступных анкет для просмотра.")
    except Exception as e:
        logger.error(f"Ошибка в next_profile: {e}")
        await query.answer(text="Произошла ошибка при загрузке следующей анкеты.", show_alert=True)
    finally:
        conn.close()

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
        try:
            cursor.execute("INSERT INTO reports (reporter_user_id, reported_user_id, reason) VALUES (?, ?, ?)",
                           (reporter_user_id, reported_user_id, reason))
            conn.commit()
            await update.message.reply_text("Ваша жалоба принята и будет рассмотрена.")

            if ADMIN_CHAT_ID:
                cursor.execute("SELECT name FROM users WHERE user_id = ?", (reporter_user_id,))
                user_info_reporter = cursor.fetchone()
                cursor.execute("SELECT name FROM users WHERE user_id = ?", (reported_user_id,))
                user_info_reported = cursor.fetchone()
                if user_info_reporter and user_info_reported:
                    await context.bot.send_message(
                        chat_id=ADMIN_CHAT_ID,
                        text=f"Новая жалоба:\nОт пользователя ID {reporter_user_id} ({user_info_reporter[0]})\nНа пользователя ID {reported_user_id} ({user_info_reported[0]})\nПричина: {reason}"
                    )
            return ConversationHandler.END
        except Exception as e:
            logger.error(f"Ошибка в get_report_reason: {e}")
            await update.message.reply_text("Произошла ошибка при обработке жалобы.")
            return ConversationHandler.END
        finally:
            conn.close()
    else:
        await update.message.reply_text("Произошла ошибка при обработке жалобы. Пожалуйста, попробуйте еще раз.")
        return ConversationHandler.END

async def show_matches(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT u.name, u.user_id
            FROM matches m
            JOIN users u ON (m.user_id_1 = u.user_id OR m.user_id_2 = u.user_id) AND u.user_id != ?
            WHERE m.is_match = TRUE AND (m.user_id_1 = ? OR m.user_id_2 = ?)
        """, (user_id, user_id, user_id))
        matches = cursor.fetchall()

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
    except Exception as e:
        logger.error(f"Ошибка в show_matches: {e}")
        await update.message.reply_text("Произошла ошибка при загрузке ваших мэтчей.")
    finally:
        conn.close()

async def start_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    matched_user_id = int(query.data.split('_')[1])
    await query.message.reply_text(f"Вы выбрали пользователя с ID {matched_user_id}. Вы можете попробовать найти его в Telegram и написать ему.")

def setup_registration_conversation():
    return ConversationHandler(
        entry_points=[CommandHandler("register", register_start)],
        states={
            GET_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            GET_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            GET_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gender)],
            GET_GENDER_OTHER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gender_other)],
            GET_PHOTO: [MessageHandler(filters.PHOTO, get_photo)],
            GET_BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_bio)],
        },
        fallbacks=[],
    )

def setup_edit_profile_conversation():
    return ConversationHandler(
        entry_points=[CommandHandler("edit_profile", edit_profile)],
        states={
            EDIT_PROFILE: [
                MessageHandler(filters.Regex("^Изменить имя$"), edit_name),
                MessageHandler(filters.Regex("^Изменить возраст$"), edit_age),
                MessageHandler(filters.Regex("^Изменить пол$"), edit_gender),
                MessageHandler(filters.Regex("^Изменить фото$"), edit_photo),
                MessageHandler(filters.Regex("^Изменить био$"), edit_bio),
                MessageHandler(filters.Regex("^Отмена$"), cancel_edit),
            ],
            EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_name)],
            EDIT_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_age)],
            EDIT_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_gender)],
            EDIT_GENDER_OTHER: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_gender_other_input)],
            EDIT_PHOTO: [MessageHandler(filters.PHOTO, update_photo)],
            EDIT_BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_bio)],
        },
        fallbacks=[MessageHandler(filters.TEXT & ~filters.COMMAND, cancel_edit)],
    )

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

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("profile", show_profile))
    application.add_handler(CommandHandler("matches", show_matches))
    application.add_handler(CommandHandler("browse", browse_profiles))
    
    # Обработчики ConversationHandler
    application.add_handler(setup_registration_conversation())
    application.add_handler(setup_edit_profile_conversation())
    application.add_handler(setup_report_conversation())
    
    # Обработчики callback-запросов
    application.add_handler(CallbackQueryHandler(like_profile, pattern='^like_'))
    application.add_handler(CallbackQueryHandler(next_profile, pattern='^next$'))
    application.add_handler(CallbackQueryHandler(start_chat, pattern='^chat_'))

    # Инициализация базы данных
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

    application.run_polling()

if __name__ == "__main__":
    main()
