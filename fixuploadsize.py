#!/usr/bin/env python3
"""
WordPressアップロードサイズ制限を修正
1. nginx.conf の http ブロックに client_max_body_size 64M 追加
2. PHP の upload_max_filesize / post_max_size を 64M に変更
"""
import subprocess, sys, re, os, glob

# ===== 1. nginx =====
print("=== 1. nginx client_max_body_size ===")
NGINX_CONF = '/etc/nginx/nginx.conf'
with open(NGINX_CONF) as f:
    conf = f.read()

subprocess.run(['cp', NGINX_CONF, '/tmp/nginx.conf.bak.bodysize'])

if 'client_max_body_size' in conf:
    conf = re.sub(r'client_max_body_size\s+\S+;', 'client_max_body_size 64M;', conf)
    print("OK: 既存の client_max_body_size を 64M に更新")
elif 'http {' in conf:
    conf = conf.replace('http {', 'http {\n    client_max_body_size 64M;', 1)
    print("OK: client_max_body_size 64M を nginx.conf に追加")
else:
    print("ERROR: nginx.conf の http { が見つかりません")
    sys.exit(1)

with open(NGINX_CONF, 'w') as f:
    f.write(conf)

r = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
print(r.stderr.strip())
if r.returncode != 0:
    print("nginx エラー! 元に戻します")
    subprocess.run(['cp', '/tmp/nginx.conf.bak.bodysize', NGINX_CONF])
    sys.exit(1)

# ===== 2. PHP =====
print("\n=== 2. PHP アップロード制限 ===")

# PHP-FPM の php.ini を探す
php_inis = glob.glob('/etc/php/*/fpm/php.ini')
if not php_inis:
    php_inis = glob.glob('/etc/php/*/cli/php.ini')
if not php_inis:
    php_inis = ['/etc/php.ini']

print(f"対象ファイル: {php_inis}")

for ini_path in php_inis:
    if not os.path.exists(ini_path):
        continue
    with open(ini_path) as f:
        ini = f.read()
    subprocess.run(['cp', ini_path, ini_path + '.bak.bodysize'])

    changed = False
    # upload_max_filesize
    if re.search(r'^upload_max_filesize\s*=', ini, re.MULTILINE):
        ini = re.sub(r'^(upload_max_filesize\s*=\s*)\S+', r'\g<1>64M', ini, flags=re.MULTILINE)
        changed = True
        print(f"OK: upload_max_filesize = 64M ({ini_path})")
    else:
        ini += '\nupload_max_filesize = 64M\n'
        changed = True
        print(f"OK: upload_max_filesize = 64M 追加 ({ini_path})")

    # post_max_size
    if re.search(r'^post_max_size\s*=', ini, re.MULTILINE):
        ini = re.sub(r'^(post_max_size\s*=\s*)\S+', r'\g<1>64M', ini, flags=re.MULTILINE)
        print(f"OK: post_max_size = 64M ({ini_path})")
    else:
        ini += '\npost_max_size = 64M\n'
        print(f"OK: post_max_size = 64M 追加 ({ini_path})")

    if changed:
        with open(ini_path, 'w') as f:
            f.write(ini)

# PHP-FPM 再起動
print("\n=== 3. PHP-FPM 再起動 ===")
for ver_dir in glob.glob('/etc/php/*/fpm'):
    ver = ver_dir.split('/')[3]
    r = subprocess.run(['systemctl', 'restart', f'php{ver}-fpm'], capture_output=True, text=True)
    if r.returncode == 0:
        print(f"OK: php{ver}-fpm 再起動")
    else:
        print(f"INFO: php{ver}-fpm 再起動スキップ ({r.stderr.strip()})")

# nginx reload
print("\n=== 4. nginx リロード ===")
subprocess.run(['systemctl', 'reload', 'nginx'])
print("OK: nginx リロード完了!")

print("\n完了! 最大64MBのファイルがアップロードできます")
print("WordPressのテーマ・プラグインをもう一度試してください")
