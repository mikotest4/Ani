from asyncio import get_event_loop, new_event_loop, set_event_loop
from signal import signal, SIGINT, SIGTERM
from uvloop import install

install()

from bot import bot, LOGS, sch
from bot.core.auto_animes import sched_animes

async def start():
    await bot.start()
    me = await bot.get_me()
    LOGS.info(f"Bot Started as {me.first_name} (@{me.username})")
    sch.add_job(sched_animes, "interval", minutes=20, max_instances=1)
    sch.start()

async def stop():
    await bot.stop()

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
        loop.run_until_complete(start())
        loop.run_forever()
    except KeyboardInterrupt:
        LOGS.info("Bot stopped by user")
    except Exception as e:
        LOGS.error(f"Error running bot: {e}")
    finally:
        try:
            loop.run_until_complete(stop())
        except:
            pass
        loop.close()
