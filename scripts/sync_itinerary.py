#!/usr/bin/env python3
"""Download the public California Escape JSONP feed and save validated JSON."""
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

API_URL = os.environ.get('CALIFORNIA_API_URL', '').strip()
CALLBACK = 'californiaEscapeCallback'
OUTPUT = Path(__file__).resolve().parent.parent / 'itinerary.json'

if not API_URL.startswith('https://script.google.com/macros/s/') or not API_URL.endswith('/exec'):
    raise SystemExit('CALIFORNIA_API_URL must be the Apps Script /exec URL')

request = Request(API_URL + '?callback=' + CALLBACK, headers={'User-Agent': 'CaliforniaEscapeSync/1.0'})
with urlopen(request, timeout=35) as response:
    body = response.read(5_000_000).decode('utf-8-sig').strip()

prefix = CALLBACK + '('

if not (body.startswith(prefix) and body.endswith(');')):
    print("=== API DIAGNOSTICS ===")
    print("Response length:", len(body))
    print("Response preview:", repr(body[:300]))
    print("Starts with expected callback:", body.startswith(prefix))
    print("Ends with expected characters:", body.endswith(');'))
    print("=======================")

    raise SystemExit(
        'Unexpected API response; not JSONP. '
        'Refusing to overwrite itinerary.json'
    )

payload = json.loads(body[len(prefix):-2])
if payload.get('error') or not isinstance(payload.get('sheets'), dict):
    raise SystemExit('API returned an error or no sheets; refusing to overwrite itinerary.json')

required = ('Itinerary', 'Stays', 'Ideas', 'Budget', 'Trip Info')
if any(not isinstance(payload['sheets'].get(name), list) for name in required):
    raise SystemExit('Missing or malformed tab data; refusing to overwrite itinerary.json')

# Ensure this public file contains no excluded fields, even if the API changes.
excluded = {'confirmation number', 'booking reference', 'reservation number', 'password', 'email', 'phone', 'emergency contact'}
for name in required:
    for row in payload['sheets'][name]:
        if not isinstance(row, dict):
            raise SystemExit('Unexpected row format')
        for key in list(row):
            if key.strip().lower() in excluded:
                del row[key]

OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('Updated itinerary.json:', ', '.join(f'{name}={len(payload["sheets"][name])}' for name in required))
