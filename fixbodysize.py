#!/usr/bin/env python3
"""
nginx client_max_body_size を 64M に増加
WordPressテーマ・プラグインアップロードの413エラーを修正
"""
import subprocess, sys, re

NGINX = '/etc/nginx/sites-available/leaderboard'
with open(NGINX) as f:
    conf = f.read()

subprocess.run(['cp', NGINX, '/tmp/nginx.bak.bodysize'])

if 'client_max_body_size' in conf:
    # すでにある場合は64Mに更新
    conf = re.sub(r'client_max_body_size\s+\S+;', 'client_max_body_size 64M;', conf)
    with open(NGINX, 'w') as f:
        f.write(conf)
    print("OK: client_max_body_size を 64M に更新しました")
else:
    # server_name の直後に追加（443ブロックに）
    INSERT_AFTER = '    server_name 9high.net;\n'
    if INSERT_AFTER in conf:
        conf = conf.replace(INSERT_AFTER, INSERT_AFTER + '    client_max_body_size 64M;\n', 1)
        with open(NGINX, 'w') as f:
            f.write(conf)
        print("OK: client_max_body_size 64M を追加しました")
    else:
        print("WARNING: 挿入位置が見つかりません。手動で追加してください")
        print("  server { の中に:  client_max_body_size 64M;")
        sys.exit(1)

r = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
print(r.stderr.strip())
if r.returncode == 0:
    subprocess.run(['systemctl', 'reload', 'nginx'])
    print("OK: nginx リロード完了!")
    print("WordPressのテーマ・プラグインアップロード可能になりました（最大64MB）")
else:
    print("nginx エラー! 元に戻します")
    subprocess.run(['cp', '/tmp/nginx.bak.bodysize', NGINX])
    sys.exit(1)
