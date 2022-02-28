import loguru
import os
from flask_app import db, Users
from time import time

dirpath = os.path.dirname(os.path.realpath(__file__))
filename = os.path.join(dirpath,'loguru.log')

loguru.logger.add(
    "{}".format(filename),
    level="INFO",
    format="{time} {level} {message}",
    retention='1 minute',
)
loguru.logger.info('Loguru is up, running and saving otp notifications')
allUsers = Users.query.all()
for user in allUsers:
    curr_time = time()
    if user.otp:
        if curr_time-user.otp_released_time>300:
            loguru.logger.info("{}'s otp is being destroyed".format(user.username))
            user.otp =None
            db.session.commit()
            loguru.logger.info("{}'s otp has been destroyed.".format(user.username))