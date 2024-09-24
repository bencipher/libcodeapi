import os
import sys
import logging
from fastapi import Depends, FastAPI, HTTPException, status
import aio_pika

sys.path.append("../src")
from rabbmq import (
    create_or_get_queue,
    fetch_queue_response,
    handle_message,
    post_message,
)
from exceptions.exceptions import add_exception_handlers
from .storage import get_database, init_db, close_db_connection
from .crud import (
    create_book,
    get_book,
    update_book,
    delete_book,
)
from .schemas import BookCreate, BookUpdate, UserCreate
from .models import BookModel, UserModel
from contextlib import asynccontextmanager


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Database setup
    logger.info("Initializing database connection")
    await init_db()
    app.state.db = get_database()

    # RabbitMQ setup
    logger.info("Initializing RabbitMQ connection")
    try:
        app.state.rabbitmq_connection = await aio_pika.connect_robust(
            "amqp://guest:guest@internal_messaging:5672/"
        )
        app.state.rabbitmq_channel = await app.state.rabbitmq_connection.channel()
        logger.info("RabbitMQ connection established successfully")
    except Exception as e:
        logger.error(f"Failed to connect to RabbitMQ: {e}")
        raise

    yield

    # Cleanup
    logger.info("Closing database connection")
    await close_db_connection()
    logger.info("Closing RabbitMQ connection")
    await app.state.rabbitmq_connection.close()


app = FastAPI(
    title="Library Backend API",
    lifespan=lifespan,
    description="Backend Required Endpoints for Library App for Cowrywise",
    version="1.0.0",
)

add_exception_handlers(app)

async def get_rabbitmq_connection():
    return await aio_pika.connect_robust("amqp://guest:guest@rabbitmq/")


async def get_rabbitmq_channel():
    connection = await get_rabbitmq_connection()
    return await connection.channel()


def get_db():
    return app.state.db


# validate response later
@app.post("/books", response_model=str, status_code=status.HTTP_201_CREATED)
async def add_book(book: BookCreate, db=Depends(get_db)):
    try:
        logger.info(f"Received request to add book: {book.title}")
        new_book = await create_book(db, book)
        if not new_book:
            logger.error("Failed to create book in database")
            raise HTTPException(status_code=500, detail="Failed to create book")

        new_book.pop("total_copies", None)
        logger.info(f"Attempting to publish book to RabbitMQ: {new_book['title']}")

        send_message, book_title = await handle_message(
            current_app=app, queue_name="new_books", data=new_book
        )

        if send_message:
            logger.info(f"Successfully published book to RabbitMQ: {book_title}")
        else:
            logger.error(f"Failed to publish book to RabbitMQ: {book_title}")
            raise HTTPException(
                status_code=500, detail="Failed to publish book to queue"
            )

    except Exception as e:
        logger.error(f"Error publishing to RabbitMQ: {e}")
        await db.books.delete_one({"_id": new_book["id"]})
        raise HTTPException(
            status_code=500, detail="Book couldn't be created at the moment"
        )

    else:
        logger.info(f"Book added successfully: {new_book['id']}")
        return new_book["id"]


@app.get("/books/{book_id}", response_model=BookModel)
async def read_book(book_id: str, db=Depends(get_db)):
    book = await get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@app.put("/books/{book_id}", response_model=BookModel)
async def modify_book(book_id: str, book_update: BookUpdate, db=Depends(get_db)):
    updated_book = await update_book(db, book_id, book_update)
    if not updated_book:
        raise HTTPException(status_code=404, detail="Book not found")
    return updated_book


@app.delete("/books/{book_id}", response_model=dict)
async def remove_book(book_id: str, db=Depends(get_db)):
    book = await get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Delete the book from the backend
    success = await delete_book(db, book_id)
    if not success:
        raise HTTPException(
            status_code=500, detail="Failed to delete book from backend"
        )

    # Send ISBN to frontend for deletion
    await post_message(
        current_app=app, data=book.isbn, delivery_route="delete_books_frontend"
    )

    logger.info(
        f"Delete message Instruction for book ID: {book_id} ISBN: {book.isbn} sent!"
    )

    return {
        "message": "Book successfully deleted from backend and delete message sent to frontend"
    }


@app.get("/users", response_model=list[UserModel])
async def list_users():
    try:
        response_queue = await create_or_get_queue(app)

        await post_message(
            app,
            {"action": "get_users"},
            delivery_route="user_data_request",
            reply_to=response_queue.name,
        )

        user_data = await fetch_queue_response(response_queue)
        return [UserModel(**user) for user in user_data]

    except Exception as e:
        logger.error(f"Error fetching user data: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching user data: Please contact admin"
        )


@app.get("/users/borrowed-books/")
async def list_users_with_borrowed_books(skip: int = 0, limit: int = 100):
    try:

        response_queue = await create_or_get_queue(
            app, queue_name="users_borrowed_books_response", delete=True
        )

        await post_message(
            app,
            {"action": "get_users_with_borrowed_books", "skip": skip, "limit": limit},
            delivery_route="user_data_request",
            reply_to=response_queue.name,
        )

        response_data = await fetch_queue_response(response_queue)
        return response_data

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/unavailable-books")
async def root(skip: int = 0, limit: int = 100):
    try:

        response_queue = await create_or_get_queue(
            app, queue_name="unavailable_books_response", delete=True
        )

        await post_message(
            app,
            {"action": "get_unavailable_books", "skip": skip, "limit": limit},
            delivery_route="book_data_request",
            reply_to=response_queue.name,
        )

        response_data = await fetch_queue_response(response_queue)
        return response_data

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
