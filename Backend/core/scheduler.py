from apscheduler.schedulers.background import BackgroundScheduler

from services.reminder_service import run_reminders

scheduler = BackgroundScheduler()


def start_scheduler():

    scheduler.add_job(
        run_reminders,
        "interval",
        minutes=1
    )

    scheduler.start()

    print("✅ Reminder scheduler started")