import os
import logging
import sqlite3
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ChatMemberHandler, CommandHandler

# 1. Configuration
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
TARGET_GROUP_ID = int(os.getenv("GROUP_ID"))
KPAY_PHONE = os.getenv("KPAY_PHONE")
KPAY_NAME = os.getenv("KPAY_NAME")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# 2. Database
def init_db():
    conn = sqlite3.connect('nexus_vault.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS members (user_id INTEGER PRIMARY KEY, status TEXT)''')
    conn.commit()
    conn.close()

async def notify_owner(context: ContextTypes.DEFAULT_TYPE, message: str):
    await context.bot.send_message(chat_id=ADMIN_ID, text=f"📊 **LOGS:** {message}", parse_mode='Markdown')

# 3. Initial Flow
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id == ADMIN_ID:
        await update.message.reply_text("🛡️ Nexus Admin Portal Active.")
        return

    keyboard = [[InlineKeyboardButton("💳 ငွေလွှဲအချက်အလက်", callback_data="view_pay")]]
    await update.message.reply_text(
        text=f"🚀 **Nexus Community Trial**\n\n၃ မိနစ်အတွင်း Screenshot ပို့ပေးပါ။",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    context.job_queue.run_once(ask_admin_to_kick, 180, chat_id=user.id, data={'reason': 'Initial Timeout (3m)', 'name': user.full_name}, name=f"initial_{user.id}")

async def on_member_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if result.new_chat_member.status == ChatMember.MEMBER:
        user = result.new_chat_member.user
        await notify_owner(context, f"👤 **Joiner:** {user.full_name} (`{user.id}`) joined.")
        keyboard = [[InlineKeyboardButton("💳 ငွေလွှဲအချက်အလက်", callback_data="view_pay")]]
        await context.bot.send_message(chat_id=user.id, text=f"🚀 **Hi {user.first_name}!**\n၃ မိနစ်အတွင်း Screenshot ပို့ပေးပါ။", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        context.job_queue.run_once(ask_admin_to_kick, 180, chat_id=user.id, data={'reason': 'Join Timeout (3m)', 'name': user.full_name}, name=f"initial_{user.id}")

# 4. UI Buttons
async def handle_ui_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == "view_pay":
        await query.edit_message_text(f"💰 **KPay:** `{KPAY_PHONE}`\nName: `{KPAY_NAME}`\n\nScreenshot ပို့ပေးပါ။", parse_mode='Markdown')

    elif query.data == "confirm_refill":
        for job in context.job_queue.get_jobs_by_name(f"final_{user_id}"): job.schedule_removal()
        
        # UI format for admin (Simplified callback data to avoid ValueErrors)
        admin_kb = [
            [InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}")],
            [InlineKeyboardButton("🔄 Check Again", callback_data=f"recheck_{user_id}"),
             InlineKeyboardButton("🚫 Ban User", callback_data=f"kick_{user_id}")] # Fixed: kick_userid
        ]
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"⚠️ **URGENT REFILL CHECK**\n\nUser: {query.from_user.full_name}\nID: `{user_id}`\n\nငွေလွှဲပြီးကြောင်း အတည်ပြုလိုက်ပါသည်။",
            reply_markup=InlineKeyboardMarkup(admin_kb)
        )
        await query.edit_message_text(text="✅ Admin ထံ အရေးပေါ်အချက်ပေးစာ ပို့ပြီးပါပြီ။")

# 5. Screenshot Handling
async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        user = update.effective_user
        for j in context.job_queue.get_jobs_by_name(f"initial_{user.id}"): j.schedule_removal()

        admin_kb = [[InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user.id}"),
                     InlineKeyboardButton("❌ Decline", callback_data=f"decline_{user.id}")]]
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=update.message.photo[-1].file_id,
            caption=f"📩 **Payment Arrival**\nUser: {user.full_name}\nID: `{user.id}`",
            reply_markup=InlineKeyboardMarkup(admin_kb)
        )
        await update.message.reply_text("✅ Screenshot ရရှိပါသည်။ ၃၀ စက္ကန့်အတွင်း Refill သတိပေးချက် လာပါမည်။")
        context.job_queue.run_once(send_refill_reminder, 30, chat_id=user.id, data={'name': user.full_name}, name=f"refill_{user.id}")

async def send_refill_reminder(context: ContextTypes.DEFAULT_TYPE):
    user_id = context.job.chat_id
    keyboard = [[InlineKeyboardButton("✅ Confirm Refill", callback_data="confirm_refill")]]
    await context.bot.send_message(chat_id=user_id, text="🚨 **REFILL TIME:** ၅ စက္ကန့်အတွင်း Confirm နှိပ်ပါ။", reply_markup=InlineKeyboardMarkup(keyboard))
    context.job_queue.run_once(ask_admin_to_kick, 5, chat_id=user_id, data={'reason': 'Refill Timeout (5s)', 'name': context.job.data['name']}, name=f"final_{user_id}")

# 6. Admin Decision Actions (FIXED: Standardized Callback Parsing)
async def admin_decision_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("_")
    action = data[0]
    user_id = int(data[1]) # Now index 1 is always the ID

    async def smart_edit(text_to_show):
        if query.message.photo:
            await query.edit_message_caption(caption=text_to_show)
        else:
            await query.edit_message_text(text=text_to_show)

    if action == "approve":
        invite_link = await context.bot.create_chat_invite_link(chat_id=TARGET_GROUP_ID, member_limit=1)
        await context.bot.send_message(chat_id=user_id, text=f"🎉 အတည်ပြုပြီးပါပြီ။ Link: {invite_link.invite_link}")
        await smart_edit(f"✅ Approved: {user_id}")
        await notify_owner(context, f"✅ **Approved:** {user_id}")

    elif action == "recheck":
        await context.bot.send_message(chat_id=user_id, text="🔄 **သတိပေးချက်:** Admin မှ စစ်ဆေးရာတွင် ငွေဝင်ခြင်း မတွေ့ပါ။ ပြန်လည်စစ်ဆေးပြီး Confirm ပြန်နှိပ်ပါ။")
        context.job_queue.run_once(send_refill_reminder, 5, chat_id=user_id, data={'name': 'User'}, name=f"final_{user_id}")
        await smart_edit(f"🔄 User {user_id} ထံ Re-check ပို့လိုက်ပါပြီ။")

    elif action == "decline":
        await context.bot.send_message(chat_id=user_id, text="❌ Screenshot မမှန်ပါ။ ပြန်ပို့ပါ။")
        if query.message.photo: await query.edit_message_caption(caption=f"❌ Declined: {user_id}")
        else: await query.delete_message()

    elif action == "kick": # action is 'kick', data[1] is int ID
        try:
            await context.bot.ban_chat_member(chat_id=TARGET_GROUP_ID, user_id=user_id)
            await context.bot.unban_chat_member(chat_id=TARGET_GROUP_ID, user_id=user_id)
            await context.bot.send_message(chat_id=user_id, text="🚫 စည်းကမ်းမလိုက်နာသဖြင့် Kick လုပ်ခံရပါသည်။")
            await smart_edit(f"🚫 Banned/Kicked: {user_id}")
            await notify_owner(context, f"🚫 **Banned:** {user_id}")
        except Exception as e:
            await smart_edit(f"⚠️ Error: {e}")

    elif action == "spare":
        await context.bot.send_message(chat_id=user_id, text="ℹ️ Admin မှ သင့်အား အချိန်ပိုပေးထားပါသည်။")
        await smart_edit(f"😇 User {user_id} ကို Spare လုပ်လိုက်ပါသည်။")

# 7. Timer Expiration Notification
async def ask_admin_to_kick(context: ContextTypes.DEFAULT_TYPE):
    user_id = context.job.chat_id
    reason = context.job.data['reason']
    user_name = context.job.data['name']
    
    # Standardized callback: action_userid
    kick_kb = [[
        InlineKeyboardButton("✅ Kick အတည်ပြုမည်", callback_data=f"kick_{user_id}"),
        InlineKeyboardButton("❌ Spare", callback_data=f"spare_{user_id}")
    ]]
    await context.bot.send_message(
        chat_id=ADMIN_ID, 
        text=f"🚫 **KICK REQUEST**\nUser: {user_name}\nID: `{user_id}`\nReason: **{reason}**", 
        reply_markup=InlineKeyboardMarkup(kick_kb)
    )

if __name__ == '__main__':
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(ChatMemberHandler(on_member_join, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(CallbackQueryHandler(handle_ui_buttons, pattern="^(view_pay|confirm_refill)$"))
    app.add_handler(CallbackQueryHandler(admin_decision_callback, pattern="^(approve|decline|kick|recheck|spare)_"))
    app.add_handler(MessageHandler(filters.PHOTO, handle_screenshot))
    print("🔥 Nexus Velocity 3.9: Stable Release Active...")
    app.run_polling()
