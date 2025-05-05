import json
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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

# JSON database file
DB_FILE = 'db.json'

# Conversation states
(
    GENDER, AGE, CITY, PROFILE_TEXT, SEARCH_GENDER, SEARCH_AGE_MIN,
    SEARCH_AGE_MAX, SEARCH_CITY, VIEW_PROFILE
) = range(9)

def load_db():
    """Load JSON database."""
    if not os.path.exists(DB_FILE):
        return {"users": [], "blocked": [], "likes": [], "matches": []}
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_db(data):
    """Save JSON database."""
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message and start registration."""
    user = update.effective_user
    db = load_db()
    if any(u['telegram_id'] == user.id for u in db['users']):
        await update.message.reply_text(
            "Welcome back! Use /profile to view/edit your profile, /search to find matches, or /matches to see mutual likes."
        )
        return ConversationHandler.END
    welcome_message = (
        "🌈 Welcome to the inclusive dating bot! We're here to connect you with amazing people. "
        "Let's create your profile. First, please choose your gender identity:"
    )
    keyboard = [
        [InlineKeyboardButton("Trans Man", callback_data="t_man")],
        [InlineKeyboardButton("Trans Woman", callback_data="t_woman")],
        [InlineKeyboardButton("Non-Binary", callback_data="non_binary")],
        [InlineKeyboardButton("Other", callback_data="other")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)
    return GENDER

async def gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle gender selection."""
    query = update.callback_query
    await query.answer()
    gender = query.data
    context.user_data['gender'] = gender
    if gender == "other":
        await query.message.reply_text("Please enter your gender identity:")
        return GENDER
    else:
        context.user_data['gender'] = gender.replace('_', ' ').title()
        await query.message.reply_text("Please enter your age (e.g., 18):")
        return AGE

async def gender_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom gender input."""
    context.user_data['gender'] = update.message.text
    await update.message.reply_text("Please enter your age (e.g., 18):")
    return AGE

async def age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle age input and enforce age group separation."""
    try:
        age = int(update.message.text)
        if age < 16:
            await update.message.reply_text("Sorry, you must be at least 16 to use this bot.")
            return ConversationHandler.END
        context.user_data['age'] = age
        await update.message.reply_text(
            "Enter your city (or type 'Any' to match with all cities):"
        )
        return CITY
    except ValueError:
        await update.message.reply_text("Please enter a valid number for age.")
        return AGE

async def city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle city input."""
    city = update.message.text.strip()
    context.user_data['city'] = city if city.lower() != 'any' else None
    await update.message.reply_text("Tell us about yourself (your profile description):")
    return PROFILE_TEXT

async def profile_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save profile and complete registration."""
    user = update.effective_user
    db = load_db()
    profile = {
        'telegram_id': user.id,
        'username': user.username or f"user_{user.id}",
        'gender': context.user_data['gender'],
        'age': context.user_data['age'],
        'city': context.user_data['city'],
        'profile_text': update.message.text
    }
    db['users'].append(profile)
    save_db(db)
    await update.message.reply_text(
        "Profile created! Use /profile to view/edit, /search to find matches, or /matches to see mutual likes."
    )
    return ConversationHandler.END

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user profile."""
    user = update.effective_user
    db = load_db()
    user_profile = next((u for u in db['users'] if u['telegram_id'] == user.id), None)
    if not user_profile:
        await update.message.reply_text("No profile found. Create one with /start.")
        return
    text = (
        f"Username: @{user_profile['username']}\n"
        f"Gender: {user_profile['gender']}\n"
        f"Age: {user_profile['age']}\n"
        f"City: {user_profile['city'] or 'Not specified'}\n"
        f"About: {user_profile['profile_text']}\n\n"
        "To edit, restart with /start."
    )
    await update.message.reply_text(text)

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start search process."""
    user = update.effective_user
    db = load_db()
    if not any(u['telegram_id'] == user.id for u in db['users']):
        await update.message.reply_text("Please create a profile first with /start.")
        return ConversationHandler.END
    keyboard = [
        [InlineKeyboardButton("Trans Man", callback_data="t_man")],
        [InlineKeyboardButton("Trans Woman", callback_data="t_woman")],
        [InlineKeyboardButton("Non-Binary", callback_data="non_binary")],
        [InlineKeyboardButton("Other", callback_data="other")],
        [InlineKeyboardButton("Any", callback_data="any")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Which gender identity are you interested in?", reply_markup=reply_markup
    )
    return SEARCH_GENDER

async def search_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle search gender preference."""
    query = update.callback_query
    await query.answer()
    gender = query.data
    context.user_data['search_gender'] = gender.replace('_', ' ').title() if gender != "any" else None
    if gender == "other":
        await query.message.reply_text("Please specify the gender identity:")
        return SEARCH_GENDER
    await query.message.reply_text("Enter the minimum age you're interested in:")
    return SEARCH_AGE_MIN

async def search_gender_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom search gender input."""
    context.user_data['search_gender'] = update.message.text
    await update.message.reply_text("Enter the minimum age you're interested in:")
    return SEARCH_AGE_MIN

async def search_age_min(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle minimum age filter."""
    try:
        min_age = int(update.message.text)
        db = load_db()
        user_profile = next(u for u in db['users'] if u['telegram_id'] == update.effective_user.id)
        if (user_profile['age'] < 18 and min_age >= 18) or (user_profile['age'] >= 18 and min_age < 18):
            await update.message.reply_text("Age groups cannot cross 18 (minors and adults are separate).")
            return SEARCH_AGE_MIN
        context.user_data['search_age_min'] = min_age
        await update.message.reply_text("Enter the maximum age you're interested in:")
        return SEARCH_AGE_MAX
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return SEARCH_AGE_MIN

async def search_age_max(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle maximum age filter."""
    try:
        max_age = int(update.message.text)
        min_age = context.user_data['search_age_min']
        db = load_db()
        user_profile = next(u for u in db['users'] if u['telegram_id'] == update.effective_user.id)
        if max_age < min_age:
            await update.message.reply_text("Maximum age must be greater than or equal to minimum age.")
            return SEARCH_AGE_MAX
        if (user_profile['age'] < 18 and max_age >= 18) or (user_profile['age'] >= 18 and max_age < 18):
            await update.message.reply_text("Age groups cannot cross 18 (minors and adults are separate).")
            return SEARCH_AGE_MAX
        context.user_data['search_age_max'] = max_age
        await update.message.reply_text("Enter a city to filter by (or 'Any' for all cities):")
        return SEARCH_CITY
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return SEARCH_AGE_MAX

async def search_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle city filter and show profiles."""
    user = update.effective_user
    city = update.message.text.strip()
    context.user_data['search_city'] = city if city.lower() != 'any' else None
    db = load_db()
    user_profile = next(u for u in db['users'] if u['telegram_id'] == user.id)
    blocked_ids = [b['blocked_id'] for b in db['blocked'] if b['blocker_id'] == user.id]
    profiles = [
        u for u in db['users']
        if u['telegram_id'] != user.id and u['telegram_id'] not in blocked_ids
    ]
    if context.user_data['search_gender']:
        profiles = [u for u in profiles if u['gender'] == context.user_data['search_gender']]
    if user_profile['age'] < 18:
        profiles = [u for u in profiles if u['age'] < 18]
    else:
        profiles = [
            u for u in profiles
            if context.user_data['search_age_min'] <= u['age'] <= context.user_data['search_age_max']
        ]
    if context.user_data['search_city']:
        profiles = [u for u in profiles if u['city'] == context.user_data['search_city']]
    context.user_data['profiles'] = profiles
    context.user_data['current_profile'] = 0
    if not profiles:
        await update.message.reply_text("No matching profiles found.")
        return ConversationHandler.END
    await show_profile(update, context)
    return VIEW_PROFILE

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display a profile with options."""
    profiles = context.user_data['profiles']
    index = context.user_data['current_profile']
    if index >= len(profiles):
        await update.message.reply_text("No more profiles to show.")
        return ConversationHandler.END
    profile = profiles[index]
    text = (
        f"Username: @{profile['username']}\n"
        f"Gender: {profile['gender']}\n"
        f"Age: {profile['age']}\n"
        f"City: {profile['city'] or 'Not specified'}\n"
        f"About: {profile['profile_text']}"
    )
    keyboard = [
        [InlineKeyboardButton("Like ❤️", callback_data="like")],
        [InlineKeyboardButton("Next ➡️", callback_data="next")],
        [InlineKeyboardButton("Report/Block 🚫", callback_data="block")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup)

async def view_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle profile navigation, liking, and blocking."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    profiles = context.user_data['profiles']
    index = context.user_data['current_profile']
    if index >= len(profiles):
        await query.message.reply_text("No more profiles to show.")
        return ConversationHandler.END
    profile = profiles[index]
    db = load_db()
    if query.data == "like":
        # Record like
        db['likes'].append({'liker_id': user_id, 'liked_id': profile['telegram_id']})
        # Check for mutual like
        if any(l['liker_id'] == profile['telegram_id'] and l['liked_id'] == user_id for l in db['likes']):
            db['matches'].append({'user1_id': min(user_id, profile['telegram_id']), 'user2_id': max(user_id, profile['telegram_id'])})
            await query.message.reply_text(f"It's a match with @{profile['username']}! You can now chat.")
        save_db(db)
        context.user_data['current_profile'] += 1
        await show_profile(query, context)
        return VIEW_PROFILE
    elif query.data == "next":
        context.user_data['current_profile'] += 1
        await show_profile(query, context)
        return VIEW_PROFILE
    elif query.data == "block":
        db['blocked'].append({'blocker_id': user_id, 'blocked_id': profile['telegram_id']})
        save_db(db)
        await query.message.reply_text("Profile reported and blocked.")
        context.user_data['current_profile'] += 1
        await show_profile(query, context)
        return VIEW_PROFILE

async def matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show mutual matches."""
    user = update.effective_user
    db = load_db()
    user_matches = [
        m for m in db['matches']
        if m['user1_id'] == user.id or m['user2_id'] == user.id
    ]
    if not user_matches:
        await update.message.reply_text("No matches yet. Keep searching!")
        return
    response = "Your matches:\n"
    for match in user_matches:
        other_id = match['user2_id'] if match['user1_id'] == user.id else match['user1_id']
        other_user = next(u for u in db['users'] if u['telegram_id'] == other_id)
        response += f"- @{other_user['username']} (Gender: {other_user['gender']}, Age: {other_user['age']})\n"
    await update.message.reply_text(response)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the conversation."""
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END

def main():
    """Run the bot."""
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', 'your-telegram-bot-token-here')
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start), CommandHandler('search', search)],
        states={
            GENDER: [
                CallbackQueryHandler(gender, pattern='^(t_man|t_woman|non_binary|other)$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, gender_text)
            ],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age)],
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, city)],
            PROFILE_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_text)],
            SEARCH_GENDER: [
                CallbackQueryHandler(search_gender, pattern='^(t_man|t_woman|non_binary|other|any)$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, search_gender_text)
            ],
            SEARCH_AGE_MIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_age_min)],
            SEARCH_AGE_MAX: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_age_max)],
            SEARCH_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_city)],
            VIEW_PROFILE: [CallbackQueryHandler(view_profile, pattern='^(like|next|block)$')]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('profile', profile))
    application.add_handler(CommandHandler('matches', matches))
    application.run_polling()

if __name__ == '__main__':
    main()