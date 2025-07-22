from asyncio import sleep as asleep
from pyrogram import filters
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, UserNotParticipant
from pyrogram.types import Message

from bot import bot, Var, bot_loop
from bot.core.func_utils import sendMessage, editMessage, new_task
from bot.core.database import db
from bot.core.reporter import rep

REPLY_ERROR = "<code>Use this command as a reply to any telegram message without any spaces.</code>"

@bot.on_message(filters.private & filters.command('pbroadcast') & filters.user(Var.ADMINS))
@new_task
async def pin_broadcast(client, message: Message):
    """Broadcast and pin message to all users"""
    if not message.reply_to_message:
        msg = await sendMessage(message, "Reply to a message to broadcast and pin it.")
        await asleep(8)
        await msg.delete()
        return

    # Get all users from database
    query = await db.get_all_users()
    if not query:
        await sendMessage(message, "No users found in database.")
        return

    broadcast_msg = message.reply_to_message
    total = 0
    successful = 0
    blocked = 0
    deleted = 0
    unsuccessful = 0

    pls_wait = await sendMessage(message, "<i>ʙʀᴏᴀᴅᴄᴀꜱᴛ ᴘʀᴏᴄᴇꜱꜱɪɴɢ....</i>")
    
    for chat_id in query:
        try:
            # Send and pin the message
            sent_msg = await broadcast_msg.copy(chat_id)
            try:
                await client.pin_chat_message(chat_id=chat_id, message_id=sent_msg.id, both_sides=True)
            except Exception as pin_error:
                await rep.report(f"Failed to pin message for user {chat_id}: {pin_error}", "warning", log=False)
            successful += 1
        except FloodWait as e:
            await asleep(e.value)
            try:
                sent_msg = await broadcast_msg.copy(chat_id)
                try:
                    await client.pin_chat_message(chat_id=chat_id, message_id=sent_msg.id, both_sides=True)
                except Exception:
                    pass
                successful += 1
            except Exception:
                unsuccessful += 1
        except UserIsBlocked:
            await db.remove_user(chat_id)
            blocked += 1
        except InputUserDeactivated:
            await db.remove_user(chat_id)
            deleted += 1
        except Exception as e:
            await rep.report(f"Failed to send or pin message to {chat_id}: {e}", "error", log=False)
            unsuccessful += 1
        total += 1

    status = f"""<b><u>ʙʀᴏᴀᴅᴄᴀꜱᴛ ᴄᴏᴍᴘʟᴇᴛᴇᴅ</u></b>

Total Users: <code>{total}</code>
Successful: <code>{successful}</code>
Blocked Users: <code>{blocked}</code>
Deleted Accounts: <code>{deleted}</code>
Unsuccessful: <code>{unsuccessful}</code>"""

    await editMessage(pls_wait, status)

@bot.on_message(filters.private & filters.command('broadcast') & filters.user(Var.ADMINS))
@new_task
async def normal_broadcast(client, message: Message):
    """Normal broadcast to all users"""
    if not message.reply_to_message:
        msg = await sendMessage(message, REPLY_ERROR)
        await asleep(8)
        await msg.delete()
        return

    # Get all users from database
    query = await db.get_all_users()
    if not query:
        await sendMessage(message, "No users found in database.")
        return

    broadcast_msg = message.reply_to_message
    total = 0
    successful = 0
    blocked = 0
    deleted = 0
    unsuccessful = 0

    pls_wait = await sendMessage(message, "<i>ʙʀᴏᴀᴅᴄᴀꜱᴛ ᴘʀᴏᴄᴇꜱꜱɪɴɢ....</i>")
    
    for chat_id in query:
        try:
            await broadcast_msg.copy(chat_id)
            successful += 1
        except FloodWait as e:
            await asleep(e.value)
            try:
                await broadcast_msg.copy(chat_id)
                successful += 1
            except Exception:
                unsuccessful += 1
        except UserIsBlocked:
            await db.remove_user(chat_id)
            blocked += 1
        except InputUserDeactivated:
            await db.remove_user(chat_id)
            deleted += 1
        except Exception as e:
            await rep.report(f"Failed to send message to {chat_id}: {e}", "error", log=False)
            unsuccessful += 1
        total += 1

    status = f"""<b><u>ʙʀᴏᴀᴅᴄᴀꜱᴛ ᴄᴏᴍᴘʟᴇᴛᴇᴅ</u></b>

Total Users: <code>{total}</code>
Successful: <code>{successful}</code>
Blocked Users: <code>{blocked}</code>
Deleted Accounts: <code>{deleted}</code>
Unsuccessful: <code>{unsuccessful}</code>"""

    await editMessage(pls_wait, status)

@bot.on_message(filters.private & filters.command('dbroadcast') & filters.user(Var.ADMINS))
@new_task
async def delete_broadcast(client, message: Message):
    """Broadcast with auto-delete after specified duration"""
    if not message.reply_to_message:
        msg = await sendMessage(message, "Pʟᴇᴀsᴇ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴍᴇssᴀɢᴇ ᴛᴏ ʙʀᴏᴀᴅᴄᴀsᴛ ɪᴛ ᴡɪᴛʜ Aᴜᴛᴏ-Dᴇʟᴇᴛᴇ.")
        await asleep(8)
        await msg.delete()
        return

    try:
        duration = int(message.command[1]) if len(message.command) > 1 else 60  # Default 60 seconds
    except (IndexError, ValueError):
        await sendMessage(message, "<b>Pʟᴇᴀsᴇ ᴜsᴇ ᴀ ᴠᴀʟɪᴅ ᴅᴜʀᴀᴛɪᴏɴ ɪɴ sᴇᴄᴏɴᴅs.</b>\nUsᴀɢᴇ: <code>/dbroadcast {duration}</code>")
        return

    # Get all users from database
    query = await db.get_all_users()
    if not query:
        await sendMessage(message, "No users found in database.")
        return

    broadcast_msg = message.reply_to_message
    total = 0
    successful = 0
    blocked = 0
    deleted = 0
    unsuccessful = 0

    pls_wait = await sendMessage(message, f"<i>Broadcast with {duration}s auto-delete processing....</i>")
    
    for chat_id in query:
        try:
            sent_msg = await broadcast_msg.copy(chat_id)
            # Schedule deletion after specified duration
            bot_loop.create_task(delete_after_delay(sent_msg, duration))
            successful += 1
        except FloodWait as e:
            await asleep(e.value)
            try:
                sent_msg = await broadcast_msg.copy(chat_id)
                bot_loop.create_task(delete_after_delay(sent_msg, duration))
                successful += 1
            except Exception:
                unsuccessful += 1
        except UserIsBlocked:
            await db.remove_user(chat_id)
            blocked += 1
        except InputUserDeactivated:
            await db.remove_user(chat_id)
            deleted += 1
        except Exception as e:
            await rep.report(f"Failed to send message to {chat_id}: {e}", "error", log=False)
            unsuccessful += 1
        total += 1

    status = f"""<b><u>Bʀᴏᴀᴅᴄᴀsᴛɪɴɢ ᴡɪᴛʜ Aᴜᴛᴏ-Dᴇʟᴇᴛᴇ ᴄᴏᴍᴘʟᴇᴛᴇᴅ</u></b>

Total Users: <code>{total}</code>
Successful: <code>{successful}</code>
Blocked Users: <code>{blocked}</code>
Deleted Accounts: <code>{deleted}</code>
Unsuccessful: <code>{unsuccessful}</code>
Duration: <code>{duration}s</code>"""

    await editMessage(pls_wait, status)

@bot.on_message(filters.private & filters.command('gbroadcast') & filters.user(Var.ADMINS))
@new_task
async def group_broadcast(client, message: Message):
    """Broadcast to groups/channels (if applicable)"""
    if not message.reply_to_message:
        msg = await sendMessage(message, REPLY_ERROR)
        await asleep(8)
        await msg.delete()
        return

    # Define target groups/channels
    target_chats = [Var.MAIN_CHANNEL]
    if Var.LOG_CHANNEL:
        target_chats.append(Var.LOG_CHANNEL)
    if Var.BACKUP_CHANNEL:
        for chat_id in str(Var.BACKUP_CHANNEL).split():
            try:
                target_chats.append(int(chat_id))
            except ValueError:
                continue

    broadcast_msg = message.reply_to_message
    total = 0
    successful = 0
    unsuccessful = 0

    pls_wait = await sendMessage(message, "<i>ɢʀᴏᴜᴘ ʙʀᴏᴀᴅᴄᴀꜱᴛ ᴘʀᴏᴄᴇꜱꜱɪɴɢ....</i>")
    
    for chat_id in target_chats:
        try:
            await broadcast_msg.copy(chat_id)
            successful += 1
        except FloodWait as e:
            await asleep(e.value)
            try:
                await broadcast_msg.copy(chat_id)
                successful += 1
            except Exception:
                unsuccessful += 1
        except Exception as e:
            await rep.report(f"Failed to send message to group {chat_id}: {e}", "error", log=False)
            unsuccessful += 1
        total += 1

    status = f"""<b><u>ɢʀᴏᴜᴘ ʙʀᴏᴀᴅᴄᴀꜱᴛ ᴄᴏᴍᴘʟᴇᴛᴇᴅ</u></b>

Total Chats: <code>{total}</code>
Successful: <code>{successful}</code>
Unsuccessful: <code>{unsuccessful}</code>"""

    await editMessage(pls_wait, status)

@bot.on_message(filters.private & filters.command('stats') & filters.user(Var.ADMINS))
@new_task
async def bot_stats(client, message: Message):
    """Get bot statistics"""
    try:
        total_users = await db.get_user_count()
        status = f"""<b>📊 ʙᴏᴛ sᴛᴀᴛɪsᴛɪᴄs</b>

👥 Total Users: <code>{total_users}</code>
🤖 Bot Status: <code>Running</code>
📺 Main Channel: <code>{Var.MAIN_CHANNEL}</code>
📁 File Store: <code>{Var.FILE_STORE}</code>
🔧 Admin Count: <code>{len(Var.ADMINS)}</code>"""
        
        await sendMessage(message, status)
    except Exception as e:
        await rep.report(f"Error getting stats: {e}", "error")
        await sendMessage(message, "Error getting bot statistics.")

@bot.on_message(filters.private & filters.command('adduser') & filters.user(Var.ADMINS))
@new_task
async def add_user_manual(client, message: Message):
    """Manually add a user to database"""
    try:
        if len(message.command) < 2:
            await sendMessage(message, "<b>Usage:</b> <code>/adduser {user_id} [name]</code>")
            return
        
        user_id = int(message.command[1])
        name = " ".join(message.command[2:]) if len(message.command) > 2 else None
        
        success = await db.add_user(user_id, name)
        if success:
            await sendMessage(message, f"<b>User {user_id} added successfully!</b>")
        else:
            await sendMessage(message, f"<b>Failed to add user {user_id}</b>")
    except ValueError:
        await sendMessage(message, "<b>Invalid user ID. Please provide a valid number.</b>")
    except Exception as e:
        await rep.report(f"Error adding user manually: {e}", "error")
        await sendMessage(message, "<b>Error adding user.</b>")

@bot.on_message(filters.private & filters.command('removeuser') & filters.user(Var.ADMINS))
@new_task
async def remove_user_manual(client, message: Message):
    """Manually remove a user from database"""
    try:
        if len(message.command) < 2:
            await sendMessage(message, "<b>Usage:</b> <code>/removeuser {user_id}</code>")
            return
        
        user_id = int(message.command[1])
        
        success = await db.remove_user(user_id)
        if success:
            await sendMessage(message, f"<b>User {user_id} removed successfully!</b>")
        else:
            await sendMessage(message, f"<b>Failed to remove user {user_id}</b>")
    except ValueError:
        await sendMessage(message, "<b>Invalid user ID. Please provide a valid number.</b>")
    except Exception as e:
        await rep.report(f"Error removing user manually: {e}", "error")
        await sendMessage(message, "<b>Error removing user.</b>")

# Helper functions
async def delete_after_delay(message, delay):
    """Delete a message after specified delay"""
    try:
        await asleep(delay)
        await message.delete()
    except Exception as e:
        await rep.report(f"Failed to delete message: {e}", "error", log=False)
