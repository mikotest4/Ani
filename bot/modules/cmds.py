from asyncio import sleep as asleep, gather
from urllib.parse import parse_qs, urlparse, unquote
from pyrogram.filters import command, private, user
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors import FloodWait, MessageNotModified

from bot import bot, bot_loop, Var, ani_cache, admin
from bot.core.database import db
from bot.core.func_utils import decode, is_fsubbed, get_fsubs, editMessage, sendMessage, new_task, convertTime, getfeed
from bot.core.auto_animes import get_animes
from bot.core.reporter import rep

@bot.on_message(command('start') & private)
@new_task
async def start_msg(client, message):
    uid = message.from_user.id
    from_user = message.from_user
    txtargs = message.text.split()
    
    # Track user in database
    await db.add_user(uid)
    
    temp = await sendMessage(message, "<b>ᴄᴏɴɴᴇᴄᴛɪɴɢ..</ib")
    if not await is_fsubbed(uid):
        txt, btns = await get_fsubs(uid, txtargs)
        return await editMessage(temp, txt, InlineKeyboardMarkup(btns))
    if len(txtargs) <= 1:
        await temp.delete()
        btns = []
        for elem in Var.START_BUTTONS.split():
            try:
                bt, link = elem.split('|', maxsplit=1)
            except:
                continue
            if len(btns) != 0 and len(btns[-1]) == 1:
                btns[-1].insert(1, InlineKeyboardButton(bt, url=link))
            else:
                btns.append([InlineKeyboardButton(bt, url=link)])
        smsg = Var.START_MSG.format(first_name=from_user.first_name,
                                    last_name=from_user.first_name,
                                    mention=from_user.mention, 
                                    user_id=from_user.id)
        if Var.START_PHOTO:
            await message.reply_photo(
                photo=Var.START_PHOTO, 
                caption=smsg,
                reply_markup=InlineKeyboardMarkup(btns) if len(btns) != 0 else None
            )
        else:
            await sendMessage(message, smsg, InlineKeyboardMarkup(btns) if len(btns) != 0 else None)
        return
    try:
        arg = (await decode(txtargs[1])).split('-')
    except Exception as e:
        await rep.report(f"User : {uid} | Error : {str(e)}", "error")
        await editMessage(temp, "<b>ɪɴᴘᴜᴛ ʟɪɴᴋ ᴄᴏᴅᴇ ᴅᴇᴄᴏᴅᴇ ғᴀɪʟᴇᴅ !</b>")
        return
    if len(arg) == 2 and arg[0] == 'get':
        try:
            fid = int(int(arg[1]) / abs(int(Var.FILE_STORE)))
        except Exception as e:
            await rep.report(f"User : {uid} | Error : {str(e)}", "error")
            await editMessage(temp, "<b>ɪɴᴘᴜᴛ ʟɪɴᴋ ᴄᴏᴅᴇ ɪs ɪɴᴠᴀʟɪᴅ !</b>")
            return
        try:
            msg = await client.get_messages(Var.FILE_STORE, message_ids=fid)
            if msg.empty:
                return await editMessage(temp, "<b>ғɪʟᴇ ɴᴏᴛ ғᴏᴜɴᴅ !</b>")
            nmsg = await msg.copy(message.chat.id, reply_markup=None)
            await temp.delete()
            if Var.AUTO_DEL:
                async def auto_del(msg, timer, original_command, user_message):
                    # Send notification before deletion
                    notification_msg = await sendMessage(
                        user_message, 
                        f'<b>⏰ ғɪʟᴇ ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇᴅ ɪɴ {convertTime(timer)}, ғᴏʀᴡᴏʀᴅ ᴛᴏ sᴀᴠᴇᴅ ᴍᴇssᴀɢᴇs ɴᴏᴡ ..</b>'
                    )
                    await asleep(timer)
                    await msg.delete()
                    
                    # Create reload URL and button
                    try:
                        bot_info = await client.get_me()
                        reload_url = (
                            f"https://t.me/{bot_info.username}?start={original_command}"
                            if original_command and bot_info.username
                            else None
                        )
                    except Exception as e:
                        await rep.report(f"Error getting bot info: {e}", "error")
                        reload_url = None
                    
                    keyboard = InlineKeyboardMarkup(
                        [[InlineKeyboardButton("ɢᴇᴛ ғɪʟᴇ ᴀɢᴀɪɴ!", url=reload_url)]]
                    ) if reload_url else None

                    # Update notification with reload button
                    try:
                        await editMessage(
                            notification_msg,
                            "<b>ʏᴏᴜʀ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ ɪꜱ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ !!</b>",
                            keyboard
                        )
                    except Exception as e:
                        await rep.report(f"Error updating notification with 'Get File Again' button: {e}", "error")
                
                # Get dynamic delete timer from database
                del_timer = await db.get_del_timer()
                bot_loop.create_task(auto_del(nmsg, del_timer, txtargs[1] if len(txtargs) > 1 else None, message))
        except Exception as e:
            await rep.report(f"User : {uid} | Error : {str(e)}", "error")
            await editMessage(temp, "<b>ғɪʟᴇ ɴᴏᴛ ғᴏᴜɴᴅ !</b>")
    else:
        await editMessage(temp, "<b>ɪɴᴘᴜᴛ ʟɪɴᴋ ɪs ɪɴᴠᴀʟɪᴅ ғᴏʀ ᴜsᴀɢᴇ !</b>")

@bot.on_message(command('users') & private & admin)
@new_task
async def get_users(client, message):
    msg = await sendMessage(message, Var.WAIT_MSG)
    users = await db.full_userbase()
    await editMessage(msg, f"<b>{len(users)} users are using this bot</b>")
    
@bot.on_message(command('pause') & private & admin)
async def pause_fetch(client, message):
    ani_cache['fetch_animes'] = False
    await sendMessage(message, "<b>sᴜᴄᴄᴇssғᴜʟʟʏ ᴘᴀᴜsᴇᴅ ғᴇᴛᴄʜɪɴɢ ᴀɴɪᴍᴇ...</b>")

@bot.on_message(command('resume') & private & admin)
async def resume_fetch(client, message):
    ani_cache['fetch_animes'] = True
    await sendMessage(message, "<b>sᴜᴄᴄᴇssғᴜʟʟʏ ʀᴇsᴜᴍᴇᴅ ғᴇᴛᴄʜɪɴɢ ᴀɴɪᴍᴇ...</b>")

@bot.on_message(command('log') & private & admin)
@new_task
async def _log(client, message):
    await message.reply_document("log.txt", quote=True)

@bot.on_message(command('addlink') & private & admin)
@new_task
async def add_link(client, message):
    if len(args := message.text.split()) <= 1:
        return await sendMessage(message, "<b>ɴᴏ ʟɪɴᴋ ғᴏᴜɴᴅ ᴛᴏ ᴀᴅᴅ</b>")
    
    Var.RSS_ITEMS.append(args[1])
    req_msg = await sendMessage(message, f"<b>ɢʟᴏʙᴀʟ ʟɪɴᴋ ᴀᴅᴅᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!</b>\n\n <b>• ᴀʟʟ ʟɪɴᴋ(s) :</b> {', '.join(Var.RSS_ITEMS)[:-2]}")

@bot.on_message(command('addtask') & private & admin)
@new_task
async def add_task(client, message):
    if len(args := message.text.split()) <= 1:
        return await sendMessage(message, "<b>ɴᴏ ᴛᴀsᴋ ғᴏᴜɴᴅ ᴛᴏ ᴀᴅᴅ</b>")
    
    index = int(args[2]) if len(args) > 2 and args[2].isdigit() else 0
    if not (taskInfo := await getfeed(args[1], index)):
        return await sendMessage(message, "<b>ɴᴏ ᴛᴀsᴋ ғᴏᴜɴᴅ ᴛᴏ ᴀᴅᴅ ғᴏʀ ᴛʜᴇ ᴘʀᴏᴠɪᴅᴇᴅ ʟɪɴᴋ</b>")
    
    ani_task = bot_loop.create_task(get_animes(taskInfo.title, taskInfo.link, True))
    await sendMessage(message, f"<b>ᴛᴀsᴋ ᴀᴅᴅᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!</b>\n\n • <b>ᴛᴀsᴋ ɴᴀᴍᴇ : {taskInfo.title}</b>\n • <b>ᴛᴀsᴋ ʟɪɴᴋ :</b> {args[1]}")

@bot.on_message(command('addmagnet') & private & admin)
@new_task
async def add_magnet_task(client, message):
    if len(args := message.text.split(maxsplit=1)) <= 1:
        return await sendMessage(message, "<b>ɴᴏ ᴍᴀɢɴᴇᴛ ʟɪɴᴋ ғᴏᴜɴᴅ ᴛᴏ ᴀᴅᴅ</b>")
    
    magnet_link = args[1]
    
    # Extract name from magnet link
    try:
        parsed = parse_qs(urlparse(magnet_link).query)
        anime_name = unquote(parsed['dn'][0]) if 'dn' in parsed else "Unknown Anime"
    except:
        anime_name = "Unknown Anime"
    
    # Send confirmation message
    confirmation_msg = f"""✅ <b>ᴍᴀɢɴᴇᴛ ᴛᴀsᴋ ᴀᴅᴅᴇᴅ !</b>

🔸 <b>ɴᴀᴍᴇ: {anime_name}<b>

🧲 <b>ᴍᴀɢɴᴇᴛ: {magnet_link[:50]}...<b>"""
    
    await sendMessage(message, confirmation_msg)
    
    # Start processing the anime
    ani_task = bot_loop.create_task(get_animes(anime_name, magnet_link, True))
    await sendMessage(message, f"<b>ᴘʀᴏᴄᴇssɪɴɢ sᴛᴀʀᴛᴇᴅ !</b>\n\n• <b>ᴛᴀsᴋ ɴᴀᴍᴇ :</b> {anime_name}")

@bot.on_message(command('help') & private & admin)
@new_task
async def help_command(client, message):
    user_id = message.from_user.id
    
    if user_id == Var.OWNER_ID:
        help_text = """
<b>🔧 Owner Commands:</b>
• /restart - Restart the bot
• /add_admin [user_id] - Add admin
• /deladmin [user_id] or /deladmin all - Remove admin(s)
• /admins - View all admins
• /broadcast - Broadcast message to all users
• /pbroadcast - Broadcast and pin message
• /dbroadcast [duration] - Broadcast with auto-delete
• /users - Check total users
• /log - Get bot logs
• /addlink [rss_url] - Add RSS feed
• /addtask [rss_url] [index] - Add specific task
• /addmagnet [magnet_link] - Add magnet download
• /pause - Pause anime fetching
• /resume - Resume anime fetching
• /dlt_time [seconds] - Set auto-delete timer
• /check_dlt_time - Check current delete timer

<b>📊 Admin Commands:</b>
• /users - Check total users
• /log - Get bot logs
• /pause - Pause anime fetching
• /resume - Resume anime fetching
• /addlink [rss_url] - Add RSS feed
• /addtask [rss_url] [index] - Add specific task
• /addmagnet [magnet_link] - Add magnet download
• /dlt_time [seconds] - Set auto-delete timer
• /check_dlt_time - Check current delete timer
        """
    else:
        help_text = """
<b>📊 Admin Commands:</b>
• /users - Check total users
• /log - Get bot logs
• /pause - Pause anime fetching
• /resume - Resume anime fetching
• /addlink [rss_url] - Add RSS feed
• /addtask [rss_url] [index] - Add specific task
• /addmagnet [magnet_link] - Add magnet download
• /dlt_time [seconds] - Set auto-delete timer
• /check_dlt_time - Check current delete timer
        """
    
    await sendMessage(message, help_text)
