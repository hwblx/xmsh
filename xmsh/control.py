"""
Command dispatcher for the CLI interface, mapping commands to handlers.

Copyright (c) 2025 hwblx
"""

from lxml import etree
from dataclasses import dataclass
from typing import Optional


@dataclass
class CommandResult:
    output: Optional[str] = None     # What to show in the UI
    error: Optional[str] = None      # Any error message
    data: Optional[object] = None    # Raw data for non-textual views
    status: str = "ok"               # "ok" or "error" or "info", etc.


def cmd_mount(args, vfs):
    """Mount an XML/HTML document at a given name."""
    if len(args) != 2:
        return CommandResult(error="Usage: mount <name> <filepath>", status="error")

    name, filepath = args
    try:
        vfs.mount(name, filepath)
        vfs.cwd = vfs.get_node_by_path(f"/{name}")
        return CommandResult(output=f"Mounted {name} at /{name}")
    except Exception as e:
        return CommandResult(error=f"Error mounting: {e}", status="error")


def cmd_ls(args, vfs):
    path = args[0] if args else None
    try:
        listing = vfs.ls(path)
        return CommandResult(output=listing)
    except Exception as e:
        return CommandResult(error=str(e), status="error")


def cmd_cd(args, vfs):
    """Change current working node to a specified path."""
    if not args:
        return CommandResult(error="Usage: cd <path> [count]", status="error")

    # Handle special navigation: cd .. 2, cd + 3, cd - 1
    if args[0] in ('..', '+', '-'):
        if len(args) == 1:
            count = 1
        else:
            try:
                count = int(args[1])
            except ValueError:
                return CommandResult(error=f"Invalid number: {args[1]}", status="error")

        current = vfs.cwd

        if args[0] == '..':
            for _ in range(count):
                parent = current.getparent()
                if parent is None:
                    return CommandResult(error="Already at root, cannot go up", status="error")
                current = parent

        elif args[0] == '+':
            for _ in range(count):
                next_node = current.getnext()
                if next_node is None:
                    return CommandResult(error="No younger sibling", status="error")
                current = next_node

        elif args[0] == '-':
            for _ in range(count):
                prev_node = current.getprevious()
                if prev_node is None:
                    return CommandResult(error="No older sibling", status="error")
                current = prev_node

        vfs.cwd = current
        return None  # Success, no output

    # Default: path resolution
    path = args[0]
    try:
        new_cwd = vfs.get_node_by_path(path)
        vfs.cwd = new_cwd
        return None  # Success, no output
    except Exception as e:
        return CommandResult(error=f"Error: {e}", status="error")


def cmd_tree(args, vfs):
    if vfs.cwd is None:
        return CommandResult(error="Nothing mounted. Use 'mount' first.", status="error")

    max_depth = None
    if args:
        try:
            max_depth = int(args[0])
        except ValueError:
            return CommandResult(error=f"Invalid depth value: {args[0]}", status="error")

    try:
        tree_str = print_tree(vfs.cwd, max_depth=max_depth, return_string=True)
        return CommandResult(output=tree_str)
    except Exception as e:
        return CommandResult(error=str(e), status="error")


def print_tree(element, prefix="", is_last=True, depth=0, max_depth=None, return_string=False):
    """Recursively build a visual tree structure string of XML/HTML nodes with optional depth folding."""

    lines = []

    def _print_tree(element, prefix, is_last, depth, max_depth):
        connector = "└── " if is_last else "├── "
        line = prefix + connector + str(element.tag)
        if return_string:
            lines.append(line)
        else:
            print(line)

        # Stop recursion if we've reached the folding level
        if max_depth is not None and depth >= max_depth:
            if len(element):
                folded_prefix = prefix + ("    " if is_last else "│   ")
                folded_line = folded_prefix + "└── [...]"
                if return_string:
                    lines.append(folded_line)
                else:
                    print(folded_line)
            return

        children = list(element)
        for i, child in enumerate(children):
            last = (i == len(children) - 1)
            new_prefix = prefix + ("    " if is_last else "│   ")
            _print_tree(child, new_prefix, last, depth + 1, max_depth)

    _print_tree(element, prefix, is_last, depth, max_depth)

    if return_string:
        return "\n".join(lines)


def cmd_unmount(args, vfs):
    """Unmount a previously mounted document."""
    if not args:
        return CommandResult(error="Usage: unmount <name>", status="error")

    name = args[0]
    try:
        vfs.unmount(name)
        return CommandResult(output=f"Unmounted '{name}'")
    except Exception as e:
        return CommandResult(error=f"Error: {e}", status="error")


def cmd_mount_url(args, vfs):
    """Mount an XML/HTML document from a URL."""
    if len(args) != 2:
        return CommandResult(error="Usage: mount-url <name> <url>", status="error")

    name, url = args
    try:
        vfs.mount_url(name, url)
        vfs.cwd = vfs.get_node_by_path(f"/{name}")
        return CommandResult(output=f"Mounted URL {name} at /{name}")
    except Exception as e:
        return CommandResult(error=f"Error mounting URL: {e}", status="error")


def cmd_text(args, vfs):
    if vfs.cwd is None:
        return CommandResult(error="No current node selected.", status="error")

    if args:
        text = ' '.join(args)
        if text in ("''", '""'):
            text = None
        try:
            vfs.cwd.text = text
            return CommandResult(output=f"{vfs.cwd.tag} text set to: {text}")
        except Exception as e:
            return CommandResult(error=str(e), status="error")
    else:
        return CommandResult(output=vfs.cwd.text or "")


def cmd_add(args, vfs):
    """Add a new child element to the current node, optionally at 1-based index."""
    if not args:
        return "Usage: add <tag> [index]"

    tag = args[0]
    index = None

    if len(args) == 2:
        try:
            index = int(args[1])
            if index < 1:
                return "Index must be 1 or greater"
        except ValueError:
            return "Index must be an integer"

    new_elem = etree.Element(tag)

    if index is not None:
        pos = index - 1
        if pos > len(vfs.cwd):
            return f"Index {index} out of bounds for {vfs.cwd.tag}"
        vfs.cwd.insert(pos, new_elem)
    else:
        vfs.cwd.append(new_elem)

    # Register as a mountpoint if added directly under root
    if vfs.cwd == vfs.root and tag not in vfs.mounts:
        vfs.mounts[tag] = None  # No backing file yet

    return f"Added <{tag}> under <{vfs.cwd.tag}>"


def cmd_rm(args, vfs):
    """Remove a node at the specified path (absolute or relative)."""
    if not args:
        return "Usage: rm <path>"

    path = args[0]

    try:
        target_node = vfs.get_node_by_path(path)
    except Exception as e:
        return f"Invalid path: {e}"

    parent = target_node.getparent()
    if parent is None or target_node == vfs.root:
        return "Cannot remove root or a node without a parent"

    # Disallow removing cwd or any of its ancestors
    current = vfs.cwd
    while current is not None:
        if current == target_node:
            return f"Cannot remove current directory or one of its ancestors: {vfs.build_path(target_node)}"
        current = current.getparent()

    try:
        parent.remove(target_node)
        return f"Removed <{target_node.tag}> from {vfs.build_path(parent)}"
    except Exception as e:
        return f"Error removing node: {e}"


def cmd_rename(args, vfs):
    """Rename the current node to a new tag."""
    if not args:
        return "Usage: rename <newtag>"

    new_tag = args[0]
    old_tag = vfs.cwd.tag
    vfs.cwd.tag = new_tag
    return f"Renamed <{old_tag}> to <{new_tag}>"


def cmd_find(args, vfs):
    """Find nodes matching an XPath query and return their absolute paths."""
    if not args:
        return "Usage: find <xpath>"

    xpath_query = ' '.join(args)
    try:
        matches = vfs.cwd.xpath(xpath_query)
    except Exception as e:
        return f"Invalid XPath expression: {e}"

    if not matches:
        return "No matches found."

    paths = []
    for node in matches:
        try:
            path = vfs.build_path(node)
            paths.append(path)
        except Exception:
            # In case build_path fails for some reason, skip node
            continue

    if not paths:
        return "No valid matches found."

    return '\n'.join(paths)


def cmd_cp(args, vfs):
    """Copy a node to another location."""
    if len(args) != 2:
        return "Usage: cp <source> <target>"

    src_path, dest_path = args

    try:
        src_node = vfs.get_node_by_path(src_path)
    except Exception as e:
        return f"Error: source not found: {e}"

    try:
        dest_node = vfs.get_node_by_path(dest_path)
    except Exception as e:
        return f"Error: target not found: {e}"

    # Prevent copying into one of its own descendants
    current = dest_node
    while current is not None:
        if current == src_node:
            return "Cannot copy a node into one of its own descendants"
        current = current.getparent()

    try:
        vfs.cp_node(src_node, dest_node)
        return f"Copied '{src_node.tag}' to '{vfs.build_path(dest_node)}'"
    except Exception as e:
        return f"Error copying: {e}"


def cmd_mv(args, vfs):
    """
    Move a node to a new location.

    Syntax:
      mv <source_path> <target_path>   # move source as last child of target
      mv <source_path> <sibling_index> # reorder source among siblings by index (1-based)
    """
    if len(args) != 2:
        return "Usage: mv <source> <target_path|sibling_index>"

    src_path, target = args

    try:
        src_node = vfs.get_node_by_path(src_path)
    except Exception as e:
        return f"Error: source not found: {e}"

    if src_node == vfs.root:
        return "Error: cannot move root"

    parent = src_node.getparent()
    if parent is None:
        return "Error: source node has no parent"

    # Determine if target is an integer (sibling index)
    try:
        index = int(target)
        # Move among siblings
        siblings = [c for c in parent if c != src_node]
        if index < 1:
            index = 1
        if index > len(siblings) + 1:
            index = len(siblings) + 1

        # Remove from parent
        parent.remove(src_node)

        # Insert at new position (list insert at index-1)
        siblings.insert(index - 1, src_node)

        # Clear existing children and re-add all siblings in new order
        for child in list(parent):
            parent.remove(child)
        for child in siblings:
            parent.append(child)

        return f"Moved '{src_node.tag}' to position {index} under parent '{parent.tag}'"

    except ValueError:
        # target is not an int, treat as path
        try:
            target_node = vfs.get_node_by_path(target)
        except Exception as e:
            return f"Error: target not found: {e}"

        if src_node == target_node:
            return "Error: source and target are the same node"

        # Prevent moving cwd or its ancestors
        current = vfs.cwd
        while current is not None:
            if current == src_node:
                return f"Cannot move current directory or one of its ancestors: {vfs.build_path(src_node)}"
            current = current.getparent()

        # Prevent moving a node into one of its own descendants
        current = target_node
        while current is not None:
            if current == src_node:
                return "Error: cannot move a node into one of its descendants"
            current = current.getparent()

        # Remove from old parent
        parent.remove(src_node)
        # Append to new parent
        target_node.append(src_node)

        return f"Moved '{src_node.tag}' as last child of '{target_node.tag}'"


def cmd_save(args, vfs):
    filepath = None
    pretty = True
    args_copy = args[:]

    if '--raw' in args_copy:
        pretty = False
        args_copy.remove('--raw')

    if args_copy:
        filepath = args_copy[0]

    try:
        result = vfs.save(filepath, pretty=pretty)
        return result
    except Exception as e:
        return f"Error saving: {e}"


def cmd_print(args, vfs):
    """Print the specified path (or current node if not given)."""

    path = None
    pretty = True

    args_copy = args[:]

    if '--raw' in args_copy:
        pretty = False
        args_copy.remove('--raw')

    if args_copy:
        path = args_copy[0]

    try:
        vfs.print(path, pretty=pretty)
        return ""  # output already printed
    except Exception as e:
        return f"Error printing: {e}"


def cmd_get(args, vfs):
    """Get attribute value of a node at optional path (defaults to cwd). Usage: attr-get [path] attr_name"""
    if len(args) == 1:
        path = None
        attr_name = args[0]
    elif len(args) == 2:
        path, attr_name = args
    else:
        return "Usage: attr-get [path] <attribute_name>"

    try:
        node = vfs.get_node_by_path(path) if path else vfs.cwd
        value = node.get(attr_name)
        if value is None:
            return f"Attribute '{attr_name}' not found on node '{node.tag}'"
        return value
    except Exception as e:
        return f"Error: {e}"


def cmd_set(args, vfs):
    """Set attribute value on node at optional path (defaults to cwd). Usage: attr-set [path] attr_name attr_value"""
    if len(args) == 2:
        path = None
        attr_name, attr_value = args
    elif len(args) == 3:
        path, attr_name, attr_value = args
    else:
        return "Usage: attr-set [path] <attribute_name> <attribute_value>"

    try:
        node = vfs.get_node_by_path(path) if path else vfs.cwd
        node.set(attr_name, attr_value)
        return f"Set attribute '{attr_name}' = '{attr_value}' on node '{node.tag}'"
    except Exception as e:
        return f"Error: {e}"


def cmd_delattr(args, vfs):
    """Delete attribute from node at optional path (defaults to cwd). Usage: attr-del [path] attr_name"""
    if len(args) == 1:
        path = None
        attr_name = args[0]
    elif len(args) == 2:
        path, attr_name = args
    else:
        return "Usage: attr-del [path] <attribute_name>"

    try:
        node = vfs.get_node_by_path(path) if path else vfs.cwd
        if attr_name in node.attrib:
            del node.attrib[attr_name]
            return f"Deleted attribute '{attr_name}' from node '{node.tag}'"
        else:
            return f"Attribute '{attr_name}' not found on node '{node.tag}'"
    except Exception as e:
        return f"Error: {e}"


def cmd_lsattr(args, vfs):
    """List all attributes on node at optional path (defaults to cwd). Usage: attr-list [path]"""
    if len(args) > 1:
        return "Usage: attr-list [path]"

    path = args[0] if args else None
    try:
        node = vfs.get_node_by_path(path) if path else vfs.cwd
        if not node.attrib:
            return f"No attributes on node '{node.tag}'"
        return '\n'.join(f"{k}='{v}'" for k, v in node.attrib.items())
    except Exception as e:
        return f"Error: {e}"


def cmd_pwd(args, vfs):
    try:
        cwd = vfs.build_path(vfs.cwd)
        return CommandResult(output=cwd)
    except Exception as e:
        return CommandResult(error=str(e), status="error")


def dispatch_command(cmdline: str, vfs) -> tuple[str | None, bool]:
    """
    Parse and dispatch a command line string.

    Returns:
        - result: str or None (output to be printed, or None if no output)
        - done: bool (True if command ends the session, like 'exit')
    """
    cmdline = cmdline.strip()
    if not cmdline:
        return None, False

    parts = cmdline.split()
    cmd, *args = parts

    if cmd in ('exit', 'quit'):
        return "bye", True

    handler = COMMANDS.get(cmd)
    if handler is None:
        return f"Unknown command: {cmd}", False

    result = handler(args, vfs)
    return result, False


def cmd_help(args, vfs):
    """Show help for commands."""
    help_text = """
Available commands:

mount <name> <filepath>       - Mount an XML/HTML file as a virtual root.
mount-url <name> <url>        - Mount an XML/HTML document from a URL.
unmount <name>                - Unmount a previously mounted document.

ls [path]                    - List child elements under current or specified path.
cd <path|..|+|- [count]>     - Change current node (.. up, + next sibling, - prev sibling).
tree [depth]                 - Print subtree from current node, optionally folded at depth.
pwd                          - Print absolute path of the current node

text [new text]              - Get or set text content of current node.
get <attr_name>              - Get attribute value of current node.
set <attr_name> <value>      - Set attribute value on current node.
delattr <attr_name>          - Delete attribute from current node.
lsattr                       - List all attributes of current node.

add <tag> [index]            - Add new child element, optionally at 1-based index.
rm <path>                   - Remove node at specified path.
rename <newtag>              - Rename current node’s tag.

find <xpath>                - Find nodes by XPath from current node.
cp <source> <target>        - Copy node to another location.
mv <source> <target|index>  - Move node to a new location or reorder among siblings.

save [filepath] [--raw]     - Save mounted document; pretty-print by default.
print [path] [--raw]        - Print node or subtree with pretty highlighting.

help                        - Show this help message.
"""
    return help_text.strip()


COMMANDS = {
    "mount": cmd_mount,
    "unmount": cmd_unmount,
    "mount-url": cmd_mount_url,

    "ls": cmd_ls,
    "cd": cmd_cd,
    "tree": cmd_tree,
    "pwd": cmd_pwd,

    "text": cmd_text,
    "get": cmd_get,
    "set": cmd_set,
    "delattr": cmd_delattr,
    "lsattr": cmd_lsattr,

    "add": cmd_add,
    "rm": cmd_rm,
    "rename": cmd_rename,

    "find": cmd_find,
    "cp": cmd_cp,
    "mv": cmd_mv,

    "save": cmd_save,
    "print": cmd_print,

    "help": cmd_help,
}

