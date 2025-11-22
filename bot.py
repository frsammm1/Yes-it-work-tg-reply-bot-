import os
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters
)

from database import db
from user_handlers import (
    user_panel,
    handle_user_message,
    user_send_callback,
    paid_batches_callback,
    clone_bot_callback,
    plan_selected,
    handle_payment_screenshot,
    my_clone_callback,
    user_help_callback,
    cancel_payment_callback
)
from owner_handlers import (
    owner_panel,
    owner_stats_callback,
    owner_active_callback,
    owner_banned_callback,
    user_info_callback,
    ban_user_callback,
    unban_user_callback,
    owner_ban_callback,
    owner_unban_callback,
    owner_broadcast_callback,
    receive_broadcast,
    edit_batches_callback,
    receive_batches_text,
    owner_payments_callback,
    cancel_conversation,
    BROADCAST_MSG,
    EDIT_BATCHES
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID'))
OWNER_NAME = os.getenv('OWNER_NAME', 'Sam')

async def start(update: Update, context):
    user_id = update.effective_user.id
    
    context.bot_data['OWNER_ID'] = OWNER_ID
    context.bot_data['OWNER_NAME'] = OWNER_NAME
    
    if user_id == OWNER_ID:
        await owner_panel(update, context)
    else:
        await user_panel(update, context)

async def handle_text_message(update: Update, context):
    user_id = update.effective_user.id
    msg = update.message
    
    context.bot_data['OWNER_ID'] = OWNER_ID
    context.bot_data['OWNER_NAME'] = OWNER_NAME
    
    # Owner actions
    if user_id == OWNER_ID:
        # Ban action
        if 'awaiting_ban' in context.user_data and context.user_data['awaiting_ban']:
            try:
                ban_id = int(msg.text)
                db.ban_user(ban_id)
                await msg.reply_text(f"✅ User {ban_id} has been banned!")
                context.user_data['awaiting_ban'] = False
                logger.info(f"🚫 User {ban_id} banned")
                return
            except:
                await msg.reply_text("❌ Invalid ID. Send numbers only:")
                return
        
        # Unban action
        if 'awaiting_unban' in context.user_data and context.user_data['awaiting_unban']:
            try:
                unban_id = int(msg.text)
                db.unban_user(unban_id)
                await msg.reply_text(f"✅ User {unban_id} has been unbanned!")
                context.user_data['awaiting_unban'] = False
                logger.info(f"✅ User {unban_id} unbanned")
                return
            except:
                await msg.reply_text("❌ Invalid ID. Send numbers only:")
                return
        
        # Owner replying to user message
        if msg.reply_to_message:
            target_user = db.get_user_from_msg(msg.reply_to_message.message_id)
            if target_user:
                try:
                    await context.bot.send_message(target_user, msg.text)
                    await msg.reply_text(f"✅ Reply sent to user {target_user}!")
                    logger.info(f"💬 Owner replied to user {target_user}")
                    return
                except Exception as e:
                    await msg.reply_text(f"❌ Failed: {str(e)}")
                    return
    
    # Regular user sending message (this will handle bot token detection internally)
    await handle_user_message(update, context)

async def handle_media_message(update: Update, context):
    user_id = update.effective_user.id
    msg = update.message
    
    context.bot_data['OWNER_ID'] = OWNER_ID
    context.bot_data['OWNER_NAME'] = OWNER_NAME
    
    # Owner replying with media
    if user_id == OWNER_ID and msg.reply_to_message:
        target_user = db.get_user_from_msg(msg.reply_to_message.message_id)
        if target_user:
            try:
                if msg.photo:
                    await context.bot.send_photo(target_user, msg.photo[-1].file_id, caption=msg.caption or "")
                elif msg.video:
                    await context.bot.send_video(target_user, msg.video.file_id, caption=msg.caption or "")
                elif msg.document:
                    await context.bot.send_document(target_user, msg.document.file_id, caption=msg.caption or "")
                elif msg.voice:
                    await context.bot.send_voice(target_user, msg.voice.file_id)
                elif msg.audio:
                    await context.bot.send_audio(target_user, msg.audio.file_id, caption=msg.caption or "")
                
                await msg.reply_text(f"✅ Media sent to user {target_user}!")
                logger.info(f"📎 Owner sent media to user {target_user}")
                return
            except Exception as e:
                await msg.reply_text(f"❌ Failed: {str(e)}")
                return
    
    # User sending payment screenshot
    if msg.photo and 'selected_plan' in context.user_data:
        await handle_payment_screenshot(update, context)
        return
    
    # Regular user media
    await handle_user_message(update, context)

async def handle_callback(update: Update, context):
    query = update.callback_query
    data = query.data
    
    context.bot_data['OWNER_ID'] = OWNER_ID
    context.bot_data['OWNER_NAME'] = OWNER_NAME
    
    # User callbacks
    if data == "user_send":
        await user_send_callback(update, context)
    elif data == "paid_batches":
        await paid_batches_callback(update, context)
    elif data == "clone_bot":
        await clone_bot_callback(update, context)
    elif data.startswith("plan_"):
        await plan_selected(update, context)
    elif data == "my_clone":
        await my_clone_callback(update, context)
    elif data == "user_help":
        await user_help_callback(update, context)
    elif data == "cancel_payment":
        await cancel_payment_callback(update, context)
    
    # Owner callbacks
    elif data == "owner_stats":
        await owner_stats_callback(update, context)
    elif data == "owner_active":
        await owner_active_callback(update, context)
    elif data == "owner_banned":
        await owner_banned_callback(update, context)
    elif data.startswith("userinfo_"):
        await user_info_callback(update, context)
    elif data.startswith("ban_") and not data.startswith("ban_user"):
        await ban_user_callback(update, context)
    elif data.startswith("unban_") and not data.startswith("unban_user"):
        await unban_user_callback(update, context)
    elif data == "owner_ban":
        await owner_ban_callback(update, context)
    elif data == "owner_unban":
        await owner_unban_callback(update, context)
    elif data == "owner_broadcast":
        await owner_broadcast_callback(update, context)
    elif data == "edit_batches":
        await edit_batches_callback(update, context)
    elif data == "owner_payments":
        await owner_payments_callback(update, context)
    
    # Payment approval/rejection
    elif data.startswith("approve_"):
        parts = data.split("_")
        payment_id = int(parts[1])
        user_id = int(parts[2])
        
        payment = db.approve_payment(payment_id)
        
        if payment:
            await query.answer("✅ Payment approved!", show_alert=True)
            await query.message.edit_caption(
                caption=query.message.caption + "\n\n✅ APPROVED - Waiting for bot token"
            )
            
            # Set awaiting token state in database
            db.set_awaiting_token(user_id, payment)
            
            # Notify user
            await context.bot.send_message(
                user_id,
                "🎉 Payment Approved!\n\n"
                "Now send your bot token from @BotFather:\n\n"
                "📋 Steps:\n"
                "1. Open @BotFather on Telegram\n"
                "2. Send /newbot command\n"
                "3. Follow instructions to create bot\n"
                "4. Copy the bot token\n"
                "5. Send it here\n\n"
                "⚠️ Send ONLY the bot token as your next message!"
            )
            
            logger.info(f"✅ Payment {payment_id} approved, user {user_id} can now send bot token")
    
    elif data.startswith("reject_"):
        parts = data.split("_")
        payment_id = int(parts[1])
        user_id = int(parts[2])
        
        if db.reject_payment(payment_id):
            await query.answer("❌ Payment rejected!", show_alert=True)
            await query.message.edit_caption(
                caption=query.message.caption + "\n\n❌ REJECTED"
            )
            
            # Notify user
            await context.bot.send_message(
                user_id,
                "❌ Payment Rejected\n\n"
                "Your payment has been rejected by the owner.\n"
                "Please contact admin for more details."
            )
            
            logger.info(f"❌ Payment {payment_id} rejected")

def main():
    if not BOT_TOKEN or not OWNER_ID:
        logger.error("❌ Missing BOT_TOKEN or OWNER_ID!")
        return
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Broadcast conversation
    broadcast_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(owner_broadcast_callback, pattern="^owner_broadcast$")],
        states={
            BROADCAST_MSG: [MessageHandler(filters.ALL & ~filters.COMMAND, receive_broadcast)]
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)]
    )
    
    # Edit batches conversation
    batches_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_batches_callback, pattern="^edit_batches$")],
        states={
            EDIT_BATCHES: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_batches_text)]
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)]
    )
    
    # Add all handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(broadcast_conv)
    app.add_handler(batches_conv)
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(
        filters.PHOTO | filters.VIDEO | filters.Document.ALL | filters.VOICE | filters.AUDIO | filters.VIDEO_NOTE,
        handle_media_message
    ))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    logger.info("🚀 Bot starting with smart state management...")
    logger.info(f"👑 Owner ID: {OWNER_ID}")
    logger.info(f"📝 Owner Name: {OWNER_NAME}")
    logger.info("✅ Bot token detection active - won't interfere with messages!")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
