from src.scraping.normalizer import normalize_raw_items


def test_parses_explicit_dates_with_years():
    raw_items = [
        {
            "name": "Open Call",
            "date_text": "Call opens: June 10, 2026",
            "location_text": None,
            "fee_text": None,
            "url": "https://example.com/1",
        },
        {
            "name": "Deadline",
            "date_text": "Call closes: July 10, 2026",
            "location_text": None,
            "fee_text": None,
            "url": "https://example.com/2",
        },
    ]

    fairs = normalize_raw_items(raw_items)

    assert fairs[0].start_date == "2026-06-10"
    assert fairs[1].start_date == "2026-07-10"


def test_leaves_ambiguous_dates_as_none():
    raw_items = [
        {
            "name": "Open Call",
            "date_text": "Deadline to apply: August 7, 11:59pm",
            "location_text": None,
            "fee_text": None,
            "url": "https://example.com/3",
        }
    ]

    fairs = normalize_raw_items(raw_items)

    assert fairs[0].start_date is None


def test_parses_first_date_from_a_date_range():
    raw_items = [
        {
            "name": "Exhibition",
            "date_text": "Exhibition dates: Nov 7, 2025 – Jan 18, 2026",
            "location_text": "Raleigh, NC",
            "fee_text": "Table Fee: $25",
            "url": "https://example.com/4",
        }
    ]

    fairs = normalize_raw_items(raw_items)

    assert fairs[0].start_date == "2025-11-07"
    assert fairs[0].price == 25.0


def test_extracts_zip_code_from_location_text():
    raw_items = [
        {
            "name": "Market",
            "date_text": None,
            "location_text": "Raleigh, NC 27601",
            "fee_text": None,
            "url": "https://example.com/5",
        }
    ]

    fairs = normalize_raw_items(raw_items)

    assert fairs[0].zip_code == "27601"


def test_parses_dates_with_prefix_and_time_range():
    raw_items = [
        {
            "name": "Craft Fair",
            "date_text": "DATE: Saturday, November 21, 2026 10 a.m.-5 p.m.",
            "location_text": "The Crafts Center Thompson Hall 210 Jensen Drive Raleigh, NC 27606",
            "fee_text": None,
            "url": "https://example.com/6",
        }
    ]

    fairs = normalize_raw_items(raw_items)

    assert fairs[0].start_date == "2026-11-21"
    assert fairs[0].zip_code == "27606"
