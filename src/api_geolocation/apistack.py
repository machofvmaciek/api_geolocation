import requests

_API_KEY = "dc67a8734ca28b72a901606df6e3c03a"


sample_ip = "134.201.250.155"

# "http://api.ipstack.com/{IP}?access_key={YOUR_ACCESS_KEY}"

def get_geolocation(ip_or_url, access_key):
    base_url = "http://api.ipstack.com/"
    url = f"{base_url}{ip_or_url}?access_key={access_key}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx and 5xx)
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None
    
print(get_geolocation(sample_ip, _API_KEY))