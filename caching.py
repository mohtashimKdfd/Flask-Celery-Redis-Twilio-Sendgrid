from functools import wraps
import loguru

loguru.logger.add(
    "{}".format('caching.log'),
    level="INFO",
    format="{time} {level} {message}",
    retention='1 minute',
)

def cached(f):
    cache={}
    @wraps(f)
    def wrapper(*args,**kwargs):
        username = kwargs['username']
        signature = (f,username)
        loguru.logger.info('args:{}'.format(username))
        print(cache)
        print(len(cache))
        loguru.logger.debug("Using Signature {}".format(signature))
        if signature in cache:
            loguru.logger.debug("Retrieving {} from cache".format(signature))
            result = cache[signature]
        else:
            loguru.logger.debug("calculating {}".format(signature))
            result = f(*args,**kwargs)
            loguru.logger.debug("Caching {}".format(signature))
            cache[signature] = result
        loguru.logger.info('cache:{}'.format(username))
        print(len(cache))
        
        return result
    return wrapper