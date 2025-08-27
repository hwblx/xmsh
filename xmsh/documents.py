"""Implements a virtual file system for navigating XML/HTML documents."""

from lxml import etree, html
import os

class VirtualFileSystem:
    """Represents a virtual file system for XML/HTML tree navigation."""

    def __init__(self):
        """Initialize the root element and set current working directory."""
        self.root = etree.Element("vfs-root")
        self.cwd = self.root  # current working directory node

    def mount(self, name, filepath):
        """Mount a file under the given name into the virtual file system."""
        ext = os.path.splitext(filepath)[1].lower()
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        if ext in ('.html', '.htm'):
            parsed_root = html.fromstring(content)
        else:
            parser = etree.XMLParser(recover=True)
            parsed_root = etree.fromstring(content, parser=parser)

        existing = self.root.find(name)
        if existing is not None:
            raise ValueError(f"Mount '{name}' already exists")

        mount_wrapper = etree.SubElement(self.root, name)
        mount_wrapper.append(parsed_root)

    def unmount(self, name):
        """Unmount a mounted document by name."""
        mount_node = self.root.find(name)
        if mount_node is None:
            raise ValueError(f"No such mount '{name}'")
        self.root.remove(mount_node)
        if self.is_ancestor(mount_node, self.cwd):
            self.cwd = self.root

    def is_ancestor(self, ancestor, node):
        """Return True if ancestor is node or any of its parents."""
        current = node
        while current is not None:
            if current == ancestor:
                return True
            current = current.getparent()
        return False

    def get_node_by_path(self, path):
        """Resolve a path string to an element, supporting navigation features."""
        if not path or path == '.':
            return self.cwd

        if path.startswith('/'):
            current = self.root
            parts = path.strip('/').split('/')
        else:
            current = self.cwd
            parts = path.split('/')

        for part in parts:
            if part == '..':
                parent = current.getparent()
                if parent is None:
                    raise ValueError("Already at root, cannot go up")
                current = parent
            elif part == '.' or part == '':
                pass
            else:
                if '[' in part and part.endswith(']'):
                    tag = part[:part.index('[')]
                    try:
                        index = int(part[part.index('[')+1:-1])
                    except:
                        raise ValueError(f"Invalid index in path segment '{part}'")
                else:
                    tag = part
                    index = 1

                children = [c for c in current if c.tag == tag]
                if len(children) < index or index < 1:
                    raise ValueError(f"No such child '{part}' under '{current.tag}'")
                current = children[index-1]

        return current

    def ls(self, path=None):
        """List child element tags under the specified or current node."""
        node = self.get_node_by_path(path) if path else self.cwd
        children = list(node)

        if not children:
            return "(empty)"

        tag_counts = {}
        lines = []
        for child in children:
            tag_counts[child.tag] = tag_counts.get(child.tag, 0) + 1

        tag_seen = {}
        for child in children:
            count = tag_counts[child.tag]
            tag_seen[child.tag] = tag_seen.get(child.tag, 0) + 1
            if count > 1:
                lines.append(f"{child.tag}[{tag_seen[child.tag]}]")
            else:
                lines.append(child.tag)
        return ' '.join(lines)

    def build_path(self, node):
        """Build a full path string from root to the given node."""
        parts = []
        current = node

        while current is not None and current != self.root:
            parent = current.getparent()
            if parent is None:
                break
            siblings = [c for c in parent if c.tag == current.tag]
            if len(siblings) > 1:
                index = siblings.index(current) + 1
                parts.append(f"{current.tag}[{index}]")
            else:
                parts.append(current.tag)
            current = parent

        parts.reverse()
        return "/" + "/".join(parts) if parts else "/"

