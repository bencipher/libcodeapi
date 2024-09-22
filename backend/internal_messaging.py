import os
import json
import logging
import asyncio
from typing import Any, Optional
import aio_pika
from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class RabbitMQManager:
    def __init__(self):
        self.connection = None
        self.channel = None

    async def connect(self):
        logger.info("Initializing RabbitMQ connection")
        try:
            self.connection = await aio_pika.connect_robust(
                os.getenv("RABBIT_MQ_CONN_STR")
            )
            self.channel = await self.connection.channel()
            logger.info("RabbitMQ connection established successfully")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def close(self):
        if self.connection:
            await self.connection.close()
            logger.info("RabbitMQ connection closed")

    async def setup_queue(self, queue_name: str):
        await self.channel.declare_queue(queue_name, durable=True)
        logger.info(f"Queue '{queue_name}' set up successfully")

    async def publish_message(self, queue_name: str, message: Optional[dict | str]):
        response_queue = await self.channel.declare_queue("", exclusive=True)
        if type(message) != str:
            message = json.dumps(message)
        await self.channel.default_exchange.publish(
            aio_pika.Message(
                body=message.encode(),
                reply_to=response_queue.name,
                correlation_id=str(asyncio.get_running_loop().time()),
            ),
            routing_key=queue_name,
        )
        logger.info(f"Message published to queue: {queue_name}")

        return response_queue

    async def get_response(self, response_queue: aio_pika.Queue, timeout: int = 5):
        try:
            async with asyncio.timeout(timeout):
                async with response_queue.iterator() as queue_iter:
                    async for message in queue_iter:
                        async with message.process():
                            return json.loads(message.body.decode())
        except asyncio.TimeoutError:
            logger.error(f"Timeout waiting for response")
            raise


rabbitmq_manager = RabbitMQManager()


async def setup_messaging(app: FastAPI):
    await rabbitmq_manager.connect()

    # Set up all the queues
    await rabbitmq_manager.setup_queue("new_books")
    await rabbitmq_manager.setup_queue("delete_books_backend")
    await rabbitmq_manager.setup_queue("user_data_request")
    await rabbitmq_manager.setup_queue("book_data_request")

    app.state.rabbitmq_manager = rabbitmq_manager
    logger.info("All queues set up and ready to consume messages")


async def cleanup_messaging():
    await rabbitmq_manager.close()


# Helper function for API layer
async def publish_and_get_response(
    queue_name: str, message: Optional[dict | str], timeout: int = 5
) -> Any:
    response_queue = await rabbitmq_manager.publish_message(queue_name, message)
    return await rabbitmq_manager.get_response(response_queue, timeout)
