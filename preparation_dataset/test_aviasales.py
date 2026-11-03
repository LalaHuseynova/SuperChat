import html
import json
import unittest

from aviasales_scraper import (
    ScraperError, decode_astro, parse_duration, parse_price, parse_route,
)


REFERENCE = {
    'cities': {code: {'name': name, 'time_zone': tz} for code, name, tz in [
        ('BAK', 'Baku', 'Asia/Baku'), ('IST', 'Istanbul', 'Europe/Istanbul'),
        ('DXB', 'Dubai', 'Asia/Dubai'), ('SHJ', 'Sharjah', 'Asia/Dubai'),
    ]},
    'airports': {}, 'airlines': {'VF': {'name': 'Ajet'}},
}


def leg(times='23:30 – 01:45', duration='3 saat 15 dəq. / birbaşa'):
    return f'''<div class="ticket-info"><div class="ticket-date">18 Noy {times}</div>
    <span class="ticket-duration">Yolda: {duration}</span>
    <astro-airline-logo data-alt="VF" data-logo-url="//img.avs.io/logo"></astro-airline-logo></div>'''


def card(destination='IST', search_destination=None, return_date=None, times=None):
    metadata = {'origin_airport_iata': 'BAK', 'destination_airport_iata': destination,
                'depart_date': '2026-11-18', 'return_date': return_date or '',
                'price': 139, 'badge': 'Baqaj daxil'}
    code = search_destination or destination
    return_path = '2011' if return_date else ''
    contents = leg(times) if times else leg()
    if return_date:
        contents += leg('02:00 – 06:15')
    return f'''<a class="ticket" data-analytics-click-data="{html.escape(json.dumps(metadata))}"
        href="/search/BAK1811{code}{return_path}1?search_date=01112026">
        <span class="ticket-price">138,76 ₼</span>{contents}</a>'''


def parse(markup, destination='IST'):
    return parse_route(markup, {'origin': 'BAK', 'destination': destination}, REFERENCE,
                       '2026-11-02T12:00:00+04:00', 'https://www.aviasales.az/routes/bak/ist')


class AviasalesTests(unittest.TestCase):
    def test_precise_price_and_unknown_inventory(self):
        offers, _, errors = parse(card())
        self.assertEqual(errors, [])
        offer = offers[0]
        self.assertEqual(offer['price_azn'], 138.76)  # Not analytics' rounded 139.
        self.assertTrue(offer['baggage_included'])
        for key in ('flight_number', 'cabin', 'baggage_kg', 'seats_available'):
            self.assertIsNone(offer[key])
        self.assertIsNone(offer['origin']['airport_code'])
        self.assertFalse(offer['live_price_verified'])
        self.assertEqual(offer['source_search_date'], '2026-11-01')

    def test_overnight_arrival_respects_timezone(self):
        offer = parse(card())[0][0]
        self.assertEqual(offer['arrival_local'], '2026-11-19T01:45')
        self.assertEqual(offer['arrival_utc'], '2026-11-18T22:45:00+00:00')

    def test_conflicting_arrival_not_invented(self):
        offer = parse(card(times='23:30 – 02:45'))[0][0]
        self.assertIsNone(offer['arrival_local'])
        self.assertTrue(offer['data_warnings'])

    def test_round_trip_price_kept_for_whole_itinerary(self):
        offer = parse(card(return_date='2026-11-20'))[0][0]
        self.assertEqual(offer['trip_type'], 'round_trip')
        self.assertEqual(offer['price_scope'], 'entire_round_trip')
        self.assertEqual(offer['price_azn'], 138.76)
        self.assertEqual(offer['return_leg']['origin']['code'], 'IST')
        self.assertEqual(offer['return_leg']['arrival_local'], '2026-11-20T06:15')

    def test_nearby_city_is_displayed_and_original_route_retained(self):
        offer = parse(card('DXB', 'SHJ', times='23:30 – 02:45'), 'DXB')[0][0]
        self.assertTrue(offer['nearby_airport_search'])
        self.assertEqual(offer['destination']['city'], 'Sharjah')
        self.assertEqual(offer['source_route']['destination']['city'], 'Dubai')
        self.assertEqual(offer['arrival_local'], '2026-11-19T02:45')

    def test_azeri_number_and_duration_formats(self):
        self.assertEqual(parse_price('1.234,56 ₼'), 1234.56)
        self.assertEqual(parse_duration('1 Gün 1 ⁠saat 10 ⁠dəq. / 1 tranzit'), 1510)
        with self.assertRaises(ValueError):
            parse_price('$138.76')

    def test_missing_cards_fail_instead_of_silent_empty_export(self):
        with self.assertRaises(ScraperError):
            parse('<html>Unexpected page</html>')

    def test_wrong_search_date_is_rejected(self):
        with self.assertRaises(ScraperError):
            parse(card().replace('/search/BAK1811', '/search/BAK1911'))

    def test_history_decoder_does_not_execute_scripts(self):
        self.assertEqual(decode_astro('{"data":[1,[[0,{"price":[0,123]}]]]}'),
                         {'data': [{'price': 123}]})
        with self.assertRaises(ValueError):
            decode_astro('{"data":[99,"alert(1)"]}')


if __name__ == '__main__':
    unittest.main()
