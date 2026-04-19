import os
import requests

api_key = os.getenv("ALPHAVANTAGE_API_KEY")

response = requests.get(
    "https://www.alphavantage.co/query",
    params={
        "function": "GLOBAL_QUOTE",
        "symbol": "MSFT",
        "apikey": api_key,
    },
    timeout=30,
)
response.raise_for_status()
print(response.json())
