# cppref

`cppref` is a command-line tool for fetching and querying C++ and C symbol indices from cppreference.com and glibc symbol index from sourceware.org.

## Features

- Fetch symbols from cppreference.com and sourceware.org
- Query symbols using dmenu
- Open symbol documentation in the default web browser

## Requirements

- Python 3.12+
- `requests` library
- `dmenu`
- `zsh`
- `gtk-launch`
- `xdg-settings`

## Installation

1. Clone the repository:

   ```sh
   git clone https://github.com/j-nikki/cppref.git
   cd cppref
   ```

2. Create a virtual environment and install dependencies:

   ```sh
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

## Usage

1. Fetch symbols and open the selected symbol in the default web browser:

   ```sh
   bin/cppref
   ```

2. `bin/cppref` will forward any arguments passed to `dmenu`:

   ```sh
   bin/cppref -l 10
   ```
