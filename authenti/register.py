import time
import requests

class APIClient:
    def __init__(self, base_url, max_retries=3, backoff_factor=2):
        self.base_url = base_url
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    def request(self, endpoint, method="GET", **kwargs):
        retries = 0
        while retries < self.max_retries:
            try:
                response = requests.request(method, f"{self.base_url}{endpoint}", **kwargs)
                response.raise_for_status()
                return response.json()
                
            except (requests.exceptions.HTTPError, requests.exceptions.RequestException) as e:
                # Determine if we should retry
                is_rate_limit = isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 429
                is_network_error = isinstance(e, requests.exceptions.RequestException) and not isinstance(e, requests.exceptions.HTTPError)

                if is_rate_limit or is_network_error:
                    retries += 1
                    if retries >= self.max_retries:
                        print(f"Request failed after {self.max_retries} attempts: {e}")
                        raise e
                    
                    # Consistent exponential backoff formula: 2^0, 2^1, etc.
                    wait = self.backoff_factor ** (retries - 1)
                    reason = "Rate limit hit" if is_rate_limit else "Network failure"
                    print(f"{reason}. Retrying in {wait}s... (Attempt {retries}/{self.max_retries})")
                    time.sleep(wait)
                else:
                    # Fail immediately for other HTTP errors (e.g., 404, 500)
                    print(f"Non-retryable error: {e}")
                    raise e
        
        raise Exception(f"Max retries ({self.max_retries}) exceeded for {endpoint}")