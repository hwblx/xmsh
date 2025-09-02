import pytest
from xmsh.model import VirtualFileSystem
import os

HTML_CONTENT = "<html><body><h1>Title</h1></body></html>"
XML_CONTENT = "<root><item>1</item></root>"

def create_temp_file(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(content)
    return str(path)

def test_mount_html(tmp_path):
    vfs = VirtualFileSystem()
    html_path = create_temp_file(tmp_path, "/tmp/xmsh_test.html", HTML_CONTENT)
    
    vfs.mount("web", html_path)
    assert "web" in vfs.mounts
    assert vfs.ls("/web").startswith("html")

def test_mount_xml(tmp_path):
    vfs = VirtualFileSystem()
    xml_path = create_temp_file(tmp_path, "/tmp/xmsh_test.xml", XML_CONTENT)
    
    vfs.mount("data", xml_path)
    assert "data" in vfs.mounts
    assert vfs.ls("/data").startswith("root")

def test_mount_invalid_extension(tmp_path):
    vfs = VirtualFileSystem()
    invalid_path = create_temp_file(tmp_path, "/tmp/xmsh_test.txt", "Not valid XML or HTML")

    with pytest.raises(ValueError, match="Only .html and .xml files are supported"):
        vfs.mount("fail", invalid_path)

def test_mount_duplicate(tmp_path):
    vfs = VirtualFileSystem()
    xml_path = create_temp_file(tmp_path, "/tmp/xmsh_test.xml", XML_CONTENT)

    vfs.mount("data", xml_path)

    with pytest.raises(ValueError, match="Mount 'data' already exists"):
        vfs.mount("data", xml_path)

