import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from googletrans import Translator
from rembg import remove
from PIL import Image
from io import BytesIO

# 1. Configuration - Use Environment Variables for safety
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@YourChannelUsername"  # Include the @

# 2. Membership Check Logic
async def is_member(user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        # Statuses that count as "Joined"
        if member.status in ['member', 'administrator', 'creator']:
            return True
        return False
    except Exception:
        return False

# 3. Start Command (Sent in Channel or Bot)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Check if they are a member first
    if not await is_member(user_id, context):
        await update.message.reply_text(f"❌ Access Denied. Please join {CHANNEL_ID} to use these tools.")
        return

    # If member, show private tools
    keyboard = [
        [InlineKeyboardButton("🌍 Translate Text", callback_data='tool_translate')],
        [InlineKeyboardButton("🖼️ Remove Background", callback_data='tool_bg')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome to your Private Toolset. Choose a function:", reply_markup=reply_markup)

# 4. Tool Handlers (Private Interaction)
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'tool_translate':
        await query.edit_message_text("Send me the text you want to translate to English.")
        context.user_data['action'] = 'translating'
        
    elif query.data == 'tool_bg':
        await query.edit_message_text("Please upload the photo you want to process.")
        context.user_data['action'] = 'removing_bg'

# 5. Processing Messages (Translator & BG Remover)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action = context.user_data.get('action')
    user_id = update.effective_user.id

    # Always re-check membership before processing data
    if not await is_member(user_id, context):
        await update.message.reply_text("Membership expired. Please join the channel.")
        return

    if action == 'translating' and update.message.text:
        translator = Translator()
        translated = translator.translate(update.message.text, dest='en')
        await update.message.reply_text(f"📝 **Translation:**\n{translated.text}")
        
    elif action == 'removing_bg' and update.message.photo:
        await update.message.reply_text("⏳ Processing image... please wait.")
        # Download photo
        file = await context.bot.get_file(update.message.photo[-1].file_id)
        img_bytes = await file.download_as_bytearray()
        
        # Remove background using AI
        output_bytes = remove(img_bytes)
        
        # Send back to user privately
        await update.message.reply_photo(photo=BytesIO(output_bytes), caption="✅ Background removed privately!")

# Main execution
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))
    
    print("Bot is running...")
    app.run_polling()
