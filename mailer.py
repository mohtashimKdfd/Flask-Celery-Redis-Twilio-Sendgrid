from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv
import os
load_dotenv()
FROM_EMAIL = os.getenv('FROM_EMAIL')
SENDGRID_KEY = os.getenv('SENDGRID_KEY')
def SendMail(email,body):
    message = Mail(
        from_email='{}'.format(FROM_EMAIL),
        to_emails=email,
        subject='Celery Test Email',
        html_content=body)
    try:
        sg = SendGridAPIClient('{}'.format(SENDGRID_KEY))
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
        print(e)