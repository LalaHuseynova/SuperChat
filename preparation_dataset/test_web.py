import unittest

from web import ScraperError, category, in_scope, parse_page


class ParserTests(unittest.TestCase):
    def test_free_card_preserves_fee_label_and_source(self):
        html = '''<main><h1>Debet kartlar</h1><div>
        <h2 class="styles_product-hero-info__header__x">Example card</h2>
        <div><div class="styles_tariffs__item__head__x">Pulsuz</div>
        <div class="styles_tariffs__item__desc__x">Kartın qiyməti</div></div>
        <a href="https://cards.birbank.az/az/EXAMPLE/">Sifariş et</a>
        </div></main>'''
        page, rows = parse_page(html, 'https://birbank.az/debet-kartlar', 'test')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['record_type'], 'catalog_listing')
        self.assertIn('Pulsuz Kartın qiyməti', rows[0]['price_rate_mentions'][0])
        self.assertEqual(page['attributes'][0], {'label': 'Kartın qiyməti', 'value': 'Pulsuz'})

    def test_terms_retained_but_calculator_example_removed(self):
        html = '''<main><nav><span class="styles_breadcrumbs-text__x">Depozit</span></nav>
        <h1>Yüksək gəlirli depozit imkanı</h1><p>İllik faiz 10%, minimum 500 AZN.</p>
        <div class="styles_calculator__x">999999 AZN example</div></main>'''
        page, rows = parse_page(html, 'https://birbank.az/deposits', 'test')
        self.assertEqual(rows[0]['name'], 'Depozit')
        self.assertNotIn('999999', page['text'])
        self.assertIn('minimum 500 AZN', rows[0]['price_rate_mentions'][0])

    def test_insurance_is_not_misclassified_as_a_loan(self):
        self.assertEqual(category('https://birbank.az/sigortalar/kredit-heyat-sigortasi'), 'insurance')

    def test_scope_excludes_orders_and_unrelated_pages(self):
        self.assertFalse(in_scope('https://ccl.birbank.az/az/order/GTKR'))
        self.assertFalse(in_scope('https://birbank.az/news'))
        self.assertFalse(in_scope('https://birbank.az.evil.example/cards/test'))
        self.assertTrue(in_scope('https://birbank.az/kreditler/emanet-teminatli-kredit'))

    def test_block_page_is_not_a_product(self):
        with self.assertRaises(ScraperError):
            parse_page('<html>Access denied</html>', 'https://birbank.az/deposits', 'test')

    def test_private_layout_and_embedded_tab_data(self):
        html = '''<html><div class="styles_private-bank__x"><h1>Private</h1>
        <p>İndividual kreditlər: 10.9%-dən, 50000 AZN-dək</p></div>
        <script id="__NEXT_DATA__" type="application/json">
        {"props":{"pageProps":{"tabs":[{"title":"Rates","value":"10.9%"}]}}}
        </script></html>'''
        page, rows = parse_page(html, 'https://birbank.az/birbank-private', 'test')
        self.assertEqual(len(rows), 1)
        self.assertEqual(page['embedded_page_data']['tabs'][0]['value'], '10.9%')


if __name__ == '__main__':
    unittest.main()
