import requests
import json
import os
from datetime import datetime

global lasttimedata
global investigations
global item
global commentdata
global ticketID
global c

IDR_API_L4 = os.getenv("IDR_API_L4")
FS_API = os.getenv("FS_API")


def whenWasTheLastTime():
    # print("Obtaining Last Time Ran")
    lasttime = open("lasttime-l4.txt", "r")
    global lasttimedata
    lasttimedata = lasttime.read()
    lasttime.close()
    # print("Last Check: " + lasttimedata)


def getInsightInvestigations():
    print("Getting Open Investigations for LabFour")
    url = "https://us2.api.insight.rapid7.com/idr/v2/investigations"
    headers = {"X-Api-Key": IDR_API_L4, "Accept-version": "investigations-preview"}
    params = {
        "statuses": "OPEN,INVESTIGATING",
        "multi-customer": True,
        "sources": "ALERT",
        "priorities": "CRITICAL,HIGH,MEDIUM,LOW",
    }

    r = requests.get(url, headers=headers, params=params)
    global investigations
    investigations = r.json()["data"]


def checkForNew():
    print("Anything New for LabFour?")
    for i in investigations:
        created = datetime.strptime(i["created_time"], "%Y-%m-%dT%H:%M:%S.%fZ")
        checktime = datetime.strptime(lasttimedata, "%Y-%m-%dT%H:%M:%S.%fZ")

        if checktime > created:
            continue
        else:
            # print(i["title"] + "\n" + i["created_time"])
            global item
            item = i
            postTicketToFS()
            getInvestigationComments(item["rrn"])


def updateLastTime():
    lasttime = open("lasttime-l4.txt", "w")
    lasttime.write(datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"))
    lasttime.close()
    # print('Updated to current time')


def postTicketToFS():
    url = "https://securitytapestry.freshservice.com/api/v2/tickets"

    idr_priority = 1
    if item["priority"] == "LOW":
        idr_priority = 1
    elif item["priority"] == "MEDIUM":
        idr_priority = 2
    elif item["priority"] == "HIGH":
        idr_priority = 3
    elif item["priority"] == "CRITICAL":
        idr_priority = 4

    data = {
        "description": item["title"],
        "subject": "Security Investigation: " + item["title"],
        "email": "alerts@labfour.edu",
        "status": 2,
        "priority": idr_priority,
        "source": 14,
        "group_id": 21000544549,
        "category": "InsightIDR",
    }
    global ticketID
    r = requests.post(
        url,
        auth=(FS_API, "X"),
        data=json.dumps(data),
        headers={"Content-Type": "application/json"},
    )
    ticketID = r.json()["ticket"]["id"]
    print("Posted ticket #" + str(ticketID))
    # print(ticketID)
    # print(ticketResponse["ticket"]["id"])
    # print(data)


def getInvestigationComments(id):
    url = "https://us2.api.insight.rapid7.com/idr/v1/comments"
    headers = {"X-Api-Key": IDR_API_L4, "Accept-version": "comments-preview"}
    params = {"multi-customer": True, "target": id}

    r = requests.get(url, headers=headers, params=params)
    global commentdata
    comments = r.json()
    commentdata = comments["data"]
    global c
    for c in commentdata:
        created = datetime.strptime(c["created_time"], "%Y-%m-%dT%H:%M:%S.%fZ")
        checktime = datetime.strptime(lasttimedata, "%Y-%m-%dT%H:%M:%S.%fZ")

        if checktime > created:
            continue
        elif c["body"] is None:
            continue
        else:
            postCommentsToFS(str(ticketID))
            # print(
            #     c["created_time"] + "\n"
            #     + c["creator"]["name"] + "\n"
            #     + c["body"]
            #     )


def postCommentsToFS(fsID):
    webhook_url = (
        "https://securitytapestry.freshservice.com/api/v2/tickets/" + fsID + "/notes"
    )

    data = {"body": c["body"], "private": False}

    requests.post(
        webhook_url,
        auth=(FS_API, "X"),
        data=json.dumps(data),
        headers={"Content-Type": "application/json"},
    )
    print("Posted comment to ticket #" + str(fsID))


# Execution Block
whenWasTheLastTime()
getInsightInvestigations()
checkForNew()
updateLastTime()
