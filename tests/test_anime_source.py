from app.clients.anime_source import to_anime_fields


def test_maps_full_payload():
    raw = {
        "mal_id": 52991,
        "title": "Sousou no Frieren",
        "title_english": "Frieren: Beyond Journey's End",
        "synopsis": "An elf mage...",
        "images": {"jpg": {"large_image_url": "https://cdn/img.jpg"}},
        "episodes": 28,
        "airing": False,
    }
    assert to_anime_fields(raw) == {
        "jikan_id": 52991,
        "title": "Frieren: Beyond Journey's End",
        "synopsis": "An elf mage...",
        "image_url": "https://cdn/img.jpg",
        "episodes": 28,
        "is_airing": False,
        "author": None,
    }


def test_falls_back_to_romaji_when_no_english_title():
    raw = {"mal_id": 1, "title": "Sousou no Frieren", "title_english": None}
    assert to_anime_fields(raw)["title"] == "Sousou no Frieren"


def test_tolerates_unaired_entry():
    """Not-yet-aired shows have null episodes, no images, no synopsis."""
    raw = {"mal_id": 63816, "title": "Ougonkyou-hen", "episodes": None}
    fields = to_anime_fields(raw)
    assert fields["episodes"] is None
    assert fields["image_url"] is None
