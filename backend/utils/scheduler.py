from apscheduler.schedulers.background import BackgroundScheduler
from backend.utils.status import update_all_statuses
from backend.utils.email_reminder import check_and_send_reminders
from backend.database.database import db
from flask import Flask
from flask_mail import Mail

def start_scheduler(app: Flask, mail: Mail):
    """
    Start background scheduler for:
    - Automatic status updates (daily at midnight)
    - Reminder emails (daily at 9 AM)
    """
    scheduler = BackgroundScheduler()
    
    def update_statuses():
        with app.app_context():
            count = update_all_statuses()
            print(f"[Scheduler] Updated {count} requirement statuses")
    
    def send_reminders():
        with app.app_context():
            count = check_and_send_reminders(app, mail)
            print(f"[Scheduler] Sent {count} reminder emails")
    
    # Update statuses daily at midnight
    scheduler.add_job(
        func=update_statuses, 
        trigger="cron", 
        hour=0, 
        minute=0,
        id='update_statuses'
    )
    
    # Send reminders daily at 9 AM
    scheduler.add_job(
        func=send_reminders, 
        trigger="cron", 
        hour=9, 
        minute=0,
        id='send_reminders'
    )
    
    scheduler.start()
    print("[Scheduler] Background tasks started")
    
    return scheduler