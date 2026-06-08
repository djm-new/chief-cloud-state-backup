#!/usr/bin/env python3
"""Semantic podcast discovery for DJ's podcast intelligence pipeline.

This is Ring 3: discover adjacent people/topics/shows from DJ's taste profile,
not just exact watchlist matches or known RSS feeds.
"""
from __future__ import annotations
import argparse, datetime as dt, hashlib, html, json, os, re, sqlite3, time, urllib.parse
from pathlib import Path
import feedparser, yaml
from openrouter_spend import openrouter_post_json
from bs4 import BeautifulSoup

DB = BASE / 'episodes.sqlite'
DISCOVERY_DB = BASE / 'semantic_discovery.sqlite'
OUT = BASE / 'outputs'
OUT.mkdir(parents=True, exist_ok=True)
UA = 'HermesPodcastSemanticDiscovery/0.1 (+https://chief.ai)'
MODEL = os.getenv('PODCAST_OSS_MODEL','qwen/qwen3-235b-a22b')

TASTE_PROFILE = """
DJ wants a podcast intelligence radar, not a subscription digest.
Use named people/topics as positive examples, not closed lists.
Find adjacent people/topics/conversations he would likely care about.

Positive examples and taste anchors:
- Ben Thompson / Stratechery, Benedict Evans, Naval Ravikant, Marc Andreessen, Ben Horowitz, Dwarkesh Patel, Tyler Cowen.
- Top investors/allocators: Stanley Druckenmiller, Paul Tudor Jones, Bill Ackman, Howard Marks, Gavin Baker, Philippe/Thomas Laffont, Ray Dalio, Ken Griffin.
- Scaled CEOs/operators/platform builders: Satya Nadella, Brian Chesky, Jensen Huang, Patrick Collison, Dara Khosrowshahi, Alex Karp, Jamie Dimon.
- AI leaders/frontier thinkers: Sam Altman, Dario Amodei, Demis Hassabis, Andrej Karpathy, Richard Sutton, Fei-Fei Li.
- Framework builders and original thinkers: Nick Bostrom, Michael Pollan, Byrne Hobart, Eugene Wei, Matthew Ball.

Underlying archetypes:
- market/business shapers
- original framework builders
- high-leverage tech philosophers
- rational AI economics and value-accrual analysts
- elite allocators/operators
- platform strategy thinkers
- capital allocation and market structure analysts
- people explaining how AI changes software, labor, productivity, ownership, scarcity, company-building, and business models

Skip/penalize:
- generic news recaps, politics/culture war, celebrity, sports, shallow founder origin stories, generic VC promo, narrow vendor product promo, technical AI research with no business/operator implication, generic AI consciousness/alarmism without a business/investor/operator frame, crypto price chatter.
- low-quality feed aggregators, SEO feeds, non-English repost feeds, and scraped/translated feeds unless DJ explicitly asks for multilingual discovery.
"""

DEFAULT_STATIC_QUERIES = [
    # Archetype, not exact watchlist only
    'AI economics value accrual podcast',
    'AI capital allocation podcast CEO investor',
    'software is changing AI agents podcast',
    'platform shift AI podcast founder investor',
    'future of software agents podcast',
    'token economics AI enterprise podcast',
    'private evals AI enterprise podcast',
    'AI productivity labor market podcast economist',
    'Naval Ravikant AI podcast',  # included as regression test for the failure case
    'technology philosophy startups leverage podcast',
    'market structure AI podcast investor',
    'frontier AI business model podcast',
]


def clean(s):
    if not s: return ''
    s = BeautifulSoup(html.unescape(str(s)), 'html.parser').get_text(' ', strip=True)
    return re.sub(r'\s+', ' ', s).strip()


def gateway_env_key(name='OPENROUTER_API_KEY'):
    if os.getenv(name): return os.getenv(name)
    try:
        for item in Path('/proc/1/environ').read_bytes().split(b'\0'):
            if item.startswith((name+'=').encode()):
                return item.split(b'=',1)[1].decode()
    except Exception:
        pass
    return None


def call_openrouter(messages, max_tokens=2500, temperature=0.2):
    resp = openrouter_post_json(
        path='chat/completions',
        model=MODEL,
        title='Hermes Podcast Semantic Discovery',
        referer='https://hermes-agent.local/podcast-semantic-discovery',
        timeout=180,
        payload={'model': MODEL, 'messages': messages, 'temperature': temperature, 'max_tokens': max_tokens},
        source='cron',
        platform='cron',
        project_slug='podcast-intelligence-digest',
        workdir='/opt/data/podcast_digest',
        metadata={'workflow': 'podcast-intelligence-digest', 'stage': 'semantic_discovery'},
    )
    return resp


def generate_semantic_queries(limit_people=35, limit_topics=30):
    prompt = f"""/no_think
Given DJ's podcast taste profile below, generate semantic discovery targets. IMPORTANT: the named people are examples, not a closed list. Include adjacent people who fit the same archetypes. Include search queries that would discover relevant podcast episodes in Apple Podcasts/web/YouTube.

{TASTE_PROFILE}

Return ONLY JSON:
{{
  "people": [{{"name":"...", "why":"...", "archetype":"..."}}],
  "topics": [{{"topic":"...", "why":"..."}}],
  "search_queries": ["..."]
}}
Constraints:
- people max {limit_people}; topics max {limit_topics}; queries max 60.
- Include people not explicitly listed if semantically adjacent.
- Queries should be podcast-discovery friendly, not too broad.
"""
    resp = call_openrouter([{'role':'user','content':prompt}], max_tokens=4500, temperature=0.35)
    txt = resp['choices'][0]['message']['content'].strip()
    m = re.search(r'\{.*\}', txt, re.S)
    data = json.loads(m.group(0) if m else txt)
    # Add regression/static queries
    data.setdefault('search_queries', [])
    for q in DEFAULT_STATIC_QUERIES:
        if q not in data['search_queries']:
            data['search_queries'].append(q)
    return data, resp.get('usage', {})


def itunes_search(term, limit=10):
    url = 'https://itunes.apple.com/search?' + urllib.parse.urlencode({'term':term,'media':'podcast','entity':'podcast','limit':limit})
    try:
        r = requests.get(url, headers={'User-Agent':UA}, timeout=20)
        r.raise_for_status()
        return r.json().get('results', [])
    except Exception:
        return []


def parse_date(entry):
    st = entry.get('published_parsed') or entry.get('updated_parsed')
    if st:
        return dt.datetime(*st[:6], tzinfo=dt.timezone.utc)
    for k in ['published','updated']:
        v=entry.get(k)
        if v:
            try: return dt.datetime.fromisoformat(v.replace('Z','+00:00'))
            except Exception: pass
    return None


def get_audio(entry):
    for enc in entry.get('enclosures',[]):
        href=enc.get('href'); typ=enc.get('type','')
        if href and ('audio' in typ or href.endswith(('.mp3','.m4a','.wav','.ogg'))): return href
    for link in entry.get('links',[]):
        href=link.get('href'); typ=link.get('type','')
        if href and 'audio' in typ: return href
    return ''


def init_dbs():
    con = sqlite3.connect(DB)
    con.execute('''create table if not exists episodes(
        id text primary key, show_name text, resolved_show text, ring text, priority text, title text, link text, audio_url text,
        published text, summary text, duration text, feed_url text, collected_at text, score integer, label text, score_reasons text
    )''')
    con.commit()
    dcon = sqlite3.connect(DISCOVERY_DB)
    dcon.execute('''create table if not exists discovery_runs(
        id text primary key, created_at text, days integer, query_count integer, feeds_found integer, episodes_found integer, usage_json text
    )''')
    dcon.execute('''create table if not exists discovered_feeds(
        run_id text, query text, collection_name text, artist_name text, feed_url text, itunes_url text, genre text,
        primary key(run_id, feed_url)
    )''')
    dcon.execute('''create table if not exists discovered_episodes(
        run_id text, episode_id text, query text, show_name text, title text, published text, link text, feed_url text,
        summary text, semantic_score integer, semantic_tier text, reason text,
        primary key(run_id, episode_id)
    )''')
    dcon.commit()
    return con, dcon


def keyword_prefilter(title, summary, show, query):
    # Hard reject obvious low-quality/global-noise surfaces for DJ's current English-language product.
    joined = title + ' ' + summary + ' ' + show
    if re.search(r'[\u4e00-\u9fff]', joined):
        return -100
    if re.search(r'(?i)(rss订阅|translated|translation|bitcoin|crypto|coinbase|web3|defi)', joined):
        return -60
    if re.search(r'(?i)(hinton|conscious|superintelligence|doomer|doom|existential risk)', joined) and not re.search(r'(?i)(business|market|operator|capital|pricing|strategy|enterprise|investor)', joined):
        return -40
    text = (joined+' '+query).lower()
    positive = [
        'ai','artificial intelligence','agent','agents','software','platform','startup','founder','ceo','investor','capital','market',
        'wealth','leverage','productivity','automation','model','compute','nvidia','openai','anthropic','deepmind','economics','scarcity',
        'strategy','business','valuation','ipo','ownership','labor','token','eval','enterprise','technology','future'
    ]
    negative = ['election','trump','biden','senate','culture war','celebrity','sports','dating','true crime','comedy']
    score = sum(1 for p in positive if p in text) * 4
    score -= sum(1 for n in negative if n in text) * 12
    if any(name in text for name in ['naval','benedict evans','ben evans','ben thompson','marc andreessen','tyler cowen','dwarkesh']): score += 25
    return score


def qwen_filter_candidates(cands, batch_size=20):
    if not cands:
        return []
    out=[]
    system = f"""You are filtering podcast episodes for DJ's semantic podcast intelligence briefing.
Use this taste profile as a latent profile, not exact keyword matching:
{TASTE_PROFILE}
Return only JSON array. For each input include id, score 0-100, tier skip|interesting|transcript|must_listen, reason one sentence.
- interesting: qualifies for briefing lightweight summary.
- transcript: important enough to read transcript/rich page.
- must_listen: likely weekly podcast-of-podcasts candidate.
Be strict. Penalize generic news, narrow vendor promo, and low-signal episodes.
"""
    for i in range(0, len(cands), batch_size):
        batch=cands[i:i+batch_size]
        payload=[]
        for c in batch:
            payload.append({'id':c['episode_id'],'show':c['show_name'],'title':c['title'],'published':c['published'],'summary':c['summary'][:900],'discovery_query':c['query']})
        resp=call_openrouter([{'role':'system','content':system},{'role':'user','content':'/no_think\nEpisodes:\n'+json.dumps(payload,ensure_ascii=False)+'\nReturn JSON array only.'}], max_tokens=3500, temperature=0.15)
        txt=resp['choices'][0]['message']['content'].strip()
        m=re.search(r'\[.*\]', txt, re.S)
        arr=json.loads(m.group(0) if m else txt)
        mp={x['id']:x for x in arr}
        for c in batch:
            q=mp.get(c['episode_id'], {'score':0,'tier':'skip','reason':'not returned by model'})
            c.update({'semantic_score':int(q.get('score',0)), 'semantic_tier':q.get('tier','skip'), 'reason':q.get('reason','')})
            out.append(c)
        time.sleep(0.4)
    return out


def run(days=7, max_queries=45, max_feeds_per_query=8, max_candidates=120):
    created = dt.datetime.now(dt.timezone.utc).isoformat()
    run_id = hashlib.sha256(created.encode()).hexdigest()[:12]
    semantic, usage = generate_semantic_queries()
    queries=[]
    # People name queries plus generated queries
    for p in semantic.get('people', [])[:35]:
        name=p.get('name') if isinstance(p, dict) else str(p)
        if name: queries.append(f'{name} podcast')
    queries += semantic.get('search_queries', [])
    # Dedupe preserving order
    seen=set(); queries=[q for q in queries if not (q.lower() in seen or seen.add(q.lower()))][:max_queries]

    con, dcon = init_dbs()
    now=dt.datetime.now(dt.timezone.utc); cutoff=now-dt.timedelta(days=days)
    feeds={}
    for q in queries:
        for res in itunes_search(q, limit=max_feeds_per_query):
            feed=res.get('feedUrl')
            if not feed: continue
            feeds.setdefault(feed, {'queries':set(), 'res':res})['queries'].add(q)
        time.sleep(0.08)
    candidates=[]
    for feed, meta in feeds.items():
        res=meta['res']
        query='; '.join(sorted(list(meta['queries']))[:3])
        dcon.execute('insert or ignore into discovered_feeds values(?,?,?,?,?,?,?)', (run_id, query, res.get('collectionName'), res.get('artistName'), feed, res.get('trackViewUrl'), res.get('primaryGenreName')))
        try:
            fp=feedparser.parse(feed)
            for e in fp.entries[:15]:
                pub=parse_date(e)
                if pub and pub < cutoff: continue
                title=clean(e.get('title'))
                summary=clean(e.get('summary') or e.get('description'))[:4000]
                show=res.get('collectionName') or fp.feed.get('title') or ''
                link=e.get('link') or ''
                audio=get_audio(e)
                guid=e.get('id') or link or audio or title
                eid=hashlib.sha256((feed+'|'+guid).encode()).hexdigest()[:24]
                pre=keyword_prefilter(title, summary, show, query)
                if pre < 8: continue
                candidates.append({'episode_id':eid,'query':query,'show_name':show,'title':title,'published':pub.isoformat() if pub else '', 'link':link,'audio_url':audio,'feed_url':feed,'summary':summary,'prefilter':pre})
        except Exception:
            continue
    # dedupe by episode_id, keep best prefilter
    by={}
    for c in candidates:
        if c['episode_id'] not in by or c['prefilter'] > by[c['episode_id']]['prefilter']:
            by[c['episode_id']]=c
    candidates=sorted(by.values(), key=lambda c:c['prefilter'], reverse=True)[:max_candidates]
    scored=qwen_filter_candidates(candidates)
    kept=0
    for c in scored:
        dcon.execute('insert or replace into discovered_episodes values(?,?,?,?,?,?,?,?,?,?,?,?)', (
            run_id,c['episode_id'],c['query'],c['show_name'],c['title'],c['published'],c['link'],c['feed_url'],c['summary'],c['semantic_score'],c['semantic_tier'],c['reason']))
        should_insert = (
            c['semantic_tier'] in ('must_listen','transcript') and c['semantic_score'] >= 75
        ) or (
            c['semantic_tier'] == 'interesting' and c['semantic_score'] >= 75
        )
        if should_insert:
            label={'interesting':'skim_if_interested','transcript':'digest_only','must_listen':'must_listen'}.get(c['semantic_tier'],'skim_if_interested')
            con.execute('insert or replace into episodes values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (
                c['episode_id'], c['show_name'], c['show_name'], 'ring3_semantic_discovery', 'semantic', c['title'], c['link'], c['audio_url'],
                c['published'], c['summary'], '', c['feed_url'], now.isoformat(), c['semantic_score'], label,
                json.dumps(['semantic discovery: '+c['query'], c['reason']], ensure_ascii=False)))
            kept += 1
    usage_all={'query_generation':usage,'model':MODEL}
    dcon.execute('insert or replace into discovery_runs values(?,?,?,?,?,?,?)', (run_id, created, days, len(queries), len(feeds), len(scored), json.dumps(usage_all,ensure_ascii=False)))
    con.commit(); dcon.commit(); con.close(); dcon.close()
    report={
        'run_id':run_id,'created_at':created,'days':days,'semantic_queries_run':len(queries),'feeds_found':len(feeds),
        'candidate_episodes_scored':len(scored),'episodes_inserted_for_briefing':kept,
        'generated_people': semantic.get('people', [])[:50],
        'generated_topics': semantic.get('topics', [])[:50],
        'queries': queries,
        'top': sorted([{k:c[k] for k in ['semantic_score','semantic_tier','show_name','title','published','link','reason'] if k in c} for c in scored], key=lambda x:x['semantic_score'], reverse=True)[:25]
    }
    out=OUT/f'{created[:10]}_{created[11:16].replace(":","")}-semantic-discovery.json'
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(report,indent=2,ensure_ascii=False))
    print('OUT='+str(out))

if __name__ == '__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=7)
    ap.add_argument('--max-queries', type=int, default=45)
    ap.add_argument('--max-feeds-per-query', type=int, default=8)
    ap.add_argument('--max-candidates', type=int, default=120)
    args=ap.parse_args()
    run(args.days,args.max_queries,args.max_feeds_per_query,args.max_candidates)
