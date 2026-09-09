from app.config import SERVER_ROOT, Settings


def test_relative_projects_root_is_resolved_from_server_directory(monkeypatch) -> None:
    monkeypatch.setenv("PROJECTS_ROOT", "data/projects")

    settings = Settings(_env_file=None)

    assert settings.projects_root == (SERVER_ROOT / "data/projects").resolve()
