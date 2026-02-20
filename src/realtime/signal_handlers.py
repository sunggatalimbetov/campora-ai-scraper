import asyncio
import signal

from src.realtime.message_buffer import MessageBuffer


def setup_signal_handlers(buffer: MessageBuffer, client):
    """Register SIGINT/SIGTERM handlers that flush all buffers before exiting.

    Uses ``loop.add_signal_handler`` so the async flush can run inside the
    already-running event loop (unlike ``signal.signal`` which can't call
    ``run_until_complete`` when a loop is active).
    """
    loop = asyncio.get_event_loop()

    async def shutdown(sig_name: str):
        print(f"\n⚡ Received {sig_name}, flushing {buffer.total_buffered} buffered messages...")
        try:
            await buffer.flush_all()
            print("✅ Buffers flushed successfully")
        except Exception as e:
            print(f"❌ Error during flush: {e}")
        finally:
            print("👋 Disconnecting Telethon client...")
            await client.disconnect()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(
            sig,
            lambda s=sig: asyncio.create_task(shutdown(signal.Signals(s).name)),
        )
