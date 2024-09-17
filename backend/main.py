import json
import logging
from fastapi import Depends, FastAPI, HTTPException, status
import aio_pika
from .storage import get_database, init_db, close_db_connection
from .crud import (
    create_book,
    get_book,
    update_book,
    delete_book,
    get_unavailable_books,
    create_user,
    get_all_users,
    get_user_borrowing_activities,
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
    logger.info(f"Received request to add book: {book.title}")
    new_book = await create_book(db, book)
    if not new_book:
        logger.error("Failed to create book in database")
        raise HTTPException(status_code=500, detail="Failed to create book")

    new_book.pop("total_copies", None)
    try:
        logger.info(f"Attempting to publish book to RabbitMQ: {new_book['title']}")

        # Declare a durable queue
        queue = await app.state.rabbitmq_channel.declare_queue(
            "new_books", durable=True
        )

        # Enable publisher confirms
        await app.state.rabbitmq_channel.set_qos(prefetch_count=1)

        # Publish the message with mandatory flag and wait for confirmation
        confirmation = await app.state.rabbitmq_channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(new_book).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key="new_books",
            mandatory=True,
        )

        if confirmation:
            logger.info(f"Successfully published book to RabbitMQ: {new_book['title']}")
        else:
            logger.error(f"Failed to publish book to RabbitMQ: {new_book['title']}")
            raise HTTPException(
                status_code=500, detail="Failed to publish book to queue"
            )

    except Exception as e:
        logger.error(f"Error publishing to RabbitMQ: {e}")
        await db.books.delete_one({"_id": new_book["id"]})
        raise HTTPException(
            status_code=500, detail="Book couldn't be created at the moment"
        )

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
    # First, fetch the book to get its ISBN
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
    try:
        await app.state.rabbitmq_channel.default_exchange.publish(
            aio_pika.Message(body=book.isbn.encode()),
            routing_key="delete_books_frontend",
        )
        logger.info(f"Delete message published for book ISBN: {book.isbn}")
    except Exception as e:
        logger.error(f"Failed to publish delete message: {e}")
        # Note: We're not raising an exception here as the book is already deleted from the backend

    return {
        "message": "Book successfully deleted from backend and delete message sent to frontend"
    }


@app.get("/books/unavailable", response_model=list[BookModel])
async def list_unavailable_books(db=Depends(get_db)):
    return await get_unavailable_books()


@app.get("/users", response_model=list[UserModel])
async def list_users(db=Depends(get_db)):
    return await get_all_users(db)


@app.get("/users/borrowing", response_model=list[UserModel])
async def list_user_borrowing_activities(db=Depends(get_db)):
    return await get_user_borrowing_activities(db)


@app.get("/")
async def root(db=Depends(get_db)):
    db()
    return {"message": "Welcome to the Library Backend API"}


@app.get("/test")
async def root(db=Depends(get_db)):
    await db.some_collection.insert_one({"test": "data"})
    return {"message": "Data inserted into the database"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
