from lxml import etree
from xmsh.control import cmd_print, cmd_save, cmd_find, cmd_add, cmd_lsattr, cmd_delattr, cmd_set, cmd_get, cmd_cd, cmd_cp, cmd_rm, cmd_mv, cmd_tree, cmd_text, CommandResult
from xmsh.model import VirtualFileSystem


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
    
    def print(self, path=None, pretty=True):
            node = self.cwd if path is None else self.get_node_by_path(path)

            return etree.tostring(
                node,
                pretty_print=pretty,
                encoding="unicode",
                xml_declaration=False
            ).strip()

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


def test_cmd_find_no_args():
    vfs = MockVFS(build_tree())
    result = cmd_find([], vfs)
    assert result.error == "Usage: find <xpath>"
    assert result.status == "error"

def test_cmd_find_no_matches():
    vfs = MockVFS(build_tree())
    result = cmd_find(["nonexistenttag"], vfs)
    assert result.status == "ok"
    assert result.output == "No matches found."

def test_cmd_find_multiple_matches():
    vfs = MockVFS(build_tree())
    # Assuming build_tree() creates nodes with tags 'a', 'b', etc.
    result = cmd_find(["//*"], vfs)  # Match all elements
    assert result.status == "ok"
    paths = result.output.split('\n')
    assert all(p.startswith("/") for p in paths)
    assert len(paths) > 1  # Should find multiple nodes

def test_cmd_find_with_invalid_build_path(monkeypatch):
    vfs = MockVFS(build_tree())

    # Force build_path to raise for one node
    orig_build_path = vfs.build_path
    def faulty_build_path(node):
        if node.tag == 'a':
            raise Exception("fail")
        return orig_build_path(node)

    vfs.build_path = faulty_build_path

    result = cmd_find(["//*"], vfs)
    assert result.status == "ok"
    assert "a" not in result.output  # 'a' node paths skipped due to error


def test_cmd_cp_success():
    vfs = MockVFS(build_tree())
    result = cmd_cp(["/a", "/b"], vfs)
    assert isinstance(result, CommandResult)
    assert "Copied 'a' to '/b'" in result.output
    # Confirm that the new child was added
    copied = [child.tag for child in vfs.get_node_by_path("/b")]
    assert "a" in copied

def test_cmd_cp_nonexistent_source():
    vfs = MockVFS(build_tree())
    result = cmd_cp(["/nonexistent", "/b"], vfs)
    assert isinstance(result, CommandResult)
    assert result.status == "error"
    assert "source not found" in result.error

def test_cmd_cp_nonexistent_target():
    vfs = MockVFS(build_tree())
    result = cmd_cp(["/a", "/nonexistent"], vfs)
    assert isinstance(result, CommandResult)
    assert result.status == "error"
    assert "target not found" in result.error

def test_cmd_cp_into_descendant():
    vfs = MockVFS(build_tree())
    result = cmd_cp(["/b", "/b/b1"], vfs)
    assert isinstance(result, CommandResult)
    assert result.status == "error"
    assert "Cannot copy a node into one of its own descendants" in result.error

def test_cmd_cp_usage_error():
    vfs = MockVFS(build_tree())
    result = cmd_cp(["only_one_argument"], vfs)
    assert isinstance(result, CommandResult)
    assert result.status == "error"
    assert "Usage: cp <source> <target>" in result.error


def test_cmd_mv_to_new_parent():
    vfs = MockVFS(build_tree())
    assert vfs.get_node_by_path("/b/b1").getparent().tag == "b"
    result = cmd_mv(["/b/b1", "/a"], vfs)
    assert result.output == "Moved 'b1' as last child of 'a'"
    assert vfs.get_node_by_path("/a/b1") is not None

def test_cmd_mv_reorder_among_siblings():
    vfs = MockVFS(build_tree())
    parent = vfs.get_node_by_path("/b")
    children_before = [child.tag for child in parent]
    assert children_before == ["b1", "b2"]
    result = cmd_mv(["/b/b2", "1"], vfs)
    assert result.output == "Moved 'b2' to position 1 under parent 'b'"
    children_after = [child.tag for child in parent]
    assert children_after == ["b2", "b1"]

def test_cmd_mv_root():
    vfs = MockVFS(build_tree())
    result = cmd_mv(["/", "/a"], vfs)
    assert "cannot move root" in result.error

def test_cmd_mv_invalid_source():
    vfs = MockVFS(build_tree())
    result = cmd_mv(["/invalid", "/a"], vfs)
    assert "source not found" in result.error

def test_cmd_mv_invalid_target():
    vfs = MockVFS(build_tree())
    result = cmd_mv(["/a", "/invalid"], vfs)
    assert "target not found" in result.error

def test_cmd_mv_into_self():
    vfs = MockVFS(build_tree())
    result = cmd_mv(["/a", "/a"], vfs)
    assert "source and target are the same node" in result.error

def test_cmd_mv_into_descendant():
    vfs = MockVFS(build_tree())
    result = cmd_mv(["/b", "/b/b1"], vfs)
    assert "cannot move a node into one of its descendants" in result.error

def test_cmd_mv_cwd_or_ancestor():
    vfs = MockVFS(build_tree())
    vfs.cwd = vfs.get_node_by_path("/b/b1")  # cwd is descendant of /b
    result = cmd_mv(["/b", "/a"], vfs)
    assert "Cannot move current directory or one of its ancestors" in result.error


def test_cmd_save_default(tmp_path):
    # Prepare a sample file to mount
    sample_path = tmp_path / "sample.xml"
    sample_path.write_text("<root><a/></root>", encoding="utf-8")

    vfs = VirtualFileSystem()
    vfs.mount("sample", str(sample_path))
    vfs.cwd = vfs.get_node_by_path("/sample")

    result = cmd_save([], vfs)
    assert isinstance(result, CommandResult)
    assert result.status == "ok"
    assert "Saved 'sample'" in result.output
    assert sample_path.exists()

def test_cmd_save_raw(tmp_path):
    sample_path = tmp_path / "sample.xml"
    sample_path.write_text("<root><a/></root>", encoding="utf-8")

    vfs = VirtualFileSystem()
    vfs.mount("sample", str(sample_path))
    vfs.cwd = vfs.get_node_by_path("/sample")

    result = cmd_save(["--raw"], vfs)
    assert result.status == "ok"
    assert "Saved 'sample'" in result.output

def test_cmd_save_to_new_filepath(tmp_path):
    original = tmp_path / "orig.xml"
    original.write_text("<root><a/></root>", encoding="utf-8")

    newpath = tmp_path / "new.xml"

    vfs = VirtualFileSystem()
    vfs.mount("sample", str(original))
    vfs.cwd = vfs.get_node_by_path("/sample")

    result = cmd_save([str(newpath)], vfs)
    assert result.status == "ok"
    assert newpath.exists()

def test_cmd_save_error(tmp_path, monkeypatch):
    sample_path = tmp_path / "sample.xml"
    sample_path.write_text("<root><a/></root>", encoding="utf-8")

    vfs = VirtualFileSystem()
    vfs.mount("sample", str(sample_path))
    vfs.cwd = vfs.get_node_by_path("/sample")

    # Simulate save failing
    monkeypatch.setattr(vfs, "save", lambda filepath, pretty: (_ for _ in ()).throw(Exception("fail")))

    result = cmd_save([], vfs)
    assert result.status == "error"
    assert "Error saving: fail" in result.error


def test_cmd_print_cwd():
    vfs = MockVFS(build_tree())
    result = cmd_print([], vfs)
    assert result.status == "ok"
    assert "<root" in result.output  # Expect element tag present

def test_cmd_print_specific_path():
    vfs = MockVFS(build_tree())
    result = cmd_print(["/a"], vfs)
    assert result.status == "ok"
    assert "<a" in result.output

def test_cmd_print_raw():
    vfs = MockVFS(build_tree())
    result = cmd_print(["--raw"], vfs)
    assert result.status == "ok"
    assert result.output.strip().startswith("<root")  # Checks raw XML begins correctly

def test_cmd_print_invalid_path():
    vfs = MockVFS(build_tree())
    result = cmd_print(["/nonexistent"], vfs)
    assert result.status == "error"
    assert "Error printing" in result.error

def test_cmd_print_invalid_usage():
    vfs = MockVFS(build_tree())
    result = cmd_print(["--raw", "/nonexistent"], vfs)
    assert result.status == "error"
    assert "Error printing" in result.error
