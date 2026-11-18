'Versioned snapshot storage and evidence extraction.'
import re
from collections import Counter
from .text import words, clean
from .tables import parse_tables

class StoreMixin:

    def __init__(self):
        """Initialize an empty version history."""
        self.versions = []

    def ingest(self, snapshot):
        """Index one complete crawl without mixing versions."""
        rows = []
        passages = []
        for p in snapshot.pages:
            rows.extend(parse_tables(p))
            sections = re.split('(?m)^#{2,6} ', p.markdown)
            for section in sections:
                txt = clean(section)
                if 50 < len(txt) < 1000 and '|' not in txt:
                    passages.append((p.url, txt, words(txt), words(p.title + ' ' + p.url)))
            for para in re.split(r'\n\s*\n', p.markdown):
                txt = clean(para)
                if not txt or len(txt) > 2500 or 'data:image' in txt or txt.startswith('|'):
                    continue
                passages.append((p.url, txt, words(txt), words(p.title + ' ' + p.url)))
        df = Counter((w for _, _, ws, _ in passages for w in ws))
        self.versions.append(dict(snap=snapshot, rows=rows, passages=passages, df=df))
        self.versions.sort(key=lambda x: x['snap'].taken_on)

    def select(self, as_of):
        """Select the latest eligible crawl, falling back to the earliest."""
        return next((v for v in reversed(self.versions) if not as_of or v['snap'].taken_on <= as_of),
            self.versions[0])
