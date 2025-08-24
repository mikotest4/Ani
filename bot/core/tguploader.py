from time import time, sleep
from traceback import format_exc
from math import floor
from os import path as ospath
from aiofiles.os import remove as aioremove
from pyrogram.errors import FloodWait

from bot import bot, Var
from .func_utils import editMessage, sendMessage, convertBytes, convertTime
from .database import db
from .reporter import rep

class TgUploader:
    def __init__(self, message, anime_name=None):
        self.cancelled = False
        self.message = message
        self.anime_name = anime_name or ""
        self.__name = ""
        self.__qual = ""
        self.__client = bot
        self.__start = time()
        self.__updater = time()

    async def upload(self, path, qual):
        self.__name = ospath.basename(path)
        self.__qual = qual
        
        try:
            # Check for custom thumbnail for this anime
            custom_thumb = await db.get_custom_thumb(self.anime_name)
            
            # Use custom thumbnail if available, otherwise use default
            if custom_thumb:
                thumb_to_use = custom_thumb
                await rep.report(f"✅ Using custom thumbnail for: {self.anime_name}", "info")
            else:
                thumb_to_use = "thumb.jpg" if ospath.exists("thumb.jpg") else None
                await rep.report(f"🖼️ Using default thumbnail for: {self.anime_name}", "info")
            
            if Var.AS_DOC:
                return await self.__client.send_document(chat_id=Var.FILE_STORE,
                    document=path,
                    thumb=thumb_to_use,
                    caption=f"<b>{self.__name}</b>",
                    force_document=True,
                    progress=self.progress_status
                )
            else:
                return await self.__client.send_video(chat_id=Var.FILE_STORE,
                    video=path,
                    thumb=thumb_to_use,
                    caption=f"<b>{self.__name}</b>",
                    progress=self.progress_status
                )
        except FloodWait as e:
            sleep(e.value * 1.5)
            return await self.upload(path, qual)
        except Exception as e:
            await rep.report(format_exc(), "error")
            raise e
        finally:
            await aioremove(path)

    async def progress_status(self, current, total):
        if self.cancelled:
            self.__client.stop_transmission()
        now = time()
        diff = now - self.__start
        if (now - self.__updater) >= 7 or current == total:
            self.__updater = now
            percent = round(current / total * 100, 2)
            speed = current / diff 
            eta = round((total - current) / speed)
            bar = floor(percent/8)*"█" + (12 - floor(percent/8))*"▒"
            progress_str = f"""<b>ᴀɴɪᴍᴇ ɴᴀᴍᴇ :</b> <b>{self.__name}</b>

<blockquote>‣ <b>sᴛᴀᴛᴜs :</b> ᴜᴘʟᴏᴀᴅɪɴɢ
    <code>[{bar}]</code> {percent}%</blockquote>
<blockquote>‣ <b>sɪᴢᴇ :</b> {convertBytes(current)} out of ~ {convertBytes(total)}
‣ <b>sᴘᴇᴇᴅ :</b> {convertBytes(speed)}/s
‣ <b>ᴛɪᴍᴇ ᴛᴏᴏᴋ :</b> {convertTime(diff)}
‣ <b>ᴛɪᴍᴇ ʟᴇғᴛ :</b> {convertTime(eta)}</blockquote>
<blockquote>‣ <b>ғɪʟᴇ(s) ᴇɴᴄᴏᴅᴇᴅ:</b> <code>{Var.QUALS.index(self.__qual)} / {len(Var.QUALS)}</code></blockquote>"""
            
            await editMessage(self.message, progress_str)
