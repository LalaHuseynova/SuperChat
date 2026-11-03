"""Opt-in collection through ordinary Chrome navigation in an isolated session."""
import time
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import requests
from birmarket_errors import FetchBlocked, ScraperError, TemporaryServerError


class BrowserClient:
    def __init__(self, delay):
        from playwright.sync_api import sync_playwright
        self.delay, self.last = delay, 0.0
        self.driver = self.browser = None
        try:
            self.driver = sync_playwright().start()
            self.browser = self.driver.chromium.launch(channel='chrome', headless=False)
            self.context = self.browser.new_context()
            # Product facts come from HTML/JSON. Avoid downloading decorative
            # galleries/fonts on every visit; explicit main-image navigation
            # remains enabled for the visual-search archive.
            self.context.route('**/*', self.route_asset)
            self.page = self.context.new_page()
            self.check_access()
        except Exception:
            self.close()
            raise

    @staticmethod
    def route_asset(route):
        request = route.request
        if request.resource_type in {'image', 'media', 'font'} and not request.is_navigation_request():
            route.abort()
        else:
            route.continue_()

    def check_access(self):
        response = self.get('https://birmarket.az/robots.txt', allow_not_found=True)
        if response.status_code == 404:
            return
        if 'html' in response.headers.get('Content-Type', '').lower():
            raise FetchBlocked('Access check returned an HTML page instead of robots rules')
        rules = RobotFileParser()
        rules.parse(response.text.splitlines())
        for path in ['/product/', '/categories/']:
            if not rules.can_fetch('SuperChat', 'https://birmarket.az' + path):
                raise FetchBlocked('Public collection disallowed by robots.txt')

    def get(self, url, headers=None, *, allow_not_found=False):
        for attempt in range(3):
            try:
                return self._get_once(url, headers, allow_not_found=allow_not_found)
            except TemporaryServerError:
                if attempt == 2:
                    raise
                time.sleep(2 ** (attempt + 1))

    def _get_once(self, url, headers=None, *, allow_not_found=False):
        from playwright.sync_api import TimeoutError as BrowserTimeout
        from playwright.sync_api import Error as BrowserError
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or parsed.hostname not in {'birmarket.az', 'strgimgr.umico.az', 'strgimgr.b-cdn.net'} or parsed.username or parsed.password:
            raise ScraperError('Unexpected browser collection URL')
        time.sleep(max(0, self.delay - (time.monotonic() - self.last)))
        self.last = time.monotonic()
        try:
            response = self.page.goto(url, wait_until='domcontentloaded', timeout=45000)
            if response is None:
                raise ScraperError('No browser response')
            if response.status in (401, 403, 429):
                raise FetchBlocked(f'HTTP {response.status}: browser collection stopped')
            if response.status in (500, 502, 503, 504):
                raise TemporaryServerError(f'Browser request failed: HTTP {response.status}')
            if response.status >= 400 and not (response.status == 404 and allow_not_found):
                raise ScraperError(f'Browser request failed: HTTP {response.status}')
            if urlsplit(self.page.url).hostname != parsed.hostname:
                raise ScraperError('Unexpected browser redirect')
            body = response.body()
            if 'text/html' in response.headers.get('content-type', ''):
                title = self.page.title().lower()
                if any(word in title for word in ['captcha', 'just a moment', 'access denied', 'verify you are human']):
                    raise FetchBlocked('Browser verification page; collection stopped')
                if '/categories/' in parsed.path:
                    self.page.wait_for_selector('a[data-info="product-item-link"]', state='attached', timeout=20000)
                elif '/product/' in parsed.path:
                    self.page.wait_for_selector('script[type="application/ld+json"]', state='attached', timeout=20000)
                body = self.page.content().encode('utf-8')
            result = requests.Response()
            result.status_code = response.status
            result.url = self.page.url
            result.headers.update(response.headers)
            result._content = body
            result.encoding = 'utf-8'
            return result
        except BrowserTimeout as exc:
            raise ScraperError('Browser page timed out before product data was available') from exc
        except BrowserError as exc:
            raise ScraperError('Browser navigation or page read failed') from exc

    def close(self):
        try:
            if self.browser:
                self.browser.close()
        finally:
            if self.driver:
                self.driver.stop()
