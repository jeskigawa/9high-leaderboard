#!/usr/bin/env python3
"""Fix Flask secret key to be persistent (survives restarts)"""
import os
import secrets
import subprocess

APP_PATH = '/var/www/leaderboard/app.py'
KEY_PATH = '/var/www/leaderboard/data/secretkey'

# Generate and save a persistent secret key
if os.path.exists(KEY_PATH):
    with open(KEY_PATH, 'r') as f:
        key = f.read().strip()
    print(f"Existing secret key found, keeping it.")
else:
    key = secrets.token_hex(32)
    with open(KEY_PATH, 'w') as f:
        f.write(key)
    print(f"New secret key generated and saved.")

# Patch app.py to read the key from file
with open(APP_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

OLD_LINE = 'app.secret_key = secrets.token_hex(32)'
NEW_LINES = (
    '_key_path = os.path.join(os.path.dirname(__file__), \'data\', \'secretkey\')\n'
    'if os.path.exists(_key_path):\n'
    '    with open(_key_path, \'r\') as _f:\n'
    '        app.secret_key = _f.read().strip()\n'
    'else:\n'
    '    app.secret_key = secrets.token_hex(32)\n'
    '    with open(_key_path, \'w\') as _f:\n'
    '        _f.write(app.secret_key)'
)

if OLD_LINE in content:
    content = content.replace(OLD_LINE, NEW_LINES)
    with open(APP_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    print("app.py patched: secret key is now persistent.")
elif '_key_path' in content:
    print("app.py already patched, skipping.")
else:
    print("ERROR: Could not find secret key line in app.py!")
    exit(1)

# Fix file permissions
subprocess.run(['chown', 'www-data:www-data', KEY_PATH])
subprocess.run(['chmod', '600', KEY_PATH])

# Restart the service
print("Restarting leaderboard service...")
subprocess.run(['systemctl', 'restart', 'leaderboard'])
import time; time.sleep(2)
result = subprocess.run(['systemctl', 'is-active', 'leaderboard'],
                        capture_output=True, text=True)
status = result.stdout.strip()
if status == 'active':
    print("Service restarted successfully!")
    print("Login will now persist across restarts.")
else:
    print(f"Service status: {status}")
    subprocess.run(['journalctl', '-u', 'leaderboard', '-n', '20', '--no-pager'])
