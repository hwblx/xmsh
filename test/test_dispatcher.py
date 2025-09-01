import pytest
from lxml import etree
from xmsh.dispatcher import cmd_cd, cmd_cp, cmd_rm, cmd_mv

from lxml import etree

class MockVFS:
    def __init__(self, root):
        self.root = root
        self.cwd = root

    def get_node_by_path(self, path):
        if path is None:
            return self.cwd

        # Support absolute and relative paths
        if path.startswith("/"):
            node = self.root
        else:
            node = self.cwd

        for part in path.strip("/").split("/"):
            if not part:
                continue
            found = False
            for child in node:
                if child.tag == part:
                    node = child
                    found = True
                    break
            if not found:
                raise ValueError(f"Path not found: {path}")
        return node

    def build_path(self, node):
        # Rebuilds path from root to node using tags
        parts = []
        while node is not None and node != self.root:
            parts.insert(0, node.tag)
            node = node.getparent()
        return "/" + "/".join(parts) if parts else "/root"

    def cp_node(self, src_node, dest_node):
        # Deep copy the node and append to destination
        from copy import deepcopy
        dest_node.append(deepcopy(src_node))

    def unmount(self, name):
        # Not needed for current tests
        pass

    def save(self, filepath, pretty=True):
        return "Saved"

    def print(self, path, pretty=True):
        print(f"[MockPrint] {path}")

def build_tree():
    """
    <root>
        <a/>
        <b>
            <b1/>
            <b2/>
        </b>
        <c/>
    </root>
    """
    root = etree.Element("root")
    etree.SubElement(root, "a")
    b = etree.SubElement(root, "b")
    etree.SubElement(b, "b1")
    etree.SubElement(b, "b2")
    etree.SubElement(root, "c")
    return root

def test_cd_path():
    vfs = MockVFS(build_tree())
    result = cmd_cd(["b"], vfs)
    assert result is None
    assert vfs.cwd.tag == "b"

def test_cd_up():
    vfs = MockVFS(build_tree())
    vfs.cwd = vfs.get_node_by_path("/b/b1")
    result = cmd_cd([".."], vfs)
    assert result is None
    assert vfs.cwd.tag == "b"

def test_cd_up_twice():
    vfs = MockVFS(build_tree())
    vfs.cwd = vfs.get_node_by_path("/b/b1")
    result = cmd_cd(["..", "2"], vfs)
    assert result is None
    assert vfs.cwd.tag == "root"

def test_cd_up_past_root():
    vfs = MockVFS(build_tree())
    result = cmd_cd(["..", "2"], vfs)
    assert result == "Already at root, cannot go up"
    assert vfs.cwd.tag == "root"

def test_cd_next_sibling():
    vfs = MockVFS(build_tree())
    vfs.cwd = vfs.get_node_by_path("/a")
    result = cmd_cd(["+"], vfs)
    assert result is None
    assert vfs.cwd.tag == "b"

def test_cd_prev_sibling():
    vfs = MockVFS(build_tree())
    vfs.cwd = vfs.get_node_by_path("/c")
    result = cmd_cd(["-"], vfs)
    assert result is None
    assert vfs.cwd.tag == "b"

def test_cd_invalid_path():
    vfs = MockVFS(build_tree())
    result = cmd_cd(["/nonexistent"], vfs)
    assert "Error:" in result


def test_cp_success():
    vfs = MockVFS(build_tree())
    result = cmd_cp(["/b/b1", "/c"], vfs)
    assert result.startswith("Copied 'b1' to '/c'")

    # Verify copied element exists
    c_node = vfs.get_node_by_path("/c")
    copied_tags = [child.tag for child in c_node]
    assert "b1" in copied_tags

def test_cp_nonexistent_source():
    vfs = MockVFS(build_tree())
    result = cmd_cp(["/notfound", "/c"], vfs)
    assert "Error: source not found" in result

def test_cp_nonexistent_target():
    vfs = MockVFS(build_tree())
    result = cmd_cp(["/b/b1", "/notfound"], vfs)
    assert "Error: target not found" in result

def test_cp_into_descendant():
    vfs = MockVFS(build_tree())
    result = cmd_cp(["/b", "/b/b1"], vfs)
    assert "Cannot copy a node into one of its own descendants" in result

def test_rm_success():
    vfs = MockVFS(build_tree())
    assert vfs.get_node_by_path("/b/b1") is not None
    result = cmd_rm(["/b/b1"], vfs)
    assert result == "Removed <b1> from /b"

    with pytest.raises(ValueError):
        vfs.get_node_by_path("/b/b1")

def test_rm_root():
    root = build_tree()
    vfs = MockVFS(root)
    assert vfs.get_node_by_path("/") is vfs.root  # Confirm identity
    result = cmd_rm(["/"], vfs)
    assert "Cannot remove root" in result

def test_rm_invalid_path():
    vfs = MockVFS(build_tree())
    result = cmd_rm(["/invalid/path"], vfs)
    assert "Invalid path:" in result

def test_rm_cwd_or_ancestor():
    root = build_tree()
    vfs = MockVFS(root)
    vfs.cwd = vfs.get_node_by_path("/b/b1")  # cwd is a descendant of /b
    result = cmd_rm(["/b"], vfs)
    assert "Cannot remove current directory or one of its ancestors" in result


def test_mv_to_new_parent():
    vfs = MockVFS(build_tree())
    src_path = "/b/b1"
    dest_path = "/c"

    # Move b1 under c
    result = cmd_mv([src_path, dest_path], vfs)
    assert result == "Moved 'b1' as last child of 'c'"

    # b1 should no longer exist under b
    b_children = [child.tag for child in vfs.get_node_by_path("/b")]
    assert "b1" not in b_children

    # b1 should now exist under c
    c_children = [child.tag for child in vfs.get_node_by_path("/c")]
    assert "b1" in c_children

def test_mv_reorder_among_siblings():
    vfs = MockVFS(build_tree())
    
    # Move b2 to index 1 under parent b (i.e., before b1)
    result = cmd_mv(["/b/b2", "1"], vfs)
    assert result == "Moved 'b2' to position 1 under parent 'b'"

    b = vfs.get_node_by_path("/b")
    child_tags = [child.tag for child in b]
    assert child_tags == ["b2", "b1"]

def test_mv_root():
    root = build_tree()
    vfs = MockVFS(root)
    assert vfs.get_node_by_path("/") is vfs.root  # Confirm identity
    result = cmd_mv(["/", "/b"], vfs)
    assert "cannot move root" in result

def test_mv_invalid_source():
    vfs = MockVFS(build_tree())
    result = cmd_mv(["/nope", "/c"], vfs)
    assert "Error: source not found" in result

def test_mv_invalid_target():
    vfs = MockVFS(build_tree())
    result = cmd_mv(["/b/b1", "/nope"], vfs)
    assert "Error: target not found" in result

def test_mv_into_self():
    vfs = MockVFS(build_tree())
    result = cmd_mv(["/b", "/b"], vfs)
    assert "source and target are the same node" in result

def test_mv_into_descendant():
    vfs = MockVFS(build_tree())
    result = cmd_mv(["/b", "/b/b1"], vfs)
    assert "cannot move a node into one of its descendants" in result

def test_mv_cwd_or_ancestor():
    vfs = MockVFS(build_tree())
    vfs.cwd = vfs.get_node_by_path("/b/b1")
    result = cmd_mv(["/b", "/c"], vfs)
    assert "Cannot move current directory or one of its ancestors" in result

