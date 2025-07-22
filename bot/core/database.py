from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
from bot import Var, LOGS

class MongoDB:
    def __init__(self, uri, database_name):
        self.__client = AsyncIOMotorClient(uri)
        self.__db = self.__client[database_name]
        self.__animes = self.__db.animes[Var.BOT_TOKEN.split(':')[0]]
        self.__users = self.__db.users

    # Anime related methods
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
    async def add_user(self, user_id, name=None, username=None):
        """Add a user to the database"""
        try:
            user_data = {
                '_id': user_id,
                'name': name or str(user_id),
                'username': username,
                'join_date': datetime.now(),
                'last_active': datetime.now()
            }
            await self.__users.update_one({'_id': user_id}, {'$set': user_data}, upsert=True)
            return True
        except Exception as e:
            LOGS.error(f"Error adding user {user_id}: {e}")
            return False

    async def remove_user(self, user_id):
        """Remove a user from the database"""
        try:
            await self.__users.delete_one({'_id': user_id})
            return True
        except Exception as e:
            LOGS.error(f"Error removing user {user_id}: {e}")
            return False

    async def get_all_users(self):
        """Get all user IDs"""
        try:
            users = []
            async for user in self.__users.find({}):
                users.append(user['_id'])
            return users
        except Exception as e:
            LOGS.error(f"Error getting all users: {e}")
            return []

    async def get_user_count(self):
        """Get total user count"""
        try:
            return await self.__users.count_documents({})
        except Exception as e:
            LOGS.error(f"Error getting user count: {e}")
            return 0

    async def user_exists(self, user_id):
        """Check if user exists in database"""
        try:
            user = await self.__users.find_one({'_id': user_id})
            return user is not None
        except Exception as e:
            LOGS.error(f"Error checking user {user_id}: {e}")
            return False

    async def get_user_info(self, user_id):
        """Get user information"""
        try:
            return await self.__users.find_one({'_id': user_id})
        except Exception as e:
            LOGS.error(f"Error getting user info {user_id}: {e}")
            return None

    async def update_user(self, user_id, update_data):
        """Update user data"""
        try:
            await self.__users.update_one({'_id': user_id}, {'$set': update_data})
            return True
        except Exception as e:
            LOGS.error(f"Error updating user {user_id}: {e}")
            return False

    async def update_user_activity(self, user_id):
        """Update user's last activity"""
        try:
            await self.__users.update_one(
                {'_id': user_id}, 
                {'$set': {'last_active': datetime.now()}},
                upsert=False
            )
            return True
        except Exception as e:
            LOGS.error(f"Error updating user activity {user_id}: {e}")
            return False

    async def get_active_users(self, days=30):
        """Get users active in the last N days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            users = []
            async for user in self.__users.find({'last_active': {'$gte': cutoff_date}}):
                users.append(user['_id'])
            return users
        except Exception as e:
            LOGS.error(f"Error getting active users: {e}")
            return []

db = MongoDB(Var.MONGO_URI, "FZAutoAnimes")
