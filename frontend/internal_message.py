import contextlib
import json
import logging
from typing import Callable, Any
import aio_pika
from fastapi import FastAPI
from sqlalchemy.orm import Session

from frontend.crud import (
    delete_book_by_isbn,
    create_book,
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
from frontend.storage import SessionLocal

logger = logging.getLogger(__name__)


class MessageHandler:
    @staticmethod
    async def handle_message(message: aio_pika.IncomingMessage, process_func: Callable):
        async with message.process():
            try:
                response_data = await process_func(message)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {str(e)}")
                response_data = json.dumps(
                    {"error": f"Invalid JSON in message body: {str(e)}"}
                )
            except Exception as e:
                logger.error(f"Unexpected error in message processing: {str(e)}")
                response_data = json.dumps({"error": f"Unexpected error: {str(e)}"})

            await MessageHandler.send_response(message, response_data)

    @staticmethod
    async def send_response(message: aio_pika.IncomingMessage, response_data: str):
        if message.reply_to:
            await message.channel.default_exchange.publish(
                aio_pika.Message(
                    body=response_data.encode(), correlation_id=message.correlation_id
                ),
                routing_key=message.reply_to,
            )
            logger.info(f"Response sent to {message.reply_to}")
        else:
            logger.error("No reply_to in the original message. Cannot send response.")


class DatabaseSession:
    @staticmethod
    @contextlib.contextmanager
    def get_session():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()


class MessageProcessor:
    @staticmethod
    async def process_delete_book(message: aio_pika.IncomingMessage):
        isbn = message.body.decode()
        with DatabaseSession.get_session() as db:
            deleted = delete_book_by_isbn(db, isbn)
            if deleted:
                logger.info(f"Deleted book with ISBN: {isbn}")
                return json.dumps(
                    {"status": "success", "message": f"Book with ISBN {isbn} deleted"}
                )
            else:
                logger.info(f"Book with ISBN: {isbn} not found in frontend database")
                return json.dumps(
                    {
                        "status": "not_found",
                        "message": f"Book with ISBN {isbn} not found",
                    }
                )

    @staticmethod
    async def process_new_book(message: aio_pika.IncomingMessage):
        book_data = json.loads(message.body.decode())
        with DatabaseSession.get_session() as db:
            validated_book = BookCreate(**book_data)
            synced_book = create_book(db, item=validated_book)
            logger.info(f"Saved new book: {synced_book.title}")
            return json.dumps(
                {"status": "success", "message": f"Book {synced_book.title} created"}
            )

    @staticmethod
    async def process_book_data_request(message: aio_pika.IncomingMessage):
        request_data = json.loads(message.body.decode())
        action = request_data.get("action")

        if action == "get_unavailable_books":
            with DatabaseSession.get_session() as db:
                unavailable_books = get_unavailable_books_with_return_dates(db)
                book_data = []
                for book in unavailable_books:
                    book_dict = {
                        c.name: getattr(book, c.name) for c in book.__table__.columns
                    }
                    expected_return_date = None
                    if book.borrows:
                        latest_borrow = max(book.borrows, key=lambda b: b.return_date)
                        expected_return_date = latest_borrow.return_date

                    book_dict["expected_return_date"] = expected_return_date
                    unavailable_book = BookUnavailableSchema(**book_dict)
                    book_data.append(unavailable_book.model_dump())

                logger.info(f"Sending data for {len(book_data)} unavailable books")
                return json.dumps(book_data, default=str)
        else:
            logger.warning(f"Unknown action received: {action}")
            return json.dumps({"error": f"Unknown action: {action}"})

    @staticmethod
    async def process_user_data_request(message: aio_pika.IncomingMessage):
        request_data = json.loads(message.body.decode())
        action = request_data.get("action")

        with DatabaseSession.get_session() as db:
            if action == "get_users":
                users = get_users(db)
                user_data = [
                    UserSchema.model_validate(user).model_dump() for user in users
                ]
                response_data = custom_json_dumps(user_data)
                logger.info(
                    f"Sending user data: {response_data[:100]}..."
                )  # Log first 100 chars
                return response_data
            elif action == "get_users_with_borrowed_books":
                skip = request_data.get("skip", 0)
                limit = request_data.get("limit", 100)
                users_with_books = get_users_and_borrowed_books(
                    db, skip=skip, limit=limit
                )
                response_data = custom_json_dumps(
                    [
                        UserSchema.model_validate(user).model_dump()
                        for user in users_with_books
                    ]
                )
                logger.info(
                    f"Sending users with borrowed books data: {response_data[:100]}..."
                )  # Log first 100 chars
                return response_data
            else:
                logger.error(f"Unknown action received: {action}")
                return json.dumps({"error": f"Unknown action: {action}"})


class RabbitMQManager:
    def __init__(self, app: FastAPI):
        self.app = app

    async def setup(self):
        logger.info("Initializing RabbitMQ connection")
        try:
            self.app.state.rabbitmq_connection = await aio_pika.connect_robust(
                "amqp://guest:guest@internal_messaging:5672/"
            )
            self.app.state.rabbitmq_channel = (
                await self.app.state.rabbitmq_connection.channel()
            )
            logger.info("RabbitMQ connection established successfully")

            await self.setup_queue("new_books", MessageProcessor.process_new_book)
            await self.setup_queue(
                "delete_books_frontend", MessageProcessor.process_delete_book
            )
            await self.setup_queue(
                "user_data_request", MessageProcessor.process_user_data_request
            )
            await self.setup_queue(
                "book_data_request", MessageProcessor.process_book_data_request
            )

            logger.info("Started consuming messages from queues")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def setup_queue(self, queue_name: str, callback: Callable):
        queue = await self.app.state.rabbitmq_channel.declare_queue(
            queue_name, durable=True
        )
        await queue.consume(
            lambda message: MessageHandler.handle_message(message, callback)
        )

    async def cleanup(self):
        logger.info("Closing RabbitMQ connection")
        await self.app.state.rabbitmq_connection.close()


async def setup_messaging(app: FastAPI):
    rabbitmq_manager = RabbitMQManager(app)
    await rabbitmq_manager.setup()
    app.state.rabbitmq_manager = rabbitmq_manager


async def cleanup_messaging(app: FastAPI):
    await app.state.rabbitmq_manager.cleanup()
