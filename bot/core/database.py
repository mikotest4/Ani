from bot.core.reporter import rep
from datetime import datetime
import aiosqlite
import re

class Database:
    def __init__(self):
        self.db_path = "database.db"
        self.db = None

    async def connect(self):
        self.db = await aiosqlite.connect(self.db_path)
        await self.create_tables()

    async def execute(self, query, params=None):
        if params:
            return await self.db.execute(query, params)
        else:
            return await self.db.execute(query)

    async def commit(self):
        await self.db.commit()

    async def create_tables(self):
        # Your existing tables
        await self.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                date_joined TEXT,
                is_banned INTEGER DEFAULT 0
            )
        """)

        await self.execute("""
            CREATE TABLE IF NOT EXISTS anime_data (
                anime_id INTEGER,
                episode_number INTEGER,
                quality TEXT,
                post_id INTEGER,
                date_added TEXT,
                PRIMARY KEY (anime_id, episode_number, quality)
            )
        """)

        await self.execute("""
            CREATE TABLE IF NOT EXISTS anime_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                anime_name TEXT NOT NULL,
                channel_id INTEGER NOT NULL,
                channel_title TEXT,
                invite_link TEXT,
                date_added TEXT,
                UNIQUE(anime_name)
            )
        """)

        await self.execute("""
            CREATE TABLE IF NOT EXISTS pending_connections (
                user_id INTEGER PRIMARY KEY,
                anime_name TEXT NOT NULL,
                invite_link TEXT NOT NULL,
                timestamp TEXT
            )
        """)

        await self.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # NEW: Custom banners table
        await self.execute("""
            CREATE TABLE IF NOT EXISTS custom_banners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                anime_name TEXT NOT NULL,
                banner_file_id TEXT NOT NULL,
                date_added TEXT NOT NULL,
                UNIQUE(anime_name)
            )
        """)

        await self.commit()

    # YOUR EXISTING USER FUNCTIONS
    async def add_user(self, user_id, username=None, first_name=None, last_name=None):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await self.execute("""
            INSERT OR REPLACE INTO users 
            (user_id, username, first_name, last_name, date_joined, is_banned) 
            VALUES (?, ?, ?, ?, ?, COALESCE((SELECT is_banned FROM users WHERE user_id = ?), 0))
        """, (user_id, username, first_name, last_name, current_time, user_id))
        await self.commit()

    async def is_banned(self, user_id):
        result = await self.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
        row = await result.fetchone()
        return bool(row[0]) if row else False

    async def ban_user(self, user_id):
        await self.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
        await self.commit()
        return True

    async def unban_user(self, user_id):
        await self.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
        await self.commit()
        return True

    async def full_userbase(self):
        result = await self.execute("SELECT user_id FROM users")
        rows = await result.fetchall()
        return [row[0] for row in rows]

    async def get_banned_users(self):
        result = await self.execute("SELECT user_id, username, first_name FROM users WHERE is_banned = 1")
        rows = await result.fetchall()
        return [{"user_id": row[0], "username": row[1], "first_name": row[2]} for row in rows]

    # YOUR EXISTING ANIME FUNCTIONS
    async def saveAnime(self, anime_id, episode_number, quality, post_id):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await self.execute("""
            INSERT OR REPLACE INTO anime_data 
            (anime_id, episode_number, quality, post_id, date_added) 
            VALUES (?, ?, ?, ?, ?)
        """, (anime_id, episode_number, quality, post_id, current_time))
        await self.commit()

    async def getAnime(self, anime_id):
        result = await self.execute("""
            SELECT episode_number, quality, post_id 
            FROM anime_data 
            WHERE anime_id = ?
        """, (anime_id,))
        rows = await result.fetchall()
        
        anime_data = {}
        for row in rows:
            episode = row[0]
            quality = row[1]
            post_id = row[2]
            
            if episode not in anime_data:
                anime_data[episode] = {}
            anime_data[episode][quality] = post_id
        
        return anime_data if anime_data else None

    async def reboot(self):
        await self.execute("DELETE FROM anime_data")
        await self.commit()

    # YOUR EXISTING CHANNEL FUNCTIONS
    async def add_anime_channel(self, anime_name, channel_id, channel_title, invite_link=None):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await self.execute("""
            INSERT OR REPLACE INTO anime_channels 
            (anime_name, channel_id, channel_title, invite_link, date_added) 
            VALUES (?, ?, ?, ?, ?)
        """, (anime_name, channel_id, channel_title, invite_link, current_time))
        await self.commit()
        return True

    async def find_channel_by_anime_title(self, torrent_name):
        result = await self.execute("SELECT anime_name, channel_id, channel_title, invite_link FROM anime_channels")
        rows = await result.fetchall()
        
        if not rows:
            return None
        
        clean_torrent = self.clean_name_for_matching(torrent_name)
        
        for anime_name, channel_id, channel_title, invite_link in rows:
            clean_anime = self.clean_name_for_matching(anime_name)
            
            if clean_anime.lower() in clean_torrent.lower() or clean_torrent.lower() in clean_anime.lower():
                return {
                    'anime_name': anime_name,
                    'channel_id': channel_id,
                    'channel_title': channel_title,
                    'invite_link': invite_link
                }
        
        return None

    async def get_all_anime_channels(self):
        result = await self.execute("""
            SELECT anime_name, channel_id, channel_title, invite_link 
            FROM anime_channels 
            ORDER BY date_added DESC
        """)
        rows = await result.fetchall()
        
        mappings = []
        for row in rows:
            mappings.append({
                'anime_name': row[0],
                'channel_id': row[1],
                'channel_title': row[2],
                'invite_link': row[3]
            })
        
        return mappings

    async def remove_anime_channel(self, anime_name):
        result = await self.execute("DELETE FROM anime_channels WHERE LOWER(anime_name) = LOWER(?)", (anime_name,))
        await self.commit()
        return result.rowcount > 0

    # YOUR EXISTING PENDING CONNECTION FUNCTIONS
    async def add_pending_connection(self, user_id, anime_name, invite_link):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await self.execute("""
            INSERT OR REPLACE INTO pending_connections 
            (user_id, anime_name, invite_link, timestamp) 
            VALUES (?, ?, ?, ?)
        """, (user_id, anime_name, invite_link, current_time))
        await self.commit()

    async def get_pending_connection(self, user_id):
        result = await self.execute("""
            SELECT anime_name, invite_link FROM pending_connections WHERE user_id = ?
        """, (user_id,))
        row = await result.fetchone()
        
        if row:
            return {'anime_name': row[0], 'invite_link': row[1]}
        return None

    async def remove_pending_connection(self, user_id):
        await self.execute("DELETE FROM pending_connections WHERE user_id = ?", (user_id,))
        await self.commit()

    # YOUR EXISTING SETTINGS FUNCTIONS
    async def set_del_timer(self, timer_seconds):
        await self.execute("""
            INSERT OR REPLACE INTO settings (key, value) VALUES ('del_timer', ?)
        """, (str(timer_seconds),))
        await self.commit()
        return True

    async def get_del_timer(self):
        result = await self.execute("SELECT value FROM settings WHERE key = 'del_timer'")
        row = await result.fetchone()
        return int(row[0]) if row else 300

    # NEW: CUSTOM BANNER FUNCTIONS (ONLY THESE ARE NEW!)
    async def add_custom_banner(self, anime_name, banner_file_id):
        """Add or update custom banner for anime"""
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Check if banner already exists
            existing = await self.get_custom_banner(anime_name)
            
            if existing:
                # Update existing banner
                await self.execute("""
                    UPDATE custom_banners 
                    SET banner_file_id = ?, date_added = ? 
                    WHERE LOWER(anime_name) = LOWER(?)
                """, (banner_file_id, current_time, anime_name))
                await self.commit()
                return True
            else:
                # Insert new banner
                await self.execute("""
                    INSERT INTO custom_banners (anime_name, banner_file_id, date_added) 
                    VALUES (?, ?, ?)
                """, (anime_name, banner_file_id, current_time))
                await self.commit()
                return True
                
        except Exception as e:
            await rep.report(f"Error adding custom banner: {str(e)}", "error")
            return False

    async def get_custom_banner(self, anime_name):
        """Get custom banner file_id for anime name"""
        try:
            result = await self.execute("""
                SELECT banner_file_id FROM custom_banners 
                WHERE LOWER(anime_name) = LOWER(?)
            """, (anime_name,))
            
            row = await result.fetchone()
            return row[0] if row else None
            
        except Exception as e:
            await rep.report(f"Error getting custom banner: {str(e)}", "error")
            return None

    async def get_custom_banner_by_name(self, torrent_name):
        """Get custom banner by matching torrent name with stored anime names"""
        try:
            # Get all custom banners
            result = await self.execute("SELECT anime_name, banner_file_id FROM custom_banners")
            rows = await result.fetchall()
            
            if not rows:
                return None
            
            # Clean the torrent name for comparison
            clean_torrent = self.clean_name_for_matching(torrent_name)
            
            # Try to match with stored anime names
            for anime_name, banner_file_id in rows:
                clean_anime = self.clean_name_for_matching(anime_name)
                
                # Check for partial matches
                if clean_anime.lower() in clean_torrent.lower() or clean_torrent.lower() in clean_anime.lower():
                    await rep.report(f"✅ Custom banner match found: {anime_name} -> {torrent_name}", "info")
                    return banner_file_id
            
            return None
            
        except Exception as e:
            await rep.report(f"Error matching custom banner: {str(e)}", "error")
            return None

    async def remove_custom_banner(self, anime_name):
        """Remove custom banner for anime"""
        try:
            result = await self.execute("""
                DELETE FROM custom_banners 
                WHERE LOWER(anime_name) = LOWER(?)
            """, (anime_name,))
            await self.commit()
            
            # Check if any row was deleted
            return result.rowcount > 0
            
        except Exception as e:
            await rep.report(f"Error removing custom banner: {str(e)}", "error")
            return False

    async def get_all_custom_banners(self):
        """Get all custom banners"""
        try:
            result = await self.execute("""
                SELECT anime_name, banner_file_id, date_added 
                FROM custom_banners 
                ORDER BY date_added DESC
            """)
            rows = await result.fetchall()
            
            banners = []
            for row in rows:
                banners.append({
                    'anime_name': row[0],
                    'banner_file_id': row[1],
                    'date_added': row[2]
                })
            
            return banners
            
        except Exception as e:
            await rep.report(f"Error getting all custom banners: {str(e)}", "error")
            return []

    # YOUR EXISTING UTILITY FUNCTION (kept the same)
    def clean_name_for_matching(self, name):
        """Clean name for better matching"""
        # Remove common release group tags
        name = re.sub(r'\[.*?\]', '', name)
        name = re.sub(r'\(.*?\)', '', name)
        
        # Remove quality and format info
        name = re.sub(r'\b(1080p|720p|480p|HEVC|x264|x265|WEB-DL|BluRay|BDRip|DVDRip|DUAL|Multi|Sub|Dub|RAW|AAC|AC3|FLAC|DTS)\b', '', name, flags=re.IGNORECASE)
        
        # Remove episode/season info
        name = re.sub(r'[Ss]\d+[Ee]\d+', '', name)
        name = re.sub(r'[Ee]pisode?\s*\d+', '', name, flags=re.IGNORECASE)
        name = re.sub(r'[Ee]p?\s*\d+', '', name, flags=re.IGNORECASE)
        name = re.sub(r'Season\s*\d+', '', name, flags=re.IGNORECASE)
        
        # Clean up spaces and special characters
        name = re.sub(r'[-_\.]+', ' ', name)
        name = re.sub(r'\s+', ' ', name)
        
        return name.strip()

# Initialize database instance
db = Database()
