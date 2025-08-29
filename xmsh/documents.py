"""Implements a virtual file system for navigating XML/HTML documents."""

from copy import deepcopy
from urllib.parse import urlparse

from lxml import etree, html
import requests

try:
    from rich.syntax import Syntax
    from rich.console import Console
    console = Console()
except ImportError:
    console = None


class VirtualFileSystem:
    """Represents a virtual file system for XML/HTML tree navigation."""

    def __init__(self):
        """Initialize the root element and set current working directory."""
        self.root = etree.Element("vfs-root")
        self.cwd = self.root  # current working directory node
        self.mounts = {}

    def mount(self, name, filepath):
        """Mount a file under the given name into the virtual file system."""
        
        if self.root.find(name) is not None:
            raise ValueError(f"Mount '{name}' already exists")

        if filepath.lower().endswith('.html'):
            parsed_root = html.parse(filepath).getroot()
        elif filepath.lower().endswith('.xml'):
            parsed_root = etree.parse(filepath).getroot()
        else:
            print("Only .html and .xml files are supported")

        mount_point = etree.SubElement(self.root, name)
        mount_point.append(parsed_root)
        self.mounts[name] = filepath

    def get_mount_name_for_node(self, node):
        current = node
        while current is not None and current != self.root:
            if current.getparent() == self.root:
                return current.tag
            current = current.getparent()
        return None

    def unmount(self, name):
        """Unmount a mounted document by name."""
        mount_node = self.root.find(name)
        if mount_node is None:
            raise ValueError(f"No such mount '{name}'")

        # Check if the current working node is under the mount being removed
        current = self.cwd
        while current is not None:
            if current == mount_node:
                self.cwd = self.root
                break
            current = current.getparent()

        self.root.remove(mount_node)

    def get_node_by_path(self, path):
        """
        Resolve a VFS path to an element node.
        Supports:
          - Absolute and relative paths
          - Parent references (..)
          - Indexed tags (e.g., div[2])
        """

        def split_path(p):
            return p.strip('/').split('/')

        def get_parent_or_error(node):
            parent = node.getparent()
            if parent is None:
                raise ValueError("Already at root, cannot go up")
            return parent

        def parse_tag_with_index(part):
            if '[' in part and part.endswith(']'):
                tag = part[:part.index('[')]
                try:
                    index = int(part[part.index('[') + 1:-1])
                except ValueError:
                    raise ValueError(f"Invalid index in path segment '{part}'")
            else:
                tag = part
                index = 1
            return tag, index

        def get_child_by_tag_and_index(node, tag, index):
            matches = [c for c in node if c.tag == tag]
            if index < 1 or index > len(matches):
                raise ValueError(f"No such child '{tag}[{index}]' under '{node.tag}'")
            return matches[index - 1]

        # Main logic
        if not path or path == '.':
            return self.cwd

        current = self.root if path.startswith('/') else self.cwd
        parts = split_path(path)

        for part in parts:
            if part in ('', '.'):
                continue
            elif part == '..':
                current = get_parent_or_error(current)
            else:
                tag, index = parse_tag_with_index(part)
                current = get_child_by_tag_and_index(current, tag, index)

        return current

    def ls(self, path=None):
        """List child element tags under the specified or current node."""
        node = self.get_node_by_path(path) if path else self.cwd
        children = list(node)

        if not children:
            return "(empty)"

        tags = {}
        for child in children:
            tags[child.tag] = tags.get(child.tag, 0) + 1

        seen = {}
        result = []
        for child in children:
            tag = child.tag
            seen[tag] = seen.get(tag, 0) + 1
            count = tags[tag]
            result.append(f"{tag}[{seen[tag]}]" if count > 1 else tag)

        return ' '.join(result)
    
    def build_path(self, node):
        """Build path from root to node, showing indices for duplicate siblings."""

        def tag_with_optional_index(n):
            parent = n.getparent()
            if parent is None:
                return n.tag
            siblings = [c for c in parent if c.tag == n.tag]
            if len(siblings) > 1:
                index = siblings.index(n) + 1
                return f"{n.tag}[{index}]"
            return n.tag

        if node is None:
            raise ValueError("Node is None")

        if node == self.root:
            return "/"

        parts = []
        current = node

        while current is not None and current != self.root:
            parts.append(tag_with_optional_index(current))
            current = current.getparent()

        return "/" + "/".join(reversed(parts))

    def mount_url(self, name, url):
        """Mount an XML/HTML document from a URL under the given name."""

        if self.root.find(name) is not None:
            raise ValueError(f"Mount '{name}' already exists")

        parsed = urlparse(url)
        ext = parsed.path.lower().rsplit('.', 1)[-1]

        if ext not in ('html', 'htm', 'xml'):
            raise ValueError("Only .html, .htm and .xml URLs are supported")

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except Exception as e:
            raise ValueError(f"Failed to fetch URL: {e}")

        content = response.content

        if ext in ('html', 'htm'):
            parsed_root = html.fromstring(content)
        else:  # xml
            parser = etree.XMLParser(recover=True)
            parsed_root = etree.fromstring(content, parser=parser)

        mount_point = etree.SubElement(self.root, name)
        mount_point.append(parsed_root)

    def cp_node(self, src_node, dest_node):
        """Copy src_node and append it to dest_node."""
        new_node = etree.fromstring(etree.tostring(src_node))
        dest_node.append(new_node)

    def save(self, filepath=None, pretty=True):
        """
        Save the XML document for the current mountpoint.

        Args:
            filepath (str or None): Optional path to save to; if None, saves to original mount file.
            pretty (bool): Whether to pretty-print/indent the saved XML.
        """
        mount_name = self.get_mount_name_for_node(self.cwd)
        if not mount_name:
            raise ValueError("Cannot save: no mounted document above current node")

        mount_node = self.root.find(mount_name)
        if mount_node is None or len(mount_node) == 0:
            raise ValueError(f"Mounted node '{mount_name}' is empty or invalid")

        doc_root = mount_node[0]

        if filepath is None:
            filepath = self.mounts.get(mount_name)
            if not filepath:
                raise ValueError(f"No original filepath for mount '{mount_name}'")

        # Deepcopy root to avoid modifying in-memory tree indentation/tail
        doc_copy = deepcopy(doc_root)

        if pretty:
            etree.indent(doc_copy, space="  ")
            xml_data = etree.tostring(doc_copy, pretty_print=True, encoding="utf-8", xml_declaration=True)
        else:
            xml_data = etree.tostring(doc_copy, pretty_print=False, encoding="utf-8", xml_declaration=True)

        with open(filepath, "wb") as f:
            f.write(xml_data)

        # Update mount path if user gave a new filepath
        self.mounts[mount_name] = filepath

        return f"Saved '{mount_name}' to '{filepath}'"

    def print(self, path=None, pretty=True):
        """Pretty-print the given node (or cwd) with optional rich highlighting."""
        try:
            node = self.get_node_by_path(path) if path else self.cwd
        except Exception as e:
            raise ValueError(f"Invalid path: {e}")

        if node is None:
            raise ValueError("No node found to print.")

        method = "html" if isinstance(node, html.HtmlElement) else "xml"

        try:
            # Optionally indent only for pretty mode
            if pretty:
                node_copy = deepcopy(node)
                etree.indent(node_copy, space="  ")
                output_node = node_copy
            else:
                output_node = node

            raw = etree.tostring(
                output_node,
                pretty_print=pretty,
                encoding="unicode",
                method=method,
                with_tail=False,
                xml_declaration=False
            ).strip()

            if console:
                syntax = Syntax(raw, method, theme="github-dark", line_numbers=False)
                console.print(syntax)
            else:
                print(raw)

        except Exception as e:
            raise RuntimeError(f"Error printing node: {e}")
