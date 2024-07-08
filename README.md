# miner-status

Requirement
- python 3.10+
- [Bittensor](https://github.com/opentensor/bittensor)
- [Local Subtensor](https://github.com/opentensor/subtensor) (Optional)

## Set up
Install Bittensor
```
pip install bittensor
```

Install pip packages
```
pip install pexpect
pip install requests
```

## Usage

Add coldkey and hotkey which you want to track

```
python3 miner_status.py
```

Add to cron
```
crontab -e
```
```
* * 0 0 0 python3 miner_status.py
```
