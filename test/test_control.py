import pytest
from lxml import etree
from xmsh.control import cmd_add, cmd_lsattr, cmd_delattr, cmd_set, cmd_get, cmd_cd, cmd_cp, cmd_rm, cmd_mv, cmd_tree, cmd_text, CommandResult


class MockVFS:
    def __init__(self, root):
        self.root = root
        self.cwd = root
        self.mounts = {}

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
    assert isinstance(result, CommandResult)
    assert result.error == "Already at root, cannot go up"
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
    assert isinstance(result, CommandResult)
    assert "Error:" in result.error or result.error.startswith("Error")


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


def test_cmd_tree():
    vfs = MockVFS(build_tree())
    vfs.cwd = vfs.get_node_by_path("/b")
    result = cmd_tree([], vfs)
    assert isinstance(result, CommandResult)
    assert "b" in result.output
    assert "b1" in result.output

def test_cmd_tree_no_mount():
    vfs = MockVFS(build_tree())
    vfs.cwd = None
    result = cmd_tree([], vfs)
    assert result.error == "Nothing mounted. Use 'mount' first."


def test_cmd_text_get():
    vfs = MockVFS(build_tree())
    vfs.cwd = vfs.get_node_by_path("/a")
    vfs.cwd.text = "Hello"
    result = cmd_text([], vfs)
    assert result.output == "Hello"

def test_cmd_text_set():
    vfs = MockVFS(build_tree())
    vfs.cwd = vfs.get_node_by_path("/a")
    result = cmd_text(["New", "text"], vfs)
    assert result.output == "a text set to: New text"
    assert vfs.cwd.text == "New text"

def test_cmd_text_set_empty_quotes():
    vfs = MockVFS(build_tree())
    vfs.cwd = vfs.get_node_by_path("/a")
    vfs.cwd.text = "Old"
    result = cmd_text(["''"], vfs)
    assert result.output == "a text set to: None"
    assert vfs.cwd.text is None

def test_cmd_text_no_cwd():
    vfs = MockVFS(build_tree())
    vfs.cwd = None
    result = cmd_text(["text"], vfs)
    assert result.status == "error"
    assert "No current node" in result.error


def test_cmd_get_attr_on_cwd():
    vfs = MockVFS(build_tree())
    vfs.cwd.set("foo", "bar")
    result = cmd_get(["foo"], vfs)
    assert isinstance(result, CommandResult)
    assert result.output == "bar"

def test_cmd_get_attr_on_path():
    vfs = MockVFS(build_tree())
    node = vfs.get_node_by_path("/b")
    node.set("baz", "qux")
    result = cmd_get(["/b", "baz"], vfs)
    assert isinstance(result, CommandResult)
    assert result.output == "qux"

def test_cmd_get_missing_attr():
    vfs = MockVFS(build_tree())
    result = cmd_get(["nonexistent"], vfs)
    assert isinstance(result, CommandResult)
    assert "not found" in result.error

def test_cmd_get_invalid_usage():
    vfs = MockVFS(build_tree())
    result = cmd_get([], vfs)  # no args
    assert isinstance(result, CommandResult)
    assert "Usage" in result.error

def test_cmd_get_invalid_path():
    vfs = MockVFS(build_tree())
    result = cmd_get(["/invalidpath", "foo"], vfs)
    assert isinstance(result, CommandResult)
    assert "Error" in result.error


def test_cmd_set_attr_on_cwd():
    vfs = MockVFS(build_tree())
    result = cmd_set(["foo", "bar"], vfs)
    assert isinstance(result, CommandResult)
    assert "Set attribute 'foo'" in result.output
    assert vfs.cwd.get("foo") == "bar"

def test_cmd_set_attr_on_path():
    vfs = MockVFS(build_tree())
    result = cmd_set(["/b", "baz", "qux"], vfs)
    node = vfs.get_node_by_path("/b")
    assert isinstance(result, CommandResult)
    assert "Set attribute 'baz'" in result.output
    assert node.get("baz") == "qux"

def test_cmd_set_invalid_usage():
    vfs = MockVFS(build_tree())
    result = cmd_set(["only_one_arg"], vfs)
    assert isinstance(result, CommandResult)
    assert "Usage" in result.error

def test_cmd_set_invalid_path():
    vfs = MockVFS(build_tree())
    result = cmd_set(["/invalidpath", "foo", "bar"], vfs)
    assert isinstance(result, CommandResult)
    assert "Error" in result.error


def test_cmd_delattr_on_cwd():
    vfs = MockVFS(build_tree())
    vfs.cwd.set("foo", "bar")
    result = cmd_delattr(["foo"], vfs)
    assert isinstance(result, CommandResult)
    assert result.output == "Deleted attribute 'foo' from node 'root'"
    assert "foo" not in vfs.cwd.attrib

def test_cmd_delattr_on_path():
    vfs = MockVFS(build_tree())
    node = vfs.get_node_by_path("/b")
    node.set("baz", "qux")
    result = cmd_delattr(["/b", "baz"], vfs)
    assert isinstance(result, CommandResult)
    assert result.output == "Deleted attribute 'baz' from node 'b'"
    assert "baz" not in node.attrib

def test_cmd_delattr_missing_attribute():
    vfs = MockVFS(build_tree())
    result = cmd_delattr(["nonexistent"], vfs)
    assert isinstance(result, CommandResult)
    assert "not found" in result.error

def test_cmd_delattr_invalid_path():
    vfs = MockVFS(build_tree())
    result = cmd_delattr(["/invalidpath", "foo"], vfs)
    assert isinstance(result, CommandResult)
    assert "Error" in result.error

def test_cmd_delattr_invalid_usage():
    vfs = MockVFS(build_tree())
    result = cmd_delattr([], vfs)
    assert isinstance(result, CommandResult)
    assert "Usage" in result.error


def test_cmd_lsattr_on_cwd():
    vfs = MockVFS(build_tree())
    vfs.cwd.set("foo", "bar")
    result = cmd_lsattr([], vfs)
    assert isinstance(result, CommandResult)
    assert "foo='bar'" in result.output

def test_cmd_lsattr_on_path():
    vfs = MockVFS(build_tree())
    node = vfs.get_node_by_path("/b")
    node.set("baz", "qux")
    result = cmd_lsattr(["/b"], vfs)
    assert isinstance(result, CommandResult)
    assert "baz='qux'" in result.output

def test_cmd_lsattr_no_attributes():
    vfs = MockVFS(build_tree())
    result = cmd_lsattr([], vfs)
    assert isinstance(result, CommandResult)
    assert "No attributes" in result.output

def test_cmd_lsattr_invalid_path():
    vfs = MockVFS(build_tree())
    result = cmd_lsattr(["/invalidpath"], vfs)
    assert isinstance(result, CommandResult)
    assert "Path not found" in result.error

def test_cmd_lsattr_invalid_usage():
    vfs = MockVFS(build_tree())
    result = cmd_lsattr(["/b", "extra_arg"], vfs)
    assert isinstance(result, CommandResult)
    assert "Usage" in result.error


def test_cmd_add_default_append():
    vfs = MockVFS(build_tree())
    result = cmd_add(["newtag"], vfs)
    assert result.output == "Added <newtag> under <root>"
    assert vfs.cwd[-1].tag == "newtag"

def test_cmd_add_at_index():
    vfs = MockVFS(build_tree())
    result = cmd_add(["newtag", "1"], vfs)
    assert result.output == "Added <newtag> under <root>"
    assert vfs.cwd[0].tag == "newtag"

def test_cmd_add_invalid_index():
    vfs = MockVFS(build_tree())
    result = cmd_add(["newtag", "0"], vfs)
    assert "Index must be 1 or greater" in result.error

def test_cmd_add_out_of_bounds():
    vfs = MockVFS(build_tree())
    result = cmd_add(["newtag", "99"], vfs)
    assert "out of bounds" in result.error

def test_cmd_add_missing_tag():
    vfs = MockVFS(build_tree())
    result = cmd_add([], vfs)
    assert "Usage" in result.error


def test_cmd_rm_success():
    vfs = MockVFS(build_tree())
    assert vfs.get_node_by_path("/b/b1") is not None
    result = cmd_rm(["/b/b1"], vfs)
    assert result.output == "Removed <b1> from /b"

def test_cmd_rm_root():
    root = build_tree()
    vfs = MockVFS(root)
    assert vfs.get_node_by_path("/") is vfs.root
    result = cmd_rm(["/"], vfs)
    assert "Cannot remove root" in result.error

def test_cmd_rm_invalid_path():
    vfs = MockVFS(build_tree())
    result = cmd_rm(["/invalid/path"], vfs)
    assert "Invalid path:" in result.error

def test_cmd_rm_cwd_or_ancestor():
    vfs = MockVFS(build_tree())
    vfs.cwd = vfs.get_node_by_path("/b/b1")
    result = cmd_rm(["/b"], vfs)
    assert "Cannot remove current directory or one of its ancestors" in result.error

def test_cmd_rm_cwd():
    vfs = MockVFS(build_tree())
    vfs.cwd = vfs.get_node_by_path("/b")
    result = cmd_rm(["/b"], vfs)  # ← add vfs here
    assert "Cannot remove current directory" in result.error

def test_cmd_rm_unmounts_root_child():
    vfs = MockVFS(build_tree())
    vfs.mounts["a"] = "dummyfile.html"  # Simulate mounted node
    assert "a" in vfs.mounts
    result = cmd_rm(["/a"], vfs)
    assert result.output == "Removed <a> from /"
    assert "a" not in vfs.mounts  # Confirm unmounted

