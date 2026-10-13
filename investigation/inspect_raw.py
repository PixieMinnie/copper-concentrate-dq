import os
import json
import requests

API_KEY = os.getenv("COMTRADE_KEY")
URL = "https://comtradeapi.un.org/data/v1/get/C/M/HS"
headers = {"Ocp-Apim-Subscription-Key": API_KEY}

params = {
    "reporterCode": 724,       # Spain
    "period": "202503",
    "cmdCode": "260300",
    "flowCode": "M",
    "partnerCode": 0,
    "partner2Code": 0,
    "motCode": 0,
    "customsCode": "C00",
    "includeDesc": "true",
}
r = requests.get(URL, params=params, headers=headers, timeout=60)
for row in r.json()["data"]:
    for k in ["period", "netWgt", "altQty", "altQtyUnitAbbr", "primaryValue", "isReported"]:
        print(k, "=", row.get(k))