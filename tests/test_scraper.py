from src.scraping.scraper import scrape_page


HTML_FIXTURE = """
<html>
  <body>
    <h2 class="elementor-heading-title elementor-size-large">Calls for Art</h2>
    <div class="elementor-widget-text-editor">
      <p>Deadline to apply: August 7, 11:59pm</p>
    </div>
    <div class="elementor-widget-text-editor">
      <p>Entry fee: $25 for Artspace Members / $35 for non-members</p>
    </div>
    <div class="elementor-widget-text-editor">
      <p>Location: Raleigh, NC</p>
    </div>
  </body>
</html>
"""


def test_scraper_returns_raw_records_with_expected_keys(monkeypatch):
    class DummyResponse:
        def __init__(self, text):
            self.text = text

        def raise_for_status(self):
            return None

    def fake_get(*args, **kwargs):
        return DummyResponse(HTML_FIXTURE)

    monkeypatch.setattr("src.scraping.scraper.requests.Session.get", fake_get)

    items = scrape_page("https://example.com/test", delay_seconds=0)

    assert isinstance(items, list)
    assert items

    first = items[0]
    assert set(first.keys()) == {"name", "date_text", "location_text", "fee_text", "url"}
    assert first["url"] == "https://example.com/test"


def test_scraper_falls_back_to_title_and_meta_for_generic_pages(monkeypatch):
    class DummyResponse:
        def __init__(self, text):
            self.text = text

        def raise_for_status(self):
            return None

    html = """
    <html>
      <head>
        <title>Raleigh Handmade Expo</title>
        <meta name="description" content="Friday, September 25, 2026 at Moore Square, Raleigh, NC 27601" />
      </head>
      <body>
        <main>
          <h1>Raleigh Handmade Expo</h1>
          <p>Entry fee: $20</p>
        </main>
      </body>
    </html>
    """

    def fake_get(*args, **kwargs):
        return DummyResponse(html)

    monkeypatch.setattr("src.scraping.scraper.requests.Session.get", fake_get)

    items = scrape_page("https://example.com/generic", delay_seconds=0)

    assert items
    first = items[0]
    assert first["name"] == "Raleigh Handmade Expo"
    assert "27601" in (first["location_text"] or "")
    assert "September 25, 2026" in (first["date_text"] or "")
    assert "$20" in (first["fee_text"] or "")


def test_scraper_prefers_address_like_location_snippets(monkeypatch):
    class DummyResponse:
        def __init__(self, text):
            self.text = text

        def raise_for_status(self):
            return None

    html = """
    <html>
      <body>
        <h1>Annual Holiday Crafts Fair</h1>
        <p>DATE: Saturday, November 21, 2026 10 a.m.-5 p.m.</p>
        <p>Street Gallery</p>
        <p>Location: The Crafts Center Thompson Hall 210 Jensen Drive Raleigh, NC 27606</p>
      </body>
    </html>
    """

    def fake_get(*args, **kwargs):
        return DummyResponse(html)

    monkeypatch.setattr("src.scraping.scraper.requests.Session.get", fake_get)

    items = scrape_page("https://example.com/address", delay_seconds=0)

    assert items
    first = items[0]
    assert "27606" in (first["location_text"] or "")
    assert "Thompson Hall" in (first["location_text"] or "")
