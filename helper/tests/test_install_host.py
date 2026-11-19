import base64
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

import build_chromium  # noqa: E402
import install_host  # noqa: E402

KEY_PATH = r"Software\Mozilla\NativeMessagingHosts\quick_web_clip"
CHROME_KEY = r"Software\Google\Chrome\NativeMessagingHosts\quick_web_clip"
EDGE_KEY = r"Software\Microsoft\Edge\NativeMessagingHosts\quick_web_clip"


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
        "name": "quick_web_clip",
        "description": "Quick Web Clip helper",
        "path": str(tmp_path / "clipper_host.bat"),
        "type": "stdio",
        "allowed_extensions": ["quick-web-clip@local"],
    }


def test_chromium_manifest_allows_the_chrome_and_edge_extension(tmp_path):
    m = install_host.build_chromium_manifest(tmp_path)
    assert m["allowed_origins"] == ["chrome-extension://kcdeoockaleljccbljbelmpehlnnceop/"]
    assert "allowed_extensions" not in m
    assert m["path"] == str(tmp_path / "clipper_host.bat")


def test_install_writes_manifests_and_registry(tmp_path):
    reg = FakeReg()
    path = install_host.install(tmp_path, reg=reg)
    assert path == tmp_path / "quick_web_clip.json"
    assert json.loads(path.read_text(encoding="utf-8")) == install_host.build_manifest(tmp_path)
    chromium = tmp_path / "quick_web_clip_chromium.json"
    assert json.loads(chromium.read_text(encoding="utf-8")) == install_host.build_chromium_manifest(tmp_path)
    assert reg.created == [("HKCU", KEY_PATH), ("HKCU", CHROME_KEY), ("HKCU", EDGE_KEY)]
    assert reg.values == [
        (("key", KEY_PATH), "", 1, str(path)),
        (("key", CHROME_KEY), "", 1, str(chromium)),
        (("key", EDGE_KEY), "", 1, str(chromium)),
    ]


def test_uninstall_removes_keys_and_files(tmp_path):
    reg = FakeReg()
    install_host.install(tmp_path, reg=reg)
    install_host.uninstall(tmp_path, reg=reg)
    assert reg.deleted == [("HKCU", KEY_PATH), ("HKCU", CHROME_KEY), ("HKCU", EDGE_KEY)]
    assert not (tmp_path / "quick_web_clip.json").exists()
    assert not (tmp_path / "quick_web_clip_chromium.json").exists()


def test_uninstall_tolerates_missing(tmp_path):
    install_host.uninstall(tmp_path, reg=FakeReg(missing_on_delete=True))


def test_chromium_id_matches_the_build_key():
    """The ID Chrome and Edge derive from the manifest key must be the one the helper allows."""
    digest = hashlib.sha256(base64.b64decode(build_chromium.KEY)).hexdigest()[:32]
    derived = "".join(chr(ord("a") + int(c, 16)) for c in digest)
    assert derived == install_host.CHROMIUM_ID == build_chromium.CHROMIUM_ID


def test_chromium_build(tmp_path):
    folders = build_chromium.build(tmp_path)
    assert [f.name for f in folders] == ["chrome", "edge"]
    text = (tmp_path / "chrome" / "manifest.json").read_text(encoding="utf-8")
    m = json.loads(text)
    assert "browser_specific_settings" not in m
    assert m["background"] == {"service_worker": "background.js", "type": "module"}
    assert "contextMenus" in m["permissions"] and "menus" not in m["permissions"]
    assert m["key"] == build_chromium.KEY
    assert (tmp_path / "edge" / "compat.js").is_file()
    assert (tmp_path / "edge" / "manifest.json").read_text(encoding="utf-8") == text
