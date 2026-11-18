"""Manually checked expectations from the supplied rate sheets, no live data."""
import json
from pathlib import Path
rows=[
('What APY does the standard 17 month certificate offer in June?', '2026-06-30', ['3.85%'], ['4.10%'], 'temporal_as_of','june-standard'),
('As of June 2026, what is the seventeen-month non-jumbo certificate APY?', '2026-06-30', ['3.85%'], ['4.10%'], 'temporal_as_of','june-standard'),
('What was the 17-month jumbo certificate APY in August 2026?', '2026-08-31', ['4.05%'], ['4.20%'], 'temporal_as_of',None),
('What is the current APY for a ten month jumbo certificate?', None, ['4.00%'], ['3.90%'], 'stale_trap','ten-jumbo'),
('How much APY does the 10-month jumbo certificate pay now?', None, ['4.00%'], ['3.90%'], 'stale_trap','ten-jumbo'),
('What dividend rate does the 17-month standard certificate pay?', None, ['4.06%'], ['4.10%','4.15%'], 'tier_disambiguation',None),
('What was the 12 month certificate APY before the first crawl?', '2026-01-01', ['2.90%'], ['3.40%'], 'temporal_as_of',None),
('What is the current twelve month certificate APY?', None, ['3.40%'], ['2.90%'], 'current_value',None),
('What is the 48-month auto APR on a 2025 vehicle?', None, ['5.19%'], ['4.99%','5.34%'], 'tier_disambiguation',None),
('What was the 60-month auto APR for a 2025 vehicle in the first May crawl?', '2026-05-12', ['5.19%'], ['5.39%'], 'temporal_as_of',None),
('For a 2022 vehicle, what is the 72-month auto loan APR?', None, ['5.79%'], ['5.49%'], 'tier_disambiguation',None),
('What APY does Share Savings pay on $3,000?', None, ['0.10%'], ['0.15%','0.20%'], 'tier_disambiguation',None),
('What dividend rate does Bright Savings pay?', None, ['2.23%'], ['2.25%'], 'tier_disambiguation',None),
('What is the High-Yield Savings APY on $600,000?', None, ['2.25%'], ['2.45%','2.05%'], 'tier_disambiguation',None),
("What is Investor's Choice money market APY on $30,000?", None, ['0.35%'], ['0.40%','0.30%'], 'tier_disambiguation',None),
('What is the personal Platinum Visa standard purchase APR?', None, ['12.50%','19.50%'], ['2.90%','9.90%'], 'tier_disambiguation',None),
('What is the Business Rewards Visa APR?', None, ['20.50%'], ['15.50%'], 'tier_disambiguation',None),
('What is the 99-month certificate APY?', None, [], [], 'should_refuse',None),
('What is the interest rate for a construction mortgage?', None, [], [], 'should_refuse',None),
('What are the lobby hours for the Atlantis branch?', None, [], [], 'should_refuse',None),
('What APR applies to financing a 2014 motorcycle over 48 months?', None, ['8.59%'], ['5.19%'], 'tier_disambiguation','older-vehicle'),
('For a 2012 used car, what interest rate applies over 48 months?', None, ['8.59%'], ['5.19%'], 'tier_disambiguation','older-vehicle'),
('What APR is available for a 2023 snowmobile for 36 months?', None, ['8.34%'], ['8.54%','8.89%'], 'tier_disambiguation',None),
('Please quote the 60-month APR for a 2019 jet ski.', None, ['8.94%'], ['8.34%','8.89%'], 'tier_disambiguation',None),
('What interest rate applies to a 2021 ATV over 48 months?', None, ['8.54%'], ['8.34%'], 'tier_disambiguation',None),
('For a $32,000 RV purchase over 96 months, what APR is listed?', None, ['8.59%'], ['8.34%'], 'tier_disambiguation',None),
('What APR applies to a $52,000 recreational loan over 120 months?', None, ['9.34%'], ['9.59%'], 'tier_disambiguation',None),
('Can you quote the APR for a $18,000 boat over 48 months?', None, ['7.59%'], ['7.29%','7.89%'], 'tier_disambiguation',None),
('What APR applies to the home equity line of credit?', None, ['6.25%'], ['12.50%'], 'current_value','equity-line'),
('Please tell me the standard HELOC interest rate.', None, ['6.25%'], ['12.50%'], 'current_value','equity-line'),
('How much APY does You Name It Savings earn on $18,000?', None, ['0.15%'], ['0.20%'], 'tier_disambiguation',None),
('On a $50 balance in Holiday Club, what APY is offered?', None, ['0.20%'], ['0.00%'], 'tier_disambiguation',None),
('What APY does Launchpad Savings pay on $750?', None, ['3.25%'], ['3.21%'], 'tier_disambiguation',None),
('What is the dividend rate for a $1,200,000 High-Yield Savings balance?', None, ['2.42%'], ['2.45%'], 'tier_disambiguation',None),
('What was the APY on the regular 24 month certificate as of June 2026?', '2026-06-30', ['2.50%'], [], 'temporal_as_of',None),

]
items=[]
for i,(q,date,must,trap,cat,group) in enumerate(rows,1):
 items.append(dict(id=f'own-{i:03}',question=q,as_of=date,expected_answer='; '.join(must) if must else 'Not listed. Please contact Dupaco.',must_include=must,must_not_include=trap,category=cat,group=group,weight=1.0))
Path(__file__).with_name('questions.jsonl').write_text('\n'.join(json.dumps(x) for x in items)+'\n')
