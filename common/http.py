import requests

def make_http_request(method, url, headers=None, data=None, params=None):
    """
    Make an HTTP request and return the response.
    
    Args:
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        url: Target URL
        headers: Optional dictionary of headers
        data: Optional request body data
        params: Optional query parameters
    
    Returns:
        Response object
    """
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, data=data, params=params)
        elif method.upper() == "PUT":
            response = requests.put(url, headers=headers, data=data, params=params)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, params=params)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        print(f"HTTP request failed: {e}")
        if e.response is not None:
          print(f"Response body: {e.response.text}")
        raise