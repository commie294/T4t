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

(
    REGISTER, GET_NAME, GET_AGE, GET_AGE_PREFERENCE, 
    GET_GENDER, GET_GENDER_OTHER, GET_PHOTO, GET_BIO, GET_CITY,
    EDIT_PROFILE, EDIT_NAME, EDIT_AGE, EDIT_AGE_PREFERENCE,
    EDIT_GENDER, EDIT_GENDER_OTHER, EDIT_BIO, EDIT_PHOTO, EDIT_CITY,
    REPORT, GET_REPORT_REASON
) = range(20)

def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

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
    if update.message.from_user.is_bot:
        return ConversationHandler.END
        
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
            context.user_data['is_adult'] = age >= 18
            
            if age >= 18:
                keyboard = [["18-25"], ["26-35"], ["36-45"], ["46+"], ["Все 18+"]]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
                await update.message.reply_text("Какой возраст вас интересует?", reply_markup=reply_markup)
                return GET_AGE_PREFERENCE
            else:
                keyboard = [["Транс-женщина"], ["Транс-мужчина"], ["Небинарная персона"], ["Другое"]]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
                await update.message.reply_text("Кем вы себя идентифицируете?", reply_markup=reply_markup)
                return GET_GENDER
        else:
            await update.message.reply_text("Возраст должен быть от 16 до 100 лет.")
            return GET_AGE
    except ValueError:
        await update.message.reply_text("Введите число.")
        return GET_AGE

async def get_age_preference(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['age_preference'] = update.message.text
    keyboard = [["Транс-женщина"], ["Транс-мужчина"], ["Небинарная персона"], ["Другое"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Кем вы себя идентифицируете?", reply_markup=reply_markup)
    return GET_GENDER

async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['gender'] = update.message.text
    if context.user_data['gender'] == "Другое":
        await update.message.reply_text("Пожалуйста, уточните вашу гендерную идентичность.")
        return GET_GENDER_OTHER
    await update.message.reply_text("Спасибо. Теперь, пожалуйста, загрузите вашу фотографию профиля.")
    return GET_PHOTO

async def get_gender_other(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['gender'] = update.message.text
    await update.message.reply_text("Спасибо. Теперь, пожалуйста, загрузите вашу фотографию профиля.")
    return GET_PHOTO

async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.photo:
        context.user_data['photo_id'] = update.message.photo[-1].file_id
        await update.message.reply_text("Отлично, фото получено. Теперь расскажите немного о себе (ваши интересы, что вы ищете и т.д.).")
        return GET_BIO
    else:
        await update.message.reply_text("Пожалуйста, отправьте фото.")
        return GET_PHOTO

async def get_bio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['bio'] = update.message.text
    await update.message.reply_text("В каком городе вы находитесь? (Необязательно, но поможет находить людей рядом)")
    return GET_CITY

async def get_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['city'] = update.message.text.title() if update.message.text else None
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
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
        await update.message.reply_text("Профиль создан! Теперь вы можете просматривать анкеты других пользователей с помощью /browse.")
    except Exception as e:
        logger.error(f"Ошибка при создании профиля: {e}")
        await update.message.reply_text("Произошла ошибка при создании профиля. Пожалуйста, попробуйте снова.")
    finally:
        conn.close()
        context.user_data.clear()
        return ConversationHandler.END

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'age_preference' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN age_preference TEXT")
        if 'is_adult' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN is_adult BOOLEAN DEFAULT FALSE")
        if 'city' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN city TEXT")
        
        conn.commit()
        
        cursor.execute("""
            SELECT name, age, gender, bio, photo_id, age_preference, city 
            FROM users WHERE user_id = ?
        """, (user_id,))
        profile = cursor.fetchone()

        if profile:
            name = profile['name']
            age = profile['age']
            gender = profile['gender']
            bio = profile['bio']
            photo_id = profile['photo_id']
            age_preference = profile.get('age_preference', 'Не указано')
            city = profile.get('city', 'Не указан')
            
            caption = f"Ваш профиль:\nИмя: {name}\nВозраст: {age}\nГендер: {gender}\nГород: {city}\nО себе: {bio}"
            if age >= 18:
                caption += f"\n\nИщу возраст: {age_preference}"
            
            await context.bot.send_photo(
                chat_id=update.message.chat_id,
                photo=photo_id,
                caption=caption
            )
        else:
            await update.message.reply_text("Профиль не найден. Используйте /register для создания профиля.")
    except Exception as e:
        logger.error(f"Ошибка при показе профиля: {e}")
        await update.message.reply_text("Произошла ошибка при загрузке профиля.")
    finally:
        conn.close()

async def edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'is_adult' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN is_adult BOOLEAN DEFAULT FALSE")
        if 'city' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN city TEXT")
            conn.commit()
        
        cursor.execute("SELECT age, is_adult FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        
        if not result:
            await update.message.reply_text("Профиль не найден. Используйте /register.")
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
        await update.message.reply_text("Произошла ошибка. Пожалуйста, попробуйте снова.")
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
        await update.message.reply_text("Имя обновлено!")
    except Exception as e:
        logger.error(f"Ошибка при обновлении имени: {e}")
        await update.message.reply_text("Произошла ошибка при обновлении имени.")
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
                UPDATE users 
                SET age = ?, is_adult = ?
                WHERE user_id = ?
            """, (new_age, is_adult, user_id))
            conn.commit()
            
            await update.message.reply_text("Возраст обновлен!")
            return ConversationHandler.END
        else:
            await update.message.reply_text("Возраст должен быть от 16 до 100 лет.")
            return EDIT_AGE
    except ValueError:
        await update.message.reply_text("Введите число.")
        return EDIT_AGE
    except Exception as e:
        logger.error(f"Ошибка при обновлении возраста: {e}")
        await update.message.reply_text("Произошла ошибка при обновлении возраста.")
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
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'age_preference' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN age_preference TEXT")
        
        cursor.execute("UPDATE users SET age_preference = ? WHERE user_id = ?", (new_pref, user_id))
        conn.commit()
        await update.message.reply_text("Возрастные предпочтения обновлены!")
    except Exception as e:
        logger.error(f"Ошибка при обновлении предпочтений: {e}")
        await update.message.reply_text("Произошла ошибка при обновлении предпочтений.")
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
        await update.message.reply_text("Гендер обновлен!")
    except Exception as e:
        logger.error(f"Ошибка при обновлении гендера: {e}")
        await update.message.reply_text("Произошла ошибка при обновлении гендера.")
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
        await update.message.reply_text("Гендер обновлен!")
    except Exception as e:
        logger.error(f"Ошибка при обновлении гендера: {e}")
        await update.message.reply_text("Произошла ошибка при обновлении гендера.")
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
        await update.message.reply_text("Описание обновлено!")
    except Exception as e:
        logger.error(f"Ошибка при обновлении описания: {e}")
        await update.message.reply_text("Произошла ошибка при обновлении описания.")
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
            await update.message.reply_text("Фото обновлено!")
            return ConversationHandler.END
        except Exception as e:
            logger.error(f"Ошибка при обновлении фото: {e}")
            await update.message.reply_text("Произошла ошибка при обновлении фото.")
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
        await update.message.reply_text("Город обновлен!" if new_city else "Город удален из профиля")
    except Exception as e:
        logger.error(f"Ошибка при обновлении города: {e}")
        await update.message.reply_text("Произошла ошибка при обновлении города.")
    finally:
        conn.close()
        return ConversationHandler.END

async def cancel_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Редактирование отменено.")
    return ConversationHandler.END

async def browse_profiles(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        if not cursor.fetchone():
            await update.message.reply_text("Сначала зарегистрируйтесь с помощью /register.")
            return

        cursor.execute("SELECT is_adult, age_preference, city FROM users WHERE user_id = ?", (user_id,))
        user_data = cursor.fetchone()
        
        if not user_data:
            await update.message.reply_text("Ошибка: данные пользователя не найдены.")
            return
            
        is_adult, age_preference, user_city = user_data
        
        query = """
            SELECT u.user_id, u.name, u.age, u.gender, u.bio, u.photo_id 
            FROM users u
            LEFT JOIN viewed_profiles v ON u.user_id = v.viewed_id AND v.viewer_id = ?
            WHERE u.user_id != ? 
            AND u.is_adult = ?
            AND u.user_id NOT IN (
                SELECT reported_user_id FROM reports 
                WHERE reporter_user_id = ?
                LIMIT 100
            )
            AND (v.viewed_id IS NULL OR v.timestamp < datetime('now', '-7 days'))
        """
        params = [user_id, user_id, is_adult, user_id]
        
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
        
        if user_city:
            query += " AND (u.city IS NULL OR lower(u.city) = lower(?))"
            params.append(user_city)
        
        query += " ORDER BY v.timestamp ASC, RANDOM() LIMIT 1"
        
        cursor.execute(query, params)
        profile = cursor.fetchone()

        if not profile:
            cursor.execute("""
                SELECT u.user_id, u.name, u.age, u.gender, u.bio, u.photo_id 
                FROM users u
                WHERE u.user_id != ? 
                AND u.is_adult = ?
                AND u.user_id NOT IN (
                    SELECT reported_user_id FROM reports 
                    WHERE reporter_user_id = ?
                    LIMIT 100
                )
                ORDER BY RANDOM()
                LIMIT 1
            """, (user_id, is_adult, user_id))
            profile = cursor.fetchone()

        if profile:
            user_id_browse, name, age, gender, bio, photo_id = profile
            cursor.execute("""
                INSERT OR REPLACE INTO viewed_profiles (viewer_id, viewed_id)
                VALUES (?, ?)
            """, (user_id, user_id_browse))
            conn.commit()

            keyboard = [
                [InlineKeyboardButton("👍 Лайк", callback_data=f'like_{user_id_browse}')],
                [InlineKeyboardButton("➡️ Следующая анкета", callback_data='next')],
                [InlineKeyboardButton("⚠️ Пожаловаться", callback_data=f'report_{user_id_browse}')],
                [InlineKeyboardButton("🌍 Показать из других городов", callback_data='other_cities')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            caption = f"Имя: {name}\nВозраст: {age}\nГендер: {gender}\nО себе: {bio}"
            await context.bot.send_photo(
                chat_id=update.message.chat_id,
                photo=photo_id,
                caption=caption,
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text("Нет доступных анкет. Попробуйте изменить критерии поиска в /edit_profile или попробуйте позже.")
    except Exception as e:
        logger.error(f"Ошибка в browse_profiles: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка. Пожалуйста, попробуйте позже.")
    finally:
        conn.close()

async def browse_other_cities(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT is_adult, age_preference FROM users WHERE user_id = ?", (user_id,))
        user_data = cursor.fetchone()
        
        if not user_data:
            await query.edit_message_text("Ошибка: данные пользователя не найдены.")
            return
            
        is_adult, age_preference = user_data
        
        query_sql = """
            SELECT u.user_id, u.name, u.age, u.gender, u.bio, u.photo_id, u.city
            FROM users u
            LEFT JOIN viewed_profiles v ON u.user_id = v.viewed_id AND v.viewer_id = ?
            WHERE u.user_id != ? 
            AND u.is_adult = ?
            AND u.user_id NOT IN (
                SELECT reported_user_id FROM reports 
                WHERE reporter_user_id = ?
                LIMIT 100
            )
        """
        params = [user_id, user_id, is_adult, user_id]
        
        if is_adult and age_preference and age_preference != "Все 18+":
            age_ranges = {
                "18-25": (18, 25),
                "26-35": (26, 35),
                "36-45": (36, 45),
                "46+": (46, 100)
            }
            if age_preference in age_ranges:
                min_age, max_age = age_ranges[age_preference]
                query_sql += " AND u.age BETWEEN ? AND ?"
                params.extend([min_age, max_age])
        
        query_sql += " ORDER BY RANDOM() LIMIT 1"
        
        cursor.execute(query_sql, params)
        profile = cursor.fetchone()

        if profile:
            user_id_browse, name, age, gender, bio, photo_id, city = profile
            cursor.execute("""
                INSERT OR REPLACE INTO viewed_profiles (viewer_id, viewed_id)
                VALUES (?, ?)
            """, (user_id, user_id_browse))
            conn.commit()

            keyboard = [
                [InlineKeyboardButton("👍 Лайк", callback_data=f'like_{user_id_browse}')],
                [InlineKeyboardButton("➡️ Следующая анкета", callback_data='next')],
                [InlineKeyboardButton("⚠️ Пожаловаться", callback_data=f'report_{user_id_browse}')],
                [InlineKeyboardButton("🏙️ Показать из моего города", callback_data='my_city')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            caption = f"Имя: {name}\nВозраст: {age}\nГендер: {gender}\nГород: {city or 'Не указан'}\nО себе: {bio}"
            await query.edit_message_caption(
                caption=caption,
                reply_markup=reply_markup
            )
        else:
            await query.edit_message_text("Нет доступных анкет.")
    except Exception as e:
        logger.error(f"Ошибка в browse_other_cities: {e}", exc_info=True)
        await query.answer("Ошибка при загрузке анкет")
    finally:
        conn.close()

async def like_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    liked_user_id = int(query.data.split('_')[1])
    liking_user_id = query.from_user.id
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT 1 FROM matches 
            WHERE user_id_1 = ? AND user_id_2 = ?
        """, (liking_user_id, liked_user_id))
        
        if cursor.fetchone():
            await query.answer("Вы уже лайкнули этот профиль", show_alert=True)
            return
            
        cursor.execute("""
            INSERT INTO matches (user_id_1, user_id_2) 
            VALUES (?, ?)
        """, (liking_user_id, liked_user_id))
        
        cursor.execute("""
            SELECT id 
            FROM matches 
            WHERE user_id_1 = ? AND user_id_2 = ?
        """, (liked_user_id, liking_user_id))
        
        if cursor.fetchone():
            cursor.execute("""
                UPDATE matches 
                SET is_match = TRUE 
                WHERE (user_id_1 = ? AND user_id_2 = ?)
                OR (user_id_1 = ? AND user_id_2 = ?)
            """, (liking_user_id, liked_user_id, liked_user_id, liking_user_id))
            
            cursor.execute("SELECT name FROM users WHERE user_id = ?", (liked_user_id,))
            liked_name = cursor.fetchone()[0]
            
            cursor.execute("SELECT name FROM users WHERE user_id = ?", (liking_user_id,))
            liking_name = cursor.fetchone()[0]
            
            await context.bot.send_message(
                chat_id=liked_user_id,
                text=f"У вас мэтч с {liking_name}!"
            )
            await context.bot.send_message(
                chat_id=liking_user_id,
                text=f"У вас мэтч с {liked_name}!"
            )
        
        conn.commit()
        
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
        logger.error(f"Ошибка в like_profile: {e}", exc_info=True)
        await query.answer("Ошибка при обработке лайка.", show_alert=True)
    finally:
        conn.close()

async def next_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await browse_profiles(update, context)

async def report_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    reported_user_id = int(query.data.split('_')[1])
    context.user_data['reported_user_id'] = reported_user_id
    
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="Опишите причину жалобы:"
    )
    return GET_REPORT_REASON

async def get_report_reason(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reason = update.message.text
    reporter_id = update.message.from_user.id
    reported_id = context.user_data.get('reported_user_id')
    
    if not reported_id:
        await update.message.reply_text("Ошибка: не найден ID пользователя для жалобы")
        return ConversationHandler.END
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 1 FROM reports 
            WHERE reporter_user_id = ? AND reported_user_id = ?
            LIMIT 1
        """, (reporter_id, reported_id))
        
        if cursor.fetchone():
            await update.message.reply_text("Вы уже жаловались на этого пользователя.")
            return ConversationHandler.END
            
        cursor.execute("""
            INSERT INTO reports 
            (reporter_user_id, reported_user_id, reason) 
            VALUES (?, ?, ?)
        """, (reporter_id, reported_id, reason))
        
        cursor.execute("SELECT name FROM users WHERE user_id = ?", (reporter_id,))
        reporter_result = cursor.fetchone()
        reporter_name = reporter_result['name'] if reporter_result else "Unknown"
        
        cursor.execute("SELECT name FROM users WHERE user_id = ?", (reported_id,))
        reported_result = cursor.fetchone()
        reported_name = reported_result['name'] if reported_result else "Unknown"
        
        conn.commit()
        
        keyboard = [
            [
                InlineKeyboardButton("🔨 Заблокировать", callback_data=f'block_{reported_id}'),
                InlineKeyboardButton("⚠️ Предупредить", callback_data=f'warn_{reported_id}')
            ],
            [
                InlineKeyboardButton("❌ Отклонить жалобу", callback_data=f'ignore_{reported_id}')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"🚨 Новая жалоба:\n"
                 f"От: {reporter_name} (ID: {reporter_id})\n"
                 f"На: {reported_name} (ID: {reported_id})\n"
                 f"Причина: {reason}",
            reply_markup=reply_markup
        )
        
        await update.message.reply_text("✅ Жалоба отправлена администраторам")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке жалобы: {e}")
        await update.message.reply_text("❌ Ошибка при отправке жалобы. Попробуйте позже.")
    finally:
        conn.close()
    
    return ConversationHandler.END

async def handle_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if str(query.from_user.id) != ADMIN_CHAT_ID:
        await query.answer("Только администратор может выполнять это действие", show_alert=True)
        return
    
    action, user_id = query.data.split('_')
    user_id = int(user_id)
    admin_id = query.from_user.id
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        if action == 'block':
            cursor.execute("UPDATE users SET is_blocked = TRUE WHERE user_id = ?", (user_id,))
            
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ Ваш аккаунт заблокирован администратором"
                )
            except Exception as e:
                logger.error(f"Не удалось уведомить пользователя: {e}")
                
            action_text = "заблокирован"
            
        elif action == 'warn':
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="⚠️ Вы получили предупреждение от администратора"
                )
            except Exception as e:
                logger.error(f"Не удалось отправить предупреждение: {e}")
                
            action_text = "получил предупреждение"
        
        elif action == 'ignore':
            action_text = "жалоба отклонена"
        
        cursor.execute("""
            UPDATE reports 
            SET admin_action = ?
            WHERE reported_user_id = ?
            ORDER BY created_at DESC 
            LIMIT 1
        """, (f"{action} by admin {admin_id}", user_id))
        
        conn.commit()
        
        await query.edit_message_text(
            text=f"✅ Действие выполнено: пользователь {user_id} {action_text}",
            reply_markup=None
        )
        
    except Exception as e:
        logger.error(f"Ошибка обработки действия админа: {e}")
        await query.answer("Ошибка при обработке действия", show_alert=True)
    finally:
        conn.close()

async def show_matches(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT u.user_id, u.name, u.photo_id
            FROM matches m
            JOIN users u ON (
                (m.user_id_1 = u.user_id AND m.user_id_2 = ?) OR
                (m.user_id_2 = u.user_id AND m.user_id_1 = ?)
            )
            WHERE m.is_match = TRUE
        """, (user_id, user_id))
        
        matches = cursor.fetchall()
        
        if matches:
            for match_user_id, match_name, photo_id in matches:
                keyboard = [
                    [InlineKeyboardButton(
                        f"Написать {match_name}", 
                        callback_data=f'chat_{match_user_id}'
                    )]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await context.bot.send_photo(
                    chat_id=update.message.chat_id,
                    photo=photo_id,
                    caption=f"Мэтч с {match_name}",
                    reply_markup=reply_markup
                )
        else:
            await update.message.reply_text("У вас пока нет мэтчей.")
    except Exception as e:
        logger.error(f"Ошибка в show_matches: {e}", exc_info=True)
        await update.message.reply_text("Ошибка при загрузке мэтчей.")
    finally:
        conn.close()

async def start_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    matched_user_id = int(query.data.split('_')[1])
    await query.message.reply_text(
        f"Вы можете написать пользователю в Telegram: @{query.from_user.username}\n"
        f"Или найти его по ID: {matched_user_id}"
    )

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

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "Список доступных команд:\n"
        "/start - Начало работы с ботом\n"
        "/register - Регистрация профиля\n"
        "/profile - Просмотр своего профиля\n"
        "/edit_profile - Редактирование профиля\n"
        "/browse - Просмотр анкет\n"
        "/matches - Ваши мэтчи\n"
        "/help - Справка по командам\n\n"
        "По всем вопросам обращайтесь к администратору."
    )
    await update.message.reply_text(help_text)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Ошибка при обработке запроса:", exc_info=context.error)
    
    if update and update.message:
        await update.message.reply_text(
            "Произошла ошибка. Пожалуйста, попробуйте позже или обратитесь к администратору."
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
    application.add_handler(CallbackQueryHandler(browse_profiles, pattern='^my_city$'))
    application.add_handler(CallbackQueryHandler(
        handle_admin_action, 
        pattern=r'^(block|warn|ignore)_\d+$'
    ))
    
    application.add_error_handler(error_handler)

def initialize_database():
    if not os.path.exists(DATABASE_NAME):
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                CREATE TABLE users (
                    user_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    age INTEGER NOT NULL,
                    gender TEXT NOT NULL,
                    bio TEXT,
                    photo_id TEXT NOT NULL,
                    is_adult BOOLEAN DEFAULT FALSE,
                    age_preference TEXT,
                    city TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_blocked BOOLEAN DEFAULT FALSE
                )
            """)
            
            cursor.execute("""
                CREATE TABLE matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id_1 INTEGER NOT NULL,
                    user_id_2 INTEGER NOT NULL,
                    is_match BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id_1) REFERENCES users(user_id),
                    FOREIGN KEY (user_id_2) REFERENCES users(user_id),
                    UNIQUE(user_id_1, user_id_2)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reporter_user_id INTEGER NOT NULL,
                    reported_user_id INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    admin_action TEXT,
                    admin_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (reporter_user_id) REFERENCES users(user_id),
                    FOREIGN KEY (reported_user_id) REFERENCES users(user_id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE viewed_profiles (
                    viewer_id INTEGER NOT NULL,
                    viewed_id INTEGER NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (viewer_id) REFERENCES users(user_id),
                    FOREIGN KEY (viewed_id) REFERENCES users(user_id),
                    PRIMARY KEY (viewer_id, viewed_id)
                )
            """)
            
            conn.commit()
            logger.info("База данных успешно инициализирована")
        except Exception as e:
            logger.error(f"Ошибка при инициализации базы данных: {e}")
        finally:
            conn.close()

def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()
    
    initialize_database()
    setup_handlers(application)
    
    application.run_polling()

if __name__ == "__main__":
    main()
