from asyncio import get_event_loop, new_event_loop, set_event_loop
from signal import signal, SIGINT, SIGTERM
from uvloop import install

install()

from bot import bot, LOGS, sch

async def start():
    await bot.start()
    me = await bot.get_me()
    LOGS.info(f"Bot Started as {me.first_name} (@{me.username})")
    
    # Try to import and schedule anime function if it exists
    try:
        from bot.core.auto_animes import sched_animes
        sch.add_job(sched_animes, "interval", minutes=20, max_instances=1)
        LOGS.info("Anime scheduler added successfully")
    except ImportError as e:
        LOGS.warning(f"Could not import sched_animes: {e}")
        LOGS.info("Bot will run without anime scheduling")
    except Exception as e:
        LOGS.error(f"Error setting up anime scheduler: {e}")
    
    sch.start()
    LOGS.info("Scheduler started successfully")

async def stop():
    try:
        sch.shutdown()
        LOGS.info("Scheduler shutdown")
    except Exception as e:
        LOGS.error(f"Error shutting down scheduler: {e}")
    
    try:
        await bot.stop()
        LOGS.info("Bot stopped successfully")
    except Exception as e:
        LOGS.error(f"Error stopping bot: {e}")

def signal_handler(signum, frame):
    LOGS.info(f"Received signal {signum}, stopping...")
    loop = get_event_loop()
    loop.create_task(stop())

if __name__ == "__main__":
    signal(SIGINT, signal_handler)
    signal(SIGTERM, signal_handler)
    
    try:
        loop = get_event_loop()
    except RuntimeError:
        loop = new_event_loop()
        set_event_loop(loop)
    
    try:
        LOGS.info("Starting bot...")
        loop.run_until_complete(start())
        LOGS.info("Bot is running. Press Ctrl+C to stop.")
        loop.run_forever()
    except KeyboardInterrupt:
        LOGS.info("Bot stopped by user (Ctrl+C)")
    except Exception as e:
        LOGS.error(f"Error running bot: {e}")
        import traceback
        LOGS.error(traceback.format_exc())
    finally:
        try:
            LOGS.info("Cleaning up...")
            loop.run_until_complete(stop())
        except Exception as e:
            LOGS.error(f"Error during cleanup: {e}")
        finally:
            try:
                loop.close()
                LOGS.info("Event loop closed")
            except Exception as e:
                LOGS.error(f"Error closing loop: {e}")
