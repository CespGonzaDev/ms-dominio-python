import json
from pathlib import Path

import pytest

from scripts.seed_cosmos import normalize_catalog, normalize_service

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "seed"


def test_catalog_gets_type_and_requires_id_and_name():
    docs = normalize_catalog([{"id": "a", "name": "A", "icon": "x"}], "area")
    assert docs == [{"id": "a", "name": "A", "icon": "x", "type": "area"}]
    with pytest.raises(ValueError):
        normalize_catalog([{"id": "a"}], "area")


def test_sample_fixtures_are_valid():
    sample = DATA_DIR / "sample"
    for name, kind in (("areas.json", "area"), ("skills.json", "skill")):
        assert normalize_catalog(json.loads((sample / name).read_text("utf-8")), kind)
    services = json.loads((sample / "services.json").read_text("utf-8"))
    docs = [normalize_service(s, now=1_000) for s in services]
    assert docs[1]["status"] == "activo" and docs[1]["mentor"]["ratingAverage"] == 0.0
    assert docs[1]["createdAtEpochMs"] == 1_000
    assert docs[0]["mentor"]["ratingAverage"] == 4.5


def test_fase1_fixtures_are_valid():
    fase1 = DATA_DIR / "fase1"
    areas = normalize_catalog(json.loads((fase1 / "areas.json").read_text("utf-8")), "area")
    skills = normalize_catalog(json.loads((fase1 / "skills.json").read_text("utf-8")), "skill")
    services = [
        normalize_service(s) for s in json.loads((fase1 / "services.json").read_text("utf-8"))
    ]
    assert len(areas) == 14
    assert len(skills) == 40
    assert len(services) == 37


def test_invalid_service_fails_at_seed_time():
    with pytest.raises(ValueError):
        normalize_service({"id": "x", "mentorId": "m", "title": ""})
