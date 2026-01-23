import requests

url = "http://127.0.0.1:8000/create_profile"

data = {
    "provider_name": "Dr. Strange",
    "npi": "999999"
}

files = {
    "attachment": open(r"C:\Users\mgven\Downloads\Final_Resume_v2.pdf", "rb")
}

response = requests.post(url, data=data, files=files)
print(response.json())