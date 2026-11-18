"""Synthetic tests of range semantics and historical evidence isolation."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'submission'))
from solution import build
from contract import Page, Snapshot
from ks.tables import amount_range, year_range


def page(url, value):
    return Page(url, 'Certificates', '# Certificates\n\n| Certificate | Dividend Rate | APY |\n| --- | --- | --- |\n| 8 Month | 1.00% | '+value+' |', '')


class TierTests(unittest.TestCase):
    def test_year_ranges(self):
        for label, expected in [
            ('2024-27 Model Year', (2024, 2027)),
            ('2021-23', (2021, 2023)),
            ('Model Year 2026-23', (2023, 2026)),
            ('2016 Model Year (and older)', (0, 2016)),
            ('1998-2003', (1998, 2003)),
            ('2020', (2020, 2020)),
        ]:
            with self.subTest(label=label):
                self.assertEqual(year_range(label), expected)
        self.assertIsNone(year_range('60 Months'))

    def test_amount_ranges(self):
        for label, expected in [
            ('$25,000+', (25000, float('inf'))),
            ('$10,000 - $24,999.99', (10000, 24999.99)),
            ('$10,000-24,999', (10000, 24999)),
            ('$0.01 - $4,999.99', (.01, 4999.99)),
            ('$0 - $99.99', (0, 99.99)),
        ]:
            with self.subTest(label=label):
                self.assertEqual(amount_range(label), expected)
        self.assertIsNone(amount_range('2024-27'))


class VersionTests(unittest.TestCase):
    def setUp(self):
        self.system = build()
        # Reverse ingestion and page order must not change temporal or authority rules.
        for date, value in [('2026-08-01', '4.80%'), ('2026-02-01', '3.20%')]:
            self.system.ingest(Snapshot(date, date, [
                page('https://cu.test/personal/certificates', '1.90%'),
                page('https://cu.test/rates', value),
                page('https://cu.test/rates/duplicate', '1.80%'),
            ]))

    def test_as_of_selects_single_authoritative_value(self):
        answer = self.system.answer('What is the 8-month certificate APY?', '2026-03-01')
        self.assertEqual(answer.text.count('%'), 1)
        self.assertIn('3.20%', answer.text)
        self.assertEqual(answer.sources[0].snapshot_id, '2026-02-01')
        self.assertEqual(answer.sources[0].url, 'https://cu.test/rates')

    def test_current_and_before_first(self):
        self.assertIn('4.80%', self.system.answer('8 month certificate APY').text)
        self.assertIn('3.20%', self.system.answer('8 month certificate APY', '2020-01-01').text)
        self.assertEqual(len(self.system.select('2026-03-01')['snap'].pages), 3)

    def test_unknown_term_does_not_use_payment_example(self):
        self.system.ingest(Snapshot('last', '2026-09-01', [Page(
            'https://cu.test/personal/loans/personal-loans', 'Personal Loans',
            'Personal Loan payment example: If you borrow $7,000 at 11.00% APR with a 97 month term.', '')]))
        answer = self.system.answer('What is the 97-month personal loan APR?')
        self.assertFalse(answer.confident)
        self.assertNotRegex(answer.text, r'\d')


if __name__ == '__main__':
    unittest.main()
