from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import re
from bot.core.reporter import rep

class Database:
    def __init__(self):
        self.client = None
        self.db = None

    async def connect(self):
        """Connect to MongoDB"""
        try:
            from bot import Var
            self.client = AsyncIOMotorClient(Var.MONGO_URI)
            self.db = self.client.anime_bot
            await rep.report("MongoDB connected successfully", "info")
            return True
        except Exception as e:
            await rep.report(f"MongoDB connection error: {str(e)}", "error")
            return False

    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()

    # USER MANAGEMENT
    async def add_user(self, user_id, username=None, first_name=None, last_name=None):
        """Add or update user"""
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            user_data = {
                "user_id": user_id,
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "date_joined": current_time,
                "is_banned": False
            }
            await self.db.users.update_one(
                {"user_id": user_id},
                {"$set": user_data},
                upsert=True
            )
        except Exception as e:
            await rep.report(f"Error adding user: {str(e)}", "error")

    async def is_banned(self, user_id):
        """Check if user is banned"""
        try:
            user = await self.db.users.find_one({"user_id": user_id})
            return user.get("is_banned", False) if user else False
        except Exception as e:
            await rep.report(f"Error checking ban status: {str(e)}", "error")
            return False

    async def add_ban_user(self, user_id):
        """Ban user"""
        try:
            await self.db.users.update_one(
                {"user_id": user_id},
                {"$set": {"is_banned": True}},
                upsert=True
            )
            return True
        except Exception as e:
            await rep.report(f"Error banning user: {str(e)}", "error")
            return False

    async def del_ban_user(self, user_id):
        """Unban user"""
        try:
            await self.db.users.update_one(
                {"user_id": user_id},
                {"$set": {"is_banned": False}}
            )
            return True
        except Exception as e:
            await rep.report(f"Error unbanning user: {str(e)}", "error")
            return False

    async def get_ban_users(self):
        """Get all banned users"""
        try:
            cursor = self.db.users.find({"is_banned": True})
            banned_users = []
            async for user in cursor:
                banned_users.append(user["user_id"])
            return banned_users
        except Exception as e:
            await rep.report(f"Error getting banned users: {str(e)}", "error")
            return []

    async def full_userbase(self):
        """Get all users"""
        try:
            cursor = self.db.users.find({})
            users = []
            async for user in cursor:
                users.append(user["user_id"])
            return users
        except Exception as e:
            await rep.report(f"Error getting userbase: {str(e)}", "error")
            return []

    # ADMIN MANAGEMENT
    async def add_admin(self, user_id):
        """Add admin"""
        try:
            await self.db.admins.update_one(
                {"user_id": user_id},
                {"$set": {"user_id": user_id, "date_added": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}},
                upsert=True
            )
            return True
        except Exception as e:
            await rep.report(f"Error adding admin: {str(e)}", "error")
            return False

    async def del_admin(self, user_id):
        """Remove admin"""
        try:
            result = await self.db.admins.delete_one({"user_id": user_id})
            return result.deleted_count > 0
        except Exception as e:
            await rep.report(f"Error removing admin: {str(e)}", "error")
            return False

    async def get_all_admins(self):
        """Get all admins"""
        try:
            cursor = self.db.admins.find({})
            admins = []
            async for admin in cursor:
                admins.append(admin["user_id"])
            return admins
        except Exception as e:
            await rep.report(f"Error getting admins: {str(e)}", "error")
            return []

    async def is_admin(self, user_id):
        """Check if user is admin"""
        try:
            admin = await self.db.admins.find_one({"user_id": user_id})
            return admin is not None
        except Exception as e:
            await rep.report(f"Error checking admin status: {str(e)}", "error")
            return False

    # ANIME DATA MANAGEMENT
    async def saveAnime(self, anime_id, episode_number, quality, post_id):
        """Save anime episode data"""
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            anime_data = {
                "anime_id": anime_id,
                "episode_number": episode_number,
                "quality": quality,
                "post_id": post_id,
                "date_added": current_time
            }
            await self.db.anime_data.update_one(
                {"anime_id": anime_id, "episode_number": episode_number, "quality": quality},
                {"$set": anime_data},
                upsert=True
            )
        except Exception as e:
            await rep.report(f"Error saving anime: {str(e)}", "error")

    async def getAnime(self, anime_id):
        """Get anime data"""
        try:
            cursor = self.db.anime_data.find({"anime_id": anime_id})
            anime_data = {}
            async for record in cursor:
                episode = record["episode_number"]
                quality = record["quality"]
                post_id = record["post_id"]
                
                if episode not in anime_data:
                    anime_data[episode] = {}
                anime_data[episode][quality] = post_id
            
            return anime_data if anime_data else None
        except Exception as e:
            await rep.report(f"Error getting anime: {str(e)}", "error")
            return None

    async def reboot(self):
        """Clear anime cache/data"""
        try:
            await self.db.anime_data.delete_many({})
        except Exception as e:
            await rep.report(f"Error rebooting: {str(e)}", "error")

    # CUSTOM BANNERS MANAGEMENT
    async def add_custom_banner(self, anime_name, banner_file_id):
        """Add custom banner"""
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            banner_data = {
                "anime_name": anime_name,
                "banner_file_id": banner_file_id,
                "date_added": current_time
            }
            await self.db.custom_banners.update_one(
                {"anime_name": anime_name},
                {"$set": banner_data},
                upsert=True
            )
            return True
        except Exception as e:
            await rep.report(f"Error adding custom banner: {str(e)}", "error")
            return False

    async def get_custom_banner(self, anime_name):
        """Get custom banner for anime"""
        try:
            banner = await self.db.custom_banners.find_one({"anime_name": anime_name})
            return banner["banner_file_id"] if banner else None
        except Exception as e:
            await rep.report(f"Error getting custom banner: {str(e)}", "error")
            return None

    async def get_all_custom_banners(self):
        """Get all custom banners"""
        try:
            cursor = self.db.custom_banners.find({})
            banners = []
            async for banner in cursor:
                banners.append({
                    "anime_name": banner["anime_name"],
                    "banner_file_id": banner["banner_file_id"],
                    "date_added": banner.get("date_added", "Unknown")
                })
            return banners
        except Exception as e:
            await rep.report(f"Error getting all banners: {str(e)}", "error")
            return []

    async def remove_custom_banner(self, anime_name):
        """Remove custom banner"""
        try:
            result = await self.db.custom_banners.delete_one({"anime_name": anime_name})
            return result.deleted_count > 0
        except Exception as e:
            await rep.report(f"Error removing banner: {str(e)}", "error")
            return False

    # SETTINGS MANAGEMENT
    async def set_del_timer(self, duration):
        """Set auto-delete timer"""
        try:
            await self.db.settings.update_one(
                {"key": "del_timer"},
                {"$set": {"key": "del_timer", "value": str(duration)}},
                upsert=True
            )
        except Exception as e:
            await rep.report(f"Error setting delete timer: {str(e)}", "error")

    async def get_del_timer(self):
        """Get auto-delete timer"""
        try:
            setting = await self.db.settings.find_one({"key": "del_timer"})
            return int(setting["value"]) if setting else 600  # Default 10 minutes
        except Exception as e:
            await rep.report(f"Error getting delete timer: {str(e)}", "error")
            return 600

# Create database instance
db = Database()
