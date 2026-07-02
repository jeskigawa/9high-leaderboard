#!/usr/bin/env python3
"""
Fix pokerfans bookmarklet URL and server upload restriction.
- Adds /pokerfans/setup route to Flask so the bookmarklet can be regenerated
- Removes localhost-only restriction from /api/pokerfans/upload
- Patches pokerfans_setup.html to auto-replace URL based on server hostname
"""
import subprocess
import re

APP_PATH = '/var/www/leaderboard/app.py'
SETUP_PATH = '/var/www/leaderboard/pokerfans_setup.html'

# ---- 1. Patch app.py ----
with open(APP_PATH, 'r', encoding='utf-8') as f:
    app_code = f.read()

# Add /pokerfans/setup route if not already present
SETUP_ROUTE = """
@app.route('/pokerfans/setup')
def pokerfans_setup_page():
    return send_from_directory('.', 'pokerfans_setup.html')

"""

if '/pokerfans/setup' not in app_code:
    # Insert after the /pokerfans route
    app_code = app_code.replace(
        "@app.route('/pokerfans')\n",
        SETUP_ROUTE + "@app.route('/pokerfans')\n"
    )
    print("Added /pokerfans/setup route")
else:
    print("/pokerfans/setup route already exists")

# Remove localhost-only restriction from /api/pokerfans/upload
OLD_CHECK = (
    "    # POST は通常ログイン必須だが、ブックマークレットはセッションCookieを持てないため\n"
    "    # 代わりにローカルからのアクセスのみ受け付ける（127.0.0.1 / ::1）\n"
    "    remote = request.remote_addr\n"
    "    if remote not in ('127.0.0.1', '::1', 'localhost'):\n"
    "        return _cors_upload_response(jsonify({'error': 'ローカルからのアクセスのみ許可されています'})), 403\n"
)
NEW_CHECK = (
    "    # ブックマークレット経由のアップロード: Origin check via CORS\n"
    "    # (localhost restriction removed for server deployment)\n"
)

if OLD_CHECK in app_code:
    app_code = app_code.replace(OLD_CHECK, NEW_CHECK)
    print("Removed localhost restriction from /api/pokerfans/upload")
elif 'ローカルからのアクセスのみ許可' in app_code:
    print("WARNING: Could not auto-patch upload restriction - check manually")
else:
    print("Upload restriction already removed")

with open(APP_PATH, 'w', encoding='utf-8') as f:
    f.write(app_code)

# ---- 2. Patch pokerfans_setup.html ----
with open(SETUP_PATH, 'r', encoding='utf-8') as f:
    html = f.read()

# Add URL replacement after bookmarklet decode
OLD_BM_LINE = "document.getElementById('bookmarklet-drag').href = bmCode;"
NEW_BM_LINE = (
    "bmCode = bmCode.replace('http://localhost:5000/api/pokerfans/upload', "
    "location.origin + '/api/pokerfans/upload');\n"
    "  document.getElementById('bookmarklet-drag').href = bmCode;"
)

if OLD_BM_LINE in html and 'location.origin' not in html:
    html = html.replace(OLD_BM_LINE, NEW_BM_LINE)
    with open(SETUP_PATH, 'w', encoding='utf-8') as f:
        f.write(html)
    print("Patched pokerfans_setup.html with dynamic URL")
elif 'location.origin' in html:
    print("pokerfans_setup.html already patched")
else:
    print("WARNING: Could not patch pokerfans_setup.html")

# ---- 3. Restart service ----
print("\nRestarting leaderboard service...")
subprocess.run(['systemctl', 'restart', 'leaderboard'])
import time; time.sleep(2)
result = subprocess.run(['systemctl', 'is-active', 'leaderboard'],
                        capture_output=True, text=True)
if result.stdout.strip() == 'active':
    print("Service restarted OK!")
    print("")
    print("Next steps:")
    print("1. Visit http://160.251.123.221/pokerfans/setup")
    print("2. Drag the new bookmarklet to replace the old one")
    print("3. Go to pokerfans.jp and run the bookmarklet to upload data")
else:
    print("Service status:", result.stdout.strip())
    subprocess.run(['journalctl', '-u', 'leaderboard', '-n', '20', '--no-pager'])
