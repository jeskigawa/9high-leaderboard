#!/usr/bin/env python3
"""
lokalhostチェックを確実に削除してCORSアップロードを修正する
"""
import subprocess

APP_PATH = '/var/www/leaderboard/app.py'

with open(APP_PATH, 'r', encoding='utf-8') as f:
    code = f.read()

# パターン1: 元のlocalhost制限
OLD1 = (
    "    # POST は通常ログイン必須だが、ブックマークレットはセッションCookieを持てないため\n"
    "    # 代わりにローカルからのアクセスのみ受け付ける（127.0.0.1 / ::1）\n"
    "    remote = request.remote_addr\n"
    "    if remote not in ('127.0.0.1', '::1', 'localhost'):\n"
    "        return _cors_upload_response(jsonify({'error': 'ローカルからのアクセスのみ許可されています'})), 403\n"
)

# パターン2: 別の書き方の場合
OLD2 = (
    "    remote = request.remote_addr\n"
    "    if remote not in ('127.0.0.1', '::1', 'localhost'):\n"
    "        return _cors_upload_response(jsonify({'error': 'ローカルからのアクセスのみ許可されています'})), 403\n"
)

NEW = (
    "    # ブックマークレット経由のアップロード: CORS経由で許可\n"
    "    # (localhost restriction removed)\n"
)

if OLD1 in code:
    code = code.replace(OLD1, NEW)
    print("OK: localhost制限を削除しました（パターン1）")
elif OLD2 in code:
    code = code.replace(OLD2, NEW)
    print("OK: localhost制限を削除しました（パターン2）")
elif 'ローカルからのアクセスのみ許可' in code:
    print("WARNING: localhost制限が見つかりましたが自動削除できません")
    print("手動で確認してください")
    exit(1)
else:
    print("INFO: localhost制限はすでに削除済みです")

with open(APP_PATH, 'w', encoding='utf-8') as f:
    f.write(code)

print("サービス再起動中...")
subprocess.run(['systemctl', 'restart', 'leaderboard'])
import time; time.sleep(2)
result = subprocess.run(['systemctl', 'is-active', 'leaderboard'],
                       capture_output=True, text=True)
if result.stdout.strip() == 'active':
    print("サービス再起動OK!")
else:
    print("サービス状態:", result.stdout.strip())
    subprocess.run(['journalctl', '-u', 'leaderboard', '-n', '20', '--no-pager'])
