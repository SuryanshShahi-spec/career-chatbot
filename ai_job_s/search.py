import json
from my_redis import redis_client

def get_search_results(query: str):
    # Create a unique cache key based on the search query
    cache_key = f"search:results:{query.lower().strip()}"
    
    # 1. Check Redis cache first
    cached_data = redis_client.get(cache_key)
    
    if cached_data:
        print("Cache Hit! Fetching from Redis...")
        # Convert the cached string back into a Python list/dictionary
        return json.loads(cached_data)
        
    print("Cache Miss! Fetching from main database...")
    # 2. Simulate fetching data from your actual database or API
    fresh_results = database_search_simulation(query)
    
    # 3. Save the results into Redis for future searches
    # ex=300 sets a Time-To-Live (TTL) of 300 seconds (5 minutes)
    redis_client.set(cache_key, json.dumps(fresh_results), ex=300)
    
    return fresh_results

def database_search_simulation(query: str):
    # Simulating a slow database lookup
    return [
        {"job_title": f"Python Developer ({query})", "company": "Tech Corp"},
        {"job_title": f"Backend Engineer ({query})", "company": "Data Inc"}
    ]

# --- Test the Caching ---
if __name__ == "__main__":
    # First run: Cache Miss (Slow)
    print(get_search_results("Remote"))

    # Second run: Cache Hit (Blazing Fast!)
    print(get_search_results("Remote"))
