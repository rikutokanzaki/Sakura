from session.set_prompt import PromptManager


def test_prompt_manager_formats_prompt_without_external_services():
    manager = PromptManager()

    assert manager.get_prompt("root", "paramiko") == "root@paramiko:~# "
    assert manager.get_prompt("alice", "host", "/tmp") == "alice@host:/tmp# "
