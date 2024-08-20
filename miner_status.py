import os
import re
import json
import pexpect
import pathlib
import requests

SLACK_WEBHOOK_URL = "<slack webhook url>"

FILE_DIR = pathlib.Path(__file__).parent.resolve()
DATA_DIR = os.path.join(FILE_DIR, "incentive-data")

LOCAL_NODE = False
SHOW_CHANGE_PERCENTAGE = True
SUBNET_IDS = []

# alert report to slack webhook
def alert_slack(message="-", title="", fields=[], color="#777777"):
    webhook = SLACK_WEBHOOK_URL
    payload = {
        "text": message,
        "attachments": [{
            "mrkdwn_in": ["text"],
            "color": color,
            "title": title,
            "fields": fields
        }]
    }
    req = requests.post(webhook, json=payload)

# generate incentive report
def init_data_directory(data_dir=DATA_DIR):
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

def get_subnet_from_title(title):
    return title.split(' | ')[0].split(' ')[-1]

def get_data_from_field(field):
    title = field.get('title')
    value = field.get('value')

    if not value:
        return title, None

    return title, float(value.split(' | ')[-2].split(' ')[-1])

def get_percentage_change(new_value, old_value):
    return round(((new_value / old_value) - 1) * 100, 2)

def get_incentive_change(sn_id, fields):
    init_data_directory()
    data_file = os.path.join(DATA_DIR, f"{sn_id}.json")

    incentive_data = {}
    if os.path.exists(data_file):
        try:
            with open(data_file) as f:
                json_data = json.load(f)

            prev_incentive_data = {}
            for data in json_data:
                title, last_incentive = get_data_from_field(data)
                prev_incentive_data[title] = last_incentive

            for data in fields:
                title, incentive = get_data_from_field(data)
                last_incentive = prev_incentive_data.get(title)

                if last_incentive == None or incentive == None:
                    incentive_data[title] = 0

                incentive_data[title] = get_percentage_change(incentive, last_incentive)

        except Exception as e:
            print(e)

    # rewrite with current data
    with open(data_file, "w") as f:
        f.write(json.dumps(fields))

    return incentive_data

def add_incentive_change(title, fields):
    try:
        _fields = fields.copy()
        change_data = get_incentive_change(get_subnet_from_title(title), _fields)
        for i, field in enumerate(_fields):
            change = change_data.get(field['title'])
            if change:
                change = f'+{change}' if change > 0 else change
                _fields[i]['value'] = f"{_fields[i]['value']} `{change}%`"
    except Exception as e:
        print(f'Failed to add incentive with error: {e}')
        return fields

    return _fields

# main function
def report_status():
    fields = []
    title = ""
    stake = 0

    if LOCAL_NODE:
        command = "btcli w overview --subtensor.network local --all"  
    else:
        command = "btcli w overview --subtensor.network subvortex.info:9944 --all"

    try:
        child = pexpect.spawn(command, encoding='utf-8', dimensions=(9999, 9999))
        child.expect(pexpect.EOF, timeout=180)
        output = child.before

        data = output.split('All Wallets:')[1]

        reaesc = re.compile(r'\x1b[^m]*m')
        data = reaesc.sub('', data)

        lines = data.split('\r\n')

        for line in lines:
            if not line.strip():
                continue

            items = line.split()

            if items and items[0] == 'COLDKEY':
                continue

            if items and items[0] == 'Subnet:':
                title = ' '.join(items)
                continue

            if len(items) < 5:
                continue
            elif len(items) < 15 and fields:
                title = f"{title} | Stake: τ{stake} | Miners: {len(fields)}"

                if not SUBNET_IDS: 
                    # send all subnets
                    # sort fields
                    fields = sorted(fields, key=lambda d: d['title'])
                    if SHOW_CHANGE_PERCENTAGE:
                        fields = add_incentive_change(title, fields)

                    alert_slack('Miner Report', title, fields)

                elif any(f"Subnet: {sn_id}" in title for sn_id in SUBNET_IDS):
                    # sort fields
                    fields = sorted(fields, key=lambda d: d['title'])
                    if SHOW_CHANGE_PERCENTAGE:
                        fields = add_incentive_change(title, fields)

                    alert_slack('Miner Report', title, fields)
                
                fields = []
                title = ""
                stake = 0

                continue
            
            fields.append(
                { "title":f"{items[1]} [uid {items[2]}]", "value":f"St: τ{items[4]} | Tr: {items[6]} | In: {items[8]} | Em: {items[10]}" }
            )

            stake = stake + float(items[4])

    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        alert_slack('Miner Report Error', str(e), [], '#ff0e0e')
    finally:
        if child.isalive():
            child.close()

report_status()
