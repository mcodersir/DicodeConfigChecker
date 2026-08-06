from pathlib import Path

from runtime_paths import application_data_dir


def test_windows_data_path_uses_local_app_data(tmp_path: Path) -> None:
    result = application_data_dir("Windows", {"LOCALAPPDATA": str(tmp_path)}, tmp_path / "home")
    assert result == tmp_path / "DicodeConfigChecker"


def test_linux_data_path_uses_xdg_data_home(tmp_path: Path) -> None:
    result = application_data_dir("Linux", {"XDG_DATA_HOME": str(tmp_path)}, tmp_path / "home")
    assert result == tmp_path / "DicodeConfigChecker"


def test_linux_data_path_falls_back_to_home(tmp_path: Path) -> None:
    result = application_data_dir("Linux", {}, tmp_path)
    assert result == tmp_path / ".local" / "share" / "DicodeConfigChecker"


def test_macos_data_path_uses_application_support(tmp_path: Path) -> None:
    result = application_data_dir("Darwin", {}, tmp_path)
    assert result == tmp_path / "Library" / "Application Support" / "DicodeConfigChecker"


def test_explicit_data_directory_wins(tmp_path: Path) -> None:
    custom = tmp_path / "custom"
    result = application_data_dir("Linux", {"DICODE_DATA_DIR": str(custom)}, tmp_path)
    assert result == custom.resolve()
