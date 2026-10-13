import os
import json
import requests

API_KEY = os.getenv("COMTRADE_KEY")
URL = "https://comtradeapi.un.org/data/v1/get/C/M/HS"
headers = {"Ocp-Apim-Subscription-Key": API_KEY}

params = {
    "reporterCode": 604,       # Peru
    "period": "202412,202501,202502,202503",
    "cmdCode": "260300",
    "flowCode": "X",           #exports
    "partnerCode": "724,410",  # Spain, Korea
    "partner2Code": 0,
    "motCode": 0,
    "customsCode": "C00",
    "includeDesc": "true",
}
r = requests.get(URL, params=params, headers=headers, timeout=60)
for row in r.json()["data"]:
    for k in ["partnerDesc", "period", "netWgt"]:
        print(k, "=", row.get(k))