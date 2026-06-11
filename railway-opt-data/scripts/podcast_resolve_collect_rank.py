#!/usr/bin/env python3
"""Resolve podcast feeds, collect recent episodes, and metadata-rank for DJ podcast intelligence prototype."""
from __future__ import annotations
import argparse, datetime as dt, hashlib, html, json, os, re, sqlite3, sys, time, urllib.parse
from email.utils import parsedate_to_datetime
from pathlib import Path
import requests, yaml, feedparser
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

BASE = Path('/opt/data/podcast_digest')
FEEDS_YAML = BASE / 'feeds.yaml'
RESOLVED_YAML = BASE / 'resolved_feeds.yaml'
DB = BASE / 'episodes.sqlite'
OUT = BASE / 'outputs'
OUT.mkdir(parents=True, exist_ok=True)
UA = 'HermesPodcastDigest/0.1 (+https://chief.ai)'

KEYWORDS_HIGH = [
 'ai','artificial intelligence','agent','agents','llm','foundation model','openai','anthropic','deepmind','nvidia','gpu','compute','data center',
 'markets','hedge fund','private equity','asset manager','capital allocation','allocator','investing','venture','vc','bank','ceo','founder','strategy',
 'platform','product','pricing','growth','enterprise','software','semiconductor','chips','datacenter','model','automation','startup'
]
KEYWORDS_SKIP = [
 'election','trump','biden','senate','congress','war','ukraine','gaza','israel','climate','energy transition','celebrity','hollywood','sports',
 'daily news','news roundup','headlines','recap','politics','culture war'
]
GUEST_HIGH = [
 'gavin baker','brian chesky','paul tudor jones','stanley druckenmiller','ben horowitz','hemant taneja','michael pollan','nick bostrom',
 'jensen huang','sam altman','dario amodei','demis hassabis','marc andreessen','bill gurley','ray dalio','howard marks','jamie dimon',
 'patrick collison','alex karp','palmer luckey','vinod khosla','reid hoffman','peter thiel','satya nadella','mark zuckerberg','elon musk',
 'larry fink','ken griffin','bill ackman','david tepper','cliff asness','mike mauboussin','chase coleman','philippe laffont',
]
SHOW_BOOST = {
 'invest like the best': 16, 'dwarkesh': 18, 'conversations with tyler': 13, 'stratechery': 14, 'acquired': 14, 'all-in': 8,
 'ben & marc': 16, 'marc & ben': 16, 'a16z': 11, 'bg2': 12, 'capital allocators': 12, 'latent space': 13,
 'cognitive revolution': 13, 'no priors': 13, 'knowledge project': 10, 'founders field guide': 12, 'decoder': 8,
}

def clean(s):
    if not s: return ''
    s = BeautifulSoup(html.unescape(str(s)), 'html.parser').get_text(' ', strip=True)
    return re.sub(r'\s+', ' ', s).strip()

def parse_date_text(v):
    if not v:
        return None
    try:
        return dt.datetime.fromisoformat(str(v).replace('Z', '+00:00'))
    except Exception:
        pass
    try:
        parsed = parsedate_to_datetime(str(v))
        if parsed is not None:
            return parsed.astimezone(dt.timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)
    except Exception:
        pass
    return None

def load_raw_pubdates(feed_url):
    try:
        r = requests.get(feed_url, headers={'User-Agent': UA}, timeout=20)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        ch = root.find('channel')
        if ch is None:
            return {}
        out = {}
        for item in ch.findall('item'):
            raw_pub = item.findtext('pubDate') or item.findtext('{http://purl.org/dc/elements/1.1/}date') or item.findtext('date')
            if not raw_pub:
                continue
            keys = [item.findtext('guid'), item.findtext('link'), clean(item.findtext('title'))]
            for key in keys:
                if key:
                    out[str(key).strip()] = raw_pub.strip()
        return out
    except Exception:
        return {}

def load_show_names():
    data = yaml.safe_load(FEEDS_YAML.read_text())
    shows=[]
    for ring, body in data.get('rings', {}).items():
        for sh in body.get('shows', []):
            if isinstance(sh, str):
                shows.append({'name': sh, 'ring': ring})
            else:
                x=dict(sh); x['ring']=ring; shows.append(x)
    return shows

def itunes_lookup(term):
    url='https://itunes.apple.com/search?' + urllib.parse.urlencode({'term':term,'media':'podcast','entity':'podcast','limit':5})
    try:
        r=requests.get(url,headers={'User-Agent':UA},timeout=20)
        r.raise_for_status()
        return r.json().get('results',[])
    except Exception as e:
        return []

def resolve_feeds():
    shows=load_show_names()
    resolved=[]
    for sh in shows:
        name=sh['name']
        candidates=[]
        for term in [name] + sh.get('aliases', [])[:2]:
            for res in itunes_lookup(term):
                feed=res.get('feedUrl')
                if feed:
                    candidates.append({
                        'collectionName':res.get('collectionName'),
                        'artistName':res.get('artistName'),
                        'feedUrl':feed,
                        'trackViewUrl':res.get('trackViewUrl'),
                        'primaryGenreName':res.get('primaryGenreName'),
                    })
            if candidates: break
        chosen=candidates[0] if candidates else {}
        resolved.append({
            **sh,
            'resolved_name': chosen.get('collectionName'),
            'feed_url': chosen.get('feedUrl'),
            'itunes_url': chosen.get('trackViewUrl'),
            'artist': chosen.get('artistName'),
            'resolve_candidates': candidates[:3],
        })
        print(f"{name:45} -> {chosen.get('collectionName')} | {chosen.get('feedUrl')}")
        time.sleep(0.15)
    RESOLVED_YAML.write_text(yaml.safe_dump({'resolved_at':dt.datetime.utcnow().isoformat()+'Z','shows':resolved},sort_keys=False,allow_unicode=True))
    return resolved

def init_db():
    con=sqlite3.connect(DB)
    con.execute('''create table if not exists episodes(
        id text primary key, show_name text, resolved_show text, ring text, priority text, title text, link text, audio_url text,
        published text, summary text, duration text, feed_url text, collected_at text, score integer, label text, score_reasons text
    )''')
    con.commit(); return con

def parse_date(entry):
    st = entry.get('published_parsed') or entry.get('updated_parsed')
    if st:
        return dt.datetime(*st[:6], tzinfo=dt.timezone.utc)
    for k in ['published', 'updated', 'pubDate', 'date', 'created']:
        v = entry.get(k)
        if not v:
            continue
        parsed = parse_date_text(v)
        if parsed is not None:
            return parsed
    # Some feed parsers expose structured or alternate date fields.
    for key in entry.keys():
        if 'date' in key.lower() or 'pub' in key.lower() or 'updated' in key.lower():
            v = entry.get(key)
            if isinstance(v, str) and v:
                parsed = parse_date_text(v)
                if parsed is not None:
                    return parsed
    return None

def get_audio(entry):
    for enc in entry.get('enclosures',[]):
        href=enc.get('href')
        typ=enc.get('type','')
        if href and ('audio' in typ or href.endswith(('.mp3','.m4a','.wav','.ogg'))): return href
    for link in entry.get('links',[]):
        href=link.get('href'); typ=link.get('type','')
        if href and 'audio' in typ: return href
    return ''

def score_episode(show, title, summary, days_old):
    text=(title+' '+summary+' '+show).lower()
    score=0; reasons=[]
    for k,v in SHOW_BOOST.items():
        if k in show.lower(): score+=v; reasons.append(f'show boost: {k}')
    for g in GUEST_HIGH:
        if g in text:
            score+=35; reasons.append(f'high-signal person: {g}')
    hits=[]
    for kw in KEYWORDS_HIGH:
        if kw in text:
            hits.append(kw)
    if hits:
        score += min(30, 4*len(set(hits)))
        reasons.append('topics: '+', '.join(sorted(set(hits))[:8]))
    skips=[]
    for kw in KEYWORDS_SKIP:
        if kw in text:
            skips.append(kw)
    if skips:
        score -= min(35, 8*len(set(skips)))
        reasons.append('penalty: '+', '.join(sorted(set(skips))[:6]))
    # title indicators
    if re.search(r'\b(ceo|founder|chairman|investor|capital|markets|ai|strategy|model|platform)\b', text): score+=8
    if days_old is not None:
        if days_old <= 1: score+=8; reasons.append('fresh')
        elif days_old <= 3: score+=4
        elif days_old > 10: score-=8
    score=max(0,min(100,score))
    label='skip'
    if score>=85: label='must_listen'
    elif score>=70: label='digest_only'
    elif score>=55: label='skim_if_interested'
    return score,label,reasons

def collect(days=3):
    if not RESOLVED_YAML.exists(): resolve_feeds()
    shows=yaml.safe_load(RESOLVED_YAML.read_text())['shows']
    con=init_db(); now=dt.datetime.now(dt.timezone.utc); cutoff=now-dt.timedelta(days=days)
    collected=0; errors=[]
    for sh in shows:
        feed=sh.get('feed_url')
        if not feed: continue
        try:
            raw_pubdates = load_raw_pubdates(feed)
            fp=feedparser.parse(feed)
            if fp.bozo and not fp.entries:
                errors.append(f"{sh['name']}: {fp.bozo_exception}"); continue
            for e in fp.entries[:30]:
                pub=parse_date(e)
                if pub is None:
                    for candidate in (e.get('id'), e.get('link'), clean(e.get('title'))):
                        raw_pub = raw_pubdates.get(str(candidate).strip()) if candidate else None
                        pub = parse_date_text(raw_pub)
                        if pub is not None:
                            break
                if pub and pub < cutoff: continue
                title=clean(e.get('title'))
                summary=clean(e.get('summary') or e.get('description'))[:4000]
                link=e.get('link') or ''
                audio=get_audio(e)
                guid=e.get('id') or link or audio or title
                eid=hashlib.sha256((feed+'|'+guid).encode()).hexdigest()[:24]
                days_old=(now-pub).total_seconds()/86400 if pub else None
                score,label,reasons=score_episode(sh.get('resolved_name') or sh['name'],title,summary,days_old)
                con.execute('''insert or replace into episodes values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(
                    eid, sh['name'], sh.get('resolved_name'), sh.get('ring'), sh.get('priority'), title, link, audio,
                    pub.isoformat() if pub else '', summary, e.get('itunes_duration') or '', feed, now.isoformat(), score, label, json.dumps(reasons,ensure_ascii=False)
                ))
                collected+=1
        except Exception as ex:
            errors.append(f"{sh['name']}: {type(ex).__name__}: {ex}")
    con.commit(); con.close()
    print(json.dumps({'collected_or_updated':collected,'errors':errors[:20]},indent=2))

def digest(days=3, limit=18):
    con=sqlite3.connect(DB); con.row_factory=sqlite3.Row
    cutoff=(dt.datetime.now(dt.timezone.utc)-dt.timedelta(days=days)).isoformat()
    rows=con.execute('''select * from episodes where published='' or published>=? order by score desc, published desc limit ?''',(cutoff,limit)).fetchall()
    ts=dt.datetime.now().strftime('%Y-%m-%d_%H%M')
    path=OUT/f'{ts}-manual-text-digest.md'
    lines=[]
    lines.append('# Podcast Intelligence Digest — Manual Prototype')
    lines.append('')
    lines.append(f'Window: last {days} days. Ranking is metadata-only for this prototype; no finalist transcription yet.')
    lines.append('')
    lines.append('## Top candidates')
    for i,r in enumerate(rows,1):
        reasons=json.loads(r['score_reasons'] or '[]')
        rec={'must_listen':'Must listen','digest_only':'Digest only','skim_if_interested':'Skim if interested','skip':'Skip'}.get(r['label'],r['label'])
        lines.append(f"\n### {i}. {clean(r['title'])}")
        lines.append(f"- Show: {r['resolved_show'] or r['show_name']}")
        lines.append(f"- Recommendation: **{rec}** ({r['score']}/100)")
        if r['published']: lines.append(f"- Published: {r['published'][:10]}")
        if r['link']: lines.append(f"- Link: {r['link']}")
        lines.append(f"- Why surfaced: {('; '.join(reasons) if reasons else 'metadata matched source/rubric')}")
        desc=clean(r['summary'])
        if desc: lines.append(f"- Metadata summary: {desc[:700]}{'…' if len(desc)>700 else ''}")
        lines.append('- Transcript status: metadata-only; would transcribe if selected as finalist.')
    path.write_text('\n'.join(lines),encoding='utf-8')
    print(path)

if __name__ == '__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['resolve','collect','digest','all'])
    ap.add_argument('--days', type=int, default=3)
    args=ap.parse_args()
    if args.cmd in ('resolve','all'): resolve_feeds()
    if args.cmd in ('collect','all'): collect(args.days)
    if args.cmd in ('digest','all'): digest(args.days)
