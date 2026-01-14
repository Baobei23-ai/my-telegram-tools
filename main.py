import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from deep_translator import GoogleTranslator
from rembg import remove
from PIL import Image
from io import BytesIO

# 1. Configuration
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@YourChannelUsername" # Change this to your real channel link

# 2. Membership Check
async def is_member(user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception:
        return False

# 3. Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_member(user_id, context):
        await update.message.reply_text(f"❌ Access Denied. Please join {CHANNEL_ID} first.")
        return

    keyboard = [
        [InlineKeyboardButton("🌍 Translate to English", callback_data='tool_translate')],
        [InlineKeyboardButton("🖼️ Remove Background", callback_data='tool_bg')]
    ]
    await update.message.reply_text("Welcome Member! Choose a private tool:", reply_markup=InlineKeyboardMarkup(keyboard))

# 4. Button Logic
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'tool_translate':
        await query.edit_message_text("Send me the text you want to translate.")
        context.user_data['action'] = 'translating'
    elif query.data == 'tool_bg':
        await query.edit_message_text("Please upload the photo you want to clean.")
        context.user_data['action'] = 'removing_bg'

# 5. Message Processing
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action = context.user_data.get('action')
    user_id = update.effective_user.id

    if not await is_member(user_id, context):
        await update.message.reply_text("Please join the channel to continue.")
        return

    if action == 'translating' and update.message.text:
        # Using deep-translator instead of googletrans
        translated = GoogleTranslator(source='auto', target='en').translate(update.message.text)
        await update.message.reply_text(f"📝 **Translation:**\n{translated}")
        
    elif action == 'removing_bg' and update.message.photo:
        await update.message.reply_text("⏳ Processing image... wait a moment.")
        file = await context.bot.get_file(update.message.photo[-1].file_id)
        img_bytes = await file.download_as_bytearray()
        
        # AI Background Removal
        output_bytes = remove(img_bytes)
        await update.message.reply_photo(photo=BytesIO(output_bytes), caption="✅ Done!")

# Run Bot
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))
    app.run_polling()
