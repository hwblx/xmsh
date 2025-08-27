"""CLI entry point for navigating XML/HTML documents in a virtual file system."""

from dispatcher import COMMANDS
from documents import VirtualFileSystem

def get_prompt(vfs):
    """Return the CLI prompt string showing the current virtual path."""
    path = vfs.build_path(vfs.cwd)
    return f"{path}> "

def main():
    """Main event loop for the CLI interface."""
    vfs = VirtualFileSystem()

    while True:
        prompt = get_prompt(vfs)
        
        try:
            cmdline = input(prompt)
        except KeyboardInterrupt:
            print('\nbye')
            exit(0)

        if cmdline in ('exit', 'quit'):
            print('bye')
            exit(0)

        if not cmdline.strip():
            continue

        parts = cmdline.strip().split()
        cmd, *args = parts

        if cmd == 'exit' or cmd == 'quit':
            break

        if cmd not in COMMANDS:
            print(f"Unknown command: {cmd}")
            continue

        result = COMMANDS[cmd](args, vfs)
        if result is not None:
            print(result)

if __name__ == "__main__":
    main()

