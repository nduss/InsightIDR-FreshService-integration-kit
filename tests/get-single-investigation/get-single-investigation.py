import requests

def getInsightInvestigation(id):
    url = 'https://us2.api.insight.rapid7.com/idr/v2/investigations/' + id
    headers = {
    "X-Api-Key": "x",
    "Accept-version": "investigations-preview"
    }
    params = {
    "multi-customer": True
    }

    r = requests.get(url, headers=headers, params=params)
    investigations = r.json()
    print(investigations)

ticket = 'rrn:investigation:us2:cc6da3c6-9246-4fb1-ac99-6c4eb2626663:investigation:296BUI5MX7I9'

getInsightInvestigation(ticket)