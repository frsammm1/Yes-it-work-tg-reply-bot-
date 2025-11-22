from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import db
import logging

logger = logging.getLogger(__name__)

# Fixed plans
PLANS = [
    {'days': 1, 'price': 2},
    {'days': 7, 'price': 12},
    {'days': 15, 'price': 18},
    {'days': 30, 'price': 25}
]
UPI_ID = "thefatherofficial-3@okaxis"

async def user_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if db.is_banned(user.id):
        await update.message.reply_text("⛔️ You are banned.")
        return
    
    db.add_user(user.id, user.username, user.first_name)
    
    welcome = """Hello Namaste !!! 🙏

You can send any Paid Batch Related Queries to me

Just Send a msg ✍️"""
    
    keyboard = [
        [InlineKeyboardButton("📩 Send msg to Admin", callback_data="user_send")],
        [InlineKeyboardButton("📚 Paid Batches List", callback_data="paid_batches")],
        [InlineKeyboardButton("🤖 Want's to Clone Bot?", callback_data="clone_bot")],
        [InlineKeyboardButton("📋 My Clone Bot", callback_data="my_clone")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="user_help")]
    ]
    
    await update.message.reply_text(welcome, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message
    
    if db.is_banned(user.id):
        return
    
    # CRITICAL: Check if user is waiting to send bot token
    if db.is_awaiting_token(user.id):
        await handle_bot_token(update, context)
        return
    
    db.add_user(user.id, user.username, user.first_name)
    owner_id = int(context.bot_data.get('OWNER_ID'))
    
    try:
        header = f"""
📨 New Message from User
━━━━━━━━━━━━━━━━
👤 Name: {user.first_name}
🆔 ID: <code>{user.id}</code>
📱 Username: @{user.username or 'None'}

💬 Content below:
"""
        sent = await context.bot.send_message(owner_id, header, parse_mode='HTML')
        db.map_message(user.id, sent.message_id)
        
        if msg.text:
            content = await context.bot.send_message(owner_id, msg.text)
            db.map_message(user.id, content.message_id)
        elif msg.photo:
            content = await context.bot.send_photo(owner_id, msg.photo[-1].file_id, caption=msg.caption or "")
            db.map_message(user.id, content.message_id)
        elif msg.video:
            content = await context.bot.send_video(owner_id, msg.video.file_id, caption=msg.caption or "")
            db.map_message(user.id, content.message_id)
        elif msg.document:
            content = await context.bot.send_document(owner_id, msg.document.file_id, caption=msg.caption or "")
            db.map_message(user.id, content.message_id)
        elif msg.voice:
            content = await context.bot.send_voice(owner_id, msg.voice.file_id)
            db.map_message(user.id, content.message_id)
        elif msg.audio:
            content = await context.bot.send_audio(owner_id, msg.audio.file_id, caption=msg.caption or "")
            db.map_message(user.id, content.message_id)
        elif msg.video_note:
            content = await context.bot.send_video_note(owner_id, msg.video_note.file_id)
            db.map_message(user.id, content.message_id)
        
        greeting = db.get_random_greeting()
        await msg.reply_text(greeting)
        
        logger.info(f"✅ Message from {user.id} forwarded to owner")
        
    except Exception as e:
        logger.error(f"❌ Error forwarding message: {e}")
        await msg.reply_text("❌ Failed to send message.")

async def handle_bot_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle bot token submission from user"""
    user = update.effective_user
    msg = update.message
    owner_id = int(context.bot_data.get('OWNER_ID'))
    
    if not msg.text:
        await msg.reply_text(
            "❌ Please send only the bot token as text.\n\n"
            "Get it from @BotFather and send it here."
        )
        return
    
    token = msg.text.strip()
    
    # Validate bot token format
    if ':' not in token or len(token) < 40:
        await msg.reply_text(
            "❌ Invalid bot token format!\n\n"
            "Bot token should look like:\n"
            "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz\n\n"
            "Please get the correct token from @BotFather"
        )
        return
    
    # Get payment data
    payment_data = db.get_awaiting_token_data(user.id)
    
    if not payment_data:
        await msg.reply_text("❌ Error: Payment data not found. Please contact admin.")
        db.remove_awaiting_token(user.id)
        return
    
    # Test the bot token
    try:
        from telegram import Bot
        test_bot = Bot(token=token)
        bot_info = await test_bot.get_me()
        
        # Token is valid, create clone bot
        db.add_cloned_bot(user.id, token, payment_data['plan_days'])
        db.remove_awaiting_token(user.id)
        
        # Success message to user
        await msg.reply_text(
            f"🎉 Congratulations! Your Clone Bot is Ready!\n\n"
            f"🤖 Bot: @{bot_info.username}\n"
            f"📅 Validity: {payment_data['plan_days']} day{'s' if payment_data['plan_days'] > 1 else ''}\n"
            f"⏰ Valid until: {payment_data['plan_days']} days from now\n\n"
            f"✅ Your bot is now active!\n"
            f"Users can start it and send you messages.\n\n"
            f"Use /start to return to main menu."
        )
        
        # Notify owner
        await context.bot.send_message(
            owner_id,
            f"✅ Clone Bot Created Successfully!\n\n"
            f"🤖 Bot: @{bot_info.username}\n"
            f"👤 User: {user.first_name} (@{user.username or 'None'})\n"
            f"🆔 User ID: {user.id}\n"
            f"📦 Plan: {payment_data['plan_days']} days\n"
            f"💰 Amount: ₹{payment_data['plan_price']}"
        )
        
        logger.info(f"🤖 Clone bot @{bot_info.username} created for user {user.id}")
        
    except Exception as e:
        await msg.reply_text(
            f"❌ Invalid bot token!\n\n"
            f"Error: {str(e)}\n\n"
            f"Please:\n"
            f"1. Go to @BotFather\n"
            f"2. Create a new bot with /newbot\n"
            f"3. Copy the token carefully\n"
            f"4. Send it here"
        )
        logger.error(f"❌ Bot token validation failed for user {user.id}: {e}")

async def user_send_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        "📝 Send your message now:\n\n"
        "You can send:\n"
        "• Text messages\n"
        "• Photos\n"
        "• Videos\n"
        "• Documents\n"
        "• Voice messages"
    )

async def paid_batches_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = db.get_paid_batches()
    await query.message.reply_text(f"📚 Paid Batches List\n━━━━━━━━━━━━━━━━\n\n{text}")

async def clone_bot_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = "🤖 Clone Bot Subscription Plans\n━━━━━━━━━━━━━━━━\n\nChoose a plan:\n"
    
    keyboard = []
    for plan in PLANS:
        days = plan['days']
        price = plan['price']
        button_text = f"{days} Day{'s' if days > 1 else ''} - ₹{price}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"plan_{days}_{price}")])
    
    await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def plan_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    parts = query.data.split('_')
    days = int(parts[1])
    price = int(parts[2])
    
    await query.answer()
    
    text = f"""
💳 Payment Details
━━━━━━━━━━━━━━━━
📦 Plan: {days} Day{'s' if days > 1 else ''}
💰 Amount: ₹{price}
🔗 UPI ID: {UPI_ID}

📋 Instructions:
1. Pay ₹{price} to UPI ID: {UPI_ID}
2. In payment note/remark, write: {days}days
3. Take screenshot of payment
4. Send screenshot here

⚠️ Important: After payment, send only the screenshot here!
"""
    
    keyboard = [
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_payment")]
    ]
    
    await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    context.user_data['selected_plan'] = {'days': days, 'price': price}
    logger.info(f"User {query.from_user.id} selected plan: {days} days - ₹{price}")

async def handle_payment_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'selected_plan' not in context.user_data:
        return
    
    msg = update.message
    user = update.effective_user
    
    if not msg.photo:
        return
    
    plan = context.user_data['selected_plan']
    screenshot = msg.photo[-1].file_id
    
    payment = db.add_pending_payment(user.id, plan['days'], plan['price'], screenshot)
    
    if payment:
        await msg.reply_text(
            "✅ Payment screenshot received!\n\n"
            "🔍 Your payment is under review\n"
            "⏳ Please wait for owner approval\n\n"
            f"Payment ID: #{payment['id']}"
        )
        
        owner_id = int(context.bot_data.get('OWNER_ID'))
        owner_text = f"""
💳 New Payment Received!
━━━━━━━━━━━━━━━━
Payment ID: #{payment['id']}
👤 User: {user.first_name}
🆔 ID: <code>{user.id}</code>
📱 Username: @{user.username or 'None'}

📦 Plan: {payment['plan_days']} day{'s' if payment['plan_days'] > 1 else ''}
💰 Amount: ₹{payment['plan_price']}
�� UPI: {UPI_ID}
"""
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_{payment['id']}_{user.id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_{payment['id']}_{user.id}")
            ]
        ]
        
        await context.bot.send_photo(
            owner_id,
            screenshot,
            caption=owner_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        
        del context.user_data['selected_plan']
        logger.info(f"💳 Payment screenshot from {user.id} sent to owner")
    else:
        await msg.reply_text("❌ Error processing payment. Please try again.")

async def my_clone_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    clone = db.get_cloned_bot(user_id)
    
    if not clone:
        await query.message.reply_text(
            "🤖 You don't have an active clone bot.\n\n"
            "Purchase a plan to get your own bot!"
        )
        return
    
    from datetime import datetime
    expiry = datetime.fromisoformat(clone['expiry'])
    days_left = (expiry - datetime.now()).days
    
    text = f"""
🤖 Your Clone Bot
━━━━━━━━━━━━━━━━
✅ Status: Active
📅 Days Left: {days_left}
⏰ Expires: {expiry.strftime('%Y-%m-%d')}

🔧 Features:
✅ Receive user messages
✅ Reply to users
✅ All message formats

Your bot is running!
"""
    
    await query.message.reply_text(text)

async def user_help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """
ℹ️ Help & Information
━━━━━━━━━━━━━━━━

🎯 How to use:

1️⃣ Send msg to Admin
   Send any message, photo, video, or document to the owner

2️⃣ Paid Batches List
   View available paid batches

3️⃣ Clone Bot
   - Choose a plan
   - Pay to UPI ID
   - Send payment screenshot
   - Wait for approval
   - Send bot token from @BotFather
   - Your clone bot is ready!

4️⃣ My Clone Bot
   Check your clone bot status and validity

💡 Need help? Send a message to admin!
"""
    
    await query.message.reply_text(text)

async def cancel_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("❌ Payment cancelled")
    
    if 'selected_plan' in context.user_data:
        del context.user_data['selected_plan']
    
    await query.message.reply_text("❌ Payment cancelled. Use /start to try again.")
