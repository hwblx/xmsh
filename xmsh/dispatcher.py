"""Command dispatcher for the CLI interface, mapping commands to handlers."""

from documents import VirtualFileSystem


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
        return "Usage: cd <path>"
    path = args[0]
    try:
        new_cwd = vfs.get_node_by_path(path)
        vfs.cwd = new_cwd
    except Exception as e:
        return f"Error: {e}"


def cmd_tree(args, context):
    """Pretty print the subtree from the current working node."""
    if context.cwd is None:
        return "Nothing mounted. Use 'mount' first."
    
    print_tree(context.cwd)
    return ""  # Or return None


def print_tree(element, prefix="", is_last=True):
    """Recursively print a visual tree structure of XML/HTML nodes."""
    connector = "└── " if is_last else "├── "
    print(prefix + connector + str(element.tag))

    children = list(element)
    for i, child in enumerate(children):
        last = (i == len(children) - 1)
        new_prefix = prefix + ("    " if is_last else "│   ")
        print_tree(child, new_prefix, last)


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


COMMANDS = {
    "mount": cmd_mount,
    "ls": cmd_ls,
    "cd": cmd_cd,
    "tree": cmd_tree,
    "unmount": cmd_unmount,
}

