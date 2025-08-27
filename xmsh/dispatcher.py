"""Command dispatcher for the CLI interface, mapping commands to handlers."""

from copy import deepcopy

from lxml import etree

# from documents import VirtualFileSystem


def cmd_mount(args, vfs):
    """Mount an XML/HTML document at a given name."""
    if len(args) != 2:
        return "Usage: mount <name> <filepath>"
    name, filepath = args
    try:
        vfs.mount(name, filepath)
        vfs.cwd = vfs.get_node_by_path(f"/{name}")
        return f"Mounted {name} at /{name}"
    except Exception as e:
        return f"Error mounting: {e}"


def cmd_ls(args, vfs):
    """List child nodes of the current or specified path."""
    path = args[0] if args else None
    try:
        return vfs.ls(path)
    except Exception as e:
        return f"Error: {e}"


def cmd_cd(args, vfs):
    """Change current working node to a specified path."""
    if not args:
        return "Usage: cd <path> [count]"

    # Handle special navigation: cd .. 2, cd + 3, cd - 1
    if args[0] in ('..', '+', '-'):
        if len(args) == 1:
            count = 1
        else:
            try:
                count = int(args[1])
            except ValueError:
                return f"Invalid number: {args[1]}"

        current = vfs.cwd

        if args[0] == '..':
            for _ in range(count):
                parent = current.getparent()
                if parent is None:
                    return "Already at root, cannot go up"
                current = parent

        elif args[0] == '+':
            for _ in range(count):
                next_node = current.getnext()
                if next_node is None:
                    return "No younger sibling"
                current = next_node

        elif args[0] == '-':
            for _ in range(count):
                prev_node = current.getprevious()
                if prev_node is None:
                    return "No older sibling"
                current = prev_node

        vfs.cwd = current
        return  # Success, no output

    # Default: path resolution
    path = args[0]
    try:
        new_cwd = vfs.get_node_by_path(path)
        vfs.cwd = new_cwd
    except Exception as e:
        return f"Error: {e}"

'''
def cmd_cd(args, vfs):
    """Change current working node to a specified path."""
    if not args:
        return "Usage: cd <path>"
    path = args[0]
    try:
        new_cwd = vfs.get_node_by_path(path)
        vfs.cwd = new_cwd
    except Exception as e:
        return f"Error: {e}"
'''
def cmd_tree(args, context):
    """Pretty print the subtree from the current working node, optionally folded at a depth."""
    if context.cwd is None:
        return "Nothing mounted. Use 'mount' first."

    max_depth = int(args[0]) if args else None
    print_tree(context.cwd, max_depth=max_depth)
    return ""


def print_tree(element, prefix="", is_last=True, depth=0, max_depth=None):
    """Recursively print a visual tree structure of XML/HTML nodes with optional depth folding."""
    connector = "└── " if is_last else "├── "
    print(prefix + connector + str(element.tag))

    # Stop recursion if we've reached the folding level
    if max_depth is not None and depth >= max_depth:
        if len(element):
            folded_prefix = prefix + ("    " if is_last else "│   ")
            print(folded_prefix + "└── [...]")
        return

    children = list(element)
    for i, child in enumerate(children):
        last = (i == len(children) - 1)
        new_prefix = prefix + ("    " if is_last else "│   ")
        print_tree(child, new_prefix, last, depth + 1, max_depth)


def cmd_unmount(args, vfs):
    """Unmount a previously mounted document."""
    if not args:
        return "Usage: unmount <name>"
    
    name = args[0]
    try:
        vfs.unmount(name)
        return f"Unmounted '{name}'"
    except Exception as e:
        return f"Error: {e}"


def cmd_mount_url(args, vfs):
    """Mount an XML/HTML document from a URL."""
    if len(args) != 2:
        return "Usage: mount-url <name> <url>"
    name, url = args
    try:
        vfs.mount_url(name, url)
        vfs.cwd = vfs.get_node_by_path(f"/{name}")
        return f"Mounted URL {name} at /{name}"
    except Exception as e:
        return f"Error mounting URL: {e}"


def cmd_text(args, vfs):
    """Get or set the text content of the current node."""
    if args:
        text = ' '.join(args)
        vfs.cwd.text = text
        return f"{vfs.cwd.tag} text set to: {text}"
    else:
        return vfs.cwd.text or ""


def cmd_add(args, vfs):
    """Added a new child element to the current node, optionally at 1-based index."""
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
        pos = index - 1  # convert to 0-based index
        if pos > len(vfs.cwd):
            return f"Index {index} out of bounds for {vfs.cwd.tag}"
        vfs.cwd.insert(pos, new_elem)
        return f"Inserted <{tag}> at position {index} under <{vfs.cwd.tag}>"
    else:
        vfs.cwd.append(new_elem)
        return f"Added <{tag}> under <{vfs.cwd.tag}>"


def cmd_rm(args, vfs):
    """Remove a child element by tag and optional index."""
    if not args:
        return "Usage: rm <tag>[index]"

    try:
        tag_part = args[0]
        if '[' in tag_part and tag_part.endswith(']'):
            tag = tag_part[:tag_part.index('[')]
            index = int(tag_part[tag_part.index('[') + 1:-1])
        else:
            tag = tag_part
            index = 1

        matches = [c for c in vfs.cwd if c.tag == tag]
        if len(matches) < index or index < 1:
            return f"No such child: {tag_part}"

        to_remove = matches[index - 1]
        vfs.cwd.remove(to_remove)
        return f"Removed {tag_part} from {vfs.cwd.tag}"
    except Exception as e:
        return f"Error: {e}"


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


def copy_element(src, dest, position='before'):
    """Copy `src` node into `dest` at the specified position."""
    new_element = deepcopy(src)

    if position == 'before':
        parent = dest.getparent()
        if parent is None:
            raise ValueError("Cannot insert before a node with no parent")
        parent.insert(parent.index(dest), new_element)
    elif position == 'append':
        dest.append(new_element)
    else:
        raise ValueError("Invalid position")

    return new_element

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

        # Avoid moving node into one of its own descendants
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

COMMANDS = {
    "mount": cmd_mount,
    "ls": cmd_ls,
    "cd": cmd_cd,
    "tree": cmd_tree,
    "unmount": cmd_unmount,
    "mount-url": cmd_mount_url,
    "text": cmd_text,
    "add": cmd_add,
    "rm": cmd_rm,
    "rename": cmd_rename,
    "find": cmd_find,
    "cp": cmd_cp,
    "mv": cmd_mv,
}

