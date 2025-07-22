from asyncio import gather, create_task, sleep as asleep, Event
from asyncio.subprocess import PIPE
from os import path as ospath, system
from aiofiles import open as aiopen
from aiofiles.os import remove as aioremove
from traceback import format_exc
from base64 import urlsafe_b64encode
from time import time
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot import bot, bot_loop, Var, ani_cache, ffQueue, ffLock, ff_queued
from .tordownload import TorDownloader
from .database import db
from .func_utils import getfeed, encode, editMessage, sendMessage, convertBytes
from .text_utils import TextEditor
from .ffencoder import FFEncoder
from .tguploader import TgUploader
from .reporter import rep

btn_formatter = {
    'Hdrip': '𝗛𝗗𝗥𝗶𝗽',
    '1080': '𝟭𝟬𝟴𝟬𝗽', 
    '720': '𝟳𝟮𝟬𝗽',
    '480': '𝟰𝟴𝟬𝗽'
 }

async def fetch_animes():
    await rep.report("Fetch Animes Started !!", "info")
    while True:
        await asleep(60)
        if ani_cache['fetch_animes']:
            for link in Var.RSS_ITEMS:
                if (info := await getfeed(link, 0)):
                    bot_loop.create_task(get_animes(info.title, info.link))

async def get_animes(name, torrent, force=False):
    try:
        aniInfo = TextEditor(name)
        await aniInfo.load_anilist()
        ani_id, ep_no = aniInfo.adata.get('id'), aniInfo.pdata.get("episode_number")
        if ani_id not in ani_cache['ongoing']:
            ani_cache['ongoing'].add(ani_id)
        elif not force:
            return
        if not force and ani_id in ani_cache['completed']:
            return
        if force or (not (ani_data := await db.getAnime(ani_id)) \
            or (ani_data and not (qual_data := ani_data.get(ep_no))) \
            or (ani_data and qual_data and not all(qual for qual in qual_data.values()))):
            
            if "[Batch]" in name:
                await rep.report(f"Torrent Skipped!\n\n{name}", "warning")
                return
            
            await rep.report(f"New Anime Torrent Found!\n\n{name}", "info")
            post_msg = await bot.send_photo(
                Var.MAIN_CHANNEL,
                photo=await aniInfo.get_poster(),
                caption=await aniInfo.get_caption()
            )
            
            # Send sticker after the post
            await bot.send_sticker(
                Var.MAIN_CHANNEL,
                sticker="CAACAgUAAxkBAAEOyQtoXB1SxAZqiP0wK7NbBBxxHwUG7gAC4BMAAp6PIFcLAAGEEdQGq4s2BA"
            )
            
            await asleep(1.5)
            stat_msg = await sendMessage(Var.MAIN_CHANNEL, f"<b>ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ᴀɴɪᴍᴇ</b>") #downloade Massage 
            dl = await TorDownloader("./downloads").download(torrent, name)
            if not dl or not ospath.exists(dl):
                await rep.report(f"<b> ғɪʟᴇ ᴅᴏᴡɴʟᴏᴀᴅ ɪɴᴄᴏᴍᴘʟᴇᴛᴇ, ᴛʀʏ ᴀɢᴀɪɴ</b>", "error")
                await stat_msg.delete()
                return

            post_id = post_msg.id
            ffEvent = Event()
            ff_queued[post_id] = ffEvent
            if ffLock.locked():
                await editMessage(stat_msg, f"<b>ϙᴜᴇᴜᴇᴅ ᴛᴏ ᴇɴᴄᴏᴅᴇ...</b>")
                await rep.report("<b>ᴀᴅᴅᴇᴅ ᴛᴀsᴋ ᴛᴏ ϙᴜᴇᴜᴇ....</b>", "info")
            await ffQueue.put(post_id)
            await ffEvent.wait()
            
            await ffLock.acquire()
            btns = []
            for qual in Var.QUALS:
                filename = await aniInfo.get_upname(qual)
                await editMessage(stat_msg, f"‣ <b>ᴀɴɪᴍᴇ ɴᴀᴍᴇ :</b><b>{name}</b>\n\n<b>ʀᴇᴀᴅʏ ᴛᴏ ᴇɴᴄᴏᴅᴇ.....</b>") # Ready to Encode...
                
                await asleep(1.5)
                await rep.report("<b>sᴛᴀʀᴛɪɴɢ ᴇɴᴄᴏᴅᴇ...</b>", "info")
                try:
                    out_path = await FFEncoder(stat_msg, dl, filename, qual).start_encode()
                except Exception as e:
                    await rep.report(f"<b>ᴇʀʀᴏʀ: {e}, ᴄᴀɴᴄᴇʟʟᴇᴅ, ʀᴇᴛʀʏ ᴀɢᴀɪᴊ !</b>", "error")
                    await stat_msg.delete()
                    ffLock.release()
                    return
                await rep.report("<b>sᴜᴄᴄᴇssғᴜʟʟʏ ᴄᴏᴍᴘʀᴇssᴇᴅ ɴᴏᴡ ɢᴏɪɴɢ ᴛᴏ ᴜᴘʟᴏᴀᴅ.... </b>", "info")
                
                await editMessage(stat_msg, f"<b>ʀᴇᴀᴅʏ ᴛᴏ ᴜᴘʟᴏᴀᴅ...</b>")
                await asleep(1.5)
                try:
                    msg = await TgUploader(stat_msg).upload(out_path, qual)
                except Exception as e:
                    await rep.report(f"<b>ᴇʀʀᴏʀ: {e}, ᴄᴀɴᴄᴇʟʟᴇᴅ, ʀᴇᴛʀʏ ᴀɢᴀɪɴ !</b>", "error")
                    await stat_msg.delete()
                    ffLock.release()
                    return
                await rep.report("<b>sᴜᴄᴄᴇsғᴜʟʟʏ ᴜᴘʟᴏᴀᴅᴇᴅ ғɪʟᴇ ɪɴᴛᴏ ᴛɢ...</b>", "info")
                
                msg_id = msg.id
                link = f"https://telegram.me/{(await bot.get_me()).username}?start={await encode('get-'+str(msg_id * abs(Var.FILE_STORE)))}"
                
                if post_msg:
                    if len(btns) != 0 and len(btns[-1]) == 1:
                        btns[-1].insert(1, InlineKeyboardButton(f"{btn_formatter[qual]} - {convertBytes(msg.document.file_size)}", url=link))
                    else:
                        btns.append([InlineKeyboardButton(f"{btn_formatter[qual]} - {convertBytes(msg.document.file_size)}", url=link)])
                    await editMessage(post_msg, post_msg.caption.html if post_msg.caption else "", InlineKeyboardMarkup(btns))
                    
                await db.saveAnime(ani_id, ep_no, qual, post_id)
                bot_loop.create_task(extra_utils(msg_id, out_path))
            ffLock.release()
            
            await stat_msg.delete()
            await aioremove(dl)
        ani_cache['completed'].add(ani_id)
    except Exception as error:
        await rep.report(format_exc(), "error")

async def extra_utils(msg_id, out_path):
    msg = await bot.get_messages(Var.FILE_STORE, message_ids=msg_id)

    if Var.BACKUP_CHANNEL != 0:
        for chat_id in Var.BACKUP_CHANNEL.split():
            await msg.copy(int(chat_id))
            
    # MediaInfo, ScreenShots, Sample Video ( Add-ons Features )
