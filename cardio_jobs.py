from cardio_bot import *
from apscheduler.schedulers.background import BlockingScheduler


scheduler = BlockingScheduler()
scheduler.add_job(tasks, 'interval', seconds=10)
scheduler.start()