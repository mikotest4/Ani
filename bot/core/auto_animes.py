import re
import os
from asyncio import sleep
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from urllib.parse import unquote

from bot import bot, Var, ani_cache
from bot.core.func_utils import progress_bar, encode, new_task, download_cover_image
from bot.core.reporter import rep
from bot.core.database import db
from bot.core.text_utils import format_text

async def get_animes(anime, link, manual):
    try:
        # Check if fetching is paused
        if not ani_cache['fetch_animes']:
            return
        
        # Skip if anime already exists in cache
        ani_cache_id = re.sub(r'[^\w\s-]', '', anime).strip()
        if ani_cache_id in ani_cache.get('animes', []):
            return
        
        # Add to cache to prevent duplicates
        if 'animes' not in ani_cache:
            ani_cache['animes'] = []
        ani_cache['animes'].append(ani_cache_id)
        
        await rep.report(f"📥 Starting download: {anime}", "info")
        
        # Download the anime
        file_path = await download_anime(anime, link)
        if not file_path:
            await rep.report(f"❌ Download failed: {anime}", "error")
            return
        
        # Extract episode info
        episode_info = extract_episode_info(anime)
        
        # Check for dedicated channel
        channel_details = await db.find_channel_by_anime_title(anime)
        
        if channel_details:
            # Post to dedicated channel
            await post_to_dedicated_channel(file_path, anime, episode_info, channel_details)
            
            # Post summary to main channel with join button
            await post_main_channel_summary(anime, episode_info, channel_details)
        else:
            # Post to main channel (existing behavior)
            await post_to_main_channel(file_path, anime, episode_info)
        
        # Cleanup
        try:
            os.remove(file_path)
        except:
            pass
            
        await rep.report(f"✅ Completed: {anime}", "info")
        
    except Exception as e:
        await rep.report(f"❌ Error processing {anime}: {str(e)}", "error")
    finally:
        # Remove from cache when done
        if ani_cache_id in ani_cache.get('animes', []):
            ani_cache['animes'].remove(ani_cache_id)

async def post_to_dedicated_channel(file_path, anime, episode_info, channel_details):
    """Post anime to dedicated channel"""
    try:
        channel_id = channel_details['channel_id']
        
        # Create caption for dedicated channel
        caption = f"<b>{anime}</b>\n\n"
        caption += f"<b>Season:</b> {episode_info['season']}\n"
        caption += f"<b>Episode:</b> {episode_info['episode']}\n"
        caption += f"<b>Quality:</b> {episode_info['quality']}\n\n"
        caption += f"<b>Size:</b> {get_file_size(file_path)}\n"
        caption += f"<b>Codec:</b> {episode_info.get('codec', 'H.264')}\n\n"
        caption += f"<i>🎬 Enjoy watching!</i>"
        
        # Send to dedicated channel
        with open(file_path, 'rb') as f:
            msg = await bot.send_video(
                chat_id=channel_id,
                video=f,
                caption=caption,
                progress=progress_bar,
                progress_args=(f"📤 Uploading to {channel_details.get('channel_title', 'Channel')}...",)
            )
        
        await rep.report(f"✅ Posted to dedicated channel: {anime}", "info")
        
    except Exception as e:
        await rep.report(f"❌ Failed to post to dedicated channel: {str(e)}", "error")

async def post_main_channel_summary(anime, episode_info, channel_details):
    """Post summary to main channel with join button"""
    try:
        # Create summary caption with specific formatting
        caption = f"<b>{anime}</b>\n"
        caption += f"<b>──────────────────────────────</b>\n"
        caption += f"<b>➤ Season - {episode_info['season']:02d}</b>\n"
        caption += f"<b>➤ Episode - {episode_info['episode']:02d}</b>\n"
        caption += f"<b>➤ Quality: {episode_info['quality']}</b>\n"
        caption += f"<b>────────────────────────────</b>"
        
        # Create join button
        keyboard = None
        if channel_details.get('invite_link'):
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("ᴊᴏɪɴ ɴᴏᴡ ᴛᴏ ᴡᴀᴛᴄʜ", url=channel_details['invite_link'])]
            ])
        
        # Send summary to main channel
        await bot.send_message(
            chat_id=Var.MAIN_CHANNEL,
            text=caption,
            reply_markup=keyboard
        )
        
        await rep.report(f"✅ Posted summary to main channel: {anime}", "info")
        
    except Exception as e:
        await rep.report(f"❌ Failed to post summary to main channel: {str(e)}", "error")

async def post_to_main_channel(file_path, anime, episode_info):
    """Post anime directly to main channel (fallback)"""
    try:
        # Create full caption for main channel
        caption = f"<b>{anime}</b>\n\n"
        caption += f"<b>Season:</b> {episode_info['season']}\n"
        caption += f"<b>Episode:</b> {episode_info['episode']}\n"
        caption += f"<b>Quality:</b> {episode_info['quality']}\n\n"
        caption += f"<b>Size:</b> {get_file_size(file_path)}\n"
        caption += f"<b>Codec:</b> {episode_info.get('codec', 'H.264')}\n\n"
        caption += f"<i>🎬 No dedicated channel configured</i>"
        
        # Send to main channel
        with open(file_path, 'rb') as f:
            msg = await bot.send_video(
                chat_id=Var.MAIN_CHANNEL,
                video=f,
                caption=caption,
                progress=progress_bar,
                progress_args=("📤 Uploading to main channel...",)
            )
        
        await rep.report(f"✅ Posted to main channel: {anime}", "info")
        
    except Exception as e:
        await rep.report(f"❌ Failed to post to main channel: {str(e)}", "error")

def extract_episode_info(anime_title):
    """Extract episode, season and quality info from anime title"""
    info = {
        'season': '01',
        'episode': '01',
        'quality': 'Multi [Sub]',
        'codec': 'H.264'
    }
    
    # Extract season
    season_match = re.search(r'[Ss](\d+)', anime_title)
    if season_match:
        info['season'] = season_match.group(1).zfill(2)
    
    # Extract episode
    episode_patterns = [
        r'[Ee](\d+)',
        r'Episode[\s\-]*(\d+)',
        r'Ep[\s\-]*(\d+)',
        r'\s(\d+)\s',
        r'-\s*(\d+)\s*-'
    ]
    
    for pattern in episode_patterns:
        episode_match = re.search(pattern, anime_title)
        if episode_match:
            info['episode'] = episode_match.group(1).zfill(2)
            break
    
    # Extract quality
    if '1080p' in anime_title.upper():
        info['quality'] = '1080p [Sub]'
    elif '720p' in anime_title.upper():
        info['quality'] = '720p [Sub]'
    elif '480p' in anime_title.upper():
        info['quality'] = '480p [Sub]'
    elif 'HEVC' in anime_title.upper():
        info['quality'] = 'HEVC [Sub]'
        info['codec'] = 'H.265'
    
    return info

def get_file_size(file_path):
    """Get formatted file size"""
    try:
        size_bytes = os.path.getsize(file_path)
        if size_bytes >= 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
        elif size_bytes >= 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / 1024:.2f} KB"
    except:
        return "Unknown"

async def download_anime(anime, link):
    """Download anime from link - implement your download logic here"""
    try:
        # Placeholder for actual download implementation
        # This should be replaced with your actual download logic
        await rep.report(f"🔄 Downloading: {anime}", "info")
        
        # Your existing download implementation goes here
        # Return the path to downloaded file
        
        return f"/tmp/{anime}.mp4"  # Replace with actual file path
        
    except Exception as e:
        await rep.report(f"❌ Download error: {str(e)}", "error")
        return None
