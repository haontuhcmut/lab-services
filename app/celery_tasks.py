from celery import Celery
from app.mail import mail, create_message
from asgiref.sync import async_to_sync
from app.config import broker_url, result_backend


c_app = Celery("worker", broker=broker_url, backend=result_backend)
c_app.config_from_object("app.config")


@c_app.task()
def send_email(recipients: list[str], subject: str, body: str):
    message = create_message(recipients, subject=subject, body=body)
    async_to_sync(mail.send_message)(message)
    print("Email sent")
