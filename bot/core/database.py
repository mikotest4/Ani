from motor.motor_asyncio import AsyncIOMotorClient
from bot import Var

class MongoDB:
    def __init__(self, uri, database_name):
        self.__client = AsyncIOMotorClient(uri)
        self.__db = self.__client[database_name]
        self.__animes = self.__db.animes[Var.BOT_TOKEN.split(':')[0]]
        self.__users = self.__db.users[Var.BOT_TOKEN.split(':')[0]]
        self.__admins = self.__db.admins[Var.BOT_TOKEN.split(':')[0]]
        self.__settings = self.__db.settings[Var.BOT_TOKEN.split(':')[0]]
        self.__banned = self.__db.banned[Var.BOT_TOKEN.split(':')[0]]
        self.__anime_channels = self.__db.anime_channels[Var.BOT_TOKEN.split(':')[0]]
        self.__pending_connections = self.__db.pending_connections[Var.BOT_TOKEN.split(':')[0]]

    async def getAnime(self, ani_id):
        botset = await self.__animes.find_one({'_id': ani_id})
        return botset or {}

    async def saveAnime(self, ani_id, ep, qual, post_id=None):
        quals = (await self.getAnime(ani_id)).get(ep, {qual: False for qual in Var.QUALS})
        quals[qual] = True
        await self.__animes.update_one({'_id': ani_id}, {'$set': {ep: quals}}, upsert=True)
        if post_id:
            await self.__animes.update_one({'_id': ani_id}, {'$set': {"msg_id": post_id}}, upsert=True)

    async def reboot(self):
        await self.__animes.drop()

    # User management methods
    async def add_user(self, user_id):
        """Add a user to the database if not exists"""
        await self.__users.update_one(
            {'_id': user_id}, 
            {'$set': {'_id': user_id}}, 
            upsert=True
        )

    async def full_userbase(self):
        """Get all users who have interacted with the bot"""
        users = await self.__users.find({}).to_list(length=None)
        return [user['_id'] for user in users]

    async def del_user(self, user_id):
        """Delete a user from the database"""
        await self.__users.delete_one({'_id': user_id})

    # Admin management methods
    async def add_admin(self, admin_id):
        """Add an admin to the database"""
        await self.__admins.update_one(
            {'_id': admin_id}, 
            {'$set': {'_id': admin_id}}, 
            upsert=True
        )

    async def del_admin(self, admin_id):
        """Remove an admin from the database"""
        await self.__admins.delete_one({'_id': admin_id})

    async def get_all_admins(self):
        """Get all admin IDs"""
        admins = await self.__admins.find({}).to_list(length=None)
        return [admin['_id'] for admin in admins]

    async def is_admin(self, user_id):
        """Check if user is admin"""
        admin = await self.__admins.find_one({'_id': user_id})
        return admin is not None

    # Delete timer management methods
    async def set_del_timer(self, duration):
        """Set delete timer duration in database"""
        await self.__settings.update_one(
            {'_id': 'delete_timer'}, 
            {'$set': {'duration': duration}}, 
            upsert=True
        )

    async def get_del_timer(self):
        """Get current delete timer duration"""
        setting = await self.__settings.find_one({'_id': 'delete_timer'})
        if setting:
            return setting['duration']
        else:
            # Return default value if not set
            return Var.DEL_TIMER

    # Ban system methods
    async def add_ban_user(self, user_id):
        """Add a user to the ban list"""
        await self.__banned.update_one(
            {'_id': user_id}, 
            {'$set': {'_id': user_id}}, 
            upsert=True
        )

    async def del_ban_user(self, user_id):
        """Remove a user from the ban list"""
        await self.__banned.delete_one({'_id': user_id})

    async def get_ban_users(self):
        """Get all banned user IDs"""
        banned_users = await self.__banned.find({}).to_list(length=None)
        return [user['_id'] for user in banned_users]

    async def is_banned(self, user_id):
        """Check if user is banned"""
        banned_user = await self.__banned.find_one({'_id': user_id})
        return banned_user is not None

    # Enhanced Anime Channel Mapping Methods
    async def add_anime_channel(self, anime_name, channel_id, channel_title=None, invite_link=None):
        """Add anime to channel mapping with invite link"""
        await self.__anime_channels.update_one(
            {'_id': anime_name.lower()}, 
            {'$set': {
                '_id': anime_name.lower(),
                'anime_name': anime_name,
                'channel_id': channel_id,
                'channel_title': channel_title,
                'invite_link': invite_link,
                'created_at': await self._get_current_time()
            }}, 
            upsert=True
        )

    async def get_anime_channel(self, anime_name):
        """Get channel ID for specific anime"""
        mapping = await self.__anime_channels.find_one({'_id': anime_name.lower()})
        return mapping['channel_id'] if mapping else None

    async def get_anime_channel_details(self, anime_name):
        """Get complete channel details for specific anime"""
        mapping = await self.__anime_channels.find_one({'_id': anime_name.lower()})
        return mapping if mapping else None

    async def find_channel_by_anime_title(self, title):
        """Smart matching to find channel details by anime title"""
        title_lower = title.lower()
        
        # Direct match
        mapping = await self.__anime_channels.find_one({'_id': title_lower})
        if mapping:
            return mapping
        
        # Partial match - check if any stored anime name is contained in the title
        all_mappings = await self.__anime_channels.find({}).to_list(length=None)
        for mapping in all_mappings:
            stored_name = mapping['anime_name'].lower()
            # Check if stored name is in the title or title is in stored name
            if stored_name in title_lower or title_lower in stored_name:
                return mapping
        
        return None

    async def remove_anime_channel(self, anime_name):
        """Remove anime channel mapping"""
        result = await self.__anime_channels.delete_one({'_id': anime_name.lower()})
        return result.deleted_count > 0

    async def get_all_anime_channels(self):
        """Get all anime channel mappings"""
        mappings = await self.__anime_channels.find({}).to_list(length=None)
        return mappings

    # Pending Connection Methods
    async def add_pending_connection(self, user_id, anime_name):
        """Add pending connection waiting for forwarded message"""
        await self.__pending_connections.update_one(
            {'_id': user_id}, 
            {'$set': {
                '_id': user_id,
                'anime_name': anime_name,
                'created_at': await self._get_current_time()
            }}, 
            upsert=True
        )

    async def get_pending_connection(self, user_id):
        """Get pending connection for user"""
        pending = await self.__pending_connections.find_one({'_id': user_id})
        return pending['anime_name'] if pending else None

    async def remove_pending_connection(self, user_id):
        """Remove pending connection"""
        await self.__pending_connections.delete_one({'_id': user_id})

    async def _get_current_time(self):
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now()

db = MongoDB(Var.MONGO_URI, "FZAutoAnimes")
