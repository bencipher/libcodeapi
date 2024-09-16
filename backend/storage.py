from motor.motor_asyncio import AsyncIOMotorClient
import os

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://mongo:27017")
client: AsyncIOMotorClient = None


async def init_db():
    global client
    client = AsyncIOMotorClient(MONGODB_URL)


async def close_db_connection():
    global client
    if client:
        client.close()


def get_database():
    return client.library_db
