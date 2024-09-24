import asyncio
import json
from typing import Optional
import logging
from fastapi import FastAPI, HTTPException
import aio_pika

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def post_message(
    current_app: FastAPI,
    data: Optional[str | dict],
    delivery_mode: Optional[int] = 1,
    delivery_route: Optional[str] = None,
    reply_to: Optional[str] = None,
    cid: str = None
):
    if isinstance(data, dict):
        data = json.dumps(data)
    confirmation = await current_app.state.rabbitmq_channel.default_exchange.publish(
        aio_pika.Message(
            body=data.encode(), delivery_mode=delivery_mode, reply_to=reply_to, correlation_id=cid
        ),
        routing_key=delivery_route,
        mandatory=True,
    )
    return confirmation


async def create_or_get_queue(
    current_app: FastAPI,
    queue_name: str = "",
    durable: bool = False,
    exclusive: bool = False,
    delete: bool = False,
):
    try:
        queue = await current_app.state.rabbitmq_channel.declare_queue(
            queue_name, durable=durable, exclusive=exclusive, auto_delete=delete
        )
        return queue
    except aio_pika.exceptions.ChannelClosed as e:
        if "RESOURCE_LOCKED" in str(e):
            # If the queue already exists and is locked, just try to get it
            return await current_app.state.rabbitmq_channel.get_queue(queue_name)
        else:
            raise


async def fetch_queue_response(queue, max_retries=3, retry_delay=2):
    for attempt in range(max_retries):
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    msg = json.loads(message.body.decode())
                    if msg:
                        return msg

        if attempt < max_retries - 1:
            await asyncio.sleep(retry_delay)

    raise HTTPException(status_code=504, detail="Timeout waiting for user data")


async def handle_message(
    current_app: FastAPI, queue_name: str, data: Optional[str | dict]
):
    # Declare a durable queue
    await create_or_get_queue(current_app, queue_name, True)

    # Enable publisher confirms
    await current_app.state.rabbitmq_channel.set_qos(prefetch_count=1)

    # Publish the message with mandatory flag and wait for confirmation
    confirmation = await post_message(
        current_app, data, delivery_mode=2, delivery_route=queue_name
    )

    return confirmation, data["title"]
