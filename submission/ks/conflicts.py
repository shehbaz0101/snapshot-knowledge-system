'Detect contradictions between matching facts with provenance.'
import re
from collections import defaultdict
from contract import Conflict
from .text import norm
from .authority import authority

class ConflictsMixin:

    def conflicts(self):
        """Compare stable row identities, retaining authority and snapshot provenance."""
        history = defaultdict(list)

        def identity(r, i):
            h = norm(r['headers'][i])
            section = norm(r['section'])
            if 'apy' in h or 'yield' in h:
                metric = 'APY'
            elif 'apr' in h or 'annual percentage rate' in h:
                metric = 'APR'
            elif 'dividend' in h:
                metric = 'dividend rate'
            elif h.strip() == 'rate':
                metric = 'rate'
            else:
                return None
            first_metric = next((j for j, h in enumerate(r['headers']) if re.search('apr|apy|rate|yield',
                h, re.I)), i)
            labels = r['cells'][:first_metric]
            label = norm(' | '.join(labels))
            label = re.sub(r'(?<=\d),(?=\d)', '', label)
            label = re.sub(r'(?<=\d)\.00\b', '', label)
            label = re.sub(r'\s+', ' ', label.replace('\xa0', ' '))
            label = re.sub(r'\s*-\s*', '-', label)
            section = re.sub(r'\baccounts?\b', '', section).strip()
            section = section.replace('certificates', 'certificate')
            if not any((x in label for x in ['savings', 'checking', 'certificate',
                'visa', 'roth', 'traditional', 'purchase:', 'refinance:', 'model year'])):
                if section == 'regular' and r['headers'][0] == 'Term':
                    section = 'regular certificate'
                label = section + ' | ' + label
            if 'model year' in label and ('auto' in section or 'motorcycle' in section):
                m = re.search(r'(20\d\d)', label)
                if m:
                    year = int(m[1])
                    ordered = auto_years.get(r['url'], [year])
                    rank = ordered.index(year) if year in ordered else 0
                    tier = ['newest', 'recent', 'older', 'oldest'][min(rank, 3)]
                    label = 'auto ' + tier + ' model year | ' + r['cells'][1].lower()
            label = label.replace('months', 'month')
            return (label, metric)
        for v in self.versions:
            auto_years = defaultdict(set)
            for r in v['rows']:
                if re.search('auto|motorcycle', norm(r['section'])) and 'model year' in norm(r['cells'][0]):
                    m = re.search(r'20\d\d', r['cells'][0])
                    if m:
                        auto_years[r['url']].add(int(m[0]))
            auto_years = {url: sorted(years, reverse=True) for url, years in auto_years.items()}
            records = defaultdict(list)
            for r in v['rows']:
                if authority(r['url']) < 4:
                    continue
                if re.search('introductory|balance transfer', norm(r['cells'][0])):
                    continue
                for i, h in enumerate(r['headers']):
                    key = identity(r, i)
                    if key is None:
                        continue
                    vals = re.findall(r'\d+(?:\.\d+)?\s*%', r['cells'][i])
                    if not vals:
                        continue
                    value = ' - '.join((x.replace(' ', '') for x in vals))
                    records[key].append((v, r, value))
            for key, items in records.items():
                items.sort(key=lambda t: (-authority(t[1]['url']), len(t[1]['url']), t[1]['url']))
                best = items[0]
                history[key].extend(items[1:] + [best])
            for url, txt, _, _ in v['passages']:
                if authority(url) < 2:
                    continue
                m = re.fullmatch(r'([^:\n]+):\s*(\d+(?:\.\d+)?%)', txt)
                if m:
                    history[norm(m[1]), ''].append((v, dict(url=url, quote=txt), m[2]))
        result = []
        for key, items in sorted(history.items()):
            vals = list(dict.fromkeys((x[2] for x in items)))
            if len(vals) < 2:
                continue
            v, r, winner = items[-1]
            if v is not self.versions[-1]:
                continue
            sources = []
            seen = set()
            for a, b, value in items:
                marker = (a['snap'].snapshot_id, value)
                if marker not in seen:
                    sources.append(self.source(a, b['url'], b['quote']))
                    seen.add(marker)
            result.append(Conflict(' '.join(key), vals, sources, winner, 'Latest authoritative rate sheet wins over earlier snapshots and embedded tables. Product, term, balance tier and metric are matched separately.'))
        latest = self.versions[-1]
        branches = []
        for p in latest['snap'].pages:
            if '/newsroom/' not in p.url:
                continue
            for m in re.finditer(r'(\d+) branch office locations', p.markdown):
                branches.append((m[1], p, m[0]))
        if len(set((x[0] for x in branches))) > 1:
            answer = self.answer('How many branches does Dupaco have?')
            result.append(Conflict('branch count office locations', sorted(set((x[0] for x in branches))),
                [self.source(latest, p, t) for _, p, t in branches], re.search(r'\d+', answer.text)[0],
                'Newest dated branch-count statement supersedes historical newsroom boilerplates.'))
        return result
