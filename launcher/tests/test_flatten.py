from app.utils.flatten import flatten_dict


def test_flatten_dict_handles_nested_dicts_lists_and_none():
    value = {
        "user": {"name": "sakura"},
        "events": [{"type": "login"}, None, "logout"],
        "empty": None,
    }

    assert flatten_dict(value) == {
        "user.name": "sakura",
        "events[0].type": "login",
        "events[1]": "",
        "events[2]": "logout",
        "empty": "",
    }
