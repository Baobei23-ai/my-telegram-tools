import os
import asyncio
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from deep_translator import GoogleTranslator
from rembg import remove

# 1. Configuration
TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = -1003582100656  # Your Verified ID

# Initialize App
app = ApplicationBuilder().token(TOKEN).build()

# 2. Membership Check
async def is_member(user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id=GROUP_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception:
        return False

# 3. Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_member(user_id, context):
        await update.message.reply_text("❌ Join our group to use these private tools.")
        return
    
    keyboard = [
        [InlineKeyboardButton("🌍 Translate to EN", callback_data='trans')],
        [InlineKeyboardButton("🖼️ Remove BG", callback_data='bg')]
    ]
    await update.message.reply_text("Welcome Member! Choose a private tool:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['action'] = query.data
    await query.edit_message_text(f"Send me your {'text' if query.data == 'trans' else 'photo'} now.")

async def process_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_member(update.effective_user.id, context):
        return
    
    action = context.user_data.get('action')
    if action == 'trans' and update.message.text:
        res = GoogleTranslator(source='auto', target='en').translate(update.message.text)
        await update.message.reply_text(f"📝 {res}")
        
    elif action == 'bg' and update.message.photo:
        await update.message.reply_text("⏳ Processing image...")
        file = await context.bot.get_file(update.message.photo[-1].file_id)
        img_bytes = await file.download_as_bytearray()
        output = remove(img_bytes)
        await update.message.reply_photo(photo=BytesIO(output), caption="✅ Done!")

# 4. Vercel Handler
async def handler(request):
    if request.method == "POST":
        if not app.running: await app.initialize()
        await app.process_update(Update.de_json(await request.json(), app.bot))
    return {"statusCode": 200, "body": "ok"}

# Register logic
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(handle_action))
app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, process_msg))
