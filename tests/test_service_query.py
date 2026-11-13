from app.repositories.service_repo import build_search_query
from app.schemas.service import ServiceFilters


def test_default_query_only_active_and_ordered_by_relevance():
    page, count, params = build_search_query(ServiceFilters())
    assert "c.status = 'activo'" in page
    assert page.endswith("ORDER BY c.mentor.ratingAverage DESC OFFSET @offset LIMIT @limit")
    assert "c.status = 'activo'" in count
    assert params == []


def test_all_filters_are_parametrized():
    f = ServiceFilters(
        search="PyThon",
        skill_id="sk_python",
        area_id="area_prog",
        mentor_id="usr_002",
        modality="virtual",
        type="grupal",
        min_rating=4.5,
        price_max=5000,
        day=1,
        sort="price:asc",
    )
    page, _, params = build_search_query(f)
    values = {p["name"]: p["value"] for p in params}
    assert values == {
        "@mentorId": "usr_002",
        "@search": "python",
        "@skillId": "sk_python",
        "@areaId": "area_prog",
        "@modality": "virtual",
        "@type": "grupal",
        "@minRating": 4.5,
        "@priceMax": 5000,
        "@day": 1,
    }
    assert "ARRAY_CONTAINS(c.skillIds, @skillId)" in page
    assert "ARRAY_CONTAINS(c.availableDays, @day)" in page
    assert "CONTAINS(LOWER(c.title), @search)" in page
    assert "c.mentor.ratingAverage >= @minRating" in page
    assert "c.price.amount <= @priceMax" in page
    assert "ORDER BY c.price.amount ASC" in page


def test_user_input_is_never_concatenated_into_sql():
    evil = "x' OR 1=1 --"
    page, count, _ = build_search_query(ServiceFilters(search=evil, skill_id=evil))
    assert evil.lower() not in page.lower() and evil not in count


def test_free_flag():
    assert "IS_NULL(c.price)" in build_search_query(ServiceFilters(free=True))[0]
    assert "c.price.amount > 0" in build_search_query(ServiceFilters(free=False))[0]
    assert "c.price" not in build_search_query(ServiceFilters())[0].split("ORDER BY")[0]


def test_sort_options_and_offset():
    assert (
        "ORDER BY c.mentor.ratingAverage DESC"
        in build_search_query(ServiceFilters(sort="rating:desc"))[0]
    )
    assert (
        "ORDER BY c.price.amount DESC"
        in build_search_query(ServiceFilters(sort="price:desc"))[0]
    )
    assert "ORDER BY c.createdAtEpochMs DESC" in build_search_query(
        ServiceFilters(sort="createdAt:desc")
    )[0]
    assert ServiceFilters(page=3, page_size=10).offset == 20
