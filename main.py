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

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN_MEET")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
if not BOT_TOKEN or not ADMIN_CHAT_ID:
    print("Ошибка: Не найден BOT_TOKEN_MEET или ADMIN_CHAT_ID.")
    exit()

DATABASE_NAME = 't4t_meet.db'

# Состояния для ConversationHandler
(
    REGISTER, GET_NAME, GET_AGE, GET_AGE_PREFERENCE, 
    GET_GENDER, GET_GENDER_OTHER, GET_PHOTO, GET_BIO,
    EDIT_PROFILE, EDIT_NAME, EDIT_AGE, EDIT_AGE_PREFERENCE,
    EDIT_GENDER, EDIT_GENDER_OTHER, EDIT_BIO, EDIT_PHOTO,
    REPORT, GET_REPORT_REASON
) = range(18)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
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
        "/edit_profile - Редактировать свой профиль."
    )

    keyboard = [
        [KeyboardButton("/register")],
        [KeyboardButton("/browse"), KeyboardButton("/matches")],
        [KeyboardButton("/profile"), KeyboardButton("/edit_profile")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(rules, reply_markup=reply_markup)

# --- Регистрация профиля ---
async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало регистрации"""
    await update.message.reply_text("Ваше имя: как вас будут видеть другие пользователи?")
    return GET_NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение имени"""
    context.user_data['name'] = update.message.text
    await update.message.reply_text(f"Отлично, ваше имя будет '{context.user_data['name']}'. Теперь скажите, сколько вам лет?")
    return GET_AGE

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение возраста"""
    try:
        age = int(update.message.text)
        if 16 <= age <= 100:
            context.user_data['age'] = age
            context.user_data['is_adult'] = age >= 18
            
            if age >= 18:
                keyboard = [["18-25"], ["26-35"], ["36-45"], ["46+"]]
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
        await update.message.reply_text("Введите число.")
        return GET_AGE

async def get_age_preference(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение возрастных предпочтений (для 18+)"""
    context.user_data['age_preference'] = update.message.text
    keyboard = [["Транс-женщина"], ["Транс-мужчина"], ["Небинарная персона"], ["Другое"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Кем вы себя идентифицируете?", reply_markup=reply_markup)
    return GET_GENDER

async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение гендера"""
    context.user_data['gender'] = update.message.text
    if context.user_data['gender'] == "Другое":
        await update.message.reply_text("Пожалуйста, уточните вашу гендерную идентичность.")
        return GET_GENDER_OTHER
    await update.message.reply_text("Спасибо. Теперь, пожалуйста, загрузите вашу фотографию профиля.")
    return GET_PHOTO

async def get_gender_other(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение уточненного гендера"""
    context.user_data['gender'] = update.message.text
    await update.message.reply_text("Спасибо. Теперь, пожалуйста, загрузите вашу фотографию профиля.")
    return GET_PHOTO

async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение фото"""
    if update.message.photo:
        context.user_data['photo_id'] = update.message.photo[-1].file_id
        await update.message.reply_text("Отлично, фото получено. Теперь расскажите немного о себе (ваши интересы, что вы ищете и т.д.).")
        return GET_BIO
    else:
        await update.message.reply_text("Пожалуйста, отправьте фото.")
        return GET_PHOTO

async def get_bio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение информации о себе"""
    context.user_data['bio'] = update.message.text
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO users 
        (user_id, name, age, gender, bio, photo_id, is_adult, age_preference) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        update.message.from_user.id,
        context.user_data['name'],
        context.user_data['age'],
        context.user_data['gender'],
        context.user_data['bio'],
        context.user_data['photo_id'],
        context.user_data.get('is_adult', False),
        context.user_data.get('age_preference')
    ))
    
    conn.commit()
    conn.close()
    await update.message.reply_text("Профиль создан! Теперь вы можете просматривать анкеты других пользователей с помощью /browse.")
    context.user_data.clear()
    return ConversationHandler.END

# --- Просмотр и редактирование профиля ---
async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показ профиля пользователя"""
    user_id = update.message.from_user.id
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name, age, gender, bio, photo_id, age_preference 
        FROM users WHERE user_id = ?
    """, (user_id,))
    profile = cursor.fetchone()
    conn.close()

    if profile:
        name, age, gender, bio, photo_id, age_preference = profile
        caption = f"Ваш профиль:\nИмя: {name}\nВозраст: {age}\nГендер: {gender}\nО себе: {bio}"
        if age_preference:
            caption += f"\n\nИщу возраст: {age_preference}"
        
        await context.bot.send_photo(
            chat_id=update.message.chat_id,
            photo=photo_id,
            caption=caption
        )
    else:
        await update.message.reply_text("Профиль не найден. Используйте /register для создания профиля.")

async def edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Меню редактирования профиля"""
    user_id = update.message.from_user.id
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT age FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        await update.message.reply_text("Профиль не найден. Используйте /register.")
        return ConversationHandler.END
    
    age = result[0]
    keyboard = [
        ["Изменить имя"],
        ["Изменить возраст"], 
        ["Изменить гендер"],
        ["Изменить фото"],
        ["Изменить описание"]
    ]
    
    if age >= 18:
        keyboard.append(["Изменить возрастные предпочтения"])
    
    keyboard.append(["Отмена"])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Что изменить?", reply_markup=reply_markup)
    return EDIT_PROFILE

async def edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Введите новое имя:")
    return EDIT_NAME

async def update_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_name = update.message.text
    user_id = update.message.from_user.id
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET name = ? WHERE user_id = ?", (new_name, user_id))
    conn.commit()
    conn.close()
    await update.message.reply_text("Имя обновлено!")
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
            
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET age = ?, is_adult = ?
                WHERE user_id = ?
            """, (new_age, is_adult, user_id))
            conn.commit()
            conn.close()
            
            await update.message.reply_text("Возраст обновлен!")
            return ConversationHandler.END
        else:
            await update.message.reply_text("Возраст должен быть от 16 до 100 лет.")
            return EDIT_AGE
    except ValueError:
        await update.message.reply_text("Введите число.")
        return EDIT_AGE

async def edit_age_preference(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [["18-25"], ["26-35"], ["36-45"], ["46+"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Выберите возраст:", reply_markup=reply_markup)
    return EDIT_AGE_PREFERENCE

async def update_age_preference(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_pref = update.message.text
    user_id = update.message.from_user.id
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET age_preference = ? WHERE user_id = ?", (new_pref, user_id))
    conn.commit()
    conn.close()
    await update.message.reply_text("Возрастные предпочтения обновлены!")
    return ConversationHandler.END

async def edit_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [["Транс-женщина"], ["Транс-мужчина"], ["Небинарная персона"], ["Другое"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Выберите гендер:", reply_markup=reply_markup)
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
    await update.message.reply_text("Гендер обновлен!")
    return ConversationHandler.END

async def edit_gender_other_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_gender = update.message.text
    user_id = update.message.from_user.id
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET gender = ? WHERE user_id = ?", (new_gender, user_id))
    conn.commit()
    conn.close()
    await update.message.reply_text("Гендер обновлен!")
    return ConversationHandler.END

async def edit_bio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Введите новое описание:")
    return EDIT_BIO

async def update_bio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_bio = update.message.text
    user_id = update.message.from_user.id
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET bio = ? WHERE user_id = ?", (new_bio, user_id))
    conn.commit()
    conn.close()
    await update.message.reply_text("Описание обновлено!")
    return ConversationHandler.END

async def edit_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Отправьте новое фото:")
    return EDIT_PHOTO

async def update_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.photo:
        new_photo = update.message.photo[-1].file_id
        user_id = update.message.from_user.id
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET photo_id = ? WHERE user_id = ?", (new_photo, user_id))
        conn.commit()
        conn.close()
        await update.message.reply_text("Фото обновлено!")
        return ConversationHandler.END
    else:
        await update.message.reply_text("Пожалуйста, отправьте фото.")
        return EDIT_PHOTO

async def cancel_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Редактирование отменено.")
    return ConversationHandler.END

# --- Просмотр анкет ---
async def browse_profiles(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Просмотр анкет других пользователей"""
    user_id = update.message.from_user.id
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    try:
        # Проверяем, зарегистрирован ли пользователь
        cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        if not cursor.fetchone():
            await update.message.reply_text("Сначала зарегистрируйтесь с помощью /register.")
            return

        # Получаем данные текущего пользователя
        cursor.execute("SELECT age, is_adult, age_preference FROM users WHERE user_id = ?", (user_id,))
        user_data = cursor.fetchone()
        
        if not user_data:
            await update.message.reply_text("Ошибка: данные пользователя не найдены.")
            return
            
        user_age, is_adult, age_preference = user_data
        
        # Формируем запрос в зависимости от возраста
        query = """
            SELECT user_id, name, age, gender, bio, photo_id 
            FROM users 
            WHERE user_id != ? 
            AND is_adult = ?
        """
        params = [user_id, is_adult]
        
        if is_adult and age_preference:
            # Разбираем возрастной диапазон
            if age_preference == "18-25":
                min_age, max_age = 18, 25
            elif age_preference == "26-35":
                min_age, max_age = 26, 35
            elif age_preference == "36-45":
                min_age, max_age = 36, 45
            elif age_preference == "46+":
                min_age, max_age = 46, 100
            
            query += " AND age BETWEEN ? AND ?"
            params.extend([min_age, max_age])
        
        query += " ORDER BY RANDOM() LIMIT 1"
        
        cursor.execute(query, params)
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
                caption=f"Имя: {name}\nВозраст: {age}\nГендер: {gender}\nО себе: {bio}",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text("Нет доступных анкет в выбранной категории.")
    except Exception as e:
        logger.error(f"Ошибка в browse_profiles: {e}", exc_info=True)
        await update.message.reply_text("Ошибка при загрузке анкеты.")
    finally:
        conn.close()

async def like_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка лайка анкеты"""
    query = update.callback_query
    await query.answer()
    
    liked_user_id = int(query.data.split('_')[1])
    liking_user_id = query.from_user.id
    
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    try:
        # Добавляем лайк в базу
        cursor.execute("""
            INSERT INTO matches (user_id_1, user_id_2) 
            VALUES (?, ?)
        """, (liking_user_id, liked_user_id))
        
        # Проверяем взаимный лайк
        cursor.execute("""
            SELECT id 
            FROM matches 
            WHERE user_id_1 = ? AND user_id_2 = ?
        """, (liked_user_id, liking_user_id))
        
        if cursor.fetchone():
            # Если есть взаимный лайк, отмечаем как мэтч
            cursor.execute("""
                UPDATE matches 
                SET is_match = TRUE 
                WHERE (user_id_1 = ? AND user_id_2 = ?)
                OR (user_id_1 = ? AND user_id_2 = ?)
            """, (liking_user_id, liked_user_id, liked_user_id, liking_user_id))
            
            # Получаем имена для уведомления
            cursor.execute("SELECT name FROM users WHERE user_id = ?", (liked_user_id,))
            liked_name = cursor.fetchone()[0]
            
            cursor.execute("SELECT name FROM users WHERE user_id = ?", (liking_user_id,))
            liking_name = cursor.fetchone()[0]
            
            # Уведомляем обоих пользователей
            await context.bot.send_message(
                chat_id=liked_user_id,
                text=f"У вас мэтч с {liking_name}!"
            )
            await context.bot.send_message(
                chat_id=liking_user_id,
                text=f"У вас мэтч с {liked_name}!"
            )
        
        conn.commit()
        
        # Обновляем сообщение
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
    """Показ следующей анкеты"""
    query = update.callback_query
    await query.answer()
    await browse_profiles(update, context)

# --- Жалобы ---
async def report_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало процесса жалобы"""
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
    """Получение причины жалобы"""
    reason = update.message.text
    reporter_id = update.message.from_user.id
    reported_id = context.user_data.get('reported_user_id')
    
    if reported_id:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        try:
            # Сохраняем жалобу в базу
            cursor.execute("""
                INSERT INTO reports 
                (reporter_user_id, reported_user_id, reason) 
                VALUES (?, ?, ?)
            """, (reporter_id, reported_id, reason))
            
            # Получаем имена для уведомления админа
            cursor.execute("SELECT name FROM users WHERE user_id = ?", (reporter_id,))
            reporter_name = cursor.fetchone()[0]
            
            cursor.execute("SELECT name FROM users WHERE user_id = ?", (reported_id,))
            reported_name = cursor.fetchone()[0]
            
            conn.commit()
            
            # Уведомляем админа
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"Жалоба от {reporter_name} (ID: {reporter_id})\n"
                     f"На пользователя {reported_name} (ID: {reported_id})\n"
                     f"Причина: {reason}"
            )
            
            await update.message.reply_text("Жалоба отправлена администратору.")
            return ConversationHandler.END
        except Exception as e:
            logger.error(f"Ошибка в get_report_reason: {e}", exc_info=True)
            await update.message.reply_text("Ошибка при отправке жалобы.")
            return ConversationHandler.END
        finally:
            conn.close()
    else:
        await update.message.reply_text("Ошибка обработки жалобы.")
        return ConversationHandler.END

# --- Мэтчи ---
async def show_matches(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показ мэтчей пользователя"""
    user_id = update.message.from_user.id
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT u.user_id, u.name 
            FROM matches m
            JOIN users u ON (
                (m.user_id_1 = u.user_id AND m.user_id_2 = ?) OR
                (m.user_id_2 = u.user_id AND m.user_id_1 = ?)
            )
            WHERE m.is_match = TRUE
        """, (user_id, user_id))
        
        matches = cursor.fetchall()
        
        if matches:
            message = "Ваши мэтчи:\n"
            keyboard = []
            for match_user_id, match_name in matches:
                message += f"- {match_name}\n"
                keyboard.append([InlineKeyboardButton(
                    f"Написать {match_name}", 
                    callback_data=f'chat_{match_user_id}'
                )])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(message, reply_markup=reply_markup)
        else:
            await update.message.reply_text("У вас пока нет мэтчей.")
    except Exception as e:
        logger.error(f"Ошибка в show_matches: {e}", exc_info=True)
        await update.message.reply_text("Ошибка при загрузке мэтчей.")
    finally:
        conn.close()

async def start_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик кнопки начала чата"""
    query = update.callback_query
    await query.answer()
    
    matched_user_id = int(query.data.split('_')[1])
    await query.message.reply_text(
        f"Вы можете написать пользователю в Telegram: @{query.from_user.username}\n"
        f"Или найти его по ID: {matched_user_id}"
    )

# --- Настройка ConversationHandler ---
def setup_registration_conversation():
    """Настройка диалога регистрации"""
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
        },
        fallbacks=[]
    )

def setup_edit_profile_conversation():
    """Настройка диалога редактирования профиля"""
    return ConversationHandler(
        entry_points=[CommandHandler("edit_profile", edit_profile)],
        states={
            EDIT_PROFILE: [
                MessageHandler(filters.Regex("^Изменить имя$"), edit_name),
                MessageHandler(filters.Regex("^Изменить возраст$"), edit_age),
                MessageHandler(filters.Regex("^Изменить гендер$"), edit_gender),
                MessageHandler(filters.Regex("^Изменить фото$"), edit_photo),
                MessageHandler(filters.Regex("^Изменить описание$"), edit_bio),
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
        },
        fallbacks=[MessageHandler(filters.TEXT & ~filters.COMMAND, cancel_edit)]
    )

def setup_report_conversation():
    """Настройка диалога жалобы"""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(report_profile, pattern='^report_')],
        states={
            GET_REPORT_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_report_reason)],
        },
        fallbacks=[]
    )

def main() -> None:
    """Основная функция запуска бота"""
    application = Application.builder().token(BOT_TOKEN).build()

    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("profile", show_profile))
    application.add_handler(CommandHandler("matches", show_matches))
    application.add_handler(CommandHandler("browse", browse_profiles))
    
    # ConversationHandler
    application.add_handler(setup_registration_conversation())
    application.add_handler(setup_edit_profile_conversation())
    application.add_handler(setup_report_conversation())
    
    # CallbackQueryHandler
    application.add_handler(CallbackQueryHandler(like_profile, pattern='^like_'))
    application.add_handler(CallbackQueryHandler(next_profile, pattern='^next$'))
    application.add_handler(CallbackQueryHandler(start_chat, pattern='^chat_'))

    # Инициализация базы данных
    if not os.path.exists(DATABASE_NAME):
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        # Таблица пользователей
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица мэтчей
        cursor.execute("""
            CREATE TABLE matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id_1 INTEGER NOT NULL,
                user_id_2 INTEGER NOT NULL,
                is_match BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id_1) REFERENCES users(user_id),
                FOREIGN KEY (user_id_2) REFERENCES users(user_id)
            )
        """)
        
        # Таблица жалоб
        cursor.execute("""
            CREATE TABLE reports (
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
