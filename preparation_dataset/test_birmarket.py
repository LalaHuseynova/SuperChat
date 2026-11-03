import json
import unittest

from birmarket_product import parse_product, discount, description_images
from birmarket_state import decode_state, StateError


def fixture():
    product = {
        'id': 123, 'name': 'İdman ayaqqabısı', 'description': 'Yüngül ayaqqabı',
        'brand': {'name': 'Example'}, 'ratings': {'rating_value': 4.5, 'session_count': 17, 'review_count': 9},
        'default_offer': {'uuid': 'offer1', 'retail_price': 66.5, 'old_price': 100, 'qty': 0},
        'custom_fields': [{'master_field_id': 1, 'values': ['Qara']},
                          {'master_field_id': 2, 'values': ['42']},
                          {'master_field_id': 3, 'values': ['30']}],
        'imgs': [{'big': 'https://strgimgr.umico.az/example.jpg'}],
    }
    market = {'product': product, 'productCategory': {'id': 5, 'name': 'Ayaqqabı',
              'custom_fields': [{'master_field_id': 1, 'name': 'Rəng'},
                                {'master_field_id': 2, 'name': 'Ölçü'},
                                {'master_field_id': 3, 'name': 'Uzunluğu, sm'}]},
              'productVariations': [{'id': 124, 'name': 'Ayaqqabı 43', 'slugged_name': 'ayaqqabi-43',
                                     'status': 'active', 'custom_fields': [{'master_field_id': 2, 'values': ['43']}]}]}
    schema = {'@type': 'Product', 'sku': 123, 'offers': {'availability': 'https://schema.org/InStock', 'priceCurrency': 'AZN'},
              'aggregateRating': {'ratingValue': 5, 'reviewCount': 9}}
    state = {'pinia': {'market': market}}
    return ('<html lang="az"><script type="application/ld+json">' + json.dumps(schema) + '</script>'
            '<script>window.__UMICO__=' + json.dumps(state) + ';</script>'
            '<div data-info="product-price-main"><span data-info="discount-label">-34%</span></div></html>')


class BirmarketTests(unittest.TestCase):
    def test_image_only_description_is_preserved(self):
        source = 'https://strgimgr.umico.az/details.jpg'
        self.assertEqual(description_images(f'&lt;img src=&quot;{source}&quot;&gt;'), [source])

    def test_stock_placeholder_does_not_mean_out_of_stock(self):
        p, _ = parse_product(fixture(), 'https://birmarket.az/product/123-test', 'sport', 'test')
        self.assertIsNone(p['stock'])
        self.assertTrue(p['in_stock'])
        self.assertEqual(p['rating'], 4.5)  # Exact state rating, not rounded JSON-LD.

    def test_sizes_and_dimensions_remain_separate(self):
        p, _ = parse_product(fixture(), 'https://birmarket.az/product/123-test', 'sport', 'test')
        self.assertEqual(p['size'], '42')
        self.assertEqual(p['sizes'], ['42', '43'])
        self.assertEqual(p['dimensions'][0]['values'], ['30'])
        self.assertIsNone(p['variants'][0]['price_azn'])
        self.assertIsNone(p['variants'][0]['in_stock'])

    def test_unrated_product_is_not_a_zero_star_rating(self):
        html = fixture().replace('"rating_value": 4.5', '"rating_value": 0').replace('"session_count": 17', '"session_count": 0')
        p, _ = parse_product(html, 'https://birmarket.az/product/123-test', 'sport', 'test')
        self.assertIsNone(p['rating'])

    def test_discount_amount_and_site_rounding(self):
        p, _ = parse_product(fixture(), 'https://birmarket.az/product/123-test', 'sport', 'test')
        self.assertEqual(p['discount_amount_azn'], 33.5)
        self.assertEqual(p['discount_percent'], 33.5)
        self.assertEqual(p['discount_label'], '-34%')
        self.assertFalse(discount(100, 0)['has_discount'])
        self.assertFalse(discount(100, 100)['has_discount'])

    def test_mock_keys_and_unknown_translation(self):
        p, _ = parse_product(fixture(), 'https://birmarket.az/product/123-test', 'sport', 'test')
        self.assertTrue({'id', 'name', 'category', 'brand', 'price_azn', 'rating', 'stock', 'color', 'description'} <= p.keys())
        self.assertIsNone(p['name']['en'])
        self.assertEqual(p['images'][0]['url'], p['image_url'])

    def test_state_aliases_and_sparse_arrays(self):
        value = decode_state('window.__UMICO__=(function(a,b){a.x=b;b[0]=3;return {data:a};}({},Array(2)));')
        self.assertEqual(value, {'data': {'x': [3, None]}})

    def test_no_execution_of_arbitrary_javascript(self):
        for script in ['window.__UMICO__=fetch("https://example.com");',
                       'window.__UMICO__=(function(){while(true){} return {};})();']:
            with self.assertRaises(StateError):
                decode_state(script)

    def test_block_page_rejected(self):
        with self.assertRaises(ValueError):
            parse_product('<h1>Access denied</h1>', 'https://birmarket.az/product/123-test', 'sport', 'test')


if __name__ == '__main__':
    unittest.main()
