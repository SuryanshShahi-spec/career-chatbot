from my_redis import redis_client

try:
    # Test the connection by setting a temporary key
    redis_client.set('test_key', 'Success!')
    print(redis_client.get('test_key'))
except Exception as e:
    print(f"Connection failed: {e}")
