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
        "mal_id": 52991,
        "title": "Frieren: Beyond Journey's End",
        "synopsis": "An elf mage...",
        "image_url": "https://cdn/img.jpg",
        "episodes": 28,
        "is_airing": False,
        "author": None,
        "rating": None,
        "duration": None,
        "type": None,
        "trailer_youtube_id": None,
        "trailer_embed_url": None,
    }


def test_maps_rating_duration_type_trailer():
    raw = {
        "mal_id": 52991,
        "title": "Sousou no Frieren",
        "images": {"jpg": {"large_image_url": "https://cdn/img.jpg"}},
        "episodes": 28,
        "airing": False,
        "rating": "PG-13 - Teens 13 or older",
        "duration": "24 min per ep",
        "type": "TV",
        "trailer": {"youtube_id": "abc123", "embed_url": "https://youtube.com/embed/abc123"},
    }
    fields = to_anime_fields(raw)
    assert fields["rating"] == "PG-13 - Teens 13 or older"
    assert fields["duration"] == "24 min per ep"
    assert fields["type"] == "TV"
    assert fields["trailer_youtube_id"] == "abc123"
    assert fields["trailer_embed_url"] == "https://youtube.com/embed/abc123"


def test_falls_back_to_romaji_when_no_english_title():
    raw = {"mal_id": 1, "title": "Sousou no Frieren", "title_english": None}
    assert to_anime_fields(raw)["title"] == "Sousou no Frieren"


def test_tolerates_unaired_entry():
    """Not-yet-aired shows have null episodes, no images, no synopsis."""
    raw = {"mal_id": 63816, "title": "Ougonkyou-hen", "episodes": None}
    fields = to_anime_fields(raw)
    assert fields["episodes"] is None
    assert fields["image_url"] is None
