"""Pure question normalization, date interpretation and product classification."""
import re
from .text import norm

MONTHS = (
    'january', 'february', 'march', 'april', 'may', 'june',
    'july', 'august', 'september', 'october', 'november', 'december',
)
MONTH_DATE = r'(?:as of|in)\s+(' + '|'.join(MONTHS) + r')\s+(20\d\d)'
ISO_DATE = r'as of\s+(\d{4}-\d\d-\d\d)'

# Product vocabulary describes families, never expected values or source URLs.
PRODUCTS = (
    (r'certificate|\bcd\b|\bira\b', 'certificate'),
    (r'heloc|home equity line', 'heloc'),
    (r'home equity', 'equity'),
    (r'boat|\brv\b|recreational', 'boat'),
    (r'\batv\b|snowmobile|jet ski', 'atv'),
    (r'auto|vehicle|motorcycle|\bcar\b', 'auto'),
    (r'mortgage|home loan|adjustable|construction|\barm\b', 'mortgage'),
    (r'personal loan', 'personal'),
    (r'credit card|platinum|rewards visa', 'card'),
    (r'bright savings', 'bright'),
    (r'high.yield', 'high-yield'),
    (r'money market|investor.s choice', 'money market'),
    (r'health savings|\bhsa\b', 'health savings'),
    (r'launchpad', 'launchpad'),
    (r'you.name.it', 'you name it'),
    (r'holiday club', 'holiday club'),
    (r'share savings|savings tier', 'share savings'),
    (r'checking', 'checking'),
)


def parse(question, as_of=None):
    """Return normalized text, selected date, rate intent and product family."""
    q = norm(question).replace('non-jumbo', 'standard').replace('non jumbo', 'standard')
    if not as_of:
        iso = re.search(ISO_DATE, q)
        month = re.search(MONTH_DATE, q)
        if iso:
            as_of = iso[1]
        elif month:
            # An end-of-month lexical boundary includes every crawl in that month.
            as_of = f'{month[2]}-{MONTHS.index(month[1]) + 1:02d}-31'
    q = re.sub(MONTH_DATE, '', q)
    q = re.sub(ISO_DATE, '', q)
    rate = bool(re.search(r'\b(rate|rates|apr|aprs|apy|apys|interest|dividend|pay|earn)\b', q))
    category = next((name for pattern, name in PRODUCTS if re.search(pattern, q)), None)
    return q, as_of, rate, category
