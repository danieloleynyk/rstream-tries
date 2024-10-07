import asyncio
import signal

from rstream import (
    AMQPMessage,
    Consumer,
    ConsumerOffsetSpecification,
    EventContext,
    MessageContext,
    OffsetNotFound,
    OffsetSpecification,
    OffsetType,
    ServerError,
    StreamDoesNotExist,
    amqp_decoder,
)

cont = 0
lock = asyncio.Lock()
STREAM = "test_stream"


async def on_message(msg: AMQPMessage, message_context: MessageContext):
    global cont
    global lock

    consumer = message_context.consumer
    stream = await message_context.consumer.stream(message_context.subscriber_name)
    offset = message_context.offset

    print("Got message: {} from stream {}, offset {}".format(msg, stream, offset))

    # store the offset every 1000 messages received
    async with lock:
        cont = cont + 1
        # store the offset every 1000 messages received
        if cont % 1000 == 0:
            await asyncio.sleep(60)
            await consumer.store_offset(
                stream=stream, offset=offset, subscriber_name=message_context.subscriber_name
            )



async def consumer_update_handler_offset(is_active: bool, event_context: EventContext) -> OffsetSpecification:
    stream = str(event_context.consumer.get_stream(event_context.subscriber_name))
    print("stream is: " + stream + " subscriber_name" + event_context.subscriber_name)
    if is_active:
        offset_spec = OffsetSpecification(OffsetType.OFFSET, 1)
        try:
            offset = await event_context.consumer.query_offset(stream=STREAM, subscriber_name=event_context.subscriber_name)
            offset_spec = OffsetSpecification(OffsetType.OFFSET, offset)
        except OffsetNotFound as offset_exception:
            print(f"ValueError: {offset_exception}")

    return offset_spec



async def consume():
    consumer = Consumer(
        host="localhost",
        port=5552,
        vhost="/",
        username="guest",
        password="guest",
    )

    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(consumer.close()))

    await consumer.start()
    
    properties = {'single-active-consumer': 'true', 'name': 'consumer-group-1'}

    await consumer.subscribe(
        stream=STREAM,
        subscriber_name="consumer-group-1",
        callback=on_message,
        decoder=amqp_decoder,
        properties=properties,
        consumer_update_listener=consumer_update_handler_offset,
    )
    await consumer.run()


# main coroutine
async def main():
    # schedule the task
    task = asyncio.create_task(consume())
    # suspend a moment
    # wait a moment
    await asyncio.sleep(5)
    # cancel the task
    # was_cancelled = task.cancel()
    await task

    # report a message
    print("Main done")


# run the asyncio program
asyncio.run(main())
