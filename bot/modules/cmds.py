from asyncio import sleep as asleep, gather
from urllib.parse import parse_qs, urlparse, unquote
from pyrogram.filters import command, private, user
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors import FloodWait, MessageNotModified

from bot import bot, bot_loop, Var, ani_cache
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
                async def auto_del(msg, timer):
                    await asleep(timer)
                    await msg.delete()
                await sendMessage(message, f'<b>ғɪʟᴇ ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇᴅ ɪɴ {convertTime(Var.DEL_TIMER)},  ғᴏʀᴡᴏʀᴅ ᴛᴏ sᴀᴠᴇᴅ ᴍᴇssᴀɢᴇs ɴᴏᴡ ..</b>')
                bot_loop.create_task(auto_del(nmsg, Var.DEL_TIMER))
        except Exception as e:
            await rep.report(f"User : {uid} | Error : {str(e)}", "error")
            await editMessage(temp, "<b>ғɪʟᴇ ɴᴏᴛ ғᴏᴜɴᴅ !</b>")
    else:
        await editMessage(temp, "<b>ɪɴᴘᴜᴛ ʟɪɴᴋ ɪs ɪɴᴠᴀʟɪᴅ ғᴏʀ ᴜsᴀɢᴇ !</b>")
    
@bot.on_message(command('pause') & private & user(Var.ADMINS))
async def pause_fetch(client, message):
    ani_cache['fetch_animes'] = False
    await sendMessage(message, "<b>sᴜᴄᴄᴇssғᴜʟʟʏ ᴘᴀᴜsᴇᴅ ғᴇᴛᴄʜɪɴɢ ᴀɴɪᴍᴇ...</b>")

@bot.on_message(command('resume') & private & user(Var.ADMINS))
async def pause_fetch(client, message):
    ani_cache['fetch_animes'] = True
    await sendMessage(message, "<b>sᴜᴄᴄᴇssғᴜʟʟʏ ʀᴇsᴜᴍᴇᴅ ғᴇᴛᴄʜɪɴɢ ᴀɴɪᴍᴇ...</b>")

@bot.on_message(command('log') & private & user(Var.ADMINS))
@new_task
async def _log(client, message):
    await message.reply_document("log.txt", quote=True)

@bot.on_message(command('addlink') & private & user(Var.ADMINS))
@new_task
async def add_task(client, message):
    if len(args := message.text.split()) <= 1:
        return await sendMessage(message, "<b>No Link Found to Add</b>")
    
    Var.RSS_ITEMS.append(args[1])
    req_msg = await sendMessage(message, f"`Global Link Added Successfully!`\n\n    • **All Link(s) :** {', '.join(Var.RSS_ITEMS)[:-2]}")

@bot.on_message(command('addtask') & private & user(Var.ADMINS))
@new_task
async def add_task(client, message):
    if len(args := message.text.split()) <= 1:
        return await sendMessage(message, "<b>No Task Found to Add</b>")
    
    index = int(args[2]) if len(args) > 2 and args[2].isdigit() else 0
    if not (taskInfo := await getfeed(args[1], index)):
        return await sendMessage(message, "<b>No Task Found to Add for the Provided Link</b>")
    
    ani_task = bot_loop.create_task(get_animes(taskInfo.title, taskInfo.link, True))
    await sendMessage(message, f"<i><b>Task Added Successfully!</b></i>\n\n    • <b>Task Name :</b> {taskInfo.title}\n    • <b>Task Link :</b> {args[1]}")

@bot.on_message(command('addmagnet') & private & user(Var.ADMINS))
@new_task
async def add_magnet_task(client, message):
    if len(args := message.text.split(maxsplit=1)) <= 1:
        return await sendMessage(message, "<b>No Magnet Link Found to Add</b>")
    
    magnet_link = args[1]
    
    # Extract name from magnet link
    try:
        parsed = parse_qs(urlparse(magnet_link).query)
        anime_name = unquote(parsed['dn'][0]) if 'dn' in parsed else "Unknown Anime"
    except:
        anime_name = "Unknown Anime"
    
    # Send confirmation message
    confirmation_msg = f"""✅ **Magnet Task Added!**

🔸 **Name:** `{anime_name}`

🧲 **Magnet:** `{magnet_link[:50]}...`"""
    
    await sendMessage(message, confirmation_msg)
    
    # Start processing the anime
    ani_task = bot_loop.create_task(get_animes(anime_name, magnet_link, True))
    await sendMessage(message, f"<i><b>Processing Started!</b></i>\n\n    • <b>Task Name :</b> {anime_name}")
