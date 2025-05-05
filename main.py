import json
import logging
import os
import shutil
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Load environment variables from .env file with explicit path
load_dotenv('/home/venikpes/T4t/.env')

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')

# Debug: Print the loaded BOT_TOKEN to verify
print(f"Loaded BOT_TOKEN: {BOT_TOKEN}")

# JSON database file with absolute path
DB_FILE = '/home/venikpes/T4t/db.json'
DB_BACKUP_FILE = '/home/venikpes/T4t/db_backup.json'
DB_RESTORE_FILE = '/home/venikpes/T4t/db_restore.json'

# Conversation states
(
    REGISTER, GET_NAME, GET_AGE, GET_GENDER, GET_GENDER_OTHER, GET_PHOTO, GET_BIO,
    EDIT_PROFILE, EDIT_NAME, EDIT_AGE, EDIT_GENDER, EDIT_GENDER_OTHER, EDIT_CITY, EDIT_PHOTO, EDIT_BIO,
    REPORT, GET_REPORT_REASON, GET_REPORT_SCREENSHOT,
    FEEDBACK, GET_FEEDBACK_MESSAGE, GET_FEEDBACK_CONTACT
) = range(21)

def load_db():
    """Load JSON database with improved error handling and restoration check."""
    # Check for restoration file and apply it
    if os.path.exists(DB_RESTORE_FILE):
        logger.info(f"Restoration file {DB_RESTORE_FILE} found. Applying to {DB_FILE}")
        try:
            shutil.copyfile(DB_RESTORE_FILE, DB_FILE)
            os.remove(DB_RESTORE_FILE)
            logger.info(f"Restored {DB_FILE} from {DB_RESTORE_FILE}")
        except Exception as e:
            logger.error(f"Failed to restore database: {e}")
            raise Exception(f"Database restoration failed: {e}")

    if not os.path.exists(DB_FILE):
        logger.warning(f"Database file {DB_FILE} not found. Initializing new database.")
        default_db = {
            "users": [],
            "blocked": [],
            "likes": [],
            "matches": [],
            "reports": [],
            "feedback": []
        }
        # Create the file to ensure it exists for future operations
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_db, f, ensure_ascii=False, indent=2)
        logger.info("Initialized new database with empty users array")
        return default_db

    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Successfully loaded database from {DB_FILE}")
        logger.info(f"Number of users in database: {len(data['users'])}")
        if len(data['users']) > 0:
            logger.info(f"Sample user: {data['users'][0]}")
        return data
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to load database from {DB_FILE}: {e}")
        # Check if a backup exists
        if os.path.exists(DB_BACKUP_FILE):
            logger.info(f"Attempting to load backup database from {DB_BACKUP_FILE}")
            try:
                with open(DB_BACKUP_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.info(f"Successfully loaded backup database")
                logger.info(f"Number of users in backup database: {len(data['users'])}")
                # Restore the main database from backup
                with open(DB_FILE, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                return data
            except (json.JSONDecodeError, IOError) as backup_e:
                logger.error(f"Failed to load backup database: {backup_e}")
        raise Exception(f"Database load failed: {e}. Backup also unavailable or corrupted.")

def save_db(data):
    """Save JSON database with backup."""
    # Create a backup of the current database
    if os.path.exists(DB_FILE):
        try:
            shutil.copyfile(DB_FILE, DB_BACKUP_FILE)
            logger.info(f"Created backup of database at {DB_BACKUP_FILE}")
        except Exception as e:
            logger.error(f"Failed to create backup of database: {e}")

    # Save the new database
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Successfully saved database to {DB_FILE}")
    except Exception as e:
        logger.error(f"Failed to save database to {DB_FILE}: {e}")
        raise Exception(f"Database save failed: {e}")

def get_main_menu():
    """Return the main menu as an InlineKeyboardMarkup."""
    keyboard = [
        [InlineKeyboardButton("📝 Регистрация", callback_data="menu_register"),
         InlineKeyboardButton("🔍 Просмотр анкет", callback_data="menu_browse")],
        [InlineKeyboardButton("💖 Мэтчи", callback_data="menu_matches"),
         InlineKeyboardButton("👤 Мой профиль", callback_data="menu_profile")],
        [InlineKeyboardButton("✏️ Редактировать профиль", callback_data="menu_edit_profile"),
         InlineKeyboardButton("💬 Обратная связь", callback_data="menu_feedback")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message with rules and display the main menu as inline buttons."""
    logger.info(f"Received /start from user: {update.effective_user.id}")
    rules = (
        "Добро пожаловать в T4t Meet!\n\n"
        "Подпишитесь на наш канал: https://t.me/tperehod\n"
        "Пожалуйста, ознакомьтесь с нашими правилами:\n"
        "1. Будьте уважительны к другим участникам.\n"
        "2. Запрещены оскорбления, дискриминация и нетерпимость. Анкеты цисгендеров будут блокироваться.\n"
        "3. Не публикуйте контент 18+ и другой неприемлемый материал.\n"
        "4. Соблюдайте конфиденциальность личной информации других пользователей.\n"
        "5. Администрация оставляет за собой право удалять профили и блокировать пользователей за нарушения.\n\n"
        "Выберите действие из меню ниже:"
    )
    reply_markup = get_main_menu()
    await update.message.reply_text(rules, reply_markup=reply_markup)

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle menu button clicks by triggering corresponding commands."""
    query = update.callback_query
    await query.answer()
    command = query.data
    logger.info(f"Menu button clicked by user {query.from_user.id}: {command}")

    if command == "menu_register":
        logger.info("Routing to register_start")
        return await register_start(update, context)
    elif command == "menu_browse":
        logger.info("Routing to browse_profiles")
        return await browse_profiles(update, context)
    elif command == "menu_matches":
        logger.info("Routing to matches")
        return await matches(update, context)
    elif command == "menu_profile":
        logger.info("Routing to profile")
        return await profile(update, context)
    elif command == "menu_edit_profile":
        logger.info("Routing to edit_profile")
        return await edit_profile(update, context)
    elif command == "menu_feedback":
        logger.info("Routing to feedback_start")
        return await feedback_start(update, context)
    else:
        logger.warning(f"Unknown menu command: {command}")
        await query.message.reply_text("Неизвестная команда.", reply_markup=get_main_menu())

async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start registration process."""
    if update.callback_query:
        query = update.callback_query
        chat_id = query.message.chat_id
        message_id = query.message.message_id
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    else:
        chat_id = update.message.chat_id

    logger.info(f"Received /register from user: {update.effective_user.id}")
    db = load_db()
    if any(u['telegram_id'] == update.effective_user.id for u in db['users']):
        await context.bot.send_message(chat_id, "Вы уже зарегистрированы! Используйте 'Мой профиль' или 'Редактировать профиль'.", reply_markup=get_main_menu())
        return ConversationHandler.END
    await context.bot.send_message(chat_id, "Ваше имя: как вас будут видеть другие пользователи?", reply_markup=ReplyKeyboardRemove())
    return GET_NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle name input."""
    user_id = update.effective_user.id
    logger.info(f"Received text message for name input from user {user_id}: {update.message.text}")
    if not update.message.text:
        logger.warning(f"No text received from user {user_id} for name input")
        await update.message.reply_text("Пожалуйста, введите ваше имя текстом.")
        return GET_NAME
    context.user_data['name'] = update.message.text
    logger.info(f"Stored name for user {user_id}: {context.user_data['name']}")
    await update.message.reply_text(f"Отлично, ваше имя будет '{context.user_data['name']}'. Теперь скажите, сколько вам лет?")
    return GET_AGE

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle age input with validation."""
    user_id = update.effective_user.id
    logger.info(f"Received text message for age input from user {user_id}: {update.message.text}")
    try:
        age = int(update.message.text)
        if 16 <= age <= 100:
            context.user_data['age'] = age
            logger.info(f"Stored age for user {user_id}: {age}")
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

async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle gender selection."""
    user_id = update.effective_user.id
    gender = update.message.text
    logger.info(f"Received gender selection from user {user_id}: {gender}")
    context.user_data['gender'] = gender
    if gender == "Другое":
        await update.message.reply_text("Пожалуйста, уточните вашу гендерную идентичность.")
        return GET_GENDER_OTHER
    await update.message.reply_text("Введите ваш город (или 'Any' для всех городов):")
    return GET_PHOTO

async def get_gender_other(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom gender input."""
    user_id = update.effective_user.id
    gender = update.message.text
    logger.info(f"Received custom gender from user {user_id}: {gender}")
    context.user_data['gender'] = gender
    await update.message.reply_text("Введите ваш город (или 'Any' для всех городов):")
    return GET_PHOTO

async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle city input."""
    user_id = update.effective_user.id
    city = update.message.text.strip()
    logger.info(f"Received city from user {user_id}: {city}")
    context.user_data['city'] = city if city.lower() != 'any' else None
    await update.message.reply_text("Пожалуйста, загрузите вашу фотографию профиля.")
    return GET_BIO

async def get_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo and bio input."""
    user_id = update.effective_user.id
    if update.message.photo:
        logger.info(f"Received photo from user {user_id}")
        context.user_data['photo_id'] = update.message.photo[-1].file_id
        await update.message.reply_text("Отлично, фото получено. Теперь расскажите немного о себе (ваши интересы, что вы ищете и т.д.).")
        return REGISTER
    else:
        logger.warning(f"No photo received from user {user_id}")
        await update.message.reply_text("Пожалуйста, отправьте фотографию.")
        return GET_BIO

async def complete_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save profile and complete registration."""
    user = update.effective_user
    logger.info(f"Completing registration for user {user.id}")
    db = load_db()
    profile = {
        'telegram_id': user.id,
        'username': user.username or f"user_{user.id}",
        'name': context.user_data['name'],
        'age': context.user_data['age'],
        'gender': context.user_data['gender'],
        'city': context.user_data['city'],
        'bio': update.message.text,
        'photo_id': context.user_data['photo_id']
    }
    db['users'].append(profile)
    save_db(db)
    await update.message.reply_text("Спасибо за регистрацию! Ваш профиль создан.", reply_markup=get_main_menu())
    context.user_data.clear()
    return ConversationHandler.END

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user profile with photo."""
    if update.callback_query:
        query = update.callback_query
        chat_id = query.message.chat_id
        message_id = query.message.message_id
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    else:
        chat_id = update.message.chat_id

    user_id = update.effective_user.id
    logger.info(f"Showing profile for user: {user_id}")
    db = load_db()
    user_profile = next((u for u in db['users'] if u['telegram_id'] == user_id), None)
    if not user_profile:
        logger.info(f"Profile not found for user {user_id}")
        await context.bot.send_message(chat_id, "Ваш профиль не найден. Пожалуйста, зарегистрируйтесь.", reply_markup=get_main_menu())
        return
    logger.info(f"Found profile for user {user_id}: {user_profile}")
    caption = (
        f"Ваш профиль:\n"
        f"Имя: {user_profile['name']}\n"
        f"Возраст: {user_profile['age']}\n"
        f"Пол: {user_profile['gender']}\n"
        f"Город: {user_profile['city'] or 'Не указан'}\n"
        f"О себе: {user_profile['bio']}"
    )
    await context.bot.send_photo(
        chat_id=chat_id,
        photo=user_profile['photo_id'],
        caption=caption,
        reply_markup=get_main_menu()
    )

async def edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start profile editing."""
    if update.callback_query:
        query = update.callback_query
        chat_id = query.message.chat_id
        message_id = query.message.message_id
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        message = await context.bot.send_message(chat_id, "Что вы хотите изменить в своем профиле?")
    else:
        message = update.message

    logger.info(f"Received edit_profile from user: {update.effective_user.id}")
    keyboard = [
        ["Изменить имя"],
        ["Изменить возраст"],
        ["Изменить пол"],
        ["Изменить город"],
        ["Изменить фото"],
        ["Изменить био"],
        ["Отмена"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await message.reply_text("Что вы хотите изменить в своем профиле?", reply_markup=reply_markup)
    return EDIT_PROFILE

async def edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle name edit."""
    await update.message.reply_text("Пожалуйста, введите новое имя.")
    return EDIT_NAME

async def update_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Update name in profile."""
    new_name = update.message.text
    user_id = update.effective_user.id
    db = load_db()
    for user in db['users']:
        if user['telegram_id'] == user_id:
            user['name'] = new_name
            break
    save_db(db)
    await update.message.reply_text(f"Ваше имя обновлено на '{new_name}'.", reply_markup=get_main_menu())
    return ConversationHandler.END

async def edit_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle age edit."""
    await update.message.reply_text("Пожалуйста, введите новый возраст.")
    return EDIT_AGE

async def update_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Update age in profile."""
    try:
        new_age = int(update.message.text)
        if 16 <= new_age <= 100:
            user_id = update.effective_user.id
            db = load_db()
            for user in db['users']:
                if user['telegram_id'] == user_id:
                    user['age'] = new_age
                    break
            save_db(db)
            await update.message.reply_text(f"Ваш возраст обновлен на '{new_age}'.", reply_markup=get_main_menu())
            return ConversationHandler.END
        else:
            await update.message.reply_text("Пожалуйста, введите корректный возраст (от 16 до 100 лет).")
            return EDIT_AGE
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите возраст цифрами.")
        return EDIT_AGE

async def edit_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle gender edit."""
    keyboard = [["Транс-женщина"], ["Транс-мужчина"], ["Небинарная персона"], ["Другое"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Пожалуйста, выберите новый пол.", reply_markup=reply_markup)
    return EDIT_GENDER

async def update_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Update gender in profile."""
    new_gender = update.message.text
    if new_gender == "Другое":
        await update.message.reply_text("Пожалуйста, уточните вашу гендерную идентичность.")
        return EDIT_GENDER_OTHER
    user_id = update.effective_user.id
    db = load_db()
    for user in db['users']:
        if user['telegram_id'] == user_id:
            user['gender'] = new_gender
            break
    save_db(db)
    await update.message.reply_text(f"Ваш пол обновлен на '{new_gender}'.", reply_markup=get_main_menu())
    return ConversationHandler.END

async def edit_gender_other(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Update custom gender in profile."""
    new_gender = update.message.text
    user_id = update.effective_user.id
    db = load_db()
    for user in db['users']:
        if user['telegram_id'] == user_id:
            user['gender'] = new_gender
            break
    save_db(db)
    await update.message.reply_text(f"Ваш пол обновлен на '{new_gender}'.", reply_markup=get_main_menu())
    return ConversationHandler.END

async def edit_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle city edit."""
    await update.message.reply_text("Пожалуйста, введите новый город (или 'Any' для всех городов).")
    return EDIT_CITY

async def update_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Update city in profile."""
    new_city = update.message.text.strip()
    user_id = update.effective_user.id
    db = load_db()
    for user in db['users']:
        if user['telegram_id'] == user_id:
            user['city'] = new_city if new_city.lower() != 'any' else None
            break
    save_db(db)
    await update.message.reply_text(f"Ваш город обновлен на '{new_city or 'Не указан'}'.", reply_markup=get_main_menu())
    return ConversationHandler.END

async def edit_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo edit."""
    await update.message.reply_text("Пожалуйста, отправьте новую фотографию профиля.")
    return EDIT_PHOTO

async def update_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Update photo in profile."""
    if update.message.photo:
        new_photo_id = update.message.photo[-1].file_id
        user_id = update.effective_user.id
        db = load_db()
        for user in db['users']:
            if user['telegram_id'] == user_id:
                user['photo_id'] = new_photo_id
                break
        save_db(db)
        await update.message.reply_text("Ваша фотография профиля обновлена.", reply_markup=get_main_menu())
        return ConversationHandler.END
    else:
        await update.message.reply_text("Пожалуйста, отправьте фотографию.")
        return EDIT_PHOTO

async def edit_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle bio edit."""
    await update.message.reply_text("Пожалуйста, введите новое описание профиля.")
    return EDIT_BIO

async def update_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Update bio in profile."""
    new_bio = update.message.text
    user_id = update.effective_user.id
    db = load_db()
    for user in db['users']:
        if user['telegram_id'] == user_id:
            user['bio'] = new_bio
            break
    save_db(db)
    await update.message.reply_text("Ваше описание профиля обновлено.", reply_markup=get_main_menu())
    return ConversationHandler.END

async def cancel_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel profile editing."""
    await update.message.reply_text("Редактирование профиля отменено.", reply_markup=get_main_menu())
    return ConversationHandler.END

async def browse_profiles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Browse profiles sequentially with filters."""
    if update.callback_query:
        query = update.callback_query
        chat_id = query.message.chat_id
        message_id = query.message.message_id
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    else:
        chat_id = update.message.chat_id

    user_id = update.effective_user.id
    logger.info(f"Received browse_profiles from user: {user_id}")
    db = load_db()
    logger.info(f"Total users in database: {len(db['users'])}")
    user_profile = next((u for u in db['users'] if u['telegram_id'] == user_id), None)
    if not user_profile:
        logger.info(f"User {user_id} not registered")
        await context.bot.send_message(chat_id, "Пожалуйста, зарегистрируйтесь.", reply_markup=get_main_menu())
        return
    logger.info(f"User profile: {user_profile}")
    blocked_ids = [b['blocked_id'] for b in db['blocked'] if b['blocker_id'] == user_id]
    logger.info(f"Blocked IDs for user {user_id}: {blocked_ids}")
    profiles = [
        u for u in db['users']
        if u['telegram_id'] != user_id and u['telegram_id'] not in blocked_ids
    ]
    logger.info(f"Profiles after filtering self and blocked: {len(profiles)}")
    if user_profile['age'] < 18:
        profiles = [u for u in profiles if u['age'] < 18]
        logger.info(f"Profiles after age filter (<18): {len(profiles)}")
    else:
        profiles = [u for u in profiles if u['age'] >= 18]
        logger.info(f"Profiles after age filter (>=18): {len(profiles)}")
    if user_profile['city']:
        profiles = [u for u in profiles if u['city'] == user_profile['city'] or u['city'] is None]
        logger.info(f"Profiles after city filter ({user_profile['city']}): {len(profiles)}")
    if not profiles:
        logger.info("No profiles available to browse after all filters")
        await context.bot.send_message(chat_id, "Пока нет доступных анкет для просмотра.", reply_markup=get_main_menu())
        return
    logger.info(f"Available profiles to browse: {profiles}")
    context.user_data['profiles'] = profiles
    context.user_data['current_profile'] = 0
    await show_profile(update, context)

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display a profile with options."""
    if update.message:
        chat_id = update.message.chat_id
    else:
        chat_id = update.callback_query.message.chat_id

    profiles = context.user_data.get('profiles', [])
    index = context.user_data.get('current_profile', 0)
    if not profiles or index >= len(profiles):
        logger.info("No more profiles to display")
        await context.bot.send_message(chat_id, "Нет больше анкет для просмотра.", reply_markup=get_main_menu())
        return
    profile = profiles[index]
    logger.info(f"Displaying profile for user: {profile['telegram_id']}")
    keyboard = [
        [InlineKeyboardButton("👍 Лайк", callback_data=f"like_{profile['telegram_id']}")],
        [InlineKeyboardButton("➡️ Следующая анкета", callback_data="next")],
        [InlineKeyboardButton("⚠️ Пожаловаться", callback_data=f"report_{profile['telegram_id']}")],
        [InlineKeyboardButton("⬅️ Главное меню", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=profile['photo_id'],
            caption=f"Имя: {profile['name']}\nВозраст: {profile['age']}\nПол: {profile['gender']}\nГород: {profile['city'] or 'Не указан'}\nО себе: {profile['bio']}",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error displaying profile: {e}")
        await context.bot.send_message(chat_id, f"Ошибка при отображении анкеты: {e}", reply_markup=get_main_menu())

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to the main menu."""
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    await context.bot.send_message(chat_id, "Выберите действие:", reply_markup=get_main_menu())

async def like_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle profile like and check for matches."""
    query = update.callback_query
    await query.answer()
    logger.info(f"Received like from user: {query.from_user.id} for user: {query.data}")
    liked_user_id = int(query.data.split('_')[1])
    liking_user_id = query.from_user.id
    db = load_db()
    db['likes'].append({'liker_id': liking_user_id, 'liked_id': liked_user_id})
    if any(l['liker_id'] == liked_user_id and l['liked_id'] == liking_user_id for l in db['likes']):
        db['matches'].append({'user1_id': min(liking_user_id, liked_user_id), 'user2_id': max(liking_user_id, liked_user_id)})
        liked_user = next(u for u in db['users'] if u['telegram_id'] == liked_user_id)
        liking_user = next(u for u in db['users'] if u['telegram_id'] == liking_user_id)
        await context.bot.send_message(liked_user_id, f"У вас мэтч с {liking_user['name']}!")
        await context.bot.send_message(liking_user_id, f"У вас мэтч с {liking_user['name']}!")
    save_db(db)
    keyboard = [
        [InlineKeyboardButton("➡️ Следующая анкета", callback_data="next")],
        [InlineKeyboardButton("⚠️ Пожаловаться", callback_data=f"report_{liked_user_id}")],
        [InlineKeyboardButton("⬅️ Главное меню", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_caption(
        caption=f"{query.message.caption}\n\n❤️ Вы поставили лайк!",
        reply_markup=reply_markup
    )

async def next_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show next profile sequentially."""
    query = update.callback_query
    await query.answer()
    logger.info(f"Received next from user: {query.from_user.id}")
    context.user_data['current_profile'] = context.user_data.get('current_profile', 0) + 1
    profiles = context.user_data.get('profiles', [])
    index = context.user_data['current_profile']
    if index >= len(profiles):
        await query.message.delete()
        await query.message.reply_text("Нет больше анкет для просмотра.", reply_markup=get_main_menu())
        return
    profile = profiles[index]
    keyboard = [
        [InlineKeyboardButton("👍 Лайк", callback_data=f"like_{profile['telegram_id']}")],
        [InlineKeyboardButton("➡️ Следующая анкета", callback_data="next")],
        [InlineKeyboardButton("⚠️ Пожаловаться", callback_data=f"report_{profile['telegram_id']}")],
        [InlineKeyboardButton("⬅️ Главное меню", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_media(
        media=InputMediaPhoto(
            media=profile['photo_id'],
            caption=f"Имя: {profile['name']}\nВозраст: {profile['age']}\nПол: {profile['gender']}\nГород: {profile['city'] or 'Не указан'}\nО себе: {profile['bio']}"
        ),
        reply_markup=reply_markup
    )

async def report_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start report process."""
    query = update.callback_query
    await query.answer()
    logger.info(f"Received report from user: {query.from_user.id} for user: {query.data}")
    reported_user_id = int(query.data.split('_')[1])
    context.user_data['reported_user_id'] = reported_user_id
    await query.message.reply_text("Пожалуйста, укажите причину жалобы.")
    return GET_REPORT_REASON

async def get_report_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle report reason and request a screenshot."""
    context.user_data['report_reason'] = update.message.text
    await update.message.reply_text("Пожалуйста, прикрепите скриншот, подтверждающий нарушение (например, переписка или анкета).")
    return GET_REPORT_SCREENSHOT

async def get_report_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle screenshot for report and notify admin."""
    if not update.message.photo:
        await update.message.reply_text("Пожалуйста, отправьте скриншот в виде фотографии.")
        return GET_REPORT_SCREENSHOT

    screenshot_id = update.message.photo[-1].file_id
    reason = context.user_data.get('report_reason')
    reporter_user_id = update.message.from_user.id
    reported_user_id = context.user_data.get('reported_user_id')
    
    if reported_user_id:
        db = load_db()
        db['reports'].append({
            'reporter_id': reporter_user_id,
            'reported_id': reported_user_id,
            'reason': reason,
            'screenshot_id': screenshot_id
        })
        db['blocked'].append({'blocker_id': reporter_user_id, 'blocked_id': reported_user_id})
        save_db(db)
        await update.message.reply_text("Ваша жалоба принята и будет рассмотрена.", reply_markup=get_main_menu())
        if ADMIN_CHAT_ID:
            reporter_user = next((u for u in db['users'] if u['telegram_id'] == reporter_user_id), None)
            reported_user = next((u for u in db['users'] if u['telegram_id'] == reported_user_id), None)
            if reporter_user and reported_user:
                keyboard = [
                    [InlineKeyboardButton("Забанить", callback_data=f"ban_{reported_user_id}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                reporter_link = f"tg://user?id={reporter_user_id}"
                reported_link = f"tg://user?id={reported_user_id}"
                message = (
                    f"Новая жалоба:\n"
                    f"От пользователя: {reporter_user['name']} (ID: {reporter_user_id}, [Профиль]({reporter_link}))\n"
                    f"На пользователя: {reported_user['name']} (ID: {reported_user_id}, [Профиль]({reported_link}))\n"
                    f"Причина: {reason}"
                )
                await context.bot.send_photo(
                    chat_id=ADMIN_CHAT_ID,
                    photo=screenshot_id,
                    caption=message,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
        context.user_data.clear()
        return ConversationHandler.END
    else:
        await update.message.reply_text("Произошла ошибка при обработке жалобы.", reply_markup=get_main_menu())
        return ConversationHandler.END

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ban a user based on admin action."""
    query = update.callback_query
    await query.answer()
    logger.info(f"Received ban request from admin for user: {query.data}")
    user_id = int(query.data.split('_')[1])
    db = load_db()
    if any(u['telegram_id'] == user_id for u in db['users']):
        db['users'] = [u for u in db['users'] if u['telegram_id'] != user_id]
        db['blocked'].append({'blocker_id': int(ADMIN_CHAT_ID), 'blocked_id': user_id})
        save_db(db)
        await query.message.reply_text(f"Пользователь ID {user_id} забанен.")
    else:
        await query.message.reply_text(f"Пользователь ID {user_id} не найден.")
    await query.message.delete()

async def feedback_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start feedback process."""
    if update.callback_query:
        query = update.callback_query
        chat_id = query.message.chat_id
        message_id = query.message.message_id
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        message = await context.bot.send_message(chat_id, "Пожалуйста, опишите ваш отзыв, предложение или проблему.")
    else:
        message = update.message

    await message.reply_text("Пожалуйста, опишите ваш отзыв, предложение или проблему.", reply_markup=ReplyKeyboardRemove())
    return GET_FEEDBACK_MESSAGE

async def get_feedback_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle feedback message and ask for contact info."""
    context.user_data['feedback_message'] = update.message.text
    await update.message.reply_text("Если вы хотите, чтобы мы связались с вами, укажите ваш контакт (например, Telegram @username). Если нет, просто напишите 'Нет'.")
    return GET_FEEDBACK_CONTACT

async def get_feedback_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle feedback contact info and send to admin."""
    contact = update.message.text
    feedback_message = context.user_data.get('feedback_message')
    user_id = update.message.from_user.id
    db = load_db()
    feedback_entry = {
        'user_id': user_id,
        'message': feedback_message,
        'contact': contact if contact.lower() != 'нет' else None
    }
    db['feedback'].append(feedback_entry)
    save_db(db)
    await update.message.reply_text("Спасибо за ваш отзыв! Мы рассмотрим его в ближайшее время.", reply_markup=get_main_menu())
    if ADMIN_CHAT_ID:
        user = next((u for u in db['users'] if u['telegram_id'] == user_id), None)
        user_name = user['name'] if user else f"ID {user_id}"
        user_link = f"tg://user?id={user_id}"
        message = (
            f"Новый отзыв:\n"
            f"От пользователя: {user_name} ([Профиль]({user_link}))\n"
            f"Сообщение: {feedback_message}\n"
            f"Контакт: {contact if contact.lower() != 'нет' else 'Не указан'}"
        )
        await context.bot.send_message(ADMIN_CHAT_ID, message, parse_mode="Markdown")
    context.user_data.clear()
    return ConversationHandler.END

async def matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show mutual matches with chat buttons."""
    if update.callback_query:
        query = update.callback_query
        chat_id = query.message.chat_id
        message_id = query.message.message_id
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    else:
        chat_id = update.message.chat_id

    user_id = update.effective_user.id
    db = load_db()
    user_matches = [
        m for m in db['matches']
        if m['user1_id'] == user_id or m['user2_id'] == user_id
    ]
    if not user_matches:
        await context.bot.send_message(chat_id, "У вас пока нет мэтчей.", reply_markup=get_main_menu())
        return
    message = "Ваши мэтчи:\n"
    keyboard = []
    for match in user_matches:
        other_id = match['user2_id'] if match['user1_id'] == user_id else match['user1_id']
        other_user = next(u for u in db['users'] if u['telegram_id'] == other_id)
        message += f"- {other_user['name']} (Возраст: {other_user['age']}, Пол: {other_user['gender']})\n"
        keyboard.append([InlineKeyboardButton(f"Начать чат с {other_user['name']}", callback_data=f"chat_{other_id}")])
    keyboard.append([InlineKeyboardButton("⬅️ Главное меню", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id, message, reply_markup=reply_markup)

async def start_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle chat initiation."""
    query = update.callback_query
    await query.answer()
    matched_user_id = int(query.data.split('_')[1])
    db = load_db()
    matched_user = next((u for u in db['users'] if u['telegram_id'] == matched_user_id), None)
    if matched_user:
        await query.message.reply_text(f"Вы выбрали пользователя @{matched_user['username']}. Найдите его в Telegram и начните чат!", reply_markup=get_main_menu())
    else:
        await query.message.reply_text("Пользователь не найден.", reply_markup=get_main_menu())

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel any conversation."""
    await update.message.reply_text("Операция отменена.", reply_markup=get_main_menu())
    return ConversationHandler.END

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unknown messages."""
    logger.info(f"Received unknown message from user {update.effective_user.id}: {update.message.text}")
    await update.message.reply_text("Извините, я не понимаю это сообщение. Пожалуйста, используйте команды из меню.", reply_markup=get_main_menu())

def main():
    """Run the bot."""
    application = Application.builder().token(BOT_TOKEN).build()
    logger.info("Bot started")

    register_handler = ConversationHandler(
        entry_points=[
            CommandHandler("register", register_start),
            CallbackQueryHandler(register_start, pattern='^menu_register$')
        ],
        states={
            GET_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            GET_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            GET_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gender)],
            GET_GENDER_OTHER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gender_other)],
            GET_PHOTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_photo)],
            GET_BIO: [MessageHandler(filters.PHOTO, get_bio)],
            REGISTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, complete_registration)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    edit_profile_handler = ConversationHandler(
        entry_points=[CommandHandler("edit_profile", edit_profile)],
        states={
            EDIT_PROFILE: [
                MessageHandler(filters.Regex(".*Изменить имя.*"), edit_name),
                MessageHandler(filters.Regex(".*Изменить возраст.*"), edit_age),
                MessageHandler(filters.Regex(".*Изменить пол.*"), edit_gender),
                MessageHandler(filters.Regex(".*Изменить город.*"), edit_city),
                MessageHandler(filters.Regex(".*Изменить фото.*"), edit_photo),
                MessageHandler(filters.Regex(".*Изменить био.*"), edit_bio),
                MessageHandler(filters.Regex(".*Отмена.*"), cancel_edit),
            ],
            EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_name)],
            EDIT_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_age)],
            EDIT_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_gender)],
            EDIT_GENDER_OTHER: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_gender_other)],
            EDIT_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_city)],
            EDIT_PHOTO: [MessageHandler(filters.PHOTO, update_photo)],
            EDIT_BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_bio)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    report_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(report_profile, pattern='^report_')],
        states={
            GET_REPORT_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_report_reason)],
            GET_REPORT_SCREENSHOT: [MessageHandler(filters.ALL, get_report_screenshot)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    feedback_handler = ConversationHandler(
        entry_points=[CommandHandler("feedback", feedback_start)],
        states={
            GET_FEEDBACK_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_feedback_message)],
            GET_FEEDBACK_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_feedback_contact)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    # Prioritize handlers
    application.add_handler(register_handler)
    application.add_handler(edit_profile_handler)
    application.add_handler(report_handler)
    application.add_handler(feedback_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("profile", profile))
    application.add_handler(CommandHandler("browse", browse_profiles))
    application.add_handler(CommandHandler("matches", matches))
    application.add_handler(CallbackQueryHandler(menu_handler, pattern='^menu_'))
    application.add_handler(CallbackQueryHandler(back_to_menu, pattern='^back_to_menu$'))
    application.add_handler(CallbackQueryHandler(like_profile, pattern='^like_'))
    application.add_handler(CallbackQueryHandler(next_profile, pattern='^next$'))
    application.add_handler(CallbackQueryHandler(start_chat, pattern='^chat_'))
    application.add_handler(CallbackQueryHandler(ban_user, pattern='^ban_'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))

    application.run_polling()

if __name__ == '__main__':
    main()
