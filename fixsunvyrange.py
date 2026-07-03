#!/usr/bin/env python3
"""
Sunvy期間取込の2つのバグを修正:
  Fix1: ページ0が未来イベントのみでも即停止するバグ
  Fix2: Phase2でnginxタイムアウト(300秒)によりSSEが切れるバグ
"""
import subprocess, sys, time

APP = '/var/www/leaderboard/app.py'
with open(APP) as f:
    lines = f.readlines()

subprocess.run(['cp', APP, '/tmp/app.py.bak.sunvyrange'])

fix1 = False
fix2 = False
new_lines = []
i = 0

while i < len(lines):

    # ===== Fix 1: ページ0早期停止バグ =====
    # 「if not page_links and page == 0 and not applyers_links:」を見つけ、
    # 次の yield + break を「未来イベントのみの場合は続行」に変更
    if ('if not page_links and page == 0 and not applyers_links:' in lines[i]
            and not fix1):
        # 行頭のスペースを取得（インデント）
        base = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
        inner = base + '    '

        new_lines.append(lines[i])  # if not page_links ... はそのまま
        i += 1

        # 次の2行は yield + break → 新ロジックに置き換え
        original_yield = lines[i]
        i += 1
        original_break = lines[i]
        i += 1

        # 未来イベントのみの場合はスキップしてページを続行
        new_lines.append(inner + '# 未来イベントしかないページはスキップして続行\n')
        new_lines.append(inner + 'all_future = bool(\n')
        new_lines.append(inner + '    page_event_dates and eff_end\n')
        new_lines.append(inner + '    and all(d > eff_end for d in page_event_dates))\n')
        new_lines.append(inner + 'if not all_future:\n')
        # yield と break は元の内容を使い、さらに1段インデント
        new_lines.append(inner + '    ' + original_yield.lstrip())
        new_lines.append(inner + '    ' + original_break.lstrip())

        fix1 = True
        print('OK Fix1: ページ0早期停止バグを修正しました')
        continue

    # ===== Fix 2: Phase2 heartbeat =====
    # 「wait_sec = random.randint(3, 7)」を見つけ（前行が「if i > 0:」の場合）
    # time.sleep(wait_sec) を 1秒×wait_sec のheartbeatループに変更
    if ('wait_sec = random.randint(3, 7)' in lines[i]
            and i > 0
            and 'if i > 0:' in lines[i - 1]
            and not fix2):
        indent = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
        new_lines.append(lines[i])    # wait_sec = random.randint(3, 7)
        i += 1
        yield_line = lines[i]         # yield waiting message
        i += 1
        sleep_line = lines[i]         # time.sleep(wait_sec)
        i += 1

        # 待機メッセージは1回だけ表示し、その後heartbeatループ
        new_lines.append(yield_line)
        new_lines.append(indent + 'for _tick in range(wait_sec):  # heartbeat: SSE接続維持\n')
        new_lines.append(indent + '    time.sleep(1)\n')
        # SSEコメント行（クライアントは無視するが接続はリセットされる）
        new_lines.append(indent + '    yield ": heartbeat\\n\\n"\n')

        fix2 = True
        print('OK Fix2: Phase2 heartbeatループに変更しました')
        continue

    new_lines.append(lines[i])
    i += 1

# 結果確認
if not fix1:
    print('WARNING: Fix1の挿入位置が見つかりませんでした')
if not fix2:
    print('WARNING: Fix2の挿入位置が見つかりませんでした')

if fix1 or fix2:
    with open(APP, 'w') as f:
        f.writelines(new_lines)
    print('app.py 更新完了')

    subprocess.run(['systemctl', 'restart', 'leaderboard'])
    time.sleep(2)
    r = subprocess.run(['systemctl', 'is-active', 'leaderboard'],
                       capture_output=True, text=True)
    print(f'leaderboard: {r.stdout.strip()}')
    print('')
    print('修正内容:')
    if fix1:
        print('  Fix1: 昨日などの期間指定で、ページ1が未来イベントのみでも正常に続行')
    if fix2:
        print('  Fix2: 64件など多数のイベントでも接続が切れずに最後まで取込可能')
else:
    print('変更なし (すでに修正済みか、コード構造が変わっています)')
    sys.exit(1)
