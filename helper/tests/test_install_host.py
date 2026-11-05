import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import install_host  # noqa: E402

KEY_PATH = r"Software\Mozilla\NativeMessagingHosts\obsidian_quick_clip"

class FakeReg:
    HKEY_CURRENT_USER = "HKCU"
    REG_SZ = 1

    def __init__(self, missing_on_delete=False):
        self.created = []
        self.values = []
        self.deleted = []
        self.missing_on_delete = missing_on_delete

    def CreateKey(self, root, path):
        self.created.append((root, path))
        return ("key", path)

    def SetValue(self, key, sub, typ, value):
        self.values.append((key, sub, typ, value))

    def DeleteKey(self, root, path):
        if self.missing_on_delete:
            raise FileNotFoundError(path)
        self.deleted.append((root, path))

def test_build_manifest_fields(tmp_path):
    assert install_host.build_manifest(tmp_path) == {
        "name": "obsidian_quick_clip",
        "description": "Obsidian Quick Clip helper",
        "path": str(tmp_path / "clipper_host.bat"),
        "type": "stdio",
        "allowed_extensions": ["obsidian-quick-clip@local"],
    }

def test_install_writes_manifest_and_registry(tmp_path):
    reg = FakeReg()
    path = install_host.install(tmp_path, reg=reg)
    assert path == tmp_path / "obsidian_quick_clip.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data == install_host.build_manifest(tmp_path)
    assert reg.created == [("HKCU", KEY_PATH)]
    assert reg.values == [(("key", KEY_PATH), "", 1, str(path))]

def test_uninstall_removes_key_and_file(tmp_path):
    reg = FakeReg()
    install_host.install(tmp_path, reg=reg)
    install_host.uninstall(tmp_path, reg=reg)
    assert reg.deleted == [("HKCU", KEY_PATH)]
    assert not (tmp_path / "obsidian_quick_clip.json").exists()

def test_uninstall_tolerates_missing(tmp_path):
    install_host.uninstall(tmp_path, reg=FakeReg(missing_on_delete=True))
