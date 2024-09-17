from contextlib import asynccontextmanager
import json
import logging
import aio_pika
from fastapi import FastAPI, HTTPException, Depends, status
from sqlalchemy.orm import Session

from frontend.crud import (
    borrow_book,
    create_book,
    create_user_record,
    delete_book_by_isbn,
    filter_books,
    get_book,
    get_books,
    get_users,
)
from frontend.exceptions import add_exception_handlers
from frontend.schemas import (
    BookCreate,
    BookFilterParams,
    BookSchema,
    BorrowRequestSchema,
    BorrowResponse,
    UserCreate,
    UserSchema,
)
from frontend.storage import SessionLocal

from typing import List

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("INSIDE LIFESPAN")
    logger.info("Initializing RabbitMQ connection")
    try:
        app.state.rabbitmq_connection = await aio_pika.connect_robust(
            "amqp://guest:guest@internal_messaging:5672/"
        )
        app.state.rabbitmq_channel = await app.state.rabbitmq_connection.channel()
        logger.info("RabbitMQ connection established successfully")

        # Declare durable queues
        new_books_queue = await app.state.rabbitmq_channel.declare_queue(
            "new_books", durable=True
        )
        delete_books_queue = await app.state.rabbitmq_channel.declare_queue(
            "delete_books_frontend", durable=True
        )
        await new_books_queue.consume(process_new_book)
        await delete_books_queue.consume(process_delete_book)

        user_data_queue = await app.state.rabbitmq_channel.declare_queue(
            "user_data_request"
        )
        await user_data_queue.consume(process_user_data_request)
        logger.info("Started consuming messages from queues")
    except Exception as e:
        logger.error(f"Failed to connect to RabbitMQ: {e}")
        raise

    yield

    # Cleanup
    logger.info("Closing RabbitMQ connection")
    await app.state.rabbitmq_connection.close()


app = FastAPI(
    title="Library API",
    lifespan=lifespan,
    description="Frontend Required Endpoints for Library App for Cowrywise",
    version="1.0.0",
)

add_exception_handlers(app)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def process_delete_book(message: aio_pika.IncomingMessage):
    async with message.process():
        print("Processing Delete Queue")
        logger.info(f"Received delete book message: {message.body}")
        isbn = message.body.decode()
        try:
            db = next(get_db())
            deleted = delete_book_by_isbn(db, isbn)
            if deleted:
                print(f"Deleted book with ISBN: {isbn}")
            else:
                print(f"Book with ISBN: {isbn} not found in frontend database")
        except Exception as e:
            logger.error(f"Error deleting book: {e}")
        finally:
            db.close()


async def process_new_book(message: aio_pika.IncomingMessage):
    async with message.process():
        print("Processing Queue")
        logger.info(f"Received new book message: {message.body}")
        book_data = json.loads(message.body.decode())
        try:
            db = next(get_db())
            validated_book = BookCreate(**book_data)
            synced_book = create_book(db, item=validated_book)
            print(f"Saved new book: {synced_book.title}")
        except Exception as e:
            logger.error(f"Error processing new book: {e}")
        finally:
            db.close()


async def process_user_data_request(message: aio_pika.IncomingMessage):
    async with message.process():
        if message.body.decode() == "get_users":
            db = next(get_db())
            try:
                users = get_users(db)
                user_data = [
                    UserSchema.model_validate(user).model_dump() for user in users
                ]
                if message.reply_to:
                    # Send the user data back to the backend
                    await app.state.rabbitmq_channel.default_exchange.publish(
                        aio_pika.Message(body=json.dumps(user_data).encode()),
                        routing_key=message.reply_to,
                    )
                else:
                    logger.error(
                        "No reply_to in the original message. Cannot send response."
                    )
            except Exception as e:
                logger.error(f"Error processing user data request: {str(e)}")
            finally:
                db.close()


# Endpoints
@app.post("/users/", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    try:
        db_user = create_user_record(db, user)
        return db_user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.get("/books/", response_model=List[BookSchema], status_code=status.HTTP_200_OK)
def list_books(db: Session = Depends(get_db)):
    books = get_books(db)
    if books is None:
        raise HTTPException(
            status_code=500, detail="An error occurred while fetching books"
        )
    if not books:
        raise HTTPException(status_code=404, detail="No books found")
    return books


@app.get("/books/filter", response_model=List[BookSchema])
def filter_book_records(
    params: BookFilterParams = Depends(),
    db: Session = Depends(get_db),
):
    books = filter_books(db, params.category, params.publisher)
    if not books:
        raise HTTPException(status_code=404, detail="Books matching filter not found")
    return books


@app.get("/books/{id}", response_model=BookSchema)
def fetch_single_book(id: int, db: Session = Depends(get_db)):
    book = get_book(db, id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@app.post("/books/borrow/", response_model=BorrowResponse)
def borrow_book_item(
    borrow_request: BorrowRequestSchema, db: Session = Depends(get_db)
):
    borrow_task = borrow_book(db, borrow_request)
    if not borrow_task:
        raise HTTPException(
            status_code=403, detail="Book cannot be borrowed, please verify details"
        )
    return {"message": "Book borrowed successfully"}


if __name__ == "__main__":
    import uvicorn

    port = 8001
    print(f"Starting frontend server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
