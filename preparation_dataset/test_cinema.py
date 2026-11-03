import unittest

from cinema_scraper import (
    BASE, ScraperError, entity_id, merge_showtimes, parse_cinema,
    parse_movie, parse_price, parse_showtimes,
)


MOVIE_URL = BASE + '/az/films/example/'
VENUE_URL = BASE + '/az/cinema/about-cinemaplus/example-mall/'
STAMP = '2026-11-02T21:00:00+04:00'


def schedule(price='8.00', date='03.11.2026'):
    return f'''<table class="sessions_table"><tbody><tr data-date="{date}">
        <td><a href="/az/films/example/">Example</a></td><td>23:15</td>
        <td><a href="/az/cinema/about-cinemaplus/example-mall/">Example Mall</a></td>
        <td>VIP 1</td><td><span class="cc_tooltip">Film 2D formatında nümayiş olunur</span>
        <span class="cc_tooltip">Film Rus dilində nümayiş olunur</span>
        <span class="cc_tooltip">Film Azərbaycan subtitrları ilə nümayiş olunur</span></td>
        <td>{price} AZN</td><td><div class="zone_input" data-session="1" data-price="8.00"></div></td>
        </tr></tbody></table>'''


class CinemaTests(unittest.TestCase):
    def test_joinable_session_preserves_language_subtitles_and_unknown_seats(self):
        rows, errors = parse_showtimes(schedule(), MOVIE_URL, STAMP)
        self.assertEqual(errors, [])
        row = rows[0]
        self.assertEqual(row['movie_id'], entity_id('CM-M-', MOVIE_URL))
        self.assertEqual(row['cinema_id'], entity_id('CM-C-', VENUE_URL))
        self.assertEqual(row['start_local'], '2026-11-03T23:15:00+04:00')
        self.assertEqual(row['languages'], ['Rus'])
        self.assertEqual(row['subtitles'], ['Azərbaycan'])
        self.assertEqual(row['formats'], ['2D'])
        self.assertIsNone(row['seats_available'])
        self.assertIsNone(row['seats_total'])

    def test_conflicts_keep_both_prices_and_prefer_movie_in_either_order(self):
        movie = parse_showtimes(schedule('20.00'), MOVIE_URL, STAMP)[0][0]
        venue = parse_showtimes(schedule('15.00'), VENUE_URL, STAMP)[0][0]
        for rows in ([movie, venue], [venue, movie]):
            merged = merge_showtimes(rows)
            self.assertEqual(len(merged), 1)
            self.assertEqual(merged[0]['price_azn'], 20)
            self.assertTrue(merged[0]['price_conflict'])
            self.assertEqual({o['price_azn'] for o in merged[0]['price_observations']}, {15, 20})

    def test_same_clock_on_different_dates_is_not_deduplicated(self):
        a = parse_showtimes(schedule(), MOVIE_URL, STAMP)[0]
        b = parse_showtimes(schedule(date='04.11.2026'), MOVIE_URL, STAMP)[0]
        self.assertEqual(len(merge_showtimes(a + b)), 2)

    def test_bad_prices_are_reported_not_replaced_with_zero(self):
        rows, errors = parse_showtimes(schedule('unknown'), MOVIE_URL, STAMP)
        self.assertEqual(rows, [])
        self.assertEqual(len(errors), 1)
        self.assertEqual(parse_price('8,50 AZN'), 8.5)

    def test_modal_zero_price_does_not_become_session(self):
        rows, errors = parse_showtimes('<div>1 biletin qiyməti: 0 AZN</div>', MOVIE_URL, STAMP)
        self.assertEqual((rows, errors), ([], []))

    def test_upcoming_missing_values_stay_null(self):
        markup = '''<title>New movie • CinemaPlus</title><div class="desc_film">Synopsis</div>
          <ul><li><span>Müddət</span><div class="detail">dəqiqə</div></li>
          <li><span>Yaş həddi</span><div class="detail">+</div></li></ul>'''
        movie = parse_movie(markup, BASE + '/az/coming-soon/example/', STAMP)
        self.assertIsNone(movie['duration_min'])
        self.assertIsNone(movie['age_rating'])
        self.assertIsNone(movie['rating'])
        self.assertEqual(movie['id'], entity_id('CM-M-', MOVIE_URL))
        self.assertEqual(movie['listing_status'], 'coming_soon')

    def test_movie_details_required(self):
        with self.assertRaises(ScraperError):
            parse_movie('<html>Unexpected page</html>', MOVIE_URL, STAMP)

    def test_real_address_and_zero_coordinate_handling(self):
        markup = '''<title>Example Mall • CinemaPlus</title><div class="description">Cinema</div>
        <div class="tab contact"><ul><li><span>Bizim ünvan:</span><p>Example Street 1</p></li>
        <li><span>Elektron ünvan:</span><p>[email protected]</p></li></ul>
        <iframe src="https://www.google.com/maps?q=0.000000,0.000000"></iframe></div>'''
        venue = parse_cinema(markup, VENUE_URL, STAMP)
        self.assertEqual(venue['address'], 'Example Street 1')
        self.assertIsNone(venue['district'])
        self.assertIsNone(venue['coordinates'])

    def test_plain_contact_labels_and_multiple_values_in_one_list_item(self):
        markup = '''<title>Mall • CinemaPlus</title><div class="description">Cinema</div>
        <div class="tab contact"><ul><li>Bizim ünvan:<p>Street 26</p>
        Telefon:<p>+99412 499 89 88</p></li><li>İş saatı:<p>10:00–00:00</p></li></ul></div>'''
        venue = parse_cinema(markup, VENUE_URL, STAMP)
        self.assertEqual(venue['address'], 'Street 26')
        self.assertEqual(venue['phone'], '+99412 499 89 88')
        self.assertEqual(venue['opening_hours'], '10:00–00:00')

    def test_contact_labels_separated_by_line_breaks(self):
        markup = '''<title>Mall</title><div class="description"></div><div class="tab contact">
        <li>Bizim ünvan:<br/><br/>Sumqayıt, Street 72</li></div>'''
        self.assertEqual(parse_cinema(markup, VENUE_URL, STAMP)['address'], 'Sumqayıt, Street 72')


if __name__ == '__main__':
    unittest.main()
