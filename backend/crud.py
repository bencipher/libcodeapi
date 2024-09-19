import logging
from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import PyMongoError

from exceptions.exceptions import (
    BookNotFoundError,
    UserNotFoundError,
    DatabaseError,
    BookNotAvailableError,
)
from .schemas import BookCreate, BookUpdate, UserCreate
from .models import BookModel, UserModel

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_book(db, book: BookCreate):
    try:
        result = await db.books.insert_one(book.model_dump())
        if result.inserted_id:
            new_book = {**book.model_dump(), "id": str(result.inserted_id)}
            logger.info(f"Book created successfully: {new_book['title']}")
            return new_book
        logger.error("Failed to create book in database")
        return None
    except PyMongoError as e:
        logger.error(f"Database error when creating book: {str(e)}")
        raise DatabaseError("Create book", str(e))

async def get_book(db, book_id: str):
    try:
        book = await db.books.find_one({"_id": ObjectId(book_id)})
        if book:
            logger.info(f"Book retrieved: {book_id}")
            return BookModel(**book)
        logger.info(f"Book not found: {book_id}")
        return None
    except InvalidId:
        logger.error(f"Invalid ObjectId format for book_id: {book_id}")
        raise ValueError(f"Invalid book ID format: {book_id}")
    except PyMongoError as e:
        logger.error(f"Database error when fetching book {book_id}: {str(e)}")
        raise

async def update_book(db, book_id: str, book_update: BookUpdate):
    try:
        update_data = book_update.model_dump(exclude_unset=True)
        result = await db.books.update_one(
            {"_id": ObjectId(book_id)}, {"$set": update_data}
        )
        if result.modified_count == 0:
            logger.info(f"Book not found or no changes made: {book_id}")
            return None
        updated_book = await db.books.find_one({"_id": ObjectId(book_id)})
        logger.info(f"Book updated successfully: {book_id}")
        return BookModel(**updated_book)
    except InvalidId:
        logger.error(f"Invalid ObjectId format for book_id: {book_id}")
        raise ValueError(f"Invalid book ID format: {book_id}")
    except PyMongoError as e:
        logger.error(f"Database error when updating book {book_id}: {str(e)}")
        raise

async def delete_book(db, book_id: str):
    try:
        result = await db.books.delete_one({"_id": ObjectId(book_id)})
        if result.deleted_count > 0:
            logger.info(f"Book deleted successfully: {book_id}")
            return True
        logger.info(f"Book not found for deletion: {book_id}")
        return False
    except InvalidId:
        logger.error(f"Invalid ObjectId format for book_id: {book_id}")
        raise ValueError(f"Invalid book ID format: {book_id}")
    except PyMongoError as e:
        logger.error(f"Database error when deleting book {book_id}: {str(e)}")
        raise

async def get_unavailable_books(db):
    try:
        cursor = db.books.find({"available_copies": 0})
        books = [BookModel(**book) async for book in cursor]
        logger.info(f"Retrieved {len(books)} unavailable books")
        return books
    except PyMongoError as e:
        logger.error(f"Database error when fetching unavailable books: {str(e)}")
        raise

async def create_user(db, user: UserCreate):
    try:
        result = await db.users.insert_one(user.dict())
        if result.inserted_id:
            logger.info(f"User created successfully: {user.email}")
            return str(result.inserted_id)
        logger.error("Failed to create user in database")
        return None
    except PyMongoError as e:
        logger.error(f"Database error when creating user: {str(e)}")
        raise


async def get_all_users(db):
    try:
        cursor = db.users.find()
        users = [UserModel(**user) async for user in cursor]
        logger.info(f"Retrieved {len(users)} users")
        return users
    except PyMongoError as e:
        logger.error(f"Database error when fetching all users: {str(e)}")
        raise


async def get_user_borrowing_activities(db):
    try:
        cursor = db.users.find({"borrowed_books": {"$ne": []}})
        users = [UserModel(**user) async for user in cursor]
        logger.info(f"Retrieved {len(users)} users with borrowing activities")
        return users
    except PyMongoError as e:
        logger.error(
            f"Database error when fetching users with borrowing activities: {str(e)}"
        )
        raise
