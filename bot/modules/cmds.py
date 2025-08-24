from asyncio import sleep as asleep, gather
from urllib.parse import parse_qs, urlparse, unquote
from pyrogram.filters import command, private, user, forwarded
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
    
    # Check if user is banned
    if await db.is_banned(uid):
        return await sendMessage(message, "<b>⛔ Yᴏᴜ ᴀʀᴇ ʙᴀɴɴᴇᴅ ғʀᴏᴍ ᴜsɪɴɢ ᴛʜɪs ʙᴏᴛ.</b>")
    
    temp = await sendMessage(message, "<b>ᴄᴏɴɴᴇᴄᴛɪɴɢ..</b>")
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
    await sendMessage(message, f"<b>ᴛᴀsᴋ ᴀᴅᴅᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ !</b>\n\n<b>• ᴀɴɪᴍᴇ ɴᴀᴍᴇ:</b> {taskInfo.title}")

@bot.on_message(command('rtask') & private & admin)
@new_task
async def r_task(client, message):
    if len(args := message.text.split()) <= 1:
        return await sendMessage(message, "<b>ɴᴏ ʟɪɴᴋ ғᴏᴜɴᴅ ᴛᴏ ʀᴇᴛʀʏ</b>")
    
    index = int(args[2]) if len(args) > 2 and args[2].isdigit() else 0
    if not (taskInfo := await getfeed(args[1], index)):
        return await sendMessage(message, "<b>ɴᴏ ᴛᴀsᴋ ғᴏᴜɴᴅ ᴛᴏ ʀᴇᴛʀʏ ғᴏʀ ᴛʜᴇ ᴘʀᴏᴠɪᴅᴇᴅ ʟɪɴᴋ</b>")
    
    ani_task = bot_loop.create_task(get_animes(taskInfo.title, taskInfo.link, True))
    await sendMessage(message, f"<b>ᴛᴀsᴋ ʀᴇᴛʀɪᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ !</b>\n\n<b>• ᴀɴɪᴍᴇ ɴᴀᴍᴇ:</b> {taskInfo.title}")

@bot.on_message(command('reboot') & private & admin)
@new_task
async def reboot(client, message):
    await sendMessage(message, "<b>ᴄʟᴇᴀʀɪɴɢ ᴀɴɪᴍᴇ ᴄᴀᴄʜᴇ !!</b>")
    await db.reboot()
    await sendMessage(message, "<b>ʀᴇʙᴏᴏᴛ sᴜᴄᴄᴇssғᴜʟ !!</b>")

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

🔸 <b>ɴᴀᴍᴇ: {anime_name}</b>

🧲 <b>ᴍᴀɢɴᴇᴛ: {magnet_link[:50]}...</b>"""
    
    await sendMessage(message, confirmation_msg)
    
    # Start processing the anime
    ani_task = bot_loop.create_task(get_animes(anime_name, magnet_link, True))
    await sendMessage(message, f"<b>ᴘʀᴏᴄᴇssɪɴɢ sᴛᴀʀᴛᴇᴅ !</b>\n\n• <b>ᴛᴀsᴋ ɴᴀᴍᴇ :</b> {anime_name}")

# ENHANCED CHANNEL MANAGEMENT COMMANDS WITH FORWARD MESSAGE SYSTEM

@bot.on_message(command('connectchannel') & private & admin)
@new_task
async def connect_channel(client, message):
    # Get anime name from command
    text = message.text.strip()
    anime_name = text.replace('/connectchannel', '').strip()
    
    if not anime_name:
        return await sendMessage(message, 
            "<b>❌ Invalid Usage!</b>\n\n"
            "<b>📌 Usage:</b>\n"
            "<code>/connectchannel [anime_name]</code>\n\n"
            "<b>Example:</b>\n"
            "<code>/connectchannel Rascal Does Not Dream of Bunny Girl Senpai</code>"
        )
    
    # Store pending connection
    await db.add_pending_connection(message.from_user.id, anime_name)
    
    # Send instructions to user
    await sendMessage(message, 
        f"📺 <b>Setting up channel connection for:</b>\n"
        f"<code>{anime_name}</code>\n\n"
        f"👆 <b>Please forward any message from the channel you want to connect to this anime.</b>\n\n"
        f"⏱️ <b>Waiting for forwarded message...</b>\n"
        f"<i>Timeout: 30 seconds</i>"
    )
    
    # Set timeout to auto-cleanup
    async def cleanup_timeout():
        await asleep(30)
        if await db.get_pending_connection(message.from_user.id):
            await db.remove_pending_connection(message.from_user.id)
            await sendMessage(message, 
                f"⏰ <b>Connection timeout!</b>\n\n"
                f"Please try <code>/connectchannel {anime_name}</code> again and forward a message within 30 seconds."
            )
    
    bot_loop.create_task(cleanup_timeout())

@bot.on_message(forwarded & private & admin)
@new_task
async def handle_forwarded_message(client, message):
    user_id = message.from_user.id
    
    # Check if user has pending connection
    anime_name = await db.get_pending_connection(user_id)
    if not anime_name:
        return  # User doesn't have pending connection
    
    # Skip if waiting for invite link
    if anime_name.startswith("INVITE:"):
        return
    
    try:
        # Get channel info from forwarded message
        if message.forward_from_chat:
            channel = message.forward_from_chat
            channel_id = channel.id
            channel_title = channel.title
            
            # Test bot access to the channel
            test_msg = await client.send_message(channel_id, "🔗 Connection test...")
            await test_msg.delete()
            
            # Remove pending connection first
            await db.remove_pending_connection(user_id)
            
            # Ask for invite link
            await sendMessage(message, 
                f"✅ <b>Channel Access Verified!</b>\n\n"
                f"📺 <b>Anime:</b> {anime_name}\n"
                f"🆔 <b>Channel:</b> {channel_title}\n\n"
                f"📎 <b>Please send the invite link for this channel:</b>\n"
                f"<i>Example: https://t.me/+VR0qLIGlLHA4NzA1</i>"
            )
            
            # Store temporary data for invite link collection
            await db.add_pending_connection(user_id, f"INVITE:{anime_name}:{channel_id}:{channel_title}")
            
        else:
            await sendMessage(message, 
                "<b>❌ Please forward a message from a channel, not from a user or group.</b>"
            )
            
    except Exception as e:
        await db.remove_pending_connection(user_id)
        await sendMessage(message, 
            f"❌ <b>Error connecting channel:</b>\n"
            f"<code>{str(e)}</code>\n\n"
            f"<b>Make sure:</b>\n"
            f"• Bot is added to the channel\n"
            f"• Bot has admin rights with send messages permission\n"
            f"• You forwarded from the correct channel"
        )

@bot.on_message(private & admin & ~command(['connectchannel', 'listconnections', 'removeconnection', 'start', 'users', 'pause', 'resume', 'log', 'addlink', 'addtask', 'rtask', 'reboot', 'addmagnet']) & ~forwarded)
@new_task
async def handle_invite_link(client, message):
    user_id = message.from_user.id
    
    # Check if user is sending invite link
    pending = await db.get_pending_connection(user_id)
    if pending and pending.startswith("INVITE:"):
        try:
            parts = pending.split(":", 3)
            anime_name = parts[1]
            channel_id = int(parts[2])
            channel_title = parts[3]
            
            invite_link = message.text.strip()
            
            # Validate invite link format
            if not invite_link.startswith("https://t.me/"):
                return await sendMessage(message, 
                    "<b>❌ Invalid invite link format!</b>\n\n"
                    "<b>Please send a valid Telegram invite link:</b>\n"
                    "<i>Example: https://t.me/+VR0qLIGlLHA4NzA1</i>"
                )
            
            # Save to database with invite link
            await db.add_anime_channel(anime_name, channel_id, channel_title, invite_link)
            
            # Remove pending connection
            await db.remove_pending_connection(user_id)
            
            # Send success message
            await sendMessage(message, 
                f"🎉 <b>Channel Connected Successfully!</b>\n\n"
                f"📺 <b>Anime:</b> {anime_name}\n"
                f"🆔 <b>Channel:</b> {channel_title}\n"
                f"🔗 <b>Channel ID:</b> <code>{channel_id}</code>\n"
                f"📎 <b>Invite Link:</b> {invite_link}\n\n"
                f"ℹ️ <b>All future episodes will post to the dedicated channel with join buttons in main channel!</b>"
            )
            
        except Exception as e:
            await db.remove_pending_connection(user_id)
            await sendMessage(message, f"❌ <b>Error saving connection:</b> {str(e)}")

@bot.on_message(command('listconnections') & private & admin)
@new_task
async def list_connections(client, message):
    mappings = await db.get_all_anime_channels()
    
    if not mappings:
        return await sendMessage(message, 
            "<b>📋 No anime channels connected yet.</b>\n\n"
            "<b>Use:</b> <code>/connectchannel [anime_name]</code> to connect channels."
        )
    
    result = "<b>📺 Connected Anime Channels:</b>\n\n"
    for mapping in mappings:
        result += f"🎬 <b>{mapping['anime_name']}</b>\n"
        result += f"├ <b>Channel:</b> {mapping.get('channel_title', 'Unknown')}\n"
        result += f"├ <b>ID:</b> <code>{mapping['channel_id']}</code>\n"
        if mapping.get('invite_link'):
            result += f"└ <b>Link:</b> {mapping['invite_link']}\n\n"
        else:
            result += f"└ <b>Link:</b> Not set\n\n"
    
    await sendMessage(message, result)

@bot.on_message(command('removeconnection') & private & admin)
@new_task
async def remove_connection(client, message):
    # Better command parsing for anime names with spaces
    text = message.text.strip()
    anime_name = text.replace('/removeconnection', '').strip()
    
    if not anime_name:
        return await sendMessage(message, 
            "<b>❌ Invalid Usage!</b>\n\n"
            "<b>📌 Usage:</b>\n"
            "<code>/removeconnection [anime_name]</code>\n\n"
            "<b>Example:</b>\n"
            "<code>/removeconnection Rascal Does Not Dream of Bunny Girl Senpai</code>"
        )
    
    success = await db.remove_anime_channel(anime_name)
    
    if success:
        await sendMessage(message, 
            f"✅ <b>Connection Removed!</b>\n\n"
            f"📺 <b>Anime:</b> {anime_name}\n"
            f"ℹ️ <b>Future episodes will now post to main channel.</b>"
        )
    else:
        await sendMessage(message, 
            f"❌ <b>No connection found for:</b> {anime_name}\n\n"
            f"<b>Use:</b> <code>/listconnections</code> to see all connections."
        )
