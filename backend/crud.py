import bson

from exceptions.exceptions import DatabaseError
from .schemas import BookCreate, BookUpdate, UserCreate
from .models import BookModel, UserModel
from .storage import get_database
from bson import ObjectId


async def create_book(db, book: BookCreate):
    result = await db.books.insert_one(book.model_dump())
    if result.inserted_id:
        return {**book.model_dump(), "id": str(result.inserted_id)}
    return None


async def get_book(db, book_id: str):
    try:
        book = await db.books.find_one({"_id": ObjectId(book_id)})
        if book:
            return BookModel(**book)
        return None
    except bson.errors.InvalidId as e:
        raise DatabaseError("Get Book Error: ", str(e))


async def update_book(db, book_id: str, book_update: BookUpdate):
    update_data = book_update.model_dump(exclude_unset=True)
    result = await db.books.update_one(
        {"_id": ObjectId(db, book_id)}, {"$set": update_data}
    )
    if result.modified_count == 0:
        return None
    updated_book = await db.books.find_one({"_id": ObjectId(book_id)})
    return BookModel(**updated_book)


async def delete_book(db, book_id: str):
    result = await db.books.delete_one({"_id": ObjectId(book_id)})
    return result.deleted_count > 0


async def get_unavailable_books(db):
    cursor = db.books.find({"available_copies": 0})
    return [BookModel(**book) async for book in cursor]


async def create_user(db, user: UserCreate):
    result = await db.users.insert_one(user.dict())
    return str(result.inserted_id)


async def get_all_users():
    db = get_database()
    cursor = db.users.find()
    return [UserModel(**user) async for user in cursor]


async def get_user_borrowing_activities():
    db = get_database()
    cursor = db.users.find({"borrowed_books": {"$ne": []}})
    return [UserModel(**user) async for user in cursor]
