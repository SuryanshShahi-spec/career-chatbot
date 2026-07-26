import redis

# This creates the redis_client variable your other file is looking for
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
