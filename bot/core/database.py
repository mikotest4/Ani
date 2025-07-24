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

db = MongoDB(Var.MONGO_URI, "FZAutoAnimes")
