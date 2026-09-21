from auth.auth_user import Authenticator


def test_authenticator_reads_exact_and_wildcard_rules(tmp_path):
    user_file = tmp_path / "user.txt"
    user_file.write_text(
        "# ignored\nalice:secret\nguest:*\nadmin:!blocked\nmalformed\n",
        encoding="utf-8",
    )

    authenticator = Authenticator(str(user_file))

    assert authenticator.authenticate("alice", "secret")
    assert not authenticator.authenticate("alice", "wrong")
    assert authenticator.authenticate("guest", "any-password")
    assert authenticator.authenticate("admin", "allowed")
    assert not authenticator.authenticate("admin", "blocked")
    assert not authenticator.authenticate("unknown", "secret")


def test_authenticator_returns_false_when_user_file_is_missing(tmp_path):
    authenticator = Authenticator(str(tmp_path / "missing.txt"))

    assert authenticator.rules == []
    assert not authenticator.authenticate("alice", "secret")
