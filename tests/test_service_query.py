from app.repositories.service_repo import build_search_query
from app.schemas.service import ServiceFilters


def test_default_query_only_active_and_ordered_by_recent():
    page, count, params = build_search_query(ServiceFilters())
    assert "c.status = 'active'" in page
    assert page.endswith("ORDER BY c.createdAtEpochMs DESC OFFSET @offset LIMIT @limit")
    assert count == "SELECT VALUE COUNT(1) FROM c WHERE c.status = 'active'"
    assert params == []


def test_all_filters_are_parametrized():
    f = ServiceFilters(
        search="PyThon",
        skill_id="s1",
        area_id="a1",
        modality="online",
        type="group",
        min_rating=4.5,
        price_max=30,
        day="monday",
        sort="priceAsc",
    )
    page, _, params = build_search_query(f)
    values = {p["name"]: p["value"] for p in params}
    assert values == {
        "@search": "python",
        "@skillId": "s1",
        "@areaId": "a1",
        "@modality": "online",
        "@type": "group",
        "@minRating": 4.5,
        "@priceMax": 30,
        "@day": "monday",
    }
    assert "ARRAY_CONTAINS(c.skillIds, @skillId)" in page
    assert "ARRAY_CONTAINS(c.availableDays, @day)" in page
    assert "CONTAINS(LOWER(c.title), @search)" in page
    assert "c.rating >= @minRating" in page and "c.price <= @priceMax" in page
    assert "ORDER BY c.price ASC" in page


def test_user_input_is_never_concatenated_into_sql():
    evil = "x' OR 1=1 --"
    page, count, _ = build_search_query(ServiceFilters(search=evil, skill_id=evil))
    assert evil.lower() not in page.lower() and evil not in count


def test_free_flag():
    assert "c.price = 0" in build_search_query(ServiceFilters(free=True))[0]
    assert "c.price > 0" in build_search_query(ServiceFilters(free=False))[0]
    assert "c.price" not in build_search_query(ServiceFilters())[0].split("ORDER BY")[0]


def test_sort_options_and_offset():
    assert "ORDER BY c.rating DESC" in build_search_query(ServiceFilters(sort="rating"))[0]
    assert "ORDER BY c.price DESC" in build_search_query(ServiceFilters(sort="priceDesc"))[0]
    assert ServiceFilters(page=3, page_size=10).offset == 20
