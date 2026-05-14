import pytest
from pathlib import Path
from storage import Storage

@pytest.fixture
def store(tmp_path):
    return Storage(
        chats_file=tmp_path / "chats.json",
        templates_file=tmp_path / "templates.json",
        photos_dir=tmp_path / "photos",
    )

def test_load_chats_empty(store):
    assert store.load_chats() == []

def test_save_and_load_chats(store):
    chats = [{"chat": "@chat1", "suffix": ""}, {"chat": "@chat2", "suffix": "привет"}]
    store.save_chats(chats)
    assert store.load_chats() == chats

def test_load_chats_backward_compat(store):
    store.chats_file.write_text('["@chat1", "@chat2"]', encoding="utf-8")
    assert store.load_chats() == [{"chat": "@chat1", "suffix": ""}, {"chat": "@chat2", "suffix": ""}]

def test_load_templates_empty(store):
    assert store.load_templates() == []

def test_save_and_load_templates(store):
    templates = [{"id": "abc", "name": "Test", "text": "Hello", "photo": ""}]
    store.save_templates(templates)
    assert store.load_templates() == templates

def test_copy_photo(store, tmp_path):
    src = tmp_path / "photo.jpg"
    src.write_bytes(b"fakejpeg")
    dest_path = store.copy_photo(str(src), "test-id")
    assert Path(dest_path).exists()
    assert Path(dest_path).read_bytes() == b"fakejpeg"
