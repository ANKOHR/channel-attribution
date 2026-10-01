import json
import pytest
from channel_attribution.fixtures import fixture_files, fixture_records


@pytest.fixture
def records():
    return fixture_records()


@pytest.fixture
def dataset(tmp_path):
    directory = tmp_path / "input"
    directory.mkdir()
    for name, content in fixture_files().items():
        (directory / name).write_text(content, encoding="utf-8")
    return directory
