"""Stable authority rules for official pages and archived material."""
def authority(url):
    u = url.lower()
    if any((x in u for x in ['info.', '/calculators/', '/learn/', '/blog/', '/hubfs/'])):
        return -3
    if '/newsroom/' in u:
        return -1
    if '/rates' in u or 'business-rates' in u:
        return 5
    if '/resources/' in u:
        return -2
    if '/personal/' in u or '/business/' in u or '/about/' in u or '/online-and-mobile-banking/' in u:
        return 4
    return 2
