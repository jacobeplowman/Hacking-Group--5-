import json


setting = {
    "target": 70,
    "speed": 0.95,
    "remaining": 25
}

with open("setting.json", 'w') as f:
    json.dump(setting, f)