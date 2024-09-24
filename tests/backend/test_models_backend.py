import pytest
from backend.crud import create_book, get_book
from backend.schemas import BookCreate
from motor.motor_asyncio import AsyncIOMotorClient


@pytest.mark.skip()
@pytest.mark.asyncio
async def test_using_motor_client(motor_client: AsyncIOMotorClient) -> None:
    """This test has access to a Motor client."""
    await motor_client.server_info()


@pytest.mark.skip()
@pytest.mark.asyncio
async def test_add_book(test_db):
    book_data = {
        "title": "Test Book",
        "author": "Test Author",
        "isbn": "1234567890",
        "publisher": "Test Publisher",
        "category": "Test Category",
        "description": "Test Description",
        "total_copies": 5,
    }
    book = BookCreate(**book_data)
    result = await create_book(test_db, book)
    assert result is not None
    assert isinstance(result, str)  # Check if the returned value is a string (ObjectId)

    # Verify the book was added to the collection
    added_book = await test_db.books.find_one({"_id": result})
    assert added_book is not None
    assert added_book["title"] == book_data["title"]


@pytest.mark.skip()
@pytest.mark.asyncio
async def test_get_book_by_id(test_db):
    # First, add a book
    book_data = {
        "title": "Test Book",
        "author": "Test Author",
        "isbn": "1234567890",
        "publisher": "Test Publisher",
        "category": "Test Category",
        "description": "Test Description",
        "total_copies": 5,
    }
    book = BookCreate(**book_data)
    book_id = await create_book(test_db, book)

    # Now, test getting the book by ID
    retrieved_book = await get_book(test_db, book_id)
    assert retrieved_book is not None
    assert retrieved_book["title"] == book_data["title"]
    assert str(retrieved_book["_id"]) == book_id
