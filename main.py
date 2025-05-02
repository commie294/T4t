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
    InputMediaPhoto,
    ReplyKeyboardRemove
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
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN_MEET")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

if not BOT_TOKEN or not ADMIN_CHAT_ID:
    logger.error("Не найдены BOT_TOKEN_MEET или ADMIN_CHAT_ID в .env файле")
    exit()

DATABASE_NAME = 't4t_meet.db'

(
    REGISTER, GET_NAME, GET_AGE, GET_AGE_PREFERENCE,
    GET_GENDER, GET_GENDER_OTHER, GET_PHOTO, GET_BIO, GET_CITY,
    EDIT_PROFILE, EDIT_NAME, EDIT_AGE, EDIT_AGE_PREFERENCE,
    EDIT_GENDER, EDIT_GENDER_OTHER, EDIT_BIO, EDIT_PHOTO, EDIT_CITY,
    REPORT, GET_REPORT_REASON
) = range(20)

def get_db_connection():
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except Exception as e:
        logger.error(f"Ошибка подключения к БД: {e}")
        raise

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rules = (
        "Добро пожаловать в T4t Meet!\n\n"
        "Подпишись на наш канал: https://t.me/tperehod\n\n"
        "Пожалуйста, ознакомьтесь с нашими правилами:\n"
        "1. Будьте уважительны к другим участникам.\n"
        "2. Запрещены оскорбления, дискриминация и нетерпимость. Анкеты цисгендеров будут блокироваться.\n"
        "3. Не публикуйте контент 18+ и другой неприемлемый материал.\n"
        "4. Соблюдайте конфиденциальность личной информации других пользователей.\n\n"
        "Основные команды:\n"
        "/register - Зарегистрировать свой профиль.\n"
        "/browse - Просмотр анкет других пользователей.\n"
        "/matches - Просмотр ваших мэтчей.\n"
        "/profile - Просмотр вашего профиля.\n"
        "/edit_profile - Редактировать свой профиль."
    )
    keyboard = [
        [KeyboardButton("/register")],
        [KeyboardButton("/browse"), KeyboardButton("/matches")],
        [KeyboardButton("/profile"), KeyboardButton("/edit_profile")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(rules, reply_markup=reply_markup)

async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Ваше имя (как вас будут видеть другие):")
    return GET_NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['name'] = update.message.text
    await update.message.reply_text(f"Отлично, {context.user_data['name']}! Сколько вам лет?")
    return GET_AGE

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        age = int(update.message.text)
        if 16 <= age <= 100:
            context.user_data['age'] = age
            context.user_data['is_adult'] = age >= 18
            if age >= 18:
                keyboard = [["18-25"], ["26-35"], ["36-45"], ["46+"], ["Все 18+"]]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                await update.message.reply_text("Какой возраст вас интересует?", reply_markup=reply_markup)
                return GET_AGE_PREFERENCE
            else:
                keyboard = [["Транс-женщина"], ["Транс-мужчина"], ["Небинарная персона"], ["Другое"]]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                await update.message.reply_text("Кем вы себя идентифицируете?", reply_markup=reply_markup)
                return GET_GENDER
        else:
            await update.message.reply_text("Возраст должен быть от 16 до 100 лет.")
            return GET_AGE
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число.")
        return GET_AGE

async def get_age_preference(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['age_preference'] = update.message.text
    keyboard = [["Транс-женщина"], ["Транс-мужчина"], ["Небинарная персона"], ["Другое"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Кем вы себя идентифицируете?", reply_markup=reply_markup)
    return GET_GENDER

async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['gender'] = update.message.text
    if context.user_data['gender'] == "Другое":
        await update.message.reply_text("Укажите вашу гендерную идентичность:")
        return GET_GENDER_OTHER
    await update.message.reply_text("Теперь загрузите ваше фото профиля:")
    return GET_PHOTO

async def get_gender_other(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['gender'] = update.message.text
    await update.message.reply_text("Теперь загрузите ваше фото профиля:")
    return GET_PHOTO

async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.photo:
        context.user_data['photo_id'] = update.message.photo[-1].file_id
        await update.message.reply_text("Расскажите о себе (интересы, что ищете):")
        return GET_BIO
    await update.message.reply_text("Пожалуйста, отправьте фото.")
    return GET_PHOTO

async def get_bio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['bio'] = update.message.text
    await update.message.reply_text("В каком городе вы находитесь? (необязательно):")
    return GET_CITY

async def get_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['city'] = update.message.text.title() if update.message.text else None
    conn = get_db_connection()
    try:
        conn.execute("""
            INSERT OR REPLACE INTO users
            (user_id, name, age, gender, bio, photo_id, is_adult, age_preference, city)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            update.message.from_user.id,
            context.user_data['name'],
            context.user_data['age'],
            context.user_data['gender'],
            context.user_data['bio'],
            context.user_data['photo_id'],
            context.user_data.get('is_adult', False),
            context.user_data.get('age_preference'),
            context.user_data.get('city')
        ))
        conn.commit()
        await update.message.reply_text("✅ Профиль создан! Используйте /browse для просмотра анкет.")
    except Exception as e:
        logger.error(f"Ошибка создания профиля: {e}")
        await update.message.reply_text("❌ Ошибка при создании профиля. Попробуйте снова.")
    finally:
        conn.close()
        context.user_data.clear()
        return ConversationHandler.END

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    conn = get_db_connection()
    try:
        profile = conn.execute("""
            SELECT name, age, gender, bio, photo_id, age_preference, city
            FROM users WHERE user_id = ?
        """, (user_id,)).fetchone()
        if profile:
            caption = (
                f"Ваш профиль:\n"
                f"Имя: {profile['name']}\n"
                f"Возраст: {profile['age']}\n"
                f"Гендер: {profile['gender']}\n"
                f"Город: {profile['city'] if profile['city'] else 'Не указан'}\n"
                f"О себе: {profile['bio']}"
            )
            if profile['age'] >= 18:
                caption += f"\n\nИщу возраст: {profile['age_preference'] if profile['age_preference'] else 'Не указано'}"
            await context.bot.send_photo(
                chat_id=update.message.chat_id,
                photo=profile['photo_id'],
                caption=caption
            )
        else:
            await update.message.reply_text("❌ Профиль не найден. Используйте /register")
    except Exception as e:
        logger.error(f"Ошибка показа профиля: {e}")
        await update.message.reply_text("❌ Ошибка при загрузке профиля")
    finally:
        conn.close()

async def edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT age, is_adult FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        if not result:
            await update.message.reply_text("⚠️ Профиль не найден. Используйте /register.")
            return ConversationHandler.END
        age = result['age']
        is_adult = result.get('is_adult', age >= 18)
        keyboard = [
            ["Изменить имя"],
            ["Изменить возраст"],
            ["Изменить гендер"],
            ["Изменить фото"],
            ["Изменить описание"],
            ["Изменить город"]
        ]
        if is_adult:
            keyboard.append(["Изменить возрастные предпочтения"])
        keyboard.append(["Отмена"])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("Что изменить?", reply_markup=reply_markup)
        return EDIT_PROFILE
    except Exception as e:
        logger.error(f"Ошибка при редактировании профиля: {e}")
        await update.message.reply_text("🛠 Произошла ошибка. Пожалуйста, попробуйте снова.")
        return ConversationHandler.END
    finally:
        conn.close()

async def edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Введите новое имя:")
    return EDIT_NAME

async def update_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_name = update.message.text
    user_id = update.message.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET name = ? WHERE user_id = ?", (new_name, user_id))
        conn.commit()
        await update.message.reply_text("✅ Имя обновлено!")
    except Exception as e:
        logger.error(f"Ошибка при обновлении имени: {e}")
        await update.message.reply_text("🛠 Произошла ошибка при обновлении имени.")
    finally:
        conn.close()
        return ConversationHandler.END

async def edit_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Введите новый возраст:")
    return EDIT_AGE

async def update_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        new_age = int(update.message.text)
        if 16 <= new_age <= 100:
            user_id = update.message.from_user.id
            is_adult = new_age >= 18
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users                 SET age = ?, is_adult = ?
                WHERE user_id = ?
            """, (new_age, is_adult, user_id))
            conn.commit()
            await update.message.reply_text("✅ Возраст обновлен!")
            return ConversationHandler.END
        else:
            await update.message.reply_text("Возраст должен быть от 16 до 100 лет.")
            return EDIT_AGE
    except ValueError:
        await update.message.reply_text("Введите число.")
        return EDIT_AGE
    except Exception as e:
        logger.error(f"Ошибка при обновлении возраста: {e}")
        await update.message.reply_text("🛠 Произошла ошибка при обновлении возраста.")
        return ConversationHandler.END
    finally:
        if 'conn' in locals():
            conn.close()

async def edit_age_preference(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [["18-25"], ["26-35"], ["36-45"], ["46+"], ["Все 18+"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Выберите возраст:", reply_markup=reply_markup)
    return EDIT_AGE_PREFERENCE

async def update_age_preference(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_pref = update.message.text
    user_id = update.message.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET age_preference = ? WHERE user_id = ?", (new_pref, user_id))
        conn.commit()
        await update.message.reply_text("✅ Возрастные предпочтения обновлены!")
    except Exception as e:
        logger.error(f"Ошибка при обновлении предпочтений: {e}")
        await update.message.reply_text("🛠 Произошла ошибка при обновлении предпочтений.")
    finally:
        conn.close()
        return ConversationHandler.END

async def edit_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [["Транс-женщина"], ["Транс-мужчина"], ["Небинарная персона"], ["Другое"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Выберите гендер:", reply_markup=reply_markup)
    return EDIT_GENDER

async def update_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_gender = update.message.text
    if new_gender == "Другое":
        await update.message.reply_text("Пожалуйста, уточните вашу гендерную идентичность.")
        return EDIT_GENDER_OTHER
    user_id = update.message.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET gender = ? WHERE user_id = ?", (new_gender, user_id))
        conn.commit()
        await update.message.reply_text("✅ Гендер обновлен!")
    except Exception as e:
        logger.error(f"Ошибка при обновлении гендера: {e}")
        await update.message.reply_text("🛠 Произошла ошибка при обновлении гендера.")
    finally:
        conn.close()
        return ConversationHandler.END

async def edit_gender_other_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_gender = update.message.text
    user_id = update.message.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET gender = ? WHERE user_id = ?", (new_gender, user_id))
        conn.commit()
        await update.message.reply_text("✅ Гендер обновлен!")
    except Exception as e:
        logger.error(f"Ошибка при обновлении гендера: {e}")
        await update.message.reply_text("🛠 Произошла ошибка при обновлении гендера.")
    finally:
        conn.close()
        return ConversationHandler.END

async def edit_bio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Введите новое описание:")
    return EDIT_BIO

async def update_bio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_bio = update.message.text
    user_id = update.message.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET bio = ? WHERE user_id = ?", (new_bio, user_id))
        conn.commit()
        await update.message.reply_text("✅ Описание обновлено!")
    except Exception as e:
        logger.error(f"Ошибка при обновлении описания: {e}")
        await update.message.reply_text("🛠 Произошла ошибка при обновлении описания.")
    finally:
        conn.close()
        return ConversationHandler.END

async def edit_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Отправьте новое фото:")
    return EDIT_PHOTO

async def update_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.photo:
        new_photo = update.message.photo[-1].file_id
        user_id = update.message.from_user.id
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE users SET photo_id = ? WHERE user_id = ?", (new_photo, user_id))
            conn.commit()
            await update.message.reply_text("✅ Фото обновлено!")
            return ConversationHandler.END
        except Exception as e:
            logger.error(f"Ошибка при обновлении фото: {e}")
            await update.message.reply_text("🛠 Произошла ошибка при обновлении фото.")
            return EDIT_PHOTO
        finally:
            conn.close()
    else:
        await update.message.reply_text("Пожалуйста, отправьте фото.")
        return EDIT_PHOTO

async def edit_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Введите новый город (или 'нет' чтобы удалить):")
    return EDIT_CITY

async def update_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_city = update.message.text.title() if update.message.text.lower() != 'нет' else None
    user_id = update.message.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET city = ? WHERE user_id = ?", (new_city, user_id))
        conn.commit()
        await update.message.reply_text("✅ Город обновлен!" if new_city else "✅ Город удален из профиля")
    except Exception as e:
        logger.error(f"Ошибка при обновлении города: {e}")
        await update.message.reply_text("🛠 Произошла ошибка при обновлении города.")
    finally:
        conn.close()
        return ConversationHandler.END

async def cancel_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Редактирование отменено.")
    return ConversationHandler.END

async def browse_profiles(update: Update, context: ContextTypes.DEFAULT_TYPE, city_filter=None) -> None:
    user_id = update.message.from_user.id if update.message else update.callback_query.from_user.id
    conn = get_db_connection()
    try:
        user_data = conn.execute("""
            SELECT is_adult, age_preference, city FROM users WHERE user_id = ?
        """, (user_id,)).fetchone()
        if not user_data:
            if update.message:
                await update.message.reply_text("❌ Сначала зарегистрируйтесь /register")
            else:
                await update.callback_query.answer("Сначала зарегистрируйтесь", show_alert=True)
            return
        is_adult, age_preference, user_city = user_data
        query = """
            SELECT u.user_id, u.name, u.age, u.gender, u.bio, u.photo_id, u.city
            FROM users u
            LEFT JOIN viewed_profiles v ON u.user_id = v.viewed_id AND v.viewer_id = ?
            WHERE u.user_id != ? AND u.is_adult = ?
            AND u.user_id NOT IN (
                SELECT reported_user_id FROM reports WHERE reporter_user_id = ?
            )
            AND (v.viewed_id IS NULL OR v.timestamp < datetime('now', '-1 day'))
        """
        params = [user_id, user_id, is_adult, user_id]
        if city_filter == 'my' and user_city:
            query += " AND (u.city IS NULL OR lower(u.city) = lower(?))"
            params.append(user_city)
        elif city_filter == 'other' and user_city:
            query += " AND (u.city IS NULL OR lower(u.city) != lower(?))"
            params.append(user_city)
        if is_adult and age_preference and age_preference != "Все 18+":
            age_ranges = {
                "18-25": (18, 25),
                "26-35": (26, 35),
                "36-45": (36, 45),
                "46+": (46, 100)
            }
            if age_preference in age_ranges:
                min_age, max_age = age_ranges[age_preference]
                query += " AND u.age BETWEEN ? AND ?"
                params.extend([min_age, max_age])
        query += " ORDER BY RANDOM() LIMIT 1"
        profile = conn.execute(query, params).fetchone()
        if not profile:
            if update.message:
                await update.message.reply_text("🔍 Нет доступных анкет. Попробуйте позже.")
            else:
                await update.callback_query.answer("Нет анкет для показа", show_alert=True)
            return
        conn.execute("""
            INSERT OR REPLACE INTO viewed_profiles (viewer_id, viewed_id)
            VALUES (?, ?)
        """, (user_id, profile['user_id']))
        conn.commit()
        keyboard = [
            [InlineKeyboardButton("👍 Лайк", callback_data=f'like_{profile["user_id"]}')],
            [InlineKeyboardButton("➡️ Следующая", callback_data='next')],
            [InlineKeyboardButton("⚠️ Пожаловаться", callback_data=f'report_{profile["user_id"]}')],
        ]
        if city_filter == 'my':
            keyboard.append([InlineKeyboardButton("🌍 Другие города", callback_data='other_cities')])
        else:
            keyboard.append([InlineKeyboardButton("🏙️ Мой город", callback_data='my_city')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        caption = (
            f"Имя: {profile['name']}\n"
            f"Возраст: {profile['age']}\n"
            f"Гендер: {profile['gender']}\n"
            f"Город: {profile['city'] if profile['city'] else 'Не указан'}\n"
            f"О себе: {profile['bio']}"
        )
        if update.message:
            await update.message.reply_photo(
                photo=profile['photo_id'],
                caption=caption,
                reply_markup=reply_markup
            )
        else:
            await update.callback_query.message.edit_media(
                media=InputMediaPhoto(profile['photo_id'], caption=caption),
                reply_markup=reply_markup
            )
            await update.callback_query.answer()
    except Exception as e:
        logger.error(f"Ошибка показа анкет: {e}")
        if update.message:
            await update.message.reply_text("❌ Ошибка при загрузке анкет")
        else:
            await update.callback_query.answer("Ошибка загрузки", show_alert=True)
    finally:
        conn.close()

async def browse_other_cities(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await browse_profiles(update, context, city_filter='other')

async def browse_my_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await browse_profiles(update, context, city_filter='my')

async def next_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    for row in query.message.reply_markup.inline_keyboard:
        for button in row:
            if button.callback_data == 'other_cities':
                await browse_other_cities(update, context)
                return
            elif button.callback_data == 'my_city':
                await browse_my_city(update, context)
                return
    await browse_profiles(update, context)

async def like_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    liked_user_id = int(query.data.split('_')[1])
    liking_user_id = query.from_user.id
    conn = get_db_connection()
    try:
        if conn.execute("""
            SELECT 1 FROM matches
            WHERE user_id_1 = ? AND user_id_2 = ?
        """, (liking_user_id, liked_user_id)).fetchone():
            await query.answer("Вы уже лайкнули этот профиль", show_alert=True)
            return
        conn.execute("""
            INSERT INTO matches (user_id_1, user_id_2)
            VALUES (?, ?)
        """, (liking_user_id, liked_user_id))
        if conn.execute("""
            SELECT 1 FROM matches
            WHERE user_id_1 = ? AND user_id_2 = ?
        """, (liked_user_id, liking_user_id)).fetchone():
            conn.execute("""
                UPDATE matches
                SET is_match = TRUE
                WHERE (user_id_1 = ? AND user_id_2 = ?)
                OR (user_id_1 = ? AND user_id_2 = ?)
            """, (liking_user_id, liked_user_id, liked_user_id, liking_user_id))
            liked_name = conn.execute("""
                SELECT name FROM users WHERE user_id = ?
            """, (liked_user_id,)).fetchone()[0]
            liking_name = conn.execute("""
                SELECT name FROM users WHERE user_id = ?
            """, (liking_user_id,)).fetchone()[0]
            await context.bot.send_message(
                chat_id=liked_user_id,
                text=f"🎉 У вас мэтч с {liking_name}!"
            )
            await context.bot.send_message(
                chat_id=liking_user_id,
                text=f"🎉 У вас мэтч с {liked_name}!"
            )
        conn.commit()
        keyboard = [
            [InlineKeyboardButton("➡️ Следующая", callback_data='next')],
            [InlineKeyboardButton("⚠️ Пожаловаться", callback_data=f'report_{liked_user_id}')]
        ]
        for row in query.message.reply_markup.inline_keyboard:
            for button in row:
                if button.callback_data == 'other_cities':
                    keyboard.append([InlineKeyboardButton("🌍 Другие города", callback_data='other_cities')])
                    break
                elif button.callback_data == 'my_city':
                    keyboard.append([InlineKeyboardButton("🏙️ Мой город", callback_data='my_city')])
                    break
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_caption(
            caption=f"{query.message.caption}\n\n❤️ Вы поставили лайк!",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Ошибка лайка: {e}")
        await query.answer("❌ Ошибка при обработке лайка", show_alert=True)
    finally:
        conn.close()

async def report_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
    await query.answer()
    reported_user_id = int(query.data.split('_')[1])
    conn = get_db_connection()
    try:
        if conn.execute("""
            SELECT 1 FROM reports
            WHERE reporter_user_id = ? AND reported_user_id = ?
        """, (query.from_user.id, reported_user_id)).fetchone():
            await query.edit_message_text("⚠️ Вы уже жаловались на этого пользователя.")
            return ConversationHandler.END
        context.user_data['reported_user_id'] = reported_user_id
        await query.message.reply_text(
            "Опишите причину жалобы (спам, оскорбления и т.д.):",
            reply_markup=ReplyKeyboardRemove()
        )
        return GET_REPORT_REASON
    except Exception as e:
        logger.error(f"Ошибка жалобы: {e}")
        await query.message.reply_text("❌ Ошибка при обработке жалобы")
        return ConversationHandler.END
    finally:
        conn.close()

async def get_report_reason(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reason = update.message.text
    reporter_id = update.message.from_user.id
    reported_id = context.user_data.get('reported_user_id')
    if not reported_id:
        await update.message.reply_text("❌ Ошибка: не найден пользователь")
        return ConversationHandler.END
    conn = get_db_connection()
    try:
        conn.execute("""
            INSERT INTO reports
            (reporter_user_id, reported_user_id, reason)
            VALUES (?, ?, ?)
        """, (reporter_id, reported_id, reason))
        reporter_name = conn.execute("""
            SELECT name FROM users WHERE user_id = ?
        """, (reporter_id,)).fetchone()[0]
        reported_name = conn.execute("""
            SELECT name FROM users WHERE user_id = ?
        """, (reported_id,)).fetchone()[0]
        conn.commit()
        keyboard = [
            [
                InlineKeyboardButton("🔨 Заблокировать", callback_data=f'block_{reported_id}'),
                InlineKeyboardButton("⚠️ Предупредить", callback_data=f'warn_{reported_id}')
            ],
            [InlineKeyboardButton("❌ Отклонить", callback_data=f'ignore_{reported_id}')]
        ]
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=(
                f"🚨 Жалоба:\n"
                f"От: {reporter_name} (ID: {reporter_id})\n"
                f"На: {reported_name} (ID: {reported_id})\n"
                f"Причина: {reason}"
            ),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        await update.message.reply_text("✅ Жалоба отправлена администраторам")
    except Exception as e:
        logger.error(f"Ошибка отправки жалобы: {e}")
        await update.message.reply_text("❌ Ошибка при отправке жалобы")
    finally:
        conn.close()
        return ConversationHandler.END

async def handle_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        admin_id = int(ADMIN_CHAT_ID)
    except ValueError:
        await query.answer("❌ Ошибка конфигурации: ADMIN_CHAT_ID должен быть числом", show_alert=True)
        return
    if query.from_user.id != admin_id:
        await query.answer("❌ Только для администратора", show_alert=True)
        return
    try:
        action, user_id = query.data.split('_')
        user_id = int(user_id)
    except ValueError:
        await query.answer("❌ Неверный формат команды", show_alert=True)
        return
    conn = get_db_connection()
    try:
        if action == 'block':
            conn.execute("UPDATE users SET is_blocked = 1 WHERE user_id = ?", (user_id,))
            conn.execute("""
                UPDATE reports
                SET admin_action = 'blocked',
                    admin_id = ?
                WHERE reported_user_id = ?
                AND admin_action IS NULL
            """, (query.from_user.id, user_id))
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ Ваш аккаунт заблокирован за нарушение правил"
                )
            except Exception as e:
                logger.error(f"Не удалось уведомить: {e}")
            await query.edit_message_text(
                text=f"✅ Пользователь {user_id} заблокирован",
                reply_markup=None
            )
        elif action == 'warn':
            conn.execute("""
                UPDATE reports
                SET admin_action = 'warned',
                    admin_id = ?
                WHERE reported_user_id = ?
                AND admin_action IS NULL
            """, (query.from_user.id, user_id))
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="⚠️ Вы получили предупреждение от администратора"
                )
            except Exception as e:
                logger.error(f"Не удалось уведомить: {e}")
            await query.edit_message_text(
                text=f"✅ Пользователь {user_id} предупрежден",
                reply_markup=None
            )
        elif action == 'ignore':
            conn.execute("""
                UPDATE reports
                SET admin_action = 'ignored',
                    admin_id = ?
                WHERE reported_user_id = ?
                AND admin_action IS NULL
            """, (query.from_user.id, user_id))
            await query.edit_message_text(
                text=f"✅ Жалоба на {user_id} отклонена",
                reply_markup=None
            )
        conn.commit()
    except Exception as e:
        logger.error(f"Ошибка действия админа: {e}")
        await query.answer("❌ Ошибка при обработке", show_alert=True)
    finally:
        conn.close()

async def show_matches(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    conn = get_db_connection()
    try:
        matches = conn.execute("""
            SELECT u.user_id, u.name, u.photo_id
            FROM matches m
            JOIN users u ON (
                (m.user_id_1 = u.user_id AND m.user_id_2 = ?) OR
                (m.user_id_2 = u.user_id AND m.user_id_1 = ?)
            )
            WHERE m.is_match = TRUE
        """, (user_id, user_id)).fetchall()
        if matches:
            for match in matches:
                await context.bot.send_photo(
                    chat_id=update.message.chat_id,
                    photo=match['photo_id'],
                    caption=f"Мэтч с {match['name']}",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            f"Написать {match['name']}",
                            callback_data=f'chat_{match["user_id"]}'
                        )
                    ]])
                )
        else:
            await update.message.reply_text("🔍 У вас пока нет мэтчей")
    except Exception as e:
        logger.error(f"Ошибка показа мэтчей: {e}")
        await update.message.reply_text("❌ Ошибка при загрузке мэтчей")
    finally:
        conn.close()

async def start_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    matched_user_id = int(query.data.split('_')[1])
    await query.message.reply_text(
        f"Вы можете написать пользователю:\n"
        f"ID: {matched_user_id}\n"
        f"Или через @username если он указан в профиле"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "Справка по командам:\n"
        "/start - Начало работы\n"
        "/register - Регистрация\n"
        "/profile - Ваш профиль\n"
        "/edit_profile - Редактирование\n"
        "/browse - Просмотр анкет\n"
        "/matches - Ваши мэтчи\n"
        "/help - Эта справка"
    )
    await update.message.reply_text(help_text)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Ошибка:", exc_info=context.error)
    if update and update.message:
        await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")

def setup_registration_conversation():
    return ConversationHandler(
        entry_points=[CommandHandler("register", register_start)],
        states={
            GET_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            GET_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            GET_AGE_PREFERENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age_preference)],
            GET_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gender)],
            GET_GENDER_OTHER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gender_other)],
            GET_PHOTO: [MessageHandler(filters.PHOTO, get_photo)],
            GET_BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_bio)],
            GET_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_city)],
        },
        fallbacks=[CommandHandler("cancel", cancel_edit)],
        allow_reentry=True
    )

def setup_edit_profile_conversation():
    return ConversationHandler(
        entry_points=[CommandHandler("edit_profile", edit_profile)],
        states={
            EDIT_PROFILE: [
                MessageHandler(filters.Regex("^Изменить имя$"), edit_name),
                MessageHandler(filters.Regex("^Изменить возраст$"), edit_age),
                MessageHandler(filters.Regex("^Изменить гендер$"), edit_gender),
                MessageHandler(filters.Regex("^Изменить фото$"), edit_photo),
                MessageHandler(filters.Regex("^Изменить описание$"), edit_bio),
                MessageHandler(filters.Regex("^Изменить город$"), edit_city),
                MessageHandler(filters.Regex("^Изменить возрастные предпочтения$"), edit_age_preference),
                MessageHandler(filters.Regex("^Отмена$"), cancel_edit),
            ],
            EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_name)],
            EDIT_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_age)],
            EDIT_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_gender)],
            EDIT_GENDER_OTHER: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_gender_other_input)],
            EDIT_PHOTO: [MessageHandler(filters.PHOTO, update_photo)],
            EDIT_BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_bio)],
            EDIT_AGE_PREFERENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_age_preference)],
            EDIT_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_city)],
        },
        fallbacks=[CommandHandler("cancel", cancel_edit)],
        allow_reentry=True
    )

def setup_report_conversation():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(report_profile, pattern='^report_')],
        states={
            GET_REPORT_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_report_reason)],
        },
        fallbacks=[CommandHandler("cancel", cancel_edit)],
        allow_reentry=True
    )

def setup_handlers(application: Application) -> None:
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("profile", show_profile))
    application.add_handler(CommandHandler("matches", show_matches))
    application.add_handler(CommandHandler("browse", browse_profiles))
    application.add_handler(setup_registration_conversation())
    application.add_handler(setup_edit_profile_conversation())
    application.add_handler(setup_report_conversation())
    application.add_handler(CallbackQueryHandler(like_profile, pattern='^like_'))
    application.add_handler(CallbackQueryHandler(next_profile, pattern='^next$'))
    application.add_handler(CallbackQueryHandler(start_chat, pattern='^chat_'))
    application.add_handler(CallbackQueryHandler(browse_other_cities, pattern='^other_cities$'))
    application.add_handler(CallbackQueryHandler(browse_my_city, pattern='^my_city$'))
    application.add_handler(CallbackQueryHandler(
        handle_admin_action,
        pattern=r'^(block|warn|ignore)_\d+$'
    ))
    application.add_error_handler(error_handler)

def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            gender TEXT NOT NULL,
            bio TEXT,
            photo_id TEXT NOT NULL,
            is_adult BOOLEAN,
            age_preference TEXT,
            city TEXT,
            is_blocked BOOLEAN DEFAULT FALSE,
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
            admin_action TEXT,
            admin_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (reporter_user_id) REFERENCES users(user_id),
            FOREIGN KEY (reported_user_id) REFERENCES users(user_id),
            FOREIGN KEY (admin_id) REFERENCES users(user_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS viewed_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            viewer_id INTEGER NOT NULL,
            viewed_id INTEGER NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (viewer_id, viewed_id),
            FOREIGN KEY (viewer_id) REFERENCES users(user_id),
            FOREIGN KEY (viewed_id) REFERENCES users(user_id)
        )
    """)
    conn.commit()
    conn.close()

def main() -> None:
    create_tables()
    application = Application.builder().token(BOT_TOKEN).build()
    setup_handlers(application)
    application.run_polling()

if __name__ == "__main__":
    main()

