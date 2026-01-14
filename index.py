import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from deep_translator import GoogleTranslator
from rembg import remove
from io import BytesIO

# 1. Config & Initialization
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@YourChannelUsername" # MUST CHANGE THIS

# Global app instance for serverless efficiency
app = ApplicationBuilder().token(TOKEN).build()

# 2. Membership Check
async def is_member(user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception: return False

# 3. Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_member(user_id, context):
        await update.message.reply_text(f"❌ Join {CHANNEL_ID} to use this bot.")
        return
    keyboard = [[InlineKeyboardButton("🌍 Translate", callback_data='trans')],
                [InlineKeyboardButton("🖼️ Remove BG", callback_data='bg')]]
    await update.message.reply_text("Private Member Tools:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action = context.user_data.get('action')
    if action == 'trans' and update.message.text:
        res = GoogleTranslator(source='auto', target='en').translate(update.message.text)
        await update.message.reply_text(f"📝 {res}")
    elif action == 'bg' and update.message.photo:
        await update.message.reply_text("⏳ Processing image (max 10s)...")
        file = await context.bot.get_file(update.message.photo[-1].file_id)
        img_bytes = await file.download_as_bytearray()
        # This part consumes high RAM; keep images small!
        output = remove(img_bytes)
        await update.message.reply_photo(photo=BytesIO(output), caption="✅ BG Removed!")

# 4. Bot Setup Logic
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(lambda u, c: (u.callback_query.answer(), c.user_data.update({'action': u.callback_query.data}))))
app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))

# 5. The Vercel Serverless Entry Point
async def handler(request):
    if request.method == "POST":
        # Ensure app is ready
        if not app.running:
            await app.initialize()
        
        # Read the Telegram JSON update
        payload = await request.json()
        update = Update.de_json(payload, app.bot)
        
        # Process the update
        await app.process_update(update)
        
        return {"statusCode": 200, "body": "Success"}
    
    # Simple check to see if the URL is live
    return {"statusCode": 200, "body": "Bot is Online"}
