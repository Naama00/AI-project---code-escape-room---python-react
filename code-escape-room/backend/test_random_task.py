import requests
import json
import os
from dotenv import load_dotenv
import urllib3

urllib3.disable_warnings()
load_dotenv()

# Test with task 5
code_sample = '''def process(data):
    return [x.upper() for x in data if len(x) > 3]'''

response = requests.post(
    'http://127.0.0.1:8000/analyze-code',
    json={
        'code': code_sample,
        'task_id': 5
    },
    verify=False,
    timeout=30
)

print('Status:', response.status_code)
if response.status_code != 200:
    print('Error:')
    print(response.text)
else:
    print('Response:')
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
