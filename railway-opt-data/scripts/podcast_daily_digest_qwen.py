#!/usr/bin/env python3
"""Generate a calibrated daily podcast digest from a Qwen episode scoring JSON file."""
import json, os, re
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from openrouter_spend import openrouter_post_json

MODEL=os.getenv('PODCAST_OSS_MODEL','qwen/qwen3-235b-a22b')

def gateway_env_key(name='OPENROUTER_API_KEY'):
    if os.getenv(name): return os.getenv(name)
    try:
        for item in Path('/proc/1/environ').read_bytes().split(b'\0'):
            if item.startswith((name+'=').encode()):
                return item.split(b'=',1)[1].decode()
    except Exception:
        pass
    return None

def clean(s,n=1200):
    s=re.sub(r'\s+',' ',str(s or '')).strip()
    return s[:n]

def main():
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument('scores_json')
    ap.add_argument('--window-start', default='')
    ap.add_argument('--window-end', default='')
    ap.add_argument('--tag', default='')
    args=ap.parse_args()
    data=json.loads(Path(args.scores_json).read_text())
    window_label = args.tag or '24h'
    window_end_dt = datetime.fromisoformat(args.window_end.replace('Z', '+00:00')) if args.window_end else datetime.now(timezone.utc)
    window_end_et = window_end_dt.astimezone(ZoneInfo('America/New_York'))
    date_line = window_end_et.strftime('%A, %B %-d, %Y')
    episodes=[]
    for e in data['episodes']:
        q=e['qwen']
        episodes.append({
            'show': e['show_name'], 'title': e['title'], 'published': e['published'], 'link': e.get('link'),
            'summary': clean(e.get('summary'),900), 'qwen_score': q['score'], 'qwen_tier': q['tier'], 'qwen_reason': q['reason'], 'confidence': q['confidence']
        })
    system=f"""You write DJ Mauch's daily podcast intelligence digest.
Use ONLY the provided episode metadata and Qwen scores. Do not invent details beyond metadata.
Calibrated taste:
- Score/evaluate episodes, not shows.
- Lead with the date in America/New_York, then a short list of main topics.
- Then list the shows you are surfacing, and for each show name the guest/interviewee if it is explicit in the title or summary; if not explicit, say "guest not explicit in metadata".
- Daily digest casts a wider net and summarizes what was said.
- Weekly audio is finely tuned, but this is daily text.
- Be strict with Listen. Listen means original audio likely worth DJ's time.
- Digest means summarize in text; audio optional/unnecessary.
- Scan means maybe interesting / learn more.
- Skip means omit except a brief filtered-noise note.
- Promote market shapers, top investors/CEOs, AI economics, platform/business model implications, capital allocation, durable frameworks.
- Penalize narrow AI infrastructure promo, technical research without business implication, vertical vendor stories, generic Bloomberg/news recaps, Elon/media narrative, consumer brand playbooks, politics.
- Stratechery best-of/Ben Thompson content is important; include if present.
Output markdown with this structure:
# Daily Podcast Intelligence Digest — {date_line}
- Window: last {window_label} hours
- Main topics: 3-6 bullets
- Shows surfaced: 3-10 bullets, each with show name, guest if explicit, and the episode title
Then sections:
## Listen
## Summarize in digest
## Scan / maybe
## Skipped noise
For every included item, reference the show itself, the guest if explicit, what was said, why DJ should care, recommendation, and link.
Be concise but useful. No tables. No slop."""
    user="/no_think\nGenerate today's digest for this %sh window. Date (ET): %s. Window start: %s. Window end: %s. Episodes JSON:\n%s" % (window_label,date_line,args.window_start,args.window_end,json.dumps(episodes,ensure_ascii=False))
    resp = openrouter_post_json(
        path='chat/completions',
        model=MODEL,
        title='Hermes Podcast Daily Digest',
        referer='https://hermes-agent.local/podcast-digest',
        timeout=180,
        payload={
            'model': MODEL,
            'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}],
            'temperature': 0.2,
            'max_tokens': 5000,
        },
        source='cron',
        platform='cron',
        project_slug='podcast-intelligence-digest',
        workdir='/opt/data/podcast_digest',
        metadata={
            'workflow': 'podcast-intelligence-digest',
            'stage': 'daily_digest_render',
            'window_start': args.window_start,
            'window_end': args.window_end,
            'window_date_et': date_line,
            'window_label': window_label,
        },
    )
    content=resp['choices'][0]['message']['content'].strip()
    usage=resp.get('usage',{})
    est=usage.get('cost')
    stamp=datetime.now(timezone.utc).strftime('%Y-%m-%d_%H%M')
    out=Path('/opt/data/podcast_digest/outputs')/f'{stamp}-daily-podcast-digest-{window_label}.md'
    header=f'<!-- model={MODEL}; usage={usage}; cost={est} -->\n'
    out.write_text(header+content+'\n',encoding='utf-8')
    print(out)
    print('usage', usage)

if __name__=='__main__': main()
