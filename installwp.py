#!/usr/bin/env python3
"""
9high.net WordPress + リーダーボード セットアップ
  https://9high.net/             -> WordPress
  https://9high.net/leaderboard/ -> 公開リーダーボード (ログイン不要)
  https://9high.net/leaderboard/admin/ -> 管理画面 (JS側でログイン確認)
  https://9high.net/api/         -> Flask API (管理画面JSから直接アクセス)
"""
import subprocess, os, sys, re, time

def run(cmd, check=True):
    print(f"$ {cmd}")
    r = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if r.stdout.strip(): print(r.stdout.strip())
    if r.stderr.strip(): print(r.stderr.strip())
    if check and r.returncode != 0:
        print(f"FAILED (code={r.returncode})")
        sys.exit(1)
    return r

WP_DB   = 'wp9high'
WP_USER = 'wp9high'
WP_PASS = '9highWP2024'

print("=== 1. APT 更新 ===")
run("apt-get update -qq")

print("\n=== 2. PHP + MySQL インストール ===")
# まず壊れたパッケージを修正
run("apt-get install -f -y", check=False)
# mysql-server (Ubuntu 20.04: MySQL 8.0 / Ubuntu 22.04: MySQL 8.0)
run("DEBIAN_FRONTEND=noninteractive apt-get install -y "
    "php php-fpm php-mysql php-gd php-curl "
    "php-xml php-mbstring php-zip mysql-server wget")

print("\n=== 3. MySQL 起動 ===")
run("systemctl start mysql", check=False)
run("systemctl start mysqld", check=False)
run("systemctl enable mysql", check=False)
run("systemctl enable mysqld", check=False)

print("\n=== 4. WordPress DB 作成 ===")
run(f'mysql -u root -e "CREATE DATABASE IF NOT EXISTS {WP_DB} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"')
run(f"""mysql -u root -e "CREATE USER IF NOT EXISTS '{WP_USER}'@'localhost' IDENTIFIED BY '{WP_PASS}';" """)
run(f"""mysql -u root -e "GRANT ALL PRIVILEGES ON {WP_DB}.* TO '{WP_USER}'@'localhost';" """)
run('mysql -u root -e "FLUSH PRIVILEGES;"')
print(f"DB: {WP_DB} / {WP_USER} / {WP_PASS}")

print("\n=== 5. WordPress ダウンロード (日本語版) ===")
run("wget -q https://ja.wordpress.org/latest-ja.tar.gz -O /tmp/wpja.tar.gz")
run("tar -xzf /tmp/wpja.tar.gz -C /tmp/")
if os.path.exists("/var/www/wordpress"):
    run("rm -rf /var/www/wordpress")
run("mv /tmp/wordpress /var/www/wordpress")
run("chown -R www-data:www-data /var/www/wordpress")
run("chmod -R 755 /var/www/wordpress")
print("WordPress -> /var/www/wordpress")

print("\n=== 6. wp-config.php ===")
src = "/var/www/wordpress/wp-config-sample.php"
dst = "/var/www/wordpress/wp-config.php"
run(f"cp {src} {dst}")
with open(dst, 'r', encoding='utf-8') as f:
    c = f.read()
c = c.replace('database_name_here', WP_DB)
c = c.replace('username_here',      WP_USER)
c = c.replace('password_here',      WP_PASS)
with open(dst, 'w', encoding='utf-8') as f:
    f.write(c)
print("wp-config.php 完了")

print("\n=== 7. PHP-FPM ソケット確認 ===")
r2 = run("php --version 2>/dev/null | head -1", check=False)
m = re.search(r'PHP (\d+\.\d+)', r2.stdout)
php_ver = m.group(1) if m else '8.1'
php_sock = f"/var/run/php/php{php_ver}-fpm.sock"
run(f"systemctl start php{php_ver}-fpm", check=False)
run(f"systemctl enable php{php_ver}-fpm", check=False)
time.sleep(1)
# ソケット確認
r3 = run("find /var/run/php -name '*-fpm.sock' 2>/dev/null", check=False)
socks = [s for s in (r3.stdout or '').strip().split('\n') if s.endswith('.sock')]
if socks:
    php_sock = socks[0]
print(f"socket: {php_sock}")

print("\n=== 8. nginx 設定 ===")
NGINX = '/etc/nginx/sites-available/leaderboard'
with open(NGINX) as f:
    old_nginx = f.read()
run(f"cp {NGINX} /tmp/nginx.bak.wp")

# certbot SSL行を抽出
ssl_lines = []
for line in old_nginx.splitlines():
    s = line.strip()
    if any(x in s for x in ['ssl_certificate', 'ssl_certificate_key',
                              'ssl_dhparam', 'include /etc/letsencrypt']):
        ssl_lines.append('    ' + s)
ssl_block = '\n'.join(ssl_lines)

# 管理画面JSの /api/... /static/... /uploads/... を直接Flaskへ
# /leaderboard/ はプレフィックスを除去してFlask / へ
conf = (
    'server {\n'
    '    listen 80;\n'
    '    server_name 9high.net;\n'
    '    return 301 https://$host$request_uri;\n'
    '}\n\n'
    'server {\n'
    '    listen 443 ssl;\n'
    '    server_name 9high.net;\n'
    + ssl_block + '\n\n'
    '    root /var/www/wordpress;\n'
    '    index index.php index.html;\n\n'
    '    # Flask: API (管理画面JSの絶対パス /api/... を直接Flask へ)\n'
    '    location /api/ {\n'
    '        proxy_pass http://127.0.0.1:5000/api/;\n'
    '        proxy_set_header Host $host;\n'
    '        proxy_set_header X-Real-IP $remote_addr;\n'
    '        proxy_set_header X-Forwarded-Proto $scheme;\n'
    '        proxy_read_timeout 300;\n'
    '        proxy_buffering off;\n'
    '    }\n\n'
    '    # Flask: static files\n'
    '    location /static/ {\n'
    '        proxy_pass http://127.0.0.1:5000/static/;\n'
    '        proxy_set_header Host $host;\n'
    '    }\n\n'
    '    # Flask: uploaded photos\n'
    '    location /uploads/ {\n'
    '        proxy_pass http://127.0.0.1:5000/uploads/;\n'
    '        proxy_set_header Host $host;\n'
    '    }\n\n'
    '    # Flask: logo\n'
    '    location = /logo.svg {\n'
    '        proxy_pass http://127.0.0.1:5000/logo.svg;\n'
    '        proxy_set_header Host $host;\n'
    '    }\n\n'
    '    # リーダーボード: /leaderboard/ -> Flask / (プレフィックス除去)\n'
    '    location = /leaderboard {\n'
    '        return 301 /leaderboard/;\n'
    '    }\n'
    '    location /leaderboard/ {\n'
    '        proxy_pass http://127.0.0.1:5000/;\n'
    '        proxy_set_header Host $host;\n'
    '        proxy_set_header X-Real-IP $remote_addr;\n'
    '        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n'
    '        proxy_set_header X-Forwarded-Proto $scheme;\n'
    '        proxy_read_timeout 300;\n'
    '        proxy_buffering off;\n'
    '    }\n\n'
    '    # WordPress\n'
    '    location / {\n'
    '        try_files $uri $uri/ /index.php?$args;\n'
    '    }\n\n'
    '    location ~ \\.php$ {\n'
    '        include fastcgi_params;\n'
    f'        fastcgi_pass unix:{php_sock};\n'
    '        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;\n'
    '    }\n\n'
    '    location ~ /\\.ht {\n'
    '        deny all;\n'
    '    }\n'
    '}\n'
)

with open(NGINX, 'w') as f:
    f.write(conf)

r = run("nginx -t", check=False)
if r.returncode != 0:
    print("nginx エラー! 元に戻します")
    run(f"cp /tmp/nginx.bak.wp {NGINX}")
    sys.exit(1)
run("systemctl reload nginx")
print("nginx OK!")

print("\n=== 9. Flask ルート整理 ===")
# / -> 公開リーダーボード (9high-leaderboard.html)
# /admin -> 管理画面 (index.html)
APP = '/var/www/leaderboard/app.py'
with open(APP) as f:
    code = f.read()

# パターン: @app.route('/') def xxx(): return send_from_directory('.', 'index.html')
# を 9high-leaderboard.html に変更
OLD_ROOT = "@app.route('/')\ndef index():\n    return send_from_directory('.', 'index.html')"
NEW_ROOT = "@app.route('/')\ndef index():\n    return send_from_directory('.', '9high-leaderboard.html')"

# 別名のパターンも対応
OLD_ROOT2 = "@app.route('/')\ndef index_page():\n    return send_from_directory('.', 'index.html')"
NEW_ROOT2 = "@app.route('/')\ndef index_page():\n    return send_from_directory('.', '9high-leaderboard.html')"

changed = False
if OLD_ROOT in code:
    code = code.replace(OLD_ROOT, NEW_ROOT)
    changed = True
    print("OK: / -> 9high-leaderboard.html に変更")
elif OLD_ROOT2 in code:
    code = code.replace(OLD_ROOT2, NEW_ROOT2)
    changed = True
    print("OK: / -> 9high-leaderboard.html に変更 (index_page)")
else:
    print("WARNING: / ルートのパターンが見つかりません")

# /admin ルートに index.html 配信を追加 (まだなければ)
ADMIN_ROUTE = "@app.route('/admin')\ndef admin_page():\n    return redirect('/', 301)"
ADMIN_NEW   = (
    "@app.route('/admin')\n"
    "@app.route('/admin/')\n"
    "def admin_page():\n"
    "    return send_from_directory('.', 'index.html')"
)
if ADMIN_ROUTE in code:
    code = code.replace(ADMIN_ROUTE, ADMIN_NEW)
    changed = True
    print("OK: /admin -> index.html に変更")
elif "def admin_page" in code:
    print("INFO: admin_page は既に存在します")
else:
    print("WARNING: /admin ルートが見つかりません")

if changed:
    with open(APP, 'w') as f:
        f.write(code)
    print("app.py 更新完了")

print("\n=== 10. Flask ProxyFix 設定 ===")
with open(APP) as f:
    code = f.read()

if 'ProxyFix' in code:
    print("ProxyFix: 設定済み")
else:
    m = re.search(r'(app = Flask\([^)]+\))', code)
    if m:
        flask_line = m.group(1)
        replacement = (
            flask_line + '\n'
            'from werkzeug.middleware.proxy_fix import ProxyFix\n'
            'app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)\n'
            "app.config['APPLICATION_ROOT'] = '/leaderboard'"
        )
        code = code.replace(flask_line, replacement)
        with open(APP, 'w') as f:
            f.write(code)
        print("ProxyFix: 追加完了")
    else:
        print("WARNING: app = Flask(...) が見つかりません")

print("\n=== 11. leaderboard 再起動 ===")
run("systemctl restart leaderboard")
time.sleep(2)
r = run("systemctl is-active leaderboard", check=False)
print(f"leaderboard: {r.stdout.strip()}")

print("\n" + "=" * 50)
print("セットアップ完了!")
print(f"WordPress DB: {WP_DB} / {WP_USER} / {WP_PASS}")
print("")
print("ブラウザで確認:")
print("  https://9high.net/             -> WordPress セットアップ画面")
print("  https://9high.net/leaderboard/ -> 公開リーダーボード")
print("  https://9high.net/leaderboard/admin/ -> 管理画面")
