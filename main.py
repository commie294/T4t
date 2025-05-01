import logging
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

# === НАЧАЛО КОДА ЛОГИРОВАНИЯ ===
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
# === КОНЕЦ КОДА ЛОГИРОВАНИЯ ===

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN_MEET")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
if not BOT_TOKEN or not ADMIN_CHAT_ID:
    print("Ошибка: Не найден BOT_TOKEN_MEET или ADMIN_CHAT_ID.")
    exit()

DATABASE_NAME = 't4t_meet.db'

REGISTER, GET_NAME, GET_AGE, GET_GENDER, GET_GENDER_OTHER, GET_PHOTO, GET_BIO, EDIT_PROFILE, EDIT_NAME, EDIT_AGE, EDIT_GENDER, EDIT_GENDER_OTHER, EDIT_BIO, EDIT_PHOTO = range(14)
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
        print(f"Введенный возраст: {age}")  # Отладочный вывод
        if 16 <= age <= 100:
            context.user_data['age'] = age
            keyboard = [["Транс-женщина"], ["Транс-мужчина"], ["Небинарная персона"], ["Другое"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text("Кем вы себя идентифицируете?", reply_markup=reply_markup)
            print(f"Возраст корректный, возвращаю состояние: {GET_GENDER}")  # Отладочный вывод
            return GET_GENDER
        else:
            await update.message.reply_text("Пожалуйста, введите корректный возраст (от 16 до 100 лет).")
            print(f"Возраст некорректный, возвращаю состояние: {GET_AGE}")  # Отладочный вывод
            return GET_AGE
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите ваш возраст цифрами.")
        print(f"Ошибка ValueError, возвращаю состояние: {GET_AGE}")  # Отладочный вывод
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
        media = InputMediaPhoto(media=photo_id, caption=f"Ваш профиль:\nИмя: {name}\nВозраст: {age}\nПол: {gender}\nО себе: {bio}")
        await context.bot.send_media_group(chat_id=update.message.chat_id, media=[media])
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
    print("Вызвана функция browse_profiles")
    user_id = update.message.from_user.id
    print(f"ID пользователя: {user_id}")
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    print("Подключились к базе данных")
    try:
        cursor.execute("SELECT * FROM users WHERE user_id != ? ORDER BY RANDOM() LIMIT 1", (user_id,))
        profile = cursor.fetchone()
        print(f"Результат запроса: {profile}")
        conn.close()
        print("Закрыли соединение с базой данных")

        if profile:
            user_id_browse, name, age, gender, bio, photo_id, _, _ = profile
            print(f"Нашли профиль: {name}, {age}, {gender}")
            keyboard = [
                [InlineKeyboardButton("👍 Лайк", callback_data=f'like_{user_id_browse}')],
                [InlineKeyboardButton("➡️ Следующая анкета", callback_data='next')],
                [InlineKeyboardButton("⚠️ Пожаловаться", callback_data=f'report_{user_id_browse}')],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            media = InputMediaPhoto(media=photo_id, caption=f"Имя: {name}\nВозраст: {age}\nПол: {gender}\nО себе: {bio}")
            try:
                await context.bot.send_media_group(chat_id=update.message.chat_id, media=[media], reply_markup=reply_markup)
                print("Отправили медиа-группу")
            except Exception as e:
                print(f"Ошибка при отправке медиа-группы: {e}")
        else:
            await update.message.reply_text("Пока нет доступных анкет для просмотра.")
            print("Не нашли других пользователей")
    except sqlite3.Error as e:
        print(f"Ошибка базы данных при browse_profiles: {e}")
        await update.message.reply_text("Произошла ошибка при просмотре анкет.")
    finally:
        if 'conn' in locals() and conn:
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
            user_info_liked = get_user_info(liked_user_id)
            user_info_liking = get_user_info(liking_user_id)
            if user_info_liked and user_info_liking:
                await context.bot.send_message(chat_id=liked_user_id, text=f"У вас мэтч с {user_info_liking[0]}!")
                await context.bot.send_message(chat_id=liking_user_id, text=f"У вас мэтч с {user_info_liked[0]}!")

        keyboard = [[InlineKeyboardButton("➡️ Следующая анкета", callback_data='next')],
                    [InlineKeyboardButton("⚠️ Пожаловаться", callback_data=f'report_{liked_user_id}')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_caption(caption=query.message.caption_text + "\n\n❤️ Вы поставили лайк!", reply_markup=reply_markup)
    except sqlite3.Error as e:
        print(f"Ошибка базы данных при like_profile: {e}")
        await query.answer(text="Произошла ошибка при обработке лайка.", show_alert=True)
    finally:
        if conn:
            conn.close()

async def next_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    try:
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
    except sqlite3.Error as e:
        print(f"Ошибка базы данных при next_profile: {e}")
        await query.answer(text="Произошла ошибка при загрузке следующей анкеты.", show_alert=True)
    finally:
        if conn:
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
        except sqlite3.Error as e:
            print(f"Ошибка базы данных при get_report_reason: {e}")
            await update.message.reply_text("Произошла ошибка при обработке жалобы.")
            return ConversationHandler.END
        finally:
            if conn:
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
    except sqlite3.Error as e:
        print(f"Ошибка базы данных при show_matches: {e}")
        await update.message.reply_text("Произошла ошибка при загрузке ваших мэтчей.")
    finally:
        if conn:
            conn.close()

async def start_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    matched_user_id = int(query.data.split('_')[1])
    await query.message.reply_text(f"Вы выбрали пользователя с ID {matched_user_id}. Вы можете попробовать найти его в Telegram и написать ему.")

def get_user_info(user_id: int) -> tuple or None:
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM users WHERE user_id = ?", (user_id,))
        user_info = cursor.fetchone()
        return user_info
    except sqlite3.Error as e:
        print(f"Ошибка базы данных при get_user_info: {e}")
        return None
    finally:
        if conn:
            conn.close()

def setup_registration_conversation():
    return ConversationHandler(
        entry_points=[CommandHandler("register", register_start)],
        states={
            REGISTER: [MessageHandler(filters.COMMAND, register_start)],
            GET_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            GET_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            GET_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gender)],
            GET_GENDER_OTHER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gender_other)],
            GET_PHOTO: [MessageHandler(filters.PHOTO, get_photo)],
            GET_BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_bio)],
        },
        fallbacks=[],
    )

def setup_profile_commands():
    return [
        CommandHandler("profile", show_profile),
    ]

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

def setup_browsing():
    return [
        CommandHandler("browse", browse_profiles),
        CallbackQueryHandler(like_profile, pattern='^like_'),
        CallbackQueryHandler(next_profile, pattern='^next$'),
        CallbackQueryHandler(report_profile, pattern='^report_'),
    ]

def setup_matches():
    return [
        CommandHandler("matches", show_matches),
        CallbackQueryHandler(start_chat, pattern='^chat_'),
    ]

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

    async def log_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.info(f"Received message: {update.message}")

    log_handler = MessageHandler(filters.ALL, log_message)
    application.add_handler(log_handler, group=-1) # Добавляем логгер как можно раньше

    reg_handler = setup_registration_conversation()
    profile_handlers = setup_profile_commands()
    edit_profile_handler = setup_edit_profile_conversation()
    browse_handlers = setup_browsing()
    matches_handlers = setup_matches()
    report_handler = setup_report_conversation()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(reg_handler)
    application.add_handlers(profile_handlers)
    application.add_handler(edit_profile_handler)
    application.add_handlers(browse_handlers)
    application.add_handlers(matches_handlers)
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
