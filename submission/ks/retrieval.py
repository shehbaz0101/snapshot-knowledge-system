"""Deterministic BM25 evidence ranking with generic answer-shape features."""
import math
import re
from datetime import datetime
from .text import norm, words, clean
from .authority import authority

SYNONYMS = {
    'member': {'membership'},
    'join': {'membership', 'member', 'open', 'become'},
    'wallet': {'mobile', 'payments'},
    'eligible': {'eligibility', 'membership', 'qualify', 'join'},
    'recognition': {'recognized', 'honored', 'ranked'},
    'received': {'recognized'},
    'close': {'closure', 'closed'},
    'open': {'closure', 'closed'},
    'update': {'change', 'changes'},
    'student': {'education', 'college', 'university'},
    'university': {'student', 'education', 'college'},
    'flexibility': {'flexible'},
    'locator': {'location', 'locations'},
}


def expanded(query):
    """Expand common vocabulary, without inserting answer entities."""
    tokens = words(query)
    return tokens | {term for token in tokens for term in SYNONYMS.get(token, ())}


def published(page):
    """Use article publication date, rather than crawl date, for recency."""
    match = re.search(r'([A-Z][a-z]+ \d{1,2}, 20\d\d)', page.markdown[:500])
    try:
        return datetime.strptime(match[1], '%B %d, %Y').toordinal() if match else 0
    except ValueError:
        return 0


def shape(query, text):
    """Reward evidence containing a suitable shape for the requested answer."""
    q, t = norm(query), norm(text)
    score = 0
    if re.search(r'how many|number of', q):
        score += 7 if re.search(r'\b\d+\b', t) else -5
    if re.search(r'when|still open|close today', q):
        score += 8 if re.search(r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december) \d',
            t) else -3
    if 'address' in q:
        score += 7 if re.search(r'\d+ .*,.*\d{5}', t) else -4
    if 'hours' in q:
        score += 7 if re.search(r'\d.*(?:a\.m\.|p\.m\.)', t) else -4
    if re.search(r'who|eligible', q):
        score += 5 if re.search(r'live|work|qualify|eligible|membership', t) else 0
    if re.search(r'can i|what.*offer|options', q):
        score += min(4, text.count(',') + text.count('\n- '))
    return score


def ranked(v, query, entities=()):
    """BM25 over paragraphs; each paragraph also inherits page title relevance."""
    query_words = expanded(query)
    original = words(query)
    n = len(v['passages'])
    pages = {p.url: p for p in v['snap'].pages}
    results = []
    for url, text, tokens, title in v['passages']:
        overlap = query_words & tokens
        if not overlap:
            continue
        length = max(1, len(tokens))
        score = sum(math.log(1 + (n - v['df'][w] + .5) / (v['df'][w] + .5)) * 2.2 / (1 + 1.2 * (.25 + .75 * length / 65)) * (1 if w in original else .4) for w in sorted(overlap))
        score += 1.2 * len(query_words & title) + 2 * authority(url)
        sequence = re.findall(r'[a-z0-9$]+', norm(query))
        for left, right in zip(sequence, sequence[1:]):
            if left in original and right in original and left + ' ' + right in norm(text):
                score += 5
        # Rare subject terms constrain the entity, even when generic verbs match well.
        subjects = {w for w in original if v['df'][w] < max(10, n * .006)}
        score += 2 * len(subjects & tokens)
        if re.search(r'what (?:is|are)', query) and len(tokens) < 18:
            score -= 6
        if 'who' in original or 'eligible' in original:
            score += 12 * len(query_words & words(pages[url].url))
        score += shape(query, text)
        if entities and not all(entity in norm(clean(text)) for entity in entities):
            score -= 35
        # Recently published articles supersede historical articles on the same topic.
        date = published(pages[url])
        score += max(0, (date - datetime(2020, 1, 1).toordinal()) / 365) * 3 if date and '/newsroom/' in url else 0
        if len(text) > 900:
            score -= 3
        if text.rstrip().endswith('?') or text.lstrip().startswith('- Can I'):
            score -= 12
        if 'what is' in query and re.search(r'\$[\d,]+', text):
            score += 7
        if len(tokens) < 12:
            score -= 5
        if len(tokens) < 5:
            score -= 6
        results.append((score, url, text))
    return sorted(results, key=lambda item: (-item[0], item[1], item[2]))


def passage_answer(system, v, query, original=None):
    """Compose a supported evidence span, or abstain on weak lexical evidence."""
    entities = [norm(w) for w in re.findall(r'\b[A-Z][a-z]+(?:\$[a-z]+)?(?:-[A-Z][a-z]+)?',
        original or '') if w not in {'What', 'Who', 'When', 'Where', 'How', 'Can', 'Do',
        'Does', 'Is', 'Dupaco', 'I', 'Please', 'Provide', 'Get'}]
    candidates = ranked(v, query, entities)
    if not candidates or candidates[0][0] < 6:
        # Preserve last-observed non-rate facts when their page has disappeared.
        needed = words(query)
        for prior in reversed(system.versions):
            if prior['snap'].taken_on >= v['snap'].taken_on:
                continue
            for url, text, tokens, _ in prior['passages']:
                if needed <= tokens and re.search(r'\$\d', text):
                    answer = system.result(prior, text, url)
                    answer.conflict_note = 'Last observed evidence; its page is absent from the selected crawl.'
                    return answer
        return system.refuse()
    _, url, text = candidates[0]
    if re.search(r'\bwho\b', query):
        page = next(p for p in v['snap'].pages if p.url == url)
        overview = [clean(part) for part in re.split(r'\n\s*\n', page.markdown[:1800]) if len(words(clean(part))) > 8 and not part.startswith(('#',
            '!', '['))]
        text = text + '\n' + ' '.join(overview)
    return system.result(v, text[:1100], url)


def link_answer(system, v, query):
    """Rank canonical links extracted from the selected crawl, using anchor context."""
    candidates = []
    qw = expanded(query) - {'url', 'link', 'website', 'online'}
    for page in v['snap'].pages:
        if 'info.' in page.url:
            continue
        for match in re.finditer(r'\[([^\]]+)\]\((https?://[^)\s]+)\)', page.markdown):
            anchor, target = match.groups()
            if 'info.' in target or '/hubfs/' in target:
                continue
            context = page.markdown[max(0, match.start()-180):match.end()+80]
            score = 4 * len(qw & expanded(anchor)) + 2 * len(qw & expanded(target)) + len(qw & expanded(context))
            score += .3 * authority(page.url) + authority(target)
            if ('/business/' in target) != ('business' in qw):
                score -= 10
            if 'rate' in qw and '#rates' in target:
                score += 8
            if re.search(r'how.*(?:join|apply).*online', query):
                score += 5 * len(qw & expanded(anchor))
                if '/about/' in target:
                    score -= 8
            candidates.append((score, target.rstrip('/'), page.url, match[0]))
    if not candidates:
        return system.refuse()
    score, target, url, quote = sorted(candidates, key=lambda x: (-x[0], len(x[1]), x[1], x[2]))[0]
    if score < 3:
        return system.refuse()
    answer = system.result(v, target, url, quote)
    answer.sources.append(system.source(v, target, quote))
    return answer


def product_links(v, row, category):
    """Use links adjacent to a matched table, never invented URL mappings."""
    page = next((p for p in v['snap'].pages if p.url == row['url']), None)
    if not page:
        return []
    pos = page.markdown.find(row['quote'])
    tail = page.markdown[pos:]
    table_end = tail.find('\n\n')
    block = tail[table_end:table_end+6000].split('\n| ')[0]
    links = re.findall(r'\[(?:See details|[^\]]*rates[^\]]*)\]\((https?://[^)]+)\)', block, re.I)
    return [target.rstrip('/') for target in links[:1]]
