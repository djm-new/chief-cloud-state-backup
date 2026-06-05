#!/usr/bin/env python3
"""Score podcast episodes with OpenRouter Qwen using compact DJ schema."""
import argparse, json, os, re, sqlite3, time, html
from pathlib import Path
from datetime import datetime, timezone, timedelta
import requests

BASE = Path('/opt/data/podcast_digest')
DB = BASE / 'episodes.sqlite'
OUTDIR = BASE / 'outputs'
MODEL = os.getenv('PODCAST_OSS_MODEL', 'qwen/qwen3-235b-a22b')
BATCH_SIZE = int(os.getenv('PODCAST_SCORE_BATCH_SIZE', '10'))


def gateway_env_key(name='OPENROUTER_API_KEY'):
    # Terminal subprocesses can have stale env after Railway redeploy; gateway PID 1 has current env.
    val = os.getenv(name)
    if val:
        return val
    try:
        raw = Path('/proc/1/environ').read_bytes().split(b'\0')
        prefix = (name + '=').encode()
        for item in raw:
            if item.startswith(prefix):
                return item[len(prefix):].decode()
    except Exception:
        pass
    return None


def clean(s, n=1200):
    if not s:
        return ''
    s = re.sub(r'<[^>]+>', ' ', str(s))
    s = html.unescape(s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s[:n]


def load_episodes(since_hours=None):
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    params = []
    where = ''
    if since_hours is not None:
        since = (datetime.now(timezone.utc) - timedelta(hours=float(since_hours))).isoformat()
        where = 'where published >= ?'
        params.append(since)
    rows = con.execute(f'''
        select id, show_name, ring, priority, title, link, published, summary, duration, score as old_score, label as old_label
        from episodes
        {where}
        order by published desc, show_name, title
    ''', params).fetchall()
    return [dict(r) for r in rows]


def call_openrouter(api_key, batch, attempt=1):
    system = """You are DJ Mauch's podcast episode filter. Score EPISODES, not shows. Shows are only source priors.
DJ wants a daily text digest that casts a wider net summarizing what was said, while the weekly audio podcast-of-podcasts is finely tuned.
Favor episodes likely to provide: market read, capital allocation implication, CEO/operator insight, AI platform/business model insight, durable framework, or personal/professional toolkit addition.
Do not over-reward generic AI keywords, news recaps, politics, celebrity, generic VC promo, or shallow founder stories.

DJ calibration from the first 100-episode pass:
- Be stricter with `listen`; reserve it for original audio likely worth DJ's time. Daily can be broad, but listen should be sparse.
- `digest` means worth summarizing in text; many good technical/business episodes belong here, not listen.
- Promote: Benedict Evans appearances/rational AI economics, Mercor CEO on AI labor/model economics, Dara/Uber AV strategy, Gita Gopinath global rates, Ranjan Roy on AI boom warnings, Toast business breakdown, Stratechery best-of content.
- Summarize but do not necessarily listen: enterprise data infrastructure/Fivetran agents, Axiom Math, operator-led PE, RenMac market models, Mark Pincus product frameworks, evolutionary AI models, personal AI workflows, Terry Sejnowski, China vs Nvidia.
- Penalize/skip even if AI-heavy: Exa search infra promo, overly technical continual learning, video/generative-media agent demos, generic AI consciousness/alarmism, vertical vendor AI stories (Aircall/Mitel/elder care), Corgi culture promo, Elon/media narrative, consumer brand playbooks, crypto chatter, generic Bloomberg/news recaps.
- Low-priority shows can surface if the episode is right: Vergecast Nvidia chip war and MFM Idiot Index were interesting enough to learn more.
Return ONLY valid JSON with key results: an array of objects. For each input id include exactly:
{id, score, tier, reason, confidence}
score: integer 0-100.
tier: one of skip, scan, digest, listen.
reason: one short sentence, <= 24 words, saying why this episode should/shouldn't matter to DJ.
confidence: one of low, medium, high."""
    payload_items = []
    for e in batch:
        payload_items.append({
            'id': e['id'],
            'show': e['show_name'],
            'ring': e['ring'],
            'source_priority': e['priority'],
            'title': clean(e['title'], 300),
            'published': e['published'],
            'duration_seconds': e['duration'],
            'summary': clean(e['summary'], 1000),
        })
    user = "/no_think\nScore these podcast episodes for DJ using the schema. Remember: episode-by-episode, daily digest should cast a wider net. Return only JSON.\n" + json.dumps(payload_items, ensure_ascii=False)
    r = requests.post(
        'https://openrouter.ai/api/v1/chat/completions',
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://hermes-agent.local/podcast-digest',
            'X-Title': 'Hermes Podcast Intelligence',
        },
        json={
            'model': MODEL,
            'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}],
            'temperature': 0.1,
            'max_tokens': 1800,
        },
        timeout=120,
    )
    if r.status_code >= 400:
        raise RuntimeError(f'OpenRouter HTTP {r.status_code}: {r.text[:1000]}')
    data = r.json()
    content = data['choices'][0]['message']['content']
    try:
        parsed = json.loads(content)
    except Exception:
        m = re.search(r'\{.*\}', content, re.S)
        if not m:
            raise
        parsed = json.loads(m.group(0))
    results = parsed.get('results', parsed if isinstance(parsed, list) else None)
    if not isinstance(results, list):
        raise RuntimeError(f'Unexpected JSON shape: {parsed}')
    return results, data.get('usage', {})


def normalize_result(x):
    tier = str(x.get('tier','')).strip().lower()
    if tier not in {'skip','scan','digest','listen'}:
        tier = 'scan'
    conf = str(x.get('confidence','')).strip().lower()
    if conf not in {'low','medium','high'}:
        conf = 'medium'
    try:
        score = int(round(float(x.get('score', 0))))
    except Exception:
        score = 0
    score = max(0, min(100, score))
    reason = clean(x.get('reason',''), 220)
    if not reason:
        reason = 'No concise reason returned.'
    return {'id': str(x.get('id','')), 'score': score, 'tier': tier, 'reason': reason, 'confidence': conf}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--since-hours', type=float, default=None, help='Only score episodes published within the last N hours')
    parser.add_argument('--tag', default='', help='Optional filename tag')
    args = parser.parse_args()
    api_key = gateway_env_key()
    if not api_key:
        raise SystemExit('OPENROUTER_API_KEY not found in env or /proc/1/environ')
    episodes = load_episodes(args.since_hours)
    if not episodes:
        raise SystemExit('No episodes matched the requested window')
    all_results, usage_total = [], {'prompt_tokens':0,'completion_tokens':0,'total_tokens':0}
    for i in range(0, len(episodes), BATCH_SIZE):
        batch = episodes[i:i+BATCH_SIZE]
        for attempt in range(1,4):
            try:
                results, usage = call_openrouter(api_key, batch, attempt)
                break
            except Exception as e:
                if attempt == 3:
                    raise
                time.sleep(2*attempt)
        by_id = {r.get('id'): normalize_result(r) for r in results if r.get('id')}
        for e in batch:
            res = by_id.get(e['id'])
            if not res:
                res = {'id': e['id'], 'score': 0, 'tier': 'scan', 'reason': 'Model omitted this episode; needs manual review.', 'confidence': 'low'}
            merged = dict(e)
            merged.update({'qwen': res})
            all_results.append(merged)
        for k in usage_total:
            usage_total[k] += int(usage.get(k,0) or 0)
        print(f'scored {min(i+BATCH_SIZE,len(episodes))}/{len(episodes)} usage={usage}')
        time.sleep(0.5)
    stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d_%H%M')
    tag = ('-' + re.sub(r'[^A-Za-z0-9_.-]+', '-', args.tag.strip())) if args.tag.strip() else ''
    OUTDIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTDIR / f'{stamp}{tag}-qwen-episode-scores.json'
    md_path = OUTDIR / f'{stamp}{tag}-qwen-episode-calibration.md'
    json_path.write_text(json.dumps({'model': MODEL, 'created_at': stamp, 'usage': usage_total, 'episodes': all_results}, indent=2, ensure_ascii=False))
    # markdown sorted by qwen score desc, then published desc
    ranked = sorted(all_results, key=lambda e: (e['qwen']['score'], e.get('published') or ''), reverse=True)
    counts = {}
    for e in ranked:
        counts[e['qwen']['tier']] = counts.get(e['qwen']['tier'],0)+1
    q_in=0.455; q_out=1.82
    est = usage_total.get('prompt_tokens',0)/1e6*q_in + usage_total.get('completion_tokens',0)/1e6*q_out
    lines = [
        '# Qwen Episode-Level Podcast Calibration', '',
        f'**Model:** `{MODEL}`',
        f'**Episodes scored:** {len(ranked)}',
        f'**Schema:** `score`, `tier`, `reason`, `confidence`',
        f'**Tier counts:** listen={counts.get("listen",0)}, digest={counts.get("digest",0)}, scan={counts.get("scan",0)}, skip={counts.get("skip",0)}',
        f'**Token usage:** input={usage_total.get("prompt_tokens",0):,}, output={usage_total.get("completion_tokens",0):,}, total={usage_total.get("total_tokens",0):,}',
        f'**Estimated OpenRouter cost:** ~${est:.4f} at listed Qwen 235B rates ($0.455/M input, $1.82/M output).', '',
        '**Reminder:** this scores episodes, not podcasts. Source shows are priors only. Daily digest should cast a wider net; weekly audio should be more selective.', ''
    ]
    for idx,e in enumerate(ranked,1):
        q=e['qwen']
        lines += [
            f'## {idx}. {e["show_name"]} — {clean(e["title"], 220)}',
            f'- **Qwen score/tier/confidence:** {q["score"]} / {q["tier"]} / {q["confidence"]}',
            f'- **Reason:** {q["reason"]}',
            f'- **Published:** {e.get("published") or ""}',
            f'- **Old metadata score/label:** {e.get("old_score")} / {e.get("old_label")}',
            f'- **Summary metadata:** {clean(e.get("summary"), 450)}',
        ]
        if e.get('link'):
            lines.append(f'- **Link:** {e["link"]}')
        lines.append('- **DJ feedback:** ')
        lines.append('')
    md_path.write_text('\n'.join(lines), encoding='utf-8')
    print(f'JSON={json_path}')
    print(f'MD={md_path}')
    print(f'USAGE={usage_total} EST_COST=${est:.4f}')

if __name__ == '__main__':
    main()
