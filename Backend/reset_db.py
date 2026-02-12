import requests
import sys

try:
    response = requests.delete('http://localhost:8000/admin/reset')
    print(response.json())
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
