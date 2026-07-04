#!/usr/bin/env python3
"""
取込状態と最新ログを確認する診断スクリプト
"""
import subprocess, json, os

APP = '/var/www/leaderboard/app.py'

print("=== leaderboard サービス状態 ===")
r = subprocess.run(['systemctl', 'is-active', 'leaderboard'], capture_output=True, text=True)
print(f"状態: {r.stdout.strip()}")

print("\n=== 最新ログ（最後の30行）===")
r = subprocess.run(['journalctl', '-u', 'leaderboard', '-n', '30', '--no-pager'],
                   capture_output=True, text=True)
print(r.stdout[-3000:] if len(r.stdout) > 3000 else r.stdout)

print("\n=== Fix2 heartbeat が適用済みか確認 ===")
with open(APP) as f:
    code = f.read()

if 'heartbeat' in code:
    print("OK: heartbeat が app.py に存在します")
    # 該当行を表示
    for i, line in enumerate(code.splitlines(), 1):
        if 'heartbeat' in line:
            print(f"  行{i}: {line.strip()}")
else:
    print("WARNING: heartbeat が見つかりません（Fix2未適用）")

print("\n=== Phase2 wait_sec ループ確認 ===")
if 'for _tick in range(wait_sec)' in code:
    print("OK: heartbeatループが存在します")
else:
    print("WARNING: heartbeatループが見つかりません（Fix2未適用の可能性）")

print("\n=== sunvy_imported_events.json 最終更新時刻 ===")
path = '/var/www/leaderboard/data/sunvy_imported_events.json'
if os.path.exists(path):
    import time
    mtime = os.path.getmtime(path)
    print(f"最終更新: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))}")
    with open(path) as f:
        data = json.load(f)
    events = data.get('events', [])
    print(f"総イベント数: {len(events)}")
    # 最新5件
    recent = sorted(events, key=lambda e: e.get('importedAt', ''), reverse=True)[:5]
    for e in recent:
        print(f"  - {e.get('date','?')} {e.get('pokerfansName','?')} (取込: {e.get('importedAt','?')[:19]})")
else:
    print("ファイルが存在しません")
