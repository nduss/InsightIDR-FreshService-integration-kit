#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Module providing functions to Investigations.py"""

import os
import sys
import json
from datetime import datetime
import requests # pylint: disable=E0401

# LAST_TIME_DATA = None
# INVESTIGATIONS = None
# INVESTIGATION_ITEM = None
# COMMENT_DATA = None
TICKET_ID = None
# COMMENT = None
# CONFIG = None

FS_API = os.getenv("FS_API")


def function_check():
    """Functional Check for Python 3.10+ and FS_API secret"""
    print('Performing Function Check')
    if sys.version_info < (3, 10):
        sys.exit('Python 3.10+ Needed')
    if str(FS_API) == 'None':
        sys.exit('FS_API key missing')
    print('Function Check Succeeded')

def fetch_config():
    """Load Config into memory"""
    with open('config.json', 'r', encoding='UTF-8') as config_file:
        # global CONFIG # pylint: disable=W0603
        config = json.load(config_file)
        return config

def when_was_the_last_time(client):
    """Check lasttime checked from CONFIG"""
    config = fetch_config()
    # global LAST_TIME_DATA # pylint: disable=W0603
    last_time_data = config[client]["time"]
    return last_time_data

def get_insight_investigations(client):
    """Fetch Investigations from InsightIDR"""
    print("Getting Open Investigations for "+ str(client))
    config = fetch_config()
    url = "https://us2.api.insight.rapid7.com/idr/v2/investigations"
    idr_api = os.getenv(config[client]['api'])
    headers = {"X-Api-Key": idr_api, "Accept-version": "investigations-preview"}
    params = {
        "statuses": "OPEN,INVESTIGATING",
        "multi-customer": True,
        "sources": "ALERT,USER",
        "priorities": "CRITICAL,HIGH,MEDIUM,LOW",
    }
    request = requests.get(url, headers=headers, params=params)
    # global INVESTIGATIONS # pylint: disable=W0603
    investigations = request.json()["data"]
    return investigations

def check_for_new(client):
    """Use lasttime to determine if new investigations are posted"""
    print("Anything New?")
    investigations = get_insight_investigations(client)
    for investigation in investigations:
        last_time_data = when_was_the_last_time(client)
        created_time = datetime.strptime(investigation["created_time"], "%Y-%m-%dT%H:%M:%S.%fZ")
        checked_time = datetime.strptime(last_time_data, "%Y-%m-%dT%H:%M:%S.%fZ")
        if checked_time > created_time:
            continue
        # global INVESTIGATION_ITEM # pylint: disable=W0603
        investigation_item = investigation
        post_ticket_to_fs(investigation_item,client)

def update_last_time(client):
    """Update time per client in config.json"""
    config = fetch_config()
    config[client]["time"] = str(datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"))
    json.dump(config, 'config.json', indent=4)

def post_ticket_to_fs(investigation_item,client):
    """Posting ticket to FreshService"""
    url = "https://securitytapestry.freshservice.com/api/v2/tickets"
    config = fetch_config()
    email = config[client]["email"]
    if "ccs" in config[client]:
        ccs = config[client]["ccs"]
    else: ccs = []

    if investigation_item["priority"] == "LOW":
        idr_priority = 1
        idr_urgency = 1
        idr_impact = 1
    elif investigation_item["priority"] == "MEDIUM":
        idr_priority = 2
        idr_urgency = 2
        idr_impact = 2
    elif investigation_item["priority"] == "HIGH":
        idr_priority = 3
        idr_urgency = 3
        idr_impact = 3
    elif investigation_item["priority"] == "CRITICAL":
        idr_priority = 4
        idr_urgency = 3
        idr_impact = 3

    data = {
        "description": investigation_item["title"],
        "subject": "Security Investigation: " + investigation_item["title"],
        "email": email,
        "cc_emails": ccs,
        "status": 2,
        "priority": idr_priority,
        "urgency": idr_urgency,
        "impact": idr_impact,
        "source": 14,
        "group_id": 21000544549,
        "category": "InsightIDR",
    }
    # global TICKET_ID # pylint: disable=W0603
    request = requests.post(
        url,
        auth=(FS_API, "X"),
        data=json.dumps(data),
        headers={"Content-Type": "application/json"},
    )
    ticket_id = request.json()["ticket"]["id"]
    print("Posted ticket #" + str(ticket_id))
    get_investigation_comments(investigation_item["rrn"],client,ticket_id)

def get_investigation_comments(t_id,client,ticket_id):
    """Fetch Comments from InsightIDR"""
    url = "https://us2.api.insight.rapid7.com/idr/v1/comments"
    config = fetch_config()
    idr_api = os.getenv(config[client]['api'])
    headers = {"X-Api-Key": idr_api, "Accept-version": "comments-preview"}
    params = {"multi-customer": True, "target": t_id}

    request = requests.get(url, headers=headers, params=params)
    # global COMMENT_DATA # pylint: disable=W0603
    comments = request.json()
    comment_data = comments["data"]
    last_time_data = when_was_the_last_time(client)
    # global COMMENT # pylint: disable=W0603
    for comment in comment_data:
        created_time = datetime.strptime(comment["created_time"], "%Y-%m-%dT%H:%M:%S.%fZ")
        checked_time = datetime.strptime(last_time_data, "%Y-%m-%dT%H:%M:%S.%fZ")

        if checked_time > created_time:
            continue
        if comment["body"] is None:
            continue
        post_comments_to_fs(str(ticket_id), comment)

def post_comments_to_fs(fs_id, comment):
    """Posting comments from InsightIDR to FreshService"""
    webhook_url = (
        "https://securitytapestry.freshservice.com/api/v2/tickets/" + fs_id + "/notes"
    )
    data = {"body": comment["body"], "private": False}
    requests.post(
        webhook_url,
        auth=(FS_API, "X"),
        data=json.dumps(data),
        headers={"Content-Type": "application/json"},
    )
    print("Posted comment to ticket #" + str(fs_id))

def investigation_post(client):
    """Bot Main Activity"""
    when_was_the_last_time(client)
    get_insight_investigations(client)
    check_for_new(client)
    update_last_time(client)
