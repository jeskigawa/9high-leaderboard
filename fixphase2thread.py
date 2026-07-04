#!/usr/bin/env python3
"""
Phase2をバックグラウンドスレッドで実行するよう修正
SSE接続が切れても取込が継続する
"""
import subprocess, sys, time

APP = '/var/www/leaderboard/app.py'
with open(APP, encoding='utf-8') as f:
    lines = f.readlines()

subprocess.run(['cp', APP, '/tmp/app.py.bak.phase2thread'])

# ── Step 1: find key line indices ──────────────────────────────────
phase2_start_i = None
phase2_end_i   = None
finally_i      = None
lock_release_i = None

for i, line in enumerate(lines):
    if '# --- Phase 2: fetch each applyers page' in line:
        phase2_start_i = i
    if ("'type': 'done'" in line and 'events_only' in line and
            'count' in line and phase2_start_i is not None):
        phase2_end_i = i
    if '        finally:\n' == line and phase2_end_i is not None and finally_i is None:
        finally_i = i
    if (finally_i is not None and lock_release_i is None and i > finally_i and
            'SUNVY_EVENT_LOCK.release()' in line):
        lock_release_i = i

for name, idx in [('Phase2開始', phase2_start_i), ('Phase2終了', phase2_end_i),
                   ('finally:', finally_i), ('SUNVY_EVENT_LOCK.release()', lock_release_i)]:
    if idx is None:
        print(f'ERROR: {name}が見つかりません')
        sys.exit(1)
    print(f'OK: {name} = 行{idx + 1}: {lines[idx].rstrip()}')

# ── Step 2: build new Phase 2 block ───────────────────────────────
# NOTE: \\n\\n in this '''...''' string becomes \n\n in the output file (SSE terminator)
#       \\d     in this '''...''' string becomes \d  in the output file (regex)
NEW_P2 = '''\
            # --- Phase 2: バックグラウンドスレッドで実行（SSE切断でも継続）---
            phase2_done = threading.Event()
            phase2_result = {}

            def _run_phase2():
                _new_events = []
                try:
                    for i, (applyers_url, event_id) in enumerate(applyers_links):
                        if i > 0:
                            wait_sec = random.randint(3, 7)
                            _append_import_log('waiting', f'{wait_sec}秒待機中... ({i+1}/{len(applyers_links)})')
                            time.sleep(wait_sec)
                        _append_import_log('status', f'取得中 ({i+1}/{len(applyers_links)}): {applyers_url}')
                        try:
                            all_players = []
                            event_name = ''
                            event_date = ''
                            seen_nicks = set()
                            page_num = 0
                            while True:
                                paged_url = applyers_url if page_num == 0 else f'{applyers_url}?page={page_num}'
                                ap_resp = s.get(paged_url, timeout=SUNVY_REQUEST_TIMEOUT)
                                if not ap_resp.ok:
                                    _append_import_log('warning', f'HTTP {ap_resp.status_code}: {paged_url}')
                                    break
                                parsed = parse_sunvy_applyers_page(ap_resp.text)
                                if not event_name and parsed.get('name'): event_name = parsed['name']
                                if not event_date and parsed.get('date'): event_date = parsed['date']
                                new_players = [r for r in parsed['results'] if r['nickname'] not in seen_nicks]
                                if not new_players: break
                                for r in new_players: seen_nicks.add(r['nickname'])
                                all_players.extend(new_players)
                                ap_soup = BeautifulSoup(ap_resp.text, 'html.parser')
                                pagination = ap_soup.find('ul', class_='pagination')
                                has_next = False
                                if pagination:
                                    for a in pagination.find_all('a'):
                                        href = a.get('href', '')
                                        pm = re.search(r'[?&]page=(\\d+)', href)
                                        if pm and int(pm.group(1)) > page_num:
                                            has_next = True
                                            break
                                if not has_next: break
                                page_num += 1
                                time.sleep(2)
                            all_results_raw = [
                                {
                                    'ranking': idx + 1,
                                    'nickname': r['nickname'],
                                    'memberCode': r.get('memberCode', ''),
                                    'pointsRaw': '--'
                                }
                                for idx, r in enumerate(all_players)
                            ]
                            if event_date and mode == 'range':
                                if eff_end and event_date > eff_end:
                                    _append_import_log('status', f'スキップ: {event_date} (終了日 {eff_end} より後)')
                                    continue
                                if eff_start and event_date < eff_start:
                                    _append_import_log('status', f'{event_date} が開始日 {eff_start} より前のため取込を終了します')
                                    break
                            matched_results = []
                            for r in all_results_raw:
                                pid, status = match_nickname_to_player(
                                    r['nickname'], players, sunvy_members,
                                    member_code=r.get('memberCode', '')
                                )
                                matched_name = None
                                if pid:
                                    mp = next((p for p in players if p['id'] == pid), None)
                                    matched_name = mp['name'] if mp else None
                                matched_results.append({
                                    'ranking': r['ranking'],
                                    'nickname': r['nickname'],
                                    'memberCode': r.get('memberCode', ''),
                                    'pointsRaw': r['pointsRaw'],
                                    'matchedPlayerId': pid,
                                    'matchedPlayerName': matched_name,
                                    'matchStatus': status
                                })
                            candidate = {
                                'importId': f"ev-{uuid.uuid4().hex[:8]}",
                                'pokerfansUrl': applyers_url,
                                'pokerfansName': event_name or f'イベント {event_id}',
                                'date': event_date,
                                'entries': {'current': len(matched_results), 'max': 0},
                                'results': matched_results,
                                'importedAt': datetime.now().isoformat(),
                                'addedToLeaderboard': False
                            }
                            imported_data = load_json('sunvy_imported_events.json')
                            event, is_update = upsert_imported_event(imported_data, candidate)
                            imported_data['lastImportAt'] = datetime.now().isoformat()
                            save_json('sunvy_imported_events.json', imported_data)
                            _new_events.append((event, is_update))
                            auto_count = sum(1 for r in matched_results if r['matchStatus'] == 'auto')
                            action = '更新' if is_update else '新規'
                            _append_import_log('ok', f'{action}: {event_name or event_id}  {event_date}  ({auto_count}/{len(matched_results)}人マッチ)')
                        except http_requests.exceptions.Timeout:
                            _append_import_log('warning', f'タイムアウト: {applyers_url}')
                            continue
                        except Exception as ex:
                            _append_import_log('warning', f'解析エラー ({applyers_url}): {str(ex)}')
                            continue
                    added   = sum(1 for _, upd in _new_events if not upd)
                    updated = sum(1 for _, upd in _new_events if upd)
                    events_only = [ev for ev, _ in _new_events]
                    parts = []
                    if added:   parts.append(f'{added}件新規取込')
                    if updated: parts.append(f'{updated}件更新')
                    msg = '、'.join(parts) if parts else '新規イベントはありませんでした'
                    phase2_result['added'] = added
                    phase2_result['events'] = events_only
                    phase2_result['message'] = msg
                    _append_import_log('done', msg)
                except Exception as _e2:
                    phase2_result['error'] = str(_e2)
                    _append_import_log('error', f'Phase2エラー: {str(_e2)}')
                finally:
                    try:
                        SUNVY_EVENT_LOCK.release()
                    except RuntimeError:
                        pass  # cancel endpoint may have already released
                    phase2_done.set()

            phase2_started[0] = True
            _t = threading.Thread(target=_run_phase2, daemon=True)
            _t.start()

            yield f"data: {json.dumps({'type': 'status', 'message': f'{len(applyers_links)}件をバックグラウンドで取込中... 完了まで数分かかります'})}\\n\\n"

            while not phase2_done.wait(timeout=5):
                yield ": heartbeat\\n\\n"

            if 'error' in phase2_result:
                yield f"data: {json.dumps({'type': 'error', 'message': phase2_result.get('error', '不明なエラー')})}\\n\\n"
            else:
                _ev_list = phase2_result.get('events', [])
                _msg = phase2_result.get('message', '完了')
                _added = phase2_result.get('added', 0)
                yield f"data: {json.dumps({'type': 'done', 'events': _ev_list, 'count': _added, 'message': _msg})}\\n\\n"
'''

# ── Step 3: splice in the new Phase 2 block ─────────────────────
new_content = ''.join(lines[:phase2_start_i]) + NEW_P2 + ''.join(lines[phase2_end_i + 1:])
print('OK: Phase 2ブロックをスレッド版に置換しました')

# ── Step 4: add phase2_started = [False] to generate() ───────────
OLD_GEN = '    def generate():\n        try:\n'
NEW_GEN = '    def generate():\n        phase2_started = [False]\n        try:\n'
if OLD_GEN not in new_content:
    print('ERROR: def generate(): try: パターンが見つかりません')
    sys.exit(1)
new_content = new_content.replace(OLD_GEN, NEW_GEN, 1)
print('OK: phase2_started = [False] を generate() に追加しました')

# ── Step 5: update finally block to avoid double-release ─────────
OLD_FINALLY = '        finally:\n            SUNVY_EVENT_LOCK.release()\n'
NEW_FINALLY = ('        finally:\n'
               '            if not phase2_started[0]:\n'
               '                SUNVY_EVENT_LOCK.release()\n')
if OLD_FINALLY not in new_content:
    print('ERROR: finally: SUNVY_EVENT_LOCK.release() パターンが見つかりません')
    sys.exit(1)
new_content = new_content.replace(OLD_FINALLY, NEW_FINALLY, 1)
print('OK: finallyブロックをdouble-release防止版に更新しました')

# ── Step 6: write updated app.py ─────────────────────────────────
with open(APP, 'w', encoding='utf-8') as f:
    f.write(new_content)
print('OK: app.py を書き込みました')

# ── Step 7: restart and verify ───────────────────────────────────
subprocess.run(['systemctl', 'restart', 'leaderboard'])
time.sleep(2)
r = subprocess.run(['systemctl', 'is-active', 'leaderboard'], capture_output=True, text=True)
status = r.stdout.strip()
print(f'leaderboard: {status}')
if status != 'active':
    print('WARNING: サービスが起動していません！ ログ:')
    r2 = subprocess.run(['journalctl', '-u', 'leaderboard', '-n', '30', '--no-pager'],
                        capture_output=True, text=True)
    print(r2.stdout[-3000:])
    sys.exit(1)

print('')
print('=== 修正完了 ===')
print('Phase 2はバックグラウンドスレッドで実行されます。')
print('SSE接続が切れても取込は継続し、完了後にimport-statusで確認できます。')
