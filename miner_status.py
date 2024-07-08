import pexpect
import re
import requests

SLACK_WEBHOOK_URL = "<slack webhook url>"
LOCAL_NODE = False
SUBNET_IDS = []

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
                    # send all
                    alert_slack('Miner Report', title, fields)
                elif any(f"Subnet: {sn_id}" in title for sn_id in SUBNET_IDS):
                    alert_slack('Miner Report', title, fields)
                
                fields = []
                title = ""
                stake = 0

                continue
            
            fields.append(
                { "title":f"uid {items[2]} [{items[1]}]", "value":f"Stake: τ{items[4]} | Trust: {items[6]} | Incentive: {items[8]}" }
            )

            stake = stake + float(items[4])

    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        alert_slack('Miner Report Error', str(e), [], '#ff0e0e')
    finally:
        if child.isalive():
            child.close()

report_status()
