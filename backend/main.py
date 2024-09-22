import os
import logging
from fastapi import Depends, FastAPI, HTTPException, status
from dotenv import load_dotenv
from backend.internal_messaging import (
    cleanup_messaging,
    publish_and_get_response,
    publish_delete_book,
    publish_new_book,
    request_book_data,
    request_user_data,
    setup_messaging,
)
from exceptions.exceptions import add_exception_handlers
from .storage import get_database, init_db, close_db_connection
from .crud import (
    create_book,
    get_book,
    delete_book,
)
from .schemas import BookCreate
from .models import UserModel
from contextlib import asynccontextmanager


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.testing = app.state.testing if hasattr(app.state, "testing") else False

    if not app.state.testing:
        await setup_messaging(app)
        await init_db()
        app.state.db = get_database()
    yield
    if not app.state.testing:
        await cleanup_messaging(app)
        await close_db_connection()


# Database setup
def get_db():
    return app.state.db


app = FastAPI(
    title="Library Backend API",
    lifespan=lifespan,
    description="Backend Required Endpoints for Library App for Cowrywise",
    version="1.0.0",
)

add_exception_handlers(app)

@app.post("/books", response_model=str, status_code=status.HTTP_201_CREATED)
async def add_book(book: BookCreate, db=Depends(get_db)):
    logger.info(f"Received request to add book: {book.title}")
    new_book = await create_book(db, book)
    if not new_book:
        logger.error("Failed to create book in database")
        raise HTTPException(status_code=500, detail="Failed to create book")

    new_book.pop("total_copies", None)
    try:
        await publish_and_get_response("new_books", new_book)
        logger.info(f"Successfully published book to RabbitMQ: {new_book['title']}")
    except Exception as e:
        logger.error(f"Error publishing to RabbitMQ: {e}")
        await db.books.delete_one({"_id": new_book["id"]})
        raise HTTPException(
            status_code=500, detail="Book couldn't be created at the moment"
        )

    logger.info(f"Book added successfully: {new_book['id']}")
    return new_book["id"]


@app.delete("/books/{book_id}", response_model=dict)
async def remove_book(book_id: str, db=Depends(get_db)):
    book = await get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    success = await delete_book(db, book_id)
    if not success:
        raise HTTPException(
            status_code=500, detail="Failed to delete book from backend"
        )

    try:
        await publish_and_get_response("delete_books_backend", book.isbn)
        logger.info(f"Delete message published for book ISBN: {book.isbn}")
    except Exception as e:
        logger.error(f"Failed to publish delete message: {e}")

    return {
        "message": "Book successfully deleted from backend and delete message sent to frontend"
    }


@app.get("/users", response_model=list[UserModel])
async def list_users():
    try:
        data = {"action": "get_users"}
        response = await publish_and_get_response("user_data_request", data)
        return [UserModel(**user) for user in response]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching user data: {str(e)}"
        )

@app.get("/users/borrowed-books/")
async def list_users_with_borrowed_books(skip: int = 0, limit: int = 100):
    try:
        data = {"action": "get_users_with_borrowed_books", "skip": skip, "limit": limit}
        response = await publish_and_get_response("user_data_request", data)
        return response
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/unavailable-books")
async def root(skip: int = 0, limit: int = 100):
    try:
        data = {"action": "get_unavailable_books", "skip": skip, "limit": limit}
        response = await publish_and_get_response("book_data_request", data)
        return response
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
