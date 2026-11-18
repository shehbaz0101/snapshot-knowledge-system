'Question routing, rate selection, composition and abstention.'
import re
from datetime import datetime
from contract import Answer, Source
from .text import norm, words, clean
from .authority import authority
from .tables import year_range, amount_range
from .retrieval import passage_answer, link_answer, product_links
from .query import parse

class AnswerMixin:

    def source(self, v, url, quote):
        """Source."""
        return Source(url, v['snap'].snapshot_id, quote[:500])

    def result(self, v, text, url, quote=None):
        """Result."""
        return Answer(text, [self.source(v, url, quote or text)], True, 'Uses the selected snapshot and authoritative product or rate information.')

    def refuse(self):
        """Refuse."""
        return Answer("I don't know; this information isn't listed. Please contact Dupaco.", confident=False)

    def answer(self, question, as_of=None):
        """Select a snapshot, then answer only from grounded evidence."""
        if not self.versions:
            return self.refuse()
        q, as_of, rate, category = parse(question, as_of)
        v = self.select(as_of)
        if re.search(r'\b(url|link|website)\b', q) or re.search('how.*(?:join|apply).*online', q):
            return link_answer(self, v, q)
        if rate and category:
            return self.rate_answer(v, q, category)
        if re.search(r'\brouting\b|\baba\b|\btransit number\b', q):
            for p in sorted(v['snap'].pages, key=lambda p: (-authority(p.url), p.url)):
                for txt in re.split(r'\n\s*\n', p.markdown):
                    m = re.search(r'routing number[^\d\n]{0,30}(\d{9})', clean(txt), re.I)
                    if m:
                        return self.result(v, f"Dupaco's routing number is {m[1]}.", p.url, clean(txt))
        if 'branch' in q and ('address' in q or 'hours' in q or 'lobby' in q):
            name = re.search(r'(?:the|for|at) ([a-z -]+?) branch\b', q) or re.search(r'^([a-z -]+?) branch\b', q)
            if name:
                entity = name[1].strip().split(' the ')[-1]
                locator = next((p for p in v['snap'].pages if p.url.endswith('/contact')), None)
                if locator and entity not in norm(locator.markdown):
                    return self.refuse()
                if locator and 'address' in q:
                    blocks = re.split('(?m)^### ', locator.markdown)
                    block = next((b for b in blocks if entity in norm(b)), None)
                    if block:
                        address = next((l.strip() for l in block.splitlines() if re.match(r'\d+ .*,.*\d{5}',
                            l.strip())), None)
                        if address:
                            return self.result(v, address, locator.url, block)
        if re.search('how many.*branch|number of.*branch', q):
            counts = []
            for p in v['snap'].pages:
                if '/newsroom/' in p.url or '/about' in p.url:
                    for m in re.finditer(r'(\d+) branch office locations', p.markdown):
                        counts.append((m[1], p, m[0]))
            if counts:

                def published(item):
                    m = re.search(r'([A-Z][a-z]+ \d{1,2}, 20\d\d)', item[1].markdown[:400])
                    try:
                        return datetime.strptime(m[1], '%B %d, %Y') if m else datetime.min
                    except ValueError:
                        return datetime.min
                winner, p, quote = max(counts, key=published)
                return self.result(v, quote + '.', p.url, quote)
        if ('lobby' in q or re.search('drive.up', q)) and 'branch' not in q.replace('branches',
            '') or 'general lobby' in q or 'all dupaco branches' in q:
            blocks = []
            marker = 'lobby' if 'lobby' in q else 'drive-up'
            for p in v['snap'].pages:
                for m in re.finditer(r'(?im)^\*\*' + marker + r'\*\*([^#]+?)(?=\n\n\*\*|\Z)', p.markdown):
                    txt = clean(m[0])
                    if len(txt) < 600 and re.search(r'\d', txt):
                        blocks.append((p, txt))
            if blocks:
                blocks.sort(key=lambda item: (-authority(item[0].url), len(item[0].url), item[0].url, item[1]))
                p, txt = blocks[0]
                alternatives = list(dict.fromkeys((text for _, text in blocks)))
                if len(alternatives) > 1:
                    txt = ' '.join(alternatives[:3])
                txt += ' Hours vary by branch. Which branch do you need?'
                ans = self.result(v, txt, p.url, txt)
                contact = next((p for p in v['snap'].pages if p.url.endswith('/contact')), None)
                if contact:
                    ans.sources.append(self.source(v, contact.url, 'Find a Location Near You'))
                return ans
        return passage_answer(self, v, q, question)

    def rate_answer(self, v, q, cat):
        """Filter structured rows by product, term and tier before composition."""
        rows = []
        for r in v['rows']:
            blob = norm(r['section'] + ' ' + r['label'])
            label = norm(r['cells'][0])
            hs = ' '.join(r['headers']).lower()
            good = False
            if cat == 'certificate':
                good = ('certificate' in blob or (r['section'] == 'Regular' and r['headers'][0] == 'Term')) and 'ira' not in blob and ('roth' not in label) and ('traditional' not in label) and ('dividend' in hs)
            elif cat == 'auto':
                good = 'model year' in blob and ('auto' in norm(r['section']) or 'motorcycle' in norm(r['section']))
            elif cat == 'heloc':
                good = 'heloc' in norm(r['section'] + ' ' + r['label'])
            elif cat == 'equity':
                good = 'home equity loan' in norm(r['section'])
            elif cat == 'boat':
                good = 'boat' in norm(r['section']) or 'rv' in norm(r['section'])
            elif cat == 'atv':
                good = 'atv' in norm(r['section']) or 'snowmobile' in norm(r['section'])
            elif cat == 'mortgage':
                good = ('fixed' in label or 'arm' in label) and 'rate' in hs
            elif cat == 'personal':
                good = 'personal loan' in blob
            elif cat == 'card':
                good = 'visa' in blob and ('apr' in hs or 'rate' in hs)
            else:
                good = (cat in blob or (cat == 'money market' and "investor's choice" in blob)) and 'dividend' in hs
            if good and cat not in ['card', 'certificate', 'auto', 'mortgage',
                'personal', 'heloc', 'equity', 'boat', 'atv']:
                good = ('business' in blob) == ('business' in q)
            if good:
                rows.append(r)
        primary = [r for r in rows if r['url'].rstrip('/').endswith('/rates') or r['url'].endswith('/business-rates')]
        if primary:
            if cat == 'card':
                business = [r for r in rows if 'business' in norm(r['section'] + ' ' + r['cells'][0])]
                rows = primary + [r for r in business if not any(('business' in norm(x['section'] + ' ' + x['cells'][0]) for x in primary))]
            else:
                rows = primary
        if cat == 'mortgage':
            if 'construction' in q:
                rows = [r for r in rows if 'construction' in norm(r['cells'][0])]
            if 'jumbo' in q:
                rows = [r for r in rows if 'jumbo' in norm(r['cells'][0])]
            arm = re.search(r'\d+/\d+', q)
            if arm:
                rows = [r for r in rows if arm[0] in r['cells'][0]]
            if not rows:
                return self.refuse()
        term = re.search(r'(\d+)\s*[- ]?\s*(month|year)', q)
        if term:
            num = term[1]
            unit = term[2]
            if unit == 'year' and cat in ['certificate', 'auto', 'personal', 'boat', 'atv', 'equity']:
                num = str(int(num) * 12)
                unit = 'month'
            rows = [r for r in rows if re.search(r'\b' + num + r'\s*[- ]?\s*' + ('(?:month|mo)' if unit == 'month' else unit),
                norm(' '.join(r['cells'][:2])))]
        if cat == 'certificate':
            if term or 'jumbo' in q:
                rows = [r for r in rows if ('jumbo' in norm(r['cells'][0])) == ('jumbo' in q)]
            if 'ira' in q:
                rows = [r for r in v['rows'] if ('roth' if 'roth' in q else 'traditional') in norm(r['cells'][0]) and (not term or re.search(r'\b' + term[1] + r'\s*month',
                    norm(r['cells'][0]))) and (('jumbo' in norm(r['cells'][0])) == ('jumbo' in q))]
        if cat in ['auto', 'atv']:
            year = re.search(r'\b(19\d\d|20\d\d)\b', q)
            if year:

                def fits(r):
                    bounds = year_range(r['cells'][0])
                    return bounds is not None and bounds[0] <= int(year[1]) <= bounds[1]
                rows = [r for r in rows if fits(r)]
            elif rows:
                newest = max((r['cells'][0] for r in rows))
                rows = [r for r in rows if r['cells'][0] == newest]
        if cat == 'mortgage':
            rows = [r for r in rows if ('refinance' in norm(r['cells'][0])) == ('refinanc' in q)]
            if not term:
                rows = [r for r in rows if '30-year' in norm(r['cells'][0])]
        if cat == 'card':
            if 'business' in q:
                rows = [r for r in rows if 'business' in norm(r['section'] + ' ' + r['cells'][0])]
            if 'platinum' in q:
                rows = [r for r in rows if 'platinum' in norm(r['section'] + ' ' + r['cells'][0]) and ('business' in norm(r['section'] + ' ' + r['cells'][0])) == ('business' in q)]
            elif 'rewards' in q:
                rows = [r for r in rows if 'rewards' in norm(r['section'] + ' ' + r['cells'][0]) and ('business' in norm(r['section'] + ' ' + r['cells'][0])) == ('business' in q)]
            if not re.search('intro|transfer', q):
                rows = [r for r in rows if not re.search('intro|transfer', norm(r['cells'][0]))]
            else:
                rows = [r for r in rows if re.search('intro|transfer', norm(r['cells'][0]))]
        amounts = re.findall(r'\$\s*([\d,]+(?:\.\d+)?)', q)
        if amounts and cat not in ['certificate', 'card', 'auto']:
            amt = float(amounts[0].replace(',', ''))

            def balance(r):
                bounds = amount_range(' '.join(r['cells'][:2]))
                if not bounds:
                    return cat in ['heloc', 'equity', 'atv']
                if cat == 'mortgage':
                    return amt <= bounds[0]
                return bounds[0] <= amt <= bounds[1]
            rows = [r for r in rows if balance(r)]
            if cat == 'mortgage' and rows:
                least = min((float(re.search(r'\$([\d,]+)', r['cells'][0])[1].replace(',', '')) for r in rows))
                rows = [r for r in rows if float(re.search(r'\$([\d,]+)', r['cells'][0])[1].replace(',',
                    '')) == least]
        if ('highest' in q or 'top' in q or 'any' in q) and cat not in ['card', 'mortgage', 'certificate']:
            if rows:
                rows = [max(rows, key=lambda r: max(float(value) for cell in r['cells'] for value in re.findall(r'(\d+(?:\.\d+)?)%',
                    cell)))]
        if not rows:
            need = words(q) - {'apy', 'apr', 'rate', 'share', 'jumbo'}
            found = []
            for url, txt, ws, _ in v['passages']:
                if need <= ws and '%' in txt and (authority(url) > 0) and ('jumbo' not in q) and not re.search(r'example|illustrat|if you borrow',
                    txt, re.I):
                    found.append((authority(url), url, txt))
            if found:
                _, url, txt = max(found)
                return self.result(v, txt, url)
            return self.refuse()
        if cat == 'mortgage':
            rows.sort(key=lambda row: (amount_range(row['cells'][0]) or (float('inf'),))[0])
        unique = {}
        for r in sorted(rows, key=lambda r: (-authority(r['url']), len(r['url']), r['url'])):
            key = (norm(r['cells'][0]), tuple((norm(c) for c in r['cells'][1:] if '%' not in c)))
            unique.setdefault(key, r)
        rows = list(unique.values())
        if (term or amounts) and cat not in ['card', 'mortgage']:
            rows = rows[:1]
        out = []
        src = []
        for r in rows:
            metric = 'APY'
            idx = None
            if cat in ['auto', 'personal', 'card', 'heloc', 'equity', 'boat', 'atv']:
                metric = 'APR'
                idx = next((i for i, h in enumerate(r['headers']) if 'rate' in h.lower() or 'apr' in h.lower()),
                    None)
            elif cat == 'mortgage':
                metric = 'APR' if 'apr' in q else 'rate'
                idx = next((i for i, h in enumerate(r['headers']) if ('apr' in h.lower() if metric == 'APR' else h.lower() == 'rate')),
                    None)
            else:
                dividend = 'dividend' in q
                idx = next((i for i, h in enumerate(r['headers']) if ('dividend' in h.lower() if dividend else 'apy' in h.lower())),
                    None)
                metric = 'dividend rate' if dividend else 'APY'
            if idx is None:
                continue
            value = ' - '.join(re.findall(r'\d+(?:\.\d+)?\s*%', r['cells'][idx]))
            if not value:
                continue
            if cat == 'card' and re.search('intro|transfer', q):
                value = value.split(' - ')[0]
            label = ' '.join((c for i, c in enumerate(r['cells']) if i < idx and '%' not in c and (not re.fullmatch(r'\d+',
                c))))
            if cat == 'card' and 'visa' not in label.lower():
                label = r['section'] + ' ' + label
            elif cat not in ['card', 'auto', 'mortgage'] and (not re.search('[a-zA-Z]', r['cells'][0])):
                label = r['section'] + ' ' + label
            out.append(f'{label}: {value} {metric}.')
            src.append(self.source(v, r['url'], r['quote']))
            for target in product_links(v, r, cat):
                src.append(self.source(v, target, r['quote']))
        if not out:
            return self.refuse()
        return Answer(' '.join(dict.fromkeys(out)), list({s.url: s for s in src}.values()),
            True, 'Authoritative rate table, with term, balance and product tiers kept separate.')
