import json
import logging
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')

# JSON database file
DB_FILE = 'db.json'

# Conversation states
(
    REGISTER, GET_NAME, GET_AGE, GET_GENDER, GET_GENDER_OTHER, GET_PHOTO, GET_BIO,
    EDIT_PROFILE, EDIT_NAME, EDIT_AGE, EDIT_GENDER, EDIT_GENDER_OTHER, EDIT_CITY, EDIT_PHOTO, EDIT_BIO,
    REPORT, GET_REPORT_REASON
) = range(17)

def load_db():
    """Load JSON database."""
    if not os.path.exists(DB_FILE):
        return {
            "users": [],
            "blocked": [],
            "likes": [],
            "matches": [],
            "reports": []
        }
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_db(data):
    """Save JSON database."""
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message with rules and start registration."""
    rules = (
        "Добро пожаловать в T4t Meet!\n\n"
        "Подпишитесь на наш канал: https://t.me/tperehod\n"
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

async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start registration process."""
    db = load_db()
    if any(u['telegram_id'] == update.effective_user.id for u in db['users']):
        await update.message.reply_text("Вы уже зарегистрированы! Используйте /profile или /edit_profile.")
        return ConversationHandler.END
    await update.message.reply_text("Ваше имя: как вас будут видеть другие пользователи?")
    return GET_NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle name input."""
    context.user_data['name'] = update.message.text
    await update.message.reply_text(f"Отлично, ваше имя будет '{context.user_data['name']}'. Теперь скажите, сколько вам лет?")
    return GET_AGE

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle age input with validation."""
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

async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle gender selection."""
    gender = update.message.text
    context.user_data['gender'] = gender
    if gender == "Другое":
        await update.message.reply_text("Пожалуйста, уточните вашу гендерную идентичность.")
        return GET_GENDER_OTHER
    await update.message.reply_text("Введите ваш город (или 'Any' для всех городов):")
    return GET_PHOTO

async def get_gender_other(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom gender input."""
    context.user_data['gender'] = update.message.text
    await update.message.reply_text("Введите ваш город (или 'Any' для всех городов):")
    return GET_PHOTO

async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle city input."""
    city = update.message.text.strip()
    context.user_data['city'] = city if city.lower() != 'any' else None
    await update.message.reply_text("Пожалуйста, загрузите вашу фотографию профиля.")
    return GET_BIO

async def get_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo and bio input."""
    if update.message.photo:
        context.user_data['photo_id'] = update.message.photo[-1].file_id
        await update.message.reply_text("Отлично, фото получено. Теперь расскажите немного о себе (ваши интересы, что вы ищете и т.д.).")
        return REGISTER
    else:
        await update.message.reply_text("Пожалуйста, отправьте фотографию.")
        return GET_BIO

async def complete_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save profile and complete registration."""
    user = update.effective_user
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
    await update.message.reply_text("Спасибо за регистрацию! Ваш профиль создан.")
    context.user_data.clear()
    return ConversationHandler.END

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user profile with photo."""
    user_id = update.effective_user.id
    db = load_db()
    user_profile = next((u for u in db['users'] if u['telegram_id'] == user_id), None)
    if not user_profile:
        await update.message.reply_text("Ваш профиль не найден. Пожалуйста, зарегистрируйтесь с /register.")
        return
    caption = (
        f"Ваш профиль:\n"
        f"Имя: {user_profile['name']}\n"
        f"Возраст: {user_profile['age']}\n"
        f"Пол: {user_profile['gender']}\n"
        f"Город: {user_profile['city'] or 'Не указан'}\n"
        f"О себе: {user_profile['bio']}"
    )
    await context.bot.send_photo(
        chat_id=update.message.chat_id,
        photo=user_profile['photo_id'],
        caption=caption
    )

async def edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start profile editing."""
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
    await update.message.reply_text("Что вы хотите изменить в своем профиле?", reply_markup=reply_markup)
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
    await update.message.reply_text(f"Ваше имя обновлено на '{new_name}'.")
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
            await update.message.reply_text(f"Ваш возраст обновлен на '{new_age}'.")
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
    await update.message.reply_text(f"Ваш пол обновлен на '{new_gender}'.")
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
    await update.message.reply_text(f"Ваш пол обновлен на '{new_gender}'.")
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
    await update.message.reply_text(f"Ваш город обновлен на '{new_city or 'Не указан'}'.")
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
        await update.message.reply_text("Ваша фотография профиля обновлена.")
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
    await update.message.reply_text("Ваше описание профиля обновлено.")
    return ConversationHandler.END

async def cancel_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel profile editing."""
    await update.message.reply_text("Редактирование профиля отменено.")
    return ConversationHandler.END

async def browse_profiles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Browse profiles sequentially with filters."""
    user_id = update.effective_user.id
    db = load_db()
    user_profile = next((u for u in db['users'] if u['telegram_id'] == user_id), None)
    if not user_profile:
        await update.message.reply_text("Пожалуйста, зарегистрируйтесь с /register.")
        return
    blocked_ids = [b['blocked_id'] for b in db['blocked'] if b['blocker_id'] == user_id]
    profiles = [
        u for u in db['users']
        if u['telegram_id'] != user_id and u['telegram_id'] not in blocked_ids
    ]
    if user_profile['age'] < 18:
        profiles = [u for u in profiles if u['age'] < 18]
    else:
        profiles = [u for u in profiles if u['age'] >= 18]
    if user_profile['city']:
        profiles = [u for u in profiles if u['city'] == user_profile['city'] or u['city'] is None]
    context.user_data['profiles'] = profiles
    context.user_data['current_profile'] = 0
    if not profiles:
        await update.message.reply_text("Пока нет доступных анкет для просмотра.")
        return
    await show_profile(update, context)

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display a profile with options."""
    profiles = context.user_data['profiles']
    index = context.user_data['current_profile']
    if index >= len(profiles):
        await update.message.reply_text("Нет больше анкет для просмотра.")
        return
    profile = profiles[index]
    keyboard = [
        [InlineKeyboardButton("👍 Лайк", callback_data=f"like_{profile['telegram_id']}")],
        [InlineKeyboardButton("➡️ Следующая анкета", callback_data="next")],
        [InlineKeyboardButton("⚠️ Пожаловаться", callback_data=f"report_{profile['telegram_id']}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_photo(
        chat_id=update.message.chat_id,
        photo=profile['photo_id'],
        caption=f"Имя: {profile['name']}\nВозраст: {profile['age']}\nПол: {profile['gender']}\nГород: {profile['city'] or 'Не указан'}\nО себе: {profile['bio']}",
        reply_markup=reply_markup
    )

async def like_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle profile like and check for matches."""
    query = update.callback_query
    await query.answer()
    liked_user_id = int(query.data.split('_')[1])
    liking_user_id = query.from_user.id
    db = load_db()
    db['likes'].append({'liker_id': liking_user_id, 'liked_id': liked_user_id})
    if any(l['liker_id'] == liked_user_id and l['liked_id'] == liking_user_id for l in db['likes']):
        db['matches'].append({'user1_id': min(liking_user_id, liked_user_id), 'user2_id': max(liking_user_id, liked_user_id)})
        liked_user = next(u for u in db['users'] if u['telegram_id'] == liked_user_id)
        liking_user = next(u for u in db['users'] if u['telegram_id'] == liking_user_id)
        await context.bot.send_message(liked_user_id, f"У вас мэтч с {liking_user['name']}!")
        await context.bot.send_message(liking_user_id, f"У вас мэтч с {liked_user['name']}!")
    save_db(db)
    keyboard = [
        [InlineKeyboardButton("➡️ Следующая анкета", callback_data="next")],
        [InlineKeyboardButton("⚠️ Пожаловаться", callback_data=f"report_{liked_user_id}")]
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
    context.user_data['current_profile'] += 1
    profiles = context.user_data['profiles']
    index = context.user_data['current_profile']
    if index >= len(profiles):
        await query.edit_message_text("Нет больше анкет для просмотра.")
        return
    profile = profiles[index]
    keyboard = [
        [InlineKeyboardButton("👍 Лайк", callback_data=f"like_{profile['telegram_id']}")],
        [InlineKeyboardButton("➡️ Следующая анкета", callback_data="next")],
        [InlineKeyboardButton("⚠️ Пожаловаться", callback_data=f"report_{profile['telegram_id']}")]
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
    reported_user_id = int(query.data.split('_')[1])
    context.user_data['reported_user_id'] = reported_user_id
    await context.bot.send_message(query.message.chat_id, "Пожалуйста, укажите причину жалобы.")
    return GET_REPORT_REASON

async def get_report_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle report reason and notify admin."""
    reason = update.message.text
    reporter_user_id = update.message.from_user.id
    reported_user_id = context.user_data.get('reported_user_id')
    if reported_user_id:
        db = load_db()
        db['reports'].append({
            'reporter_id': reporter_user_id,
            'reported_id': reported_user_id,
            'reason': reason
        })
        db['blocked'].append({'blocker_id': reporter_user_id, 'blocked_id': reported_user_id})
        save_db(db)
        await update.message.reply_text("Ваша жалоба принята и будет рассмотрена.")
        if ADMIN_CHAT_ID:
            reporter_user = next((u for u in db['users'] if u['telegram_id'] == reporter_user_id), None)
            reported_user = next((u for u in db['users'] if u['telegram_id'] == reported_user_id), None)
            if reporter_user and reported_user:
                await context.bot.send_message(
                    ADMIN_CHAT_ID,
                    f"Новая жалоба:\nОт пользователя ID {reporter_user_id} ({reporter_user['name']})\nНа пользователя ID {reported_user_id} ({reported_user['name']})\nПричина: {reason}"
                )
        context.user_data.clear()
        return ConversationHandler.END
    else:
        await update.message.reply_text("Произошла ошибка при обработке жалобы.")
        return ConversationHandler.END

async def matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show mutual matches with chat buttons."""
    user_id = update.effective_user.id
    db = load_db()
    user_matches = [
        m for m in db['matches']
        if m['user1_id'] == user_id or m['user2_id'] == user_id
    ]
    if not user_matches:
        await update.message.reply_text("У вас пока нет мэтчей.")
        return
    message = "Ваши мэтчи:\n"
    keyboard = []
    for match in user_matches:
        other_id = match['user2_id'] if match['user1_id'] == user_id else match['user1_id']
        other_user = next(u for u in db['users'] if u['telegram_id'] == other_id)
        message += f"- {other_user['name']} (Возраст: {other_user['age']}, Пол: {other_user['gender']})\n"
        keyboard.append([InlineKeyboardButton(f"Начать чат с {other_user['name']}", callback_data=f"chat_{other_id}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, reply_markup=reply_markup)

async def start_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle chat initiation."""
    query = update.callback_query
    await query.answer()
    matched_user_id = int(query.data.split('_')[1])
    db = load_db()
    matched_user = next((u for u in db['users'] if u['telegram_id'] == matched_user_id), None)
    if matched_user:
        await query.message.reply_text(f"Вы выбрали пользователя @{matched_user['username']}. Найдите его в Telegram и начните чат!")
    else:
        await query.message.reply_text("Пользователь не найден.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel any conversation."""
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END

def main():
    """Run the bot."""
    application = Application.builder().token(BOT_TOKEN).build()

    register_handler = ConversationHandler(
        entry_points=[CommandHandler("register", register_start)],
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
                MessageHandler(filters.Regex("^Изменить имя$"), edit_name),
                MessageHandler(filters.Regex("^Изменить возраст$"), edit_age),
                MessageHandler(filters.Regex("^Изменить пол$"), edit_gender),
                MessageHandler(filters.Regex("^Изменить город$"), edit_city),
                MessageHandler(filters.Regex("^Изменить фото$"), edit_photo),
                MessageHandler(filters.Regex("^Изменить био$"), edit_bio),
                MessageHandler(filters.Regex("^Отмена$"), cancel_edit),
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
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("profile", profile))
    application.add_handler(CommandHandler("browse", browse_profiles))
    application.add_handler(CommandHandler("matches", matches))
    application.add_handler(register_handler)
    application.add_handler(edit_profile_handler)
    application.add_handler(report_handler)
    application.add_handler(CallbackQueryHandler(like_profile, pattern='^like_'))
    application.add_handler(CallbackQueryHandler(next_profile, pattern='^next$'))
    application.add_handler(CallbackQueryHandler(start_chat, pattern='^chat_'))

    application.run_polling()

if __name__ == '__main__':
    main()
