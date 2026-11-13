import json
from pathlib import Path

import pytest

from scripts.seed_cosmos import normalize_catalog, normalize_service

SAMPLE = Path(__file__).resolve().parent.parent / "data" / "seed" / "sample"


def test_catalog_gets_type_and_requires_id_and_name():
    docs = normalize_catalog([{"id": "a", "name": "A", "icon": "x"}], "area")
    assert docs == [{"id": "a", "name": "A", "icon": "x", "type": "area"}]
    with pytest.raises(ValueError):
        normalize_catalog([{"id": "a"}], "area")


def test_sample_fixtures_are_valid():
    for name, kind in (("areas.json", "area"), ("skills.json", "skill")):
        assert normalize_catalog(json.loads((SAMPLE / name).read_text("utf-8")), kind)
    services = json.loads((SAMPLE / "services.json").read_text("utf-8"))
    docs = [normalize_service(s, now=1_000) for s in services]
    assert docs[1]["status"] == "active" and docs[1]["rating"] == 0
    assert docs[1]["createdAtEpochMs"] == 1_000
    assert docs[0]["rating"] == 4.5  # los valores del fixture no se pisan


def test_invalid_service_fails_at_seed_time():
    with pytest.raises(ValueError):
        normalize_service({"id": "x", "mentorId": "m", "title": ""})
