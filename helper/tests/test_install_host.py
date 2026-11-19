import base64
import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "helper"))
sys.path.insert(0, str(ROOT / "tools"))

import install_host  # noqa: E402
import package_stores  # noqa: E402

FIREFOX_KEY = r"Software\Mozilla\NativeMessagingHosts\quick_web_clip"
CHROME_KEY = r"Software\Google\Chrome\NativeMessagingHosts\quick_web_clip"
EDGE_KEY = r"Software\Microsoft\Edge\NativeMessagingHosts\quick_web_clip"
DEV_ID = "kcdeoockaleljccbljbelmpehlnnceop"
FIREFOX_IDS = {"browser": "firefox", "ids": {"addon": "quick-web-clip@local"}}
CHROME_IDS = {"browser": "chrome", "ids": {"development": DEV_ID, "store": ""}}
EDGE_IDS = {"browser": "edge", "ids": {"development": DEV_ID, "store": ""}}


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


def test_firefox_manifest(tmp_path):
    assert install_host.build_manifest(tmp_path, FIREFOX_IDS) == {
        "name": "quick_web_clip",
        "description": "Quick Web Clip helper",
        "path": str(tmp_path / "clipper_host.bat"),
        "type": "stdio",
        "allowed_extensions": ["quick-web-clip@local"],
    }


def test_chromium_manifest_names_origins(tmp_path):
    for ids in (CHROME_IDS, EDGE_IDS):
        m = install_host.build_manifest(tmp_path, ids)
        assert m["allowed_origins"] == [f"chrome-extension://{DEV_ID}/"]
        assert "allowed_extensions" not in m
        assert m["path"] == str(tmp_path / "clipper_host.bat")


def test_install_registers_only_its_own_browser(tmp_path):
    for ids, key_path in ((FIREFOX_IDS, FIREFOX_KEY), (CHROME_IDS, CHROME_KEY), (EDGE_IDS, EDGE_KEY)):
        reg = FakeReg()
        path = install_host.install(tmp_path, reg=reg, ids=ids)
        assert path == tmp_path / "quick_web_clip.json"
        assert json.loads(path.read_text(encoding="utf-8")) == install_host.build_manifest(tmp_path, ids)
        assert reg.created == [("HKCU", key_path)]
        assert reg.values == [(("key", key_path), "", 1, str(path))]


def test_uninstall_removes_only_its_own_key_and_files(tmp_path):
    reg = FakeReg()
    install_host.install(tmp_path, reg=reg, ids=EDGE_IDS)
    (tmp_path / "quick_web_clip_chromium.json").write_text("{}", encoding="utf-8")  # left by 1.4.0 to 1.5.0
    install_host.uninstall(tmp_path, reg=reg, ids=EDGE_IDS)
    assert reg.deleted == [("HKCU", EDGE_KEY)]
    assert not (tmp_path / "quick_web_clip.json").exists()
    assert not (tmp_path / "quick_web_clip_chromium.json").exists()


def test_uninstall_tolerates_missing(tmp_path):
    install_host.uninstall(tmp_path, reg=FakeReg(missing_on_delete=True), ids=CHROME_IDS)


def test_store_id_is_allowed_once_filled_in(tmp_path):
    ids = json.loads(json.dumps(CHROME_IDS))
    ids["ids"]["store"] = "abcdefghijklmnopabcdefghijklmnop"
    assert install_host.build_manifest(tmp_path, ids)["allowed_origins"] == [
        f"chrome-extension://{DEV_ID}/",
        "chrome-extension://abcdefghijklmnopabcdefghijklmnop/",
    ]
    ids["ids"]["store"] = DEV_ID
    assert len(install_host.build_manifest(tmp_path, ids)["allowed_origins"]) == 1


def test_bad_ids_file_is_refused(tmp_path):
    path = tmp_path / "extension_ids.json"
    bad_files = [
        {"browser": "chrome", "ids": {"store": "KCDEOOCKALELJCCBLJBELMPEHLNNCEOP"}},
        {"browser": "edge", "ids": {"store": "short"}},
        {"browser": "chrome", "ids": {"store": f"chrome-extension://{DEV_ID}/"}},
        {"browser": "safari", "ids": {"store": DEV_ID}},
        {"browser": "chrome", "ids": {"development": "", "store": ""}},
    ]
    for bad in bad_files:
        path.write_text(json.dumps(bad), encoding="utf-8")
        try:
            install_host.load_ids(path)
        except ValueError:
            pass
        else:
            raise AssertionError(bad)


def test_committed_ids_file_matches_the_manifest():
    ids = install_host.load_ids()
    manifest = json.loads((ROOT / "extension" / "manifest.json").read_text(encoding="utf-8"))
    if ids["browser"] == "firefox":
        assert ids["ids"]["addon"] == manifest["browser_specific_settings"]["gecko"]["id"]
        assert "key" not in manifest
    else:
        # The ID Chrome and Edge derive from the manifest key must be the one the helper allows.
        digest = hashlib.sha256(base64.b64decode(manifest["key"])).hexdigest()[:32]
        derived = "".join(chr(ord("a") + int(c, 16)) for c in digest)
        assert derived == ids["ids"]["development"]
        assert manifest["background"] == {"service_worker": "background.js", "type": "module"}
        assert "browser_specific_settings" not in manifest
        assert "contextMenus" in manifest["permissions"] and "menus" not in manifest["permissions"]


def test_store_zips(tmp_path):
    zips = package_stores.package(tmp_path)
    browser = install_host.load_ids()["browser"]
    version = json.loads((package_stores.SOURCE / "manifest.json").read_text(encoding="utf-8"))["version"]
    assert [z.name for z in zips] == [f"quick-web-clip-{b}-{version}.zip" for b in (browser, "helper")]
    with zipfile.ZipFile(zips[1]) as f:
        names = f.namelist()
    assert "quick-web-clip-helper/install.bat" in names and "quick-web-clip-helper/LICENSE" in names
    assert "quick-web-clip-helper/extension_ids.json" in names
    assert not any("venv" in n or n.endswith(".log") or "tests" in n for n in names)
    with zipfile.ZipFile(zips[0]) as f:
        names = f.namelist()
        m = json.loads(f.read("manifest.json"))
    assert "manifest.json" in names and "background.js" in names and "icons/icon-128.png" in names
    assert not any(n.startswith("/") or "\\" in n or n.endswith((".amo-upload-uuid", ".zip", ".xpi")) for n in names)
    assert "key" not in m and m["version"] == version
