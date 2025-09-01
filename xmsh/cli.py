"""
CLI entry point for navigating XML/HTML documents 
in a virtual file system.
"""

from xmsh.dispatcher import COMMANDS
from xmsh.documents import VirtualFileSystem
from lib.completer import completer


def get_prompt(vfs):
    """Return the CLI prompt string showing the current virtual path."""
    path = vfs.build_path(vfs.cwd)
    return f"{path}> "


def collect_all_paths(vfs):
    """Traverse VFS and return all absolute paths to all nodes."""
    all_paths = []

    def traverse(node):
        path = vfs.build_path(node)
        all_paths.append(path)
        for child in node:
            traverse(child)

    traverse(vfs.root)
    return all_paths


def generate_path_variants(vfs, abs_paths):
    """Generate relative and dot-relative paths from the current cwd."""
    rel_paths = []

    cwd_node = vfs.cwd
    cwd_path = vfs.build_path(cwd_node)

    for path in abs_paths:
        if path == cwd_path:
            continue

        # Generate paths relative to the current directory
        if path.startswith(cwd_path):
            suffix = path[len(cwd_path):].lstrip('/')
            if suffix:
                rel_paths.append(suffix)           # e.g. 'header'
                rel_paths.append(f"./{suffix}")    # e.g. './header'

        # Generate paths relative to the parent directory
        parent = cwd_node.getparent()
        if parent is not None:
            parent_path = vfs.build_path(parent)
            if path.startswith(parent_path) and path != parent_path:
                up_suffix = path[len(parent_path):].lstrip('/')
                if up_suffix:
                    rel_paths.append(f"../{up_suffix}")  # e.g. '../sibling'

    # Combine and remove duplicates while preserving order
    return list(dict.fromkeys(abs_paths + rel_paths))


def update_completions(vfs, comp):
    """Update the completer with current paths."""
    abs_paths = collect_all_paths(vfs)
    all_paths = generate_path_variants(vfs, abs_paths)
    comp.set_keywords(all_paths)


def main(debug=False):
    """Main event loop for the CLI interface."""
    vfs = VirtualFileSystem()

    if debug:
        print(COMMANDS['mount'](('homepage', './data/homepage.html'), vfs))
        print(COMMANDS['mount'](('menu', './data/menu.xml'), vfs))

    comp = completer.Completer()
    comp.init_readline()
    update_completions(vfs, comp)

    while True:
        prompt = get_prompt(vfs)

        try:
            cmdline = input(prompt)
        except KeyboardInterrupt:
            print('\nbye')
            break

        if not cmdline.strip():
            continue

        parts = cmdline.strip().split()
        cmd, *args = parts

        if cmd in ('exit', 'quit'):
            print('bye')
            break

        handler = COMMANDS.get(cmd)
        if handler is None:
            print(f"Unknown command: {cmd}")
            continue

        result = handler(args, vfs)
        if result is not None:
            print(result)

        update_completions(vfs, comp)


if __name__ == "__main__":
    main(debug=True)
