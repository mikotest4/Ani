from pyrogram.filters import command, private, reply
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot import bot, admin
from bot.core.database import db
from bot.core.func_utils import sendMessage, new_task

@bot.on_message(command('setbanner') & private & admin & reply)
@new_task
async def set_custom_banner(client, message):
    """Set custom banner for anime"""
    # Get anime name from command
    text = message.text.strip()
    anime_name = text.replace('/setbanner', '').strip()
    
    if not anime_name:
        return await sendMessage(message, 
            "<b>❌ Invalid Usage!</b>\n\n"
            "<b>📌 Usage:</b>\n"
            "<code>/setbanner [anime_name]</code>\n"
            "<i>(Reply to a photo)</i>\n\n"
            "<b>Example:</b>\n"
            "<code>/setbanner Rascal Does Not Dream of Bunny Girl Senpai</code>"
        )
    
    # Check if replying to photo
    replied_msg = message.reply_to_message
    if not replied_msg or not replied_msg.photo:
        return await sendMessage(message,
            "<b>❌ Please reply to a photo!</b>\n\n"
            "<b>📌 Usage:</b>\n"
            "<code>/setbanner [anime_name]</code>\n"
            "<i>(Reply to a photo)</i>"
        )
    
    try:
        # Get photo file_id
        photo_file_id = replied_msg.photo.file_id
        
        # Save to database
        await db.add_custom_banner(anime_name, photo_file_id)
        
        # Send confirmation with preview
        await sendMessage(message,
            f"✅ <b>Custom Banner Set Successfully!</b>\n\n"
            f"📺 <b>Anime:</b> {anime_name}\n"
            f"🖼️ <b>Banner ID:</b> <code>{photo_file_id}</code>\n\n"
            f"ℹ️ <b>This banner will be used for all future posts of this anime!</b>"
        )
        
        # Send preview of the banner
        await client.send_photo(
            message.chat.id,
            photo=photo_file_id,
            caption=f"🖼️ <b>Banner Preview for:</b>\n<code>{anime_name}</code>"
        )
        
    except Exception as e:
        await sendMessage(message,
            f"❌ <b>Error setting banner:</b>\n"
            f"<code>{str(e)}</code>"
        )

@bot.on_message(command('removebanner') & private & admin)
@new_task
async def remove_custom_banner(client, message):
    """Remove custom banner for anime"""
    # Get anime name from command
    text = message.text.strip()
    anime_name = text.replace('/removebanner', '').strip()
    
    if not anime_name:
        return await sendMessage(message,
            "<b>❌ Invalid Usage!</b>\n\n"
            "<b>📌 Usage:</b>\n"
            "<code>/removebanner [anime_name]</code>\n\n"
            "<b>Example:</b>\n"
            "<code>/removebanner Rascal Does Not Dream of Bunny Girl Senpai</code>"
        )
    
    try:
        # Remove from database
        success = await db.remove_custom_banner(anime_name)
        
        if success:
            await sendMessage(message,
                f"✅ <b>Custom Banner Removed!</b>\n\n"
                f"📺 <b>Anime:</b> {anime_name}\n\n"
                f"ℹ️ <b>Future posts will use AniList default banner.</b>"
            )
        else:
            await sendMessage(message,
                f"❌ <b>No custom banner found for:</b>\n"
                f"<code>{anime_name}</code>\n\n"
                f"<b>Use:</b> <code>/listbanners</code> to see all custom banners."
            )
            
    except Exception as e:
        await sendMessage(message,
            f"❌ <b>Error removing banner:</b>\n"
            f"<code>{str(e)}</code>"
        )

@bot.on_message(command('listbanners') & private & admin)
@new_task
async def list_custom_banners(client, message):
    """List all custom banners"""
    try:
        banners = await db.get_all_custom_banners()
        
        if not banners:
            return await sendMessage(message,
                "<b>📋 No custom banners set yet.</b>\n\n"
                "<b>Use:</b> <code>/setbanner [anime_name]</code> to add custom banners."
            )
        
        result = "<b>🎨 Custom Anime Banners:</b>\n\n"
        for banner in banners:
            result += f"🎬 <b>{banner['anime_name']}</b>\n"
            result += f"├ <b>Banner ID:</b> <code>{banner['banner_file_id']}</code>\n"
            result += f"└ <b>Added:</b> {banner.get('date_added', 'Unknown')}\n\n"
        
        await sendMessage(message, result)
        
    except Exception as e:
        await sendMessage(message,
            f"❌ <b>Error fetching banners:</b>\n"
            f"<code>{str(e)}</code>"
        )

@bot.on_message(command('viewbanner') & private & admin)
@new_task
async def view_custom_banner(client, message):
    """View specific anime banner"""
    # Get anime name from command
    text = message.text.strip()
    anime_name = text.replace('/viewbanner', '').strip()
    
    if not anime_name:
        return await sendMessage(message,
            "<b>❌ Invalid Usage!</b>\n\n"
            "<b>📌 Usage:</b>\n"
            "<code>/viewbanner [anime_name]</code>\n\n"
            "<b>Example:</b>\n"
            "<code>/viewbanner Rascal Does Not Dream of Bunny Girl Senpai</code>"
        )
    
    try:
        # Get banner from database
        banner_file_id = await db.get_custom_banner(anime_name)
        
        if banner_file_id:
            # Send the banner
            await client.send_photo(
                message.chat.id,
                photo=banner_file_id,
                caption=f"🎨 <b>Custom Banner for:</b>\n<code>{anime_name}</code>\n\n"
                       f"🆔 <b>File ID:</b> <code>{banner_file_id}</code>"
            )
        else:
            await sendMessage(message,
                f"❌ <b>No custom banner found for:</b>\n"
                f"<code>{anime_name}</code>\n\n"
                f"<b>Available Commands:</b>\n"
                f"• <code>/setbanner {anime_name}</code> - Set banner\n"
                f"• <code>/listbanners</code> - View all banners"
            )
            
    except Exception as e:
        await sendMessage(message,
            f"❌ <b>Error viewing banner:</b>\n"
            f"<code>{str(e)}</code>"
        )

@bot.on_message(command('updatebanner') & private & admin & reply)
@new_task
async def update_custom_banner(client, message):
    """Update existing custom banner"""
    # Get anime name from command
    text = message.text.strip()
    anime_name = text.replace('/updatebanner', '').strip()
    
    if not anime_name:
        return await sendMessage(message,
            "<b>❌ Invalid Usage!</b>\n\n"
            "<b>📌 Usage:</b>\n"
            "<code>/updatebanner [anime_name]</code>\n"
            "<i>(Reply to a photo)</i>\n\n"
            "<b>Example:</b>\n"
            "<code>/updatebanner Rascal Does Not Dream of Bunny Girl Senpai</code>"
        )
    
    # Check if replying to photo
    replied_msg = message.reply_to_message
    if not replied_msg or not replied_msg.photo:
        return await sendMessage(message,
            "<b>❌ Please reply to a photo!</b>\n\n"
            "<b>📌 Usage:</b>\n"
            "<code>/updatebanner [anime_name]</code>\n"
            "<i>(Reply to a photo)</i>"
        )
    
    try:
        # Check if banner exists
        existing_banner = await db.get_custom_banner(anime_name)
        if not existing_banner:
            return await sendMessage(message,
                f"❌ <b>No existing banner found for:</b>\n"
                f"<code>{anime_name}</code>\n\n"
                f"<b>Use:</b> <code>/setbanner {anime_name}</code> to create new banner."
            )
        
        # Get new photo file_id
        new_photo_file_id = replied_msg.photo.file_id
        
        # Update in database
        await db.add_custom_banner(anime_name, new_photo_file_id)  # This overwrites existing
        
        # Send confirmation
        await sendMessage(message,
            f"✅ <b>Banner Updated Successfully!</b>\n\n"
            f"📺 <b>Anime:</b> {anime_name}\n"
            f"🔄 <b>Old Banner:</b> <code>{existing_banner}</code>\n"
            f"🆕 <b>New Banner:</b> <code>{new_photo_file_id}</code>\n\n"
            f"ℹ️ <b>Updated banner will be used for future posts!</b>"
        )
        
        # Send preview of new banner
        await client.send_photo(
            message.chat.id,
            photo=new_photo_file_id,
            caption=f"🔄 <b>Updated Banner Preview for:</b>\n<code>{anime_name}</code>"
        )
        
    except Exception as e:
        await sendMessage(message,
            f"❌ <b>Error updating banner:</b>\n"
            f"<code>{str(e)}</code>"
        )

# CUSTOM FILENAME COMMANDS
@bot.on_message(command('setfilename') & private & admin)
@new_task
async def set_custom_filename(client, message):
    """Set custom filename format for anime"""
    # Parse command: /setfilename [anime_name] [filename_format]
    text = message.text.strip()
    parts = text.replace('/setfilename', '').strip()
    
    if not parts:
        return await sendMessage(message,
            "<b>❌ Invalid Usage!</b>\n\n"
            "<b>📌 Usage:</b>\n"
            "<code>/setfilename [anime_name] [filename_format]</code>\n\n"
            "<b>Available Variables:</b>\n"
            "<code>{season}</code> - Season number\n"
            "<code>{episode}</code> - Episode number\n"
            "<code>{title}</code> - Clean anime title\n"
            "<code>{quality}</code> - Video quality\n"
            "<code>{codec}</code> - Video codec\n"
            "<code>{lang}</code> - Audio language\n\n"
            "<b>Example:</b>\n"
            "<code>/setfilename Bunny Girl Senpai [BGS-S{season}E{episode}] {title} [{quality}p] @MyChannel.mkv</code>"
        )
    
    # Split into anime name and filename format
    # Find the last occurrence of ] or } to split properly
    split_point = -1
    bracket_count = 0
    for i, char in enumerate(parts):
        if char in '[{':
            bracket_count += 1
        elif char in ']}':
            bracket_count -= 1
            if bracket_count == 0:
                split_point = i + 1
    
    if split_point == -1:
        # No brackets found, split by last space
        words = parts.rsplit(' ', 1)
        if len(words) < 2:
            return await sendMessage(message,
                "<b>❌ Please provide both anime name and filename format!</b>\n\n"
                "<b>Example:</b>\n"
                "<code>/setfilename Bunny Girl Senpai [BGS-S{season}E{episode}] {title} [{quality}p] @MyChannel.mkv</code>"
            )
        anime_name = words[0].strip()
        filename_format = words[1].strip()
    else:
        anime_name = parts[:split_point].strip()
        filename_format = parts[split_point:].strip()
    
    if not anime_name or not filename_format:
        return await sendMessage(message,
            "<b>❌ Please provide both anime name and filename format!</b>\n\n"
            "<b>Example:</b>\n"
            "<code>/setfilename Bunny Girl Senpai [BGS-S{season}E{episode}] {title} [{quality}p] @MyChannel.mkv</code>"
        )
    
    try:
        # Save to database
        success = await db.add_custom_filename(anime_name, filename_format)
        
        if success:
            await sendMessage(message,
                f"✅ <b>Custom Filename Set Successfully!</b>\n\n"
                f"📺 <b>Anime:</b> {anime_name}\n"
                f"📝 <b>Format:</b> <code>{filename_format}</code>\n\n"
                f"ℹ️ <b>This format will be used for all future episodes of this anime!</b>"
            )
        else:
            await sendMessage(message,
                f"❌ <b>Error setting custom filename for:</b>\n"
                f"<code>{anime_name}</code>"
            )
            
    except Exception as e:
        await sendMessage(message,
            f"❌ <b>Error setting filename:</b>\n"
            f"<code>{str(e)}</code>"
        )

@bot.on_message(command('removefilename') & private & admin)
@new_task
async def remove_custom_filename(client, message):
    """Remove custom filename format"""
    # Get anime name from command
    text = message.text.strip()
    anime_name = text.replace('/removefilename', '').strip()
    
    if not anime_name:
        return await sendMessage(message,
            "<b>❌ Invalid Usage!</b>\n\n"
            "<b>📌 Usage:</b>\n"
            "<code>/removefilename [anime_name]</code>\n\n"
            "<b>Example:</b>\n"
            "<code>/removefilename Bunny Girl Senpai</code>"
        )
    
    try:
        # Remove from database
        success = await db.remove_custom_filename(anime_name)
        
        if success:
            await sendMessage(message,
                f"✅ <b>Custom Filename Removed!</b>\n\n"
                f"📺 <b>Anime:</b> {anime_name}\n\n"
                f"ℹ️ <b>Future episodes will use default filename format.</b>"
            )
        else:
            await sendMessage(message,
                f"❌ <b>No custom filename found for:</b>\n"
                f"<code>{anime_name}</code>\n\n"
                f"<b>Use:</b> <code>/listfilenames</code> to see all custom filenames."
            )
            
    except Exception as e:
        await sendMessage(message,
            f"❌ <b>Error removing filename:</b>\n"
            f"<code>{str(e)}</code>"
        )

@bot.on_message(command('listfilenames') & private & admin)
@new_task
async def list_custom_filenames(client, message):
    """List all custom filename formats"""
    try:
        filenames = await db.get_all_custom_filenames()
        
        if not filenames:
            return await sendMessage(message,
                "<b>📋 No custom filename formats set yet.</b>\n\n"
                "<b>Use:</b> <code>/setfilename [anime_name] [format]</code> to add custom formats."
            )
        
        result = "<b>📝 Custom Filename Formats:</b>\n\n"
        for filename in filenames:
            result += f"🎬 <b>{filename['anime_name']}</b>\n"
            result += f"├ <b>Format:</b> <code>{filename['filename_format']}</code>\n"
            result += f"└ <b>Added:</b> {filename.get('date_added', 'Unknown')}\n\n"
        
        await sendMessage(message, result)
        
    except Exception as e:
        await sendMessage(message,
            f"❌ <b>Error fetching filenames:</b>\n"
            f"<code>{str(e)}</code>"
        )

# CUSTOM THUMBNAIL COMMANDS
@bot.on_message(command('setthumb') & private & admin & reply)
@new_task
async def set_custom_thumb(client, message):
    """Set custom thumbnail for anime"""
    # Get anime name from command
    text = message.text.strip()
    anime_name = text.replace('/setthumb', '').strip()
    
    if not anime_name:
        return await sendMessage(message,
            "<b>❌ Invalid Usage!</b>\n\n"
            "<b>📌 Usage:</b>\n"
            "<code>/setthumb [anime_name]</code>\n"
            "<i>(Reply to a photo)</i>\n\n"
            "<b>Example:</b>\n"
            "<code>/setthumb Bunny Girl Senpai</code>"
        )
    
    # Check if replying to photo
    replied_msg = message.reply_to_message
    if not replied_msg or not replied_msg.photo:
        return await sendMessage(message,
            "<b>❌ Please reply to a photo!</b>\n\n"
            "<b>📌 Usage:</b>\n"
            "<code>/setthumb [anime_name]</code>\n"
            "<i>(Reply to a photo)</i>"
        )
    
    try:
        # Get photo file_id
        photo_file_id = replied_msg.photo.file_id
        
        # Save to database
        success = await db.add_custom_thumb(anime_name, photo_file_id)
        
        if success:
            await sendMessage(message,
                f"✅ <b>Custom Thumbnail Set Successfully!</b>\n\n"
                f"📺 <b>Anime:</b> {anime_name}\n"
                f"🖼️ <b>Thumb ID:</b> <code>{photo_file_id}</code>\n\n"
                f"ℹ️ <b>This thumbnail will be used for all future episodes of this anime!</b>"
            )
            
            # Send preview of the thumbnail
            await client.send_photo(
                message.chat.id,
                photo=photo_file_id,
                caption=f"🖼️ <b>Thumbnail Preview for:</b>\n<code>{anime_name}</code>"
            )
        else:
            await sendMessage(message,
                f"❌ <b>Error setting custom thumbnail for:</b>\n"
                f"<code>{anime_name}</code>"
            )
        
    except Exception as e:
        await sendMessage(message,
            f"❌ <b>Error setting thumbnail:</b>\n"
            f"<code>{str(e)}</code>"
        )

@bot.on_message(command('removethumb') & private & admin)
@new_task
async def remove_custom_thumb(client, message):
    """Remove custom thumbnail"""
    # Get anime name from command
    text = message.text.strip()
    anime_name = text.replace('/removethumb', '').strip()
    
    if not anime_name:
        return await sendMessage(message,
            "<b>❌ Invalid Usage!</b>\n\n"
            "<b>📌 Usage:</b>\n"
            "<code>/removethumb [anime_name]</code>\n\n"
            "<b>Example:</b>\n"
            "<code>/removethumb Bunny Girl Senpai</code>"
        )
    
    try:
        # Remove from database
        success = await db.remove_custom_thumb(anime_name)
        
        if success:
            await sendMessage(message,
                f"✅ <b>Custom Thumbnail Removed!</b>\n\n"
                f"📺 <b>Anime:</b> {anime_name}\n\n"
                f"ℹ️ <b>Future episodes will use default thumbnail.</b>"
            )
        else:
            await sendMessage(message,
                f"❌ <b>No custom thumbnail found for:</b>\n"
                f"<code>{anime_name}</code>\n\n"
                f"<b>Use:</b> <code>/listthumbs</code> to see all custom thumbnails."
            )
            
    except Exception as e:
        await sendMessage(message,
            f"❌ <b>Error removing thumbnail:</b>\n"
            f"<code>{str(e)}</code>"
        )

@bot.on_message(command('listthumbs') & private & admin)
@new_task
async def list_custom_thumbs(client, message):
    """List all custom thumbnails"""
    try:
        thumbs = await db.get_all_custom_thumbs()
        
        if not thumbs:
            return await sendMessage(message,
                "<b>📋 No custom thumbnails set yet.</b>\n\n"
                "<b>Use:</b> <code>/setthumb [anime_name]</code> to add custom thumbnails."
            )
        
        result = "<b>🖼️ Custom Thumbnails:</b>\n\n"
        for thumb in thumbs:
            result += f"🎬 <b>{thumb['anime_name']}</b>\n"
            result += f"├ <b>Thumb ID:</b> <code>{thumb['thumb_file_id']}</code>\n"
            result += f"└ <b>Added:</b> {thumb.get('date_added', 'Unknown')}\n\n"
        
        await sendMessage(message, result)
        
    except Exception as e:
        await sendMessage(message,
            f"❌ <b>Error fetching thumbnails:</b>\n"
            f"<code>{str(e)}</code>"
        )

@bot.on_message(command('viewthumb') & private & admin)
@new_task
async def view_custom_thumb(client, message):
    """View specific anime thumbnail"""
    # Get anime name from command
    text = message.text.strip()
    anime_name = text.replace('/viewthumb', '').strip()
    
    if not anime_name:
        return await sendMessage(message,
            "<b>❌ Invalid Usage!</b>\n\n"
            "<b>📌 Usage:</b>\n"
            "<code>/viewthumb [anime_name]</code>\n\n"
            "<b>Example:</b>\n"
            "<code>/viewthumb Bunny Girl Senpai</code>"
        )
    
    try:
        # Get thumbnail from database
        thumb_file_id = await db.get_custom_thumb(anime_name)
        
        if thumb_file_id:
            # Send the thumbnail
            await client.send_photo(
                message.chat.id,
                photo=thumb_file_id,
                caption=f"🖼️ <b>Custom Thumbnail for:</b>\n<code>{anime_name}</code>\n\n"
                       f"🆔 <b>File ID:</b> <code>{thumb_file_id}</code>"
            )
        else:
            await sendMessage(message,
                f"❌ <b>No custom thumbnail found for:</b>\n"
                f"<code>{anime_name}</code>\n\n"
                f"<b>Available Commands:</b>\n"
                f"• <code>/setthumb {anime_name}</code> - Set thumbnail\n"
                f"• <code>/listthumbs</code> - View all thumbnails"
            )
            
    except Exception as e:
        await sendMessage(message,
            f"❌ <b>Error viewing thumbnail:</b>\n"
            f"<code>{str(e)}</code>"
        )

# MANAGEMENT COMMANDS
@bot.on_message(command('viewcustoms') & private & admin)
@new_task
async def view_custom_settings(client, message):
    """View all custom settings for an anime"""
    # Get anime name from command
    text = message.text.strip()
    anime_name = text.replace('/viewcustoms', '').strip()
    
    if not anime_name:
        return await sendMessage(message,
            "<b>❌ Invalid Usage!</b>\n\n"
            "<b>📌 Usage:</b>\n"
            "<code>/viewcustoms [anime_name]</code>\n\n"
            "<b>Example:</b>\n"
            "<code>/viewcustoms Bunny Girl Senpai</code>"
        )
    
    try:
        # Get all custom settings
        custom_banner = await db.get_custom_banner(anime_name)
        custom_filename = await db.get_custom_filename(anime_name)
        custom_thumb = await db.get_custom_thumb(anime_name)
        
        result = f"<b>🎬 Custom Settings for:</b>\n<code>{anime_name}</code>\n\n"
        
        if custom_banner:
            result += f"🖼️ <b>Custom Banner:</b> <code>{custom_banner}</code>\n"
        else:
            result += f"🖼️ <b>Custom Banner:</b> Not set\n"
        
        if custom_filename:
            result += f"📝 <b>Custom Filename:</b> <code>{custom_filename}</code>\n"
        else:
            result += f"📝 <b>Custom Filename:</b> Not set\n"
        
        if custom_thumb:
            result += f"🖼️ <b>Custom Thumbnail:</b> <code>{custom_thumb}</code>\n"
        else:
            result += f"🖼️ <b>Custom Thumbnail:</b> Not set\n"
        
        if not any([custom_banner, custom_filename, custom_thumb]):
            result += f"\n<b>ℹ️ No custom settings found for this anime.</b>"
        
        await sendMessage(message, result)
        
    except Exception as e:
        await sendMessage(message,
            f"❌ <b>Error viewing custom settings:</b>\n"
            f"<code>{str(e)}</code>"
        )

@bot.on_message(command('listcustoms') & private & admin)
@new_task
async def list_all_customs(client, message):
    """List all animes with custom settings"""
    try:
        banners = await db.get_all_custom_banners()
        filenames = await db.get_all_custom_filenames()
        thumbs = await db.get_all_custom_thumbs()
        
        # Combine all anime names
        all_animes = set()
        for banner in banners:
            all_animes.add(banner['anime_name'])
        for filename in filenames:
            all_animes.add(filename['anime_name'])
        for thumb in thumbs:
            all_animes.add(thumb['anime_name'])
        
        if not all_animes:
            return await sendMessage(message,
                "<b>📋 No custom settings found.</b>\n\n"
                "<b>Available Commands:</b>\n"
                "• <code>/setbanner [anime] [reply to photo]</code>\n"
                "• <code>/setfilename [anime] [format]</code>\n"
                "• <code>/setthumb [anime] [reply to photo]</code>"
            )
        
        result = "<b>🎨 Animes with Custom Settings:</b>\n\n"
        for anime_name in sorted(all_animes):
            has_banner = any(b['anime_name'] == anime_name for b in banners)
            has_filename = any(f['anime_name'] == anime_name for f in filenames)
            has_thumb = any(t['anime_name'] == anime_name for t in thumbs)
            
            result += f"🎬 <b>{anime_name}</b>\n"
            result += f"├ Banner: {'✅' if has_banner else '❌'}\n"
            result += f"├ Filename: {'✅' if has_filename else '❌'}\n"
            result += f"└ Thumbnail: {'✅' if has_thumb else '❌'}\n\n"
        
        await sendMessage(message, result)
        
    except Exception as e:
        await sendMessage(message,
            f"❌ <b>Error fetching custom settings:</b>\n"
            f"<code>{str(e)}</code>"
        )
