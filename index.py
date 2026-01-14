import os
import asyncio
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from deep_translator import GoogleTranslator
from rembg import remove

# 1. Setup
TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = -1003582100656

# Rename this to 'bot_app' to avoid confusion
bot_app = ApplicationBuilder().token(TOKEN).build()

# 2. Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🌍 Translate", callback_data='trans')],
                [InlineKeyboardButton("🖼️ Remove BG", callback_data='bg')]]
    await update.message.reply_text("Welcome! Choose a tool:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['action'] = query.data
    await query.edit_message_text(f"Send your {'text' if query.data == 'trans' else 'photo'} now.")

async def process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action = context.user_data.get('action')
    if action == 'trans' and update.message.text:
        res = GoogleTranslator(source='auto', target='en').translate(update.message.text)
        await update.message.reply_text(f"📝 {res}")
    elif action == 'bg' and update.message.photo:
        await update.message.reply_text("⏳ AI is working...")
        file = await context.bot.get_file(update.message.photo[-1].file_id)
        img = await file.download_as_bytearray()
        await update.message.reply_photo(photo=BytesIO(remove(img)), caption="✅ Done!")

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CallbackQueryHandler(handle_choice))
bot_app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, process))

# 3. Rename 'handler' to 'app' to fix the Vercel crash
async def app(request):
    if request.method == "POST":
        if not bot_app.running:
            await bot_app.initialize()
        try:
            data = await request.json()
            update = Update.de_json(data, bot_app.bot)
            await bot_app.process_update(update)
            return {"statusCode": 200, "body": "Success"}
        except Exception as e:
            return {"statusCode": 500, "body": str(e)}

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "text/html"},
        "body": "<h1>Bot Status: Online ✅</h1>"
    }
