"""Parse inclusive numeric tiers without confusing amounts with terms or years."""
import re
from .text import norm, clean


def year_range(label):
    """Return inclusive bounds, including shortened and descending year ranges."""
    text = norm(label)
    match = re.search(r'\b((?:19|20)\d{2})(?:\s*-\s*(\d{2,4}))?', text)
    if not match:
        return None
    first = int(match[1])
    last = int(match[2]) if match[2] else first
    if last < 100:
        last += first // 100 * 100
    if 'older' in text or 'earlier' in text:
        return (0, first)
    return min(first, last), max(first, last)


def amount_range(label):
    """Parse currency ranges, optional second dollar signs and open upper tiers."""
    text = norm(label).replace(',', '')
    match = re.search(r'\$\s*(\d+(?:\.\d+)?)(?:\s*(?:-|to)\s*\$?\s*(\d+(?:\.\d+)?))?', text)
    if not match:
        return None
    low = float(match[1])
    if match[2]:
        return low, float(match[2])
    if re.search(r'\+|and (?:up|over)|or more', text[match.end():]):
        return low, float('inf')
    return low, low


def parse_tables(p):
    """Extract rows while preserving headers, local headings and source quotes."""
    rows = []
    lines = p.markdown.splitlines()
    context = []
    headers = None
    for line in lines:
        t = line.strip()
        if t.startswith('|'):
            cells = [clean(c) for c in t.strip('|').split('|')]
            if all((re.fullmatch('[: -]*', c) for c in cells)):
                continue
            if not headers:
                headers = cells
                continue
            if len(cells) != len(headers):
                continue
            label = ' '.join((c for h, c in zip(headers, cells) if not re.search(r'%|\bAPR\b|\bAPY\b', c)))
            ctx = ' '.join(context[-3:])
            rows.append(dict(headers=headers[:], cells=cells, label=label, context=ctx,
                section=context[-1] if context else p.title, url=p.url, quote=t))
        else:
            headers = None
            if t and (not clean(t).startswith('Rates are')) and (len(t) < 100) and (not any((c in t for c in ['[',
                '\\', '%']))) and (not t.startswith(('Rates are', '1', '2', '!'))):
                context.append(clean(t))
    return rows
