import json
import logging
from typing import Any, Generator
import aio_pika
from fastapi import FastAPI
from frontend.crud import (
    create_book,
    delete_book_by_isbn,
    get_unavailable_books_with_return_dates,
    get_users,
    get_users_and_borrowed_books,
)
from frontend.schemas import (
    BookCreate,
    BookSchema,
    BookUnavailableSchema,
    UserSchema,
    custom_json_dumps,
)


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def setup_messaging(app: FastAPI):
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

        user_data_queue = await app.state.rabbitmq_channel.declare_queue(
            "user_data_request"
        )
        book_data_queue = await app.state.rabbitmq_channel.declare_queue(
            "book_data_request"
        )
        await new_books_queue.consume(
            lambda message: process_new_book(app, message)
        )
        await delete_books_queue.consume(
            lambda message: process_delete_book(app, message)
        )
        await user_data_queue.consume(
            lambda message: process_user_data_request(app, message)
        )
        await book_data_queue.consume(
            lambda message: process_book_data_request(app, message)
        )
        logger.info("Started consuming messages from queues")
    except Exception as e:
        logger.error(f"Failed to connect to RabbitMQ: {e}")
        raise


async def process_message(
    app: FastAPI,
    message: aio_pika.IncomingMessage,
    process_func,
    db_gen: Generator[Any, None, None],
):
    async with message.process():
        try:
            db = next(db_gen)
            await process_func(db, message)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            response_data = json.dumps(
                {"error": f"Invalid JSON in message body: {str(e)}"}
            )
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
        finally:
            db.close()

        if message.reply_to:
            await app.state.rabbitmq_channel.default_exchange.publish(
                aio_pika.Message(body=response_data.encode()),
                routing_key=message.reply_to,
            )
            logger.info(f"Response sent to {message.reply_to}")
        else:
            logger.error("No reply_to in the original message. Cannot send response.")


async def handle_delete_book(db, message):
    logger.info(f"Received delete book message: {message.body}")
    isbn = message.body.decode()
    deleted = delete_book_by_isbn(db, isbn)
    if deleted:
        print(f"Deleted book with ISBN: {isbn}")
    else:
        print(f"Book with ISBN: {isbn} not found in frontend database")


async def handle_new_book(db, message):
    logger.info(f"Received new book message: {message.body}")
    book_data = json.loads(message.body.decode())
    validated_book = BookCreate(**book_data)
    synced_book = create_book(db, item=validated_book)
    print(f"Saved new book: {synced_book.title}")


async def handle_book_data_request(db, message):
    request_data = json.loads(message.body.decode())
    action = request_data.get("action")

    if action == "get_unavailable_books":
        try:
            unavailable_books = get_unavailable_books_with_return_dates(db)
            book_data = []
            for book in unavailable_books:
                book_dict = BookSchema.model_validate(book).model_dump()
                latest_borrow = max(
                    book.borrows, key=lambda b: b.return_date, default=None
                )
                book_dict["expected_return_date"] = (
                    latest_borrow.return_date if latest_borrow else None
                )
                book_data.append(BookUnavailableSchema(**book_dict).model_dump())
            response_data = json.dumps(book_data, default=str)
            logger.info(f"Sending data for {len(book_data)} unavailable books")
        except Exception as e:
            logger.error(f"Error getting unavailable books: {str(e)}")
            response_data = json.dumps(
                {"error": f"Error getting unavailable books: {str(e)}"}
            )


async def handle_user_data_request(db, message):
    request_data = json.loads(message.body.decode())
    action = request_data.get("action")

    if action == "get_users":
        users = get_users(db)
        user_data = [UserSchema.model_validate(user).model_dump() for user in users]
        response_data = custom_json_dumps(user_data)
        logger.info(f"Sending user data: {response_data[:100]}...")

    elif action == "get_users_with_borrowed_books":
        skip = request_data.get("skip", 0)
        limit = request_data.get("limit", 100)
        users_with_books = get_users_and_borrowed_books(db, skip=skip, limit=limit)
        response_data = custom_json_dumps(
            [UserSchema.model_validate(user).model_dump() for user in users_with_books]
        )
        logger.info(f"Sending users with borrowed books data: {response_data[:100]}...")


# Refactored handlers
async def process_delete_book(app: FastAPI, message: aio_pika.IncomingMessage):
    await process_message(app, message, handle_delete_book)


async def process_new_book(app: FastAPI, message: aio_pika.IncomingMessage):
    await process_message(app, message, handle_new_book)


async def process_book_data_request(app: FastAPI, message: aio_pika.IncomingMessage):
    await process_message(app, message, handle_book_data_request)


async def process_user_data_request(app: FastAPI, message: aio_pika.IncomingMessage):
    await process_message(app, message, handle_user_data_request)
