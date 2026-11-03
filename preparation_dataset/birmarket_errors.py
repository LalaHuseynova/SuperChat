"""Shared exceptions for the CLI scraper and its browser transport."""


class ScraperError(RuntimeError):
    """The site could not be fetched or its products could not be parsed."""


class FetchBlocked(ScraperError):
    """The site refused access; stop collection without retrying."""


class TemporaryServerError(ScraperError):
    """A server-side failure eligible for a bounded retry."""
