#!/usr/bin/env python3
"""
app.pyにafter_requestハンドラを追加してCORSヘッダーを全レスポンスに付ける
エラーレスポンスにもCORSヘッダーが付くので確実に動作する
"""
import subprocess

APP_PATH = '/var/www/leaderboard/app.py'

with open(APP_PATH, 'r', encoding='utf-8') as f:
    code = f.read()

CORS_AFTER = '''@app.after_request
def after_request_cors(response):
    origin = request.headers.get('Origin', '')
    if 'pokerfans.jp' in origin:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS, GET'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response

'''

if 'after_request_cors' in code:
    print("INFO: CORSハンドラはすでに追加済みです")
elif 'def _cors_upload_response' in code:
    code = code.replace('def _cors_upload_response', CORS_AFTER + 'def _cors_upload_response')
    with open(APP_PATH, 'w', encoding='utf-8') as f:
        f.write(code)
    print("OK: after_requestCORSハンドラを追加しました")
else:
    print("ERROR: 挿入位置が見つかりません (app.pyを確認してください)")
    exit(1)

print("サービス再起動中...")
subprocess.run(['systemctl', 'restart', 'leaderboard'])
import time; time.sleep(2)
result = subprocess.run(['systemctl', 'is-active', 'leaderboard'],
                       capture_output=True, text=True)
if result.stdout.strip() == 'active':
    print("サービス再起動OK!")
    print("")
    print("ブックマークレットを再テストしてください")
else:
    print("サービス状態:", result.stdout.strip())
    subprocess.run(['journalctl', '-u', 'leaderboard', '-n', '20', '--no-pager'])
