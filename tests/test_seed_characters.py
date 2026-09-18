import seed_characters


def test_seed_adds_all_characters(db):
    seed_characters.seed()
    names = {c["name"] for c in db.get_all_characters()}
    assert names == {c["name"] for c in seed_characters.CHARACTERS}


def test_all_seeded_characters_have_a_show_from_their_source_module():
    from shows import vikings, walking_dead

    vikings_names = {c["name"] for c in vikings.CHARACTERS}
    twd_names = {c["name"] for c in walking_dead.CHARACTERS}

    for c in seed_characters.CHARACTERS:
        if c["name"] in vikings_names:
            assert c["show"] == "Vikings"
        elif c["name"] in twd_names:
            assert c["show"] == "The Walking Dead"
        else:
            assert c["show"] == "Game of Thrones"


def test_all_seeded_characters_have_an_avatar():
    for c in seed_characters.CHARACTERS:
        assert c.get("avatar"), f"{c['name']} has no avatar set"


def test_seeded_avatars_are_unique_within_each_show():
    groups = {}
    for c in seed_characters.CHARACTERS:
        groups.setdefault(c["show"], []).append(c["avatar"])

    for show, avatars in groups.items():
        assert len(avatars) == len(set(avatars)), f"duplicate avatar within {show}"


def test_seed_twice_updates_instead_of_duplicating(db, monkeypatch):
    seed_characters.seed()
    before_count = len(db.get_all_characters())

    # Simulate an edit to a character's data, then reseed.
    monkeypatch.setitem(
        seed_characters.CHARACTERS[0], "personality", "An edited personality."
    )
    seed_characters.seed()

    after = db.get_all_characters()
    assert len(after) == before_count

    first_name = seed_characters.CHARACTERS[0]["name"]
    updated_row = next(c for c in after if c["name"] == first_name)
    assert updated_row["personality"] == "An edited personality."
