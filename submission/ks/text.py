"""Text normalization shared by extraction and retrieval."""
import re
from functools import lru_cache
STOP = set("""a an the of on for to do does your our i me can you tell please current
now dupaco s are and in with it how at as was be have get is what has from become
would like know could give repeat my all still today much m going any received""".split())

NUMBER_WORDS = dict(zip(
    'zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen'.split(),
            map(str, range(20))))
NUMBER_WORDS.update(dict(zip(
    'twenty thirty forty fifty sixty seventy eighty ninety'.split(),
    map(str, range(20, 100, 10)))))

@lru_cache(maxsize=100000)
def norm(s):
    s = s.lower().replace('–', '-').replace('—', '-').replace('’', "'")
    for word, number in NUMBER_WORDS.items():
        s = re.sub(r'\b' + word + r'\b', number, s)
    s = re.sub(r'\b([2-9]0)[ -]([1-9])\b', lambda m: str(int(m[1]) + int(m[2])), s)
    return s

def words(s):
    s = norm(s)
    s = re.sub(r'\b(recognition|recognized|recognizing)\b', 'recognize', s)
    s = re.sub(r'\b(cds?|certificates?)\b', 'certificate', s)
    s = re.sub(r'\b(branches)\b', 'branch', s)
    s = re.sub(r'\b(rates|aprs|apys)\b', 'rate', s)
    return set(re.findall('[a-z0-9]+', s)) - STOP

def clean(s):
    s = re.sub(r'!\[[^\]]*\]\([^\n]*?\)', '', s)
    s = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', s)
    return re.sub('[*_#]', '', s).strip()
