from detector.detect import AttackDetector
from utils.ansi_sequences import remove_prompt, strip_ansi_sequences
from utils.extract_chars import get_completion_diff


def test_completion_diff_only_returns_new_suffix():
    assert get_completion_diff("ec", "echo") == "ho"
    assert get_completion_diff("echo", "cat") == ""


def test_ansi_helpers_remove_terminal_sequences_and_prompt_marker():
    text = "echo \x1b[31mred\x1b[0m"

    assert strip_ansi_sequences(text) == "echo red"
    assert remove_prompt("before\x1b[40mafter") == "before"
    assert remove_prompt("plain output") == "plain output"


def test_attack_detector_flags_credential_and_download_indicators():
    detector = AttackDetector()

    assert detector.check("root", "1234", "id")
    assert detector.check("user", "password", "wget http://example.test/tool")
    assert detector.check("user", "password", "curl http://example.test/tool")
    assert not detector.check("user", "password", "ls -la")
