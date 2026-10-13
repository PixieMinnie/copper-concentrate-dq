import os
import json
import requests

API_KEY = os.getenv("COMTRADE_KEY")
URL = "https://comtradeapi.un.org/data/v1/get/C/M/HS"
headers = {"Ocp-Apim-Subscription-Key": API_KEY}

params = {
    "reporterCode": 699,       # Spain
    "period": "202208,202209,202210",
    "cmdCode": "260300",
    "flowCode": "M",
    "partner2Code": 0,
    "motCode": 0,
    "customsCode": "C00",
    "includeDesc": "true",
}
r = requests.get(URL, params=params, headers=headers, timeout=60)
if r.status_code != 200:
    print(r.status_code, r.text)
    raise SystemExit
for row in sorted(r.json()["data"], key=lambda x: x.get("netWgt") or 0, reverse=True):
    print(row["period"], row["partnerDesc"], row.get("netWgt"), row.get("primaryValue"))