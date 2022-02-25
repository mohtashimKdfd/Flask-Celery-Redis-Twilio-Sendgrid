from twilio.rest import Client
from dotenv import load_dotenv
import os

load_dotenv()

TWILIO_SID =  os.getenv('TWILIO_SID')
TWILIO_TOKEN = os.getenv('TWILIO_TOKEN')

def SendOtp(otp, number):
    account_sid = "{}".format(TWILIO_SID)
    auth_token = "{}".format(TWILIO_TOKEN)
    client = Client(account_sid, auth_token)
    try:
        message = client.messages \
                    .create(
                            body="Your One Time Password is {}".format(otp),
                            from_="+19377447720",
                            to="+91{}".format(number),
                        )

        print(message.sid)
        print(message)
    except Exception as ex:
        print(ex)
