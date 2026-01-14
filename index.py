import os
import asyncio
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from deep_translator import GoogleTranslator
from rembg import remove

# 1. Configuration - Use Environment Variables in Vercel for security
TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = -1003582100656  # Your verified Group ID

# 2. Initialize the Application for Serverless Mode
# This avoids the "polling" conflict on Vercel
app = ApplicationBuilder().token(TOKEN).build()

# 3. Membership Verification
async def is_member(user_id, context):
    try:
        # Check if user is in your specified group
        member = await context.bot.get_chat_member(chat_id=GROUP_ID, user_id=user_id)
        # Returns True if they are a member, admin, or the owner
        return member.status in ['member', 'administrator', 'creator']
    except Exception:
        return False

# 4. Bot Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_member(user_id, context):
        await update.message.reply_text("❌ Access Denied. Join our group to use these tools.")
        return
    
    # Inline buttons for private tool selection
    keyboard = [
        [InlineKeyboardButton("🌍 Translate to English", callback_data='trans')],
        [InlineKeyboardButton("🖼️ Remove Background", callback_data='bg')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome Member! Select a private tool:", reply_markup=reply_markup)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    # Store the user's choice in context memory
    context.user_data['choice'] = query.data
    await query.edit_message_text(f"Please send the {'text' if query.data == 'trans' else 'photo'} you want to process.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only process messages from verified group members
    if not await is_member(update.effective_user.id, context):
        return

    user_choice = context.user_data.get('choice')
    
    # Translation Logic
    if user_choice == 'trans' and update.message.text:
        translated = GoogleTranslator(source='auto', target='en').translate(update.message.text)
        await update.message.reply_text(f"📝 Translated: {translated}")
        
    # Background Removal Logic
    elif user_choice == 'bg' and update.message.photo:
        await update.message.reply_text("⏳ AI is removing background... please wait.")
        # Get the highest resolution photo sent
        photo_file = await context.bot.get_file(update.message.photo[-1].file_id)
        img_bytes = await photo_file.download_as_bytearray()
        
        # Process image using rembg
        output_bytes = remove(img_bytes)
        await update.message.reply_photo(photo=BytesIO(output_bytes), caption="✅ Background Removed!")

# Register handlers to the app
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(handle_callback))
app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))

# 5. Vercel Serverless Entry Point
async def handler(request):
    if request.method == "POST":
        # Ensure the application is initialized
        if not app.running:
            await app.initialize()
        
        # Parse the Telegram Update from the POST request
        try:
            data = await request.json()
            update = Update.de_json(data, app.bot)
            await app.process_update(update)
        except Exception as e:
            print(f"Error processing update: {e}")
            
    return {"statusCode": 200, "body": "OK"}