import redis

redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

# Made use of redis and cache utilization