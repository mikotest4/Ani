import os
import time
import asyncio
from pyrogram.types import InputMediaDocument
from pyrogram.errors import FloodWait, MessageNotModified

from bot import Var
from bot.core.database import db
from bot.core.reporter import rep
from bot.core.text_utils import format_custom_filename

class TgUploader:
    def __init__(self, client):
        self.__client = client

    async def upload(self, path, name, thumb_path=None, anime_name=None):
        """Upload file to Telegram with custom thumbnail and filename support"""
        try:
            # Get custom thumbnail if anime_name is provided
            custom_thumb_file_id = None
            if anime_name:
                custom_thumb_file_id = await db.get_custom_thumb(anime_name)
                if custom_thumb_file_id:
                    await rep.report(f"✅  Using custom thumbnail\nfor: {anime_name}", "info")

            # Get custom filename if anime_name is provided
            final_filename = name
            if anime_name:
                custom_format = await db.get_custom_filename(anime_name)
                if custom_format:
                    final_filename = format_custom_filename(custom_format, name, anime_name)
                    await rep.report(f"✅  Using custom filename format\nfor: {anime_name}\nFilename: {final_filename}", "info")

            # Prepare thumbnail parameter
            thumbnail = None
            if custom_thumb_file_id:
                # For Telegram file_id, we need to download it first or use it directly
                try:
                    # Download the thumbnail file temporarily
                    temp_thumb_path = f"temp_thumb_{int(time.time())}.jpg"
                    await self.__client.download_media(custom_thumb_file_id, temp_thumb_path)
                    thumbnail = temp_thumb_path
                except Exception as e:
                    await rep.report(f"⚠️  Failed to download custom thumbnail: {str(e)}", "error")
                    thumbnail = thumb_path  # Fallback to default
            else:
                thumbnail = thumb_path

            # Upload file to FILE_STORE
            sent = await self.__client.send_document(
                chat_id=Var.FILE_STORE,
                document=path,
                file_name=final_filename,
                thumb=thumbnail,
                caption=f"**{final_filename}**\n\n**Size:** {self.humanbytes(os.path.getsize(path))}"
            )

            # Clean up temporary thumbnail file
            if thumbnail and thumbnail.startswith("temp_thumb_"):
                try:
                    os.remove(thumbnail)
                except:
                    pass

            return sent

        except FloodWait as e:
            await rep.report(f"FloodWait: {e.value} seconds", "error")
            await asyncio.sleep(e.value)
            return await self.upload(path, name, thumb_path, anime_name)
        except Exception as e:
            await rep.report(f"Upload error: {str(e)}", "error")
            return None

    async def send_to_channel(self, file_id, channel_id, caption="", thumb_file_id=None, filename=None, anime_name=None):
        """Send file to specific channel with custom thumbnail and filename"""
        try:
            # Get custom thumbnail if anime_name is provided
            custom_thumb_file_id = None
            if anime_name:
                custom_thumb_file_id = await db.get_custom_thumb(anime_name)
                if custom_thumb_file_id:
                    thumb_file_id = custom_thumb_file_id
                    await rep.report(f"✅  Using custom thumbnail for channel\nAnime: {anime_name}", "info")

            # Get custom filename if anime_name is provided
            final_filename = filename
            if anime_name and filename:
                custom_format = await db.get_custom_filename(anime_name)
                if custom_format:
                    final_filename = format_custom_filename(custom_format, filename, anime_name)
                    await rep.report(f"✅  Using custom filename for channel\nAnime: {anime_name}\nFilename: {final_filename}", "info")

            # Prepare thumbnail for channel upload
            thumbnail = None
            if thumb_file_id:
                if thumb_file_id.startswith("AgAC") or thumb_file_id.startswith("BAAx"):
                    # It's a Telegram file_id, download it temporarily
                    try:
                        temp_thumb_path = f"temp_channel_thumb_{int(time.time())}.jpg"
                        await self.__client.download_media(thumb_file_id, temp_thumb_path)
                        thumbnail = temp_thumb_path
                    except Exception as e:
                        await rep.report(f"⚠️  Failed to download thumbnail for channel: {str(e)}", "error")
                        thumbnail = None
                else:
                    # It's a local file path
                    thumbnail = thumb_file_id

            # Send to channel
            sent = await self.__client.send_document(
                chat_id=channel_id,
                document=file_id,
                file_name=final_filename or "video.mkv",
                thumb=thumbnail,
                caption=caption
            )

            # Clean up temporary thumbnail file
            if thumbnail and thumbnail.startswith("temp_channel_thumb_"):
                try:
                    os.remove(thumbnail)
                except:
                    pass

            return sent

        except FloodWait as e:
            await rep.report(f"FloodWait (Channel): {e.value} seconds", "error")
            await asyncio.sleep(e.value)
            return await self.send_to_channel(file_id, channel_id, caption, thumb_file_id, filename, anime_name)
        except Exception as e:
            await rep.report(f"Channel send error: {str(e)}", "error")
            return None

    async def copy_to_channel(self, message_id, from_chat_id, to_chat_id, caption=None):
        """Copy message to channel"""
        try:
            copied = await self.__client.copy_message(
                chat_id=to_chat_id,
                from_chat_id=from_chat_id,
                message_id=message_id,
                caption=caption
            )
            return copied
        except FloodWait as e:
            await rep.report(f"FloodWait (Copy): {e.value} seconds", "error")
            await asyncio.sleep(e.value)
            return await self.copy_to_channel(message_id, from_chat_id, to_chat_id, caption)
        except Exception as e:
            await rep.report(f"Copy error: {str(e)}", "error")
            return None

    async def forward_to_channel(self, message_id, from_chat_id, to_chat_id):
        """Forward message to channel"""
        try:
            forwarded = await self.__client.forward_messages(
                chat_id=to_chat_id,
                from_chat_id=from_chat_id,
                message_ids=message_id
            )
            return forwarded
        except FloodWait as e:
            await rep.report(f"FloodWait (Forward): {e.value} seconds", "error")
            await asyncio.sleep(e.value)
            return await self.forward_to_channel(message_id, from_chat_id, to_chat_id)
        except Exception as e:
            await rep.report(f"Forward error: {str(e)}", "error")
            return None

    async def edit_message_media(self, chat_id, message_id, new_file_id, caption=None, thumb_file_id=None, filename=None):
        """Edit message media"""
        try:
            # Prepare thumbnail for media edit
            thumbnail = None
            if thumb_file_id:
                if thumb_file_id.startswith("AgAC") or thumb_file_id.startswith("BAAx"):
                    # It's a Telegram file_id, download it temporarily
                    try:
                        temp_thumb_path = f"temp_edit_thumb_{int(time.time())}.jpg"
                        await self.__client.download_media(thumb_file_id, temp_thumb_path)
                        thumbnail = temp_thumb_path
                    except Exception as e:
                        await rep.report(f"⚠️  Failed to download thumbnail for edit: {str(e)}", "error")
                        thumbnail = None
                else:
                    # It's a local file path
                    thumbnail = thumb_file_id

            media = InputMediaDocument(
                media=new_file_id,
                thumb=thumbnail,
                caption=caption,
                file_name=filename
            )

            edited = await self.__client.edit_message_media(
                chat_id=chat_id,
                message_id=message_id,
                media=media
            )

            # Clean up temporary thumbnail file
            if thumbnail and thumbnail.startswith("temp_edit_thumb_"):
                try:
                    os.remove(thumbnail)
                except:
                    pass

            return edited

        except MessageNotModified:
            await rep.report("Message content is not modified", "warning")
            return None
        except FloodWait as e:
            await rep.report(f"FloodWait (Edit): {e.value} seconds", "error")
            await asyncio.sleep(e.value)
            return await self.edit_message_media(chat_id, message_id, new_file_id, caption, thumb_file_id, filename)
        except Exception as e:
            await rep.report(f"Edit media error: {str(e)}", "error")
            return None

    async def delete_message(self, chat_id, message_id):
        """Delete message"""
        try:
            await self.__client.delete_messages(
                chat_id=chat_id,
                message_ids=message_id
            )
            return True
        except Exception as e:
            await rep.report(f"Delete error: {str(e)}", "error")
            return False

    async def get_message(self, chat_id, message_id):
        """Get message by ID"""
        try:
            message = await self.__client.get_messages(
                chat_id=chat_id,
                message_ids=message_id
            )
            return message
        except Exception as e:
            await rep.report(f"Get message error: {str(e)}", "error")
            return None

    def humanbytes(self, size):
        """Convert bytes to human readable format"""
        if not size:
            return "0 B"
        power = 1024
        n = 0
        power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
        while size > power:
            size /= power
            n += 1
        return f"{size:.2f} {power_labels[n]}B"

    def format_duration(self, seconds):
        """Format duration in seconds to human readable format"""
        if not seconds:
            return "0s"
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"

    async def send_photo(self, chat_id, photo, caption=None):
        """Send photo to chat"""
        try:
            sent = await self.__client.send_photo(
                chat_id=chat_id,
                photo=photo,
                caption=caption
            )
            return sent
        except FloodWait as e:
            await rep.report(f"FloodWait (Photo): {e.value} seconds", "error")
            await asyncio.sleep(e.value)
            return await self.send_photo(chat_id, photo, caption)
        except Exception as e:
            await rep.report(f"Send photo error: {str(e)}", "error")
            return None

    async def send_video(self, chat_id, video, caption=None, duration=None, width=None, height=None, thumb=None, supports_streaming=True):
        """Send video to chat"""
        try:
            sent = await self.__client.send_video(
                chat_id=chat_id,
                video=video,
                caption=caption,
                duration=duration,
                width=width,
                height=height,
                thumb=thumb,
                supports_streaming=supports_streaming
            )
            return sent
        except FloodWait as e:
            await rep.report(f"FloodWait (Video): {e.value} seconds", "error")
            await asyncio.sleep(e.value)
            return await self.send_video(chat_id, video, caption, duration, width, height, thumb, supports_streaming)
        except Exception as e:
            await rep.report(f"Send video error: {str(e)}", "error")
            return None

    async def get_file_size(self, file_id):
        """Get file size from file_id"""
        try:
            file = await self.__client.get_file(file_id)
            return file.file_size if file else 0
        except Exception as e:
            await rep.report(f"Get file size error: {str(e)}", "error")
            return 0

    async def download_media(self, message, file_name=None, progress=None):
        """Download media from message"""
        try:
            downloaded = await self.__client.download_media(
                message=message,
                file_name=file_name,
                progress=progress
            )
            return downloaded
        except FloodWait as e:
            await rep.report(f"FloodWait (Download): {e.value} seconds", "error")
            await asyncio.sleep(e.value)
            return await self.download_media(message, file_name, progress)
        except Exception as e:
            await rep.report(f"Download error: {str(e)}", "error")
            return None
