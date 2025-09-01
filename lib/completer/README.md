# TabCompleter

A minimal, dynamic tab completer for Python CLI tools using the `readline` module. Supports keyword-based completion with fuzzy matching via `difflib.get_close_matches()`.

## Features

- Dynamic keyword list updates
- Adjustable fuzzy match sensitivity (`cutoff`)
- Readline integration with custom delimiters and bindings
- Optional readline startup hook for pre-filling input

## Installation

No dependencies other than Python's standard library.

## Usage

```python
from completer import Completer

# Initialize the completer
c = Completer()
c.set_keywords(['apple', 'banana', 'cherry'])

# (Optional) Set fuzzy match cutoff (0.0 - 1.0)
c.set_cutoff(0.7)

# Set up readline
c.init_readline()

# (Optional) Pre-fill the input line
Completer.set_readline_hook('apple')

