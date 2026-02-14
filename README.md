*This project has been created as part of the 42 curriculum by cdonaire, augperez.*

## Description

**A-Maze-ing** is a configurable maze generator based on Prim’s algorithm. It:

- Generates a maze as a hexadecimal matrix (1 hex digit per cell)
- Uses a wall bitmask per cell (N/E/S/W)
- Inserts a protected centered “42” pattern when the map is large enough
- Finds one or more solutions (BFS shortest path; extra cycles when `PERFECT=false`)
- Saves the maze + metadata to a text file and visualizes it with MiniLibX

### Objective

The objective of this project is to:
- Implement an efficient maze generation algorithm (Prim's algorithm)
- Apply bitmasking representation to optimize memory and processing
- Generate reproducible mazes using seeds
- Solve mazes using breadth-first search (BFS)
- Allow the insertion of protected patterns within the maze

### Overview

The generator creates customized mazes with a centered hexadecimal pattern that acts as a protected pattern. Prim's algorithm carves the maze paths while respecting the pattern's protected cells, and finally uses BFS to find the optimal solution.

## Instructions

### Requirements

- Python 3
- MiniLibX shared library included in `mlx/` (Linux)
- Optional dev tools for lint/format: `flake8`, `mypy`, `autopep8` (install via `make install` or `make venv`)

### Configuration

The project uses `config.txt` to customize maze parameters.

```ini
WIDTH=6
HEIGHT=4
ENTRY=1,0
EXIT=5,3
OUTPUT_FILE=maze.txt
SEED=
PERFECT=false
```

**Parameters:**

- `WIDTH`, `HEIGHT`: maze size in cells
- `ENTRY`, `EXIT`: coordinates as `x,y` (0-indexed)
- `OUTPUT_FILE`: output filename (default in repo is `maze.txt`)
- `SEED`: empty = random; integer = reproducible; also used to cache in `seeds/<seed>.maze`
- `PERFECT`:
  - `true`: perfect maze (Prim only; no cycles)
  - `false`: non-perfect maze (Prim + extra openings; may yield multiple solutions)

### Execution

#### Using Make (Recommended)

The project includes a comprehensive Makefile with the following targets:

**Quick Start:**

```bash
make run
```

**Main Commands:**
- `make run` - Generate a maze and open the MLX window (this is the default goal)
- `make all` - Byte-compile the main script to verify syntax
- `make debug` - Run with `pdb`

**Code Quality (optional):**

- `make lint` - `flake8` + a configured `mypy` run
- `make lint-strict` - strict `flake8` + `mypy --strict`
- `make format` - format with `autopep8`
- `make check-syntax` - compile all python files in the repo list

**Testing & Validation:**

- `make test` - validate `maze.txt` with `output_validator.py` (expects the file to exist)
- `make install` - install dev dependencies system-wide
- `make venv` - create a local `.venv/` and install dev dependencies there

**Cleanup:**
- `make clean` - Remove cache and compiled files
- `make fclean` - Full clean (includes seeds/ and venv/)
- `make re` - Clean and rebuild (fclean + all)

**Development:**
- `make venv` - Create Python virtual environment
- `make info` - Show project information

#### Direct Execution

Alternatively, run directly with Python:

```bash
python3 a_maze_ing.py
```

You can also pass a custom config path as the first argument:

```bash
python3 a_maze_ing.py path/to/config.txt
```

The script:

1. Loads and validates configuration
2. If `SEED` is set and `seeds/<seed>.maze` exists, it reuses it
3. Otherwise generates a maze (retrying until it meets internal validation)
4. Solves it and writes the output file
5. Opens a visualization window using the bundled `mlx/` library

### Output Format

The output file contains:

```
[Hexadecimal maze matrix - 1 hexadecimal digit per cell]
[Blank line]
[Entry coordinates (1-based)]
[Exit coordinates (1-based)]
[Seed used]
[Blank line]
[Solution path (N/E/S/W)]
```

Directions:

- `N`: North
- `E`: East
- `S`: South
- `W`: West

### Output Validation

The project includes `output_validator.py`, which validates that a generated file matches the expected format.

**Features:**
- Validates hexadecimal matrix format
- Checks mandatory metadata (WIDTH, HEIGHT, ENTRY, EXIT)
- Verifies maze dimensions match configuration
- Reports errors and warnings clearly

**Usage:**

```bash
make test
```

Or directly:

```bash
python3 output_validator.py maze.txt
```

**Sample Output:**
```
✓ Maze validation successful
  Dimensions: 70 x 5
  Entry: 5,2
  Exit: 19,0
```

The validator ensures the maze output is properly formatted and ready for processing in downstream systems.

## Seeds cache

When a maze is generated with a new seed, it’s saved to `seeds/<seed>.maze`.
On the next run, if the same seed is set in `config.txt`, the generator will load that file instead of generating again.

## Troubleshooting

- **`make lint` fails**: it requires `flake8` and `mypy`. Run `make venv` (recommended) or `make install`.
- **MLX window doesn’t show / crashes**: the project uses the bundled `mlx/libmlx.so`. On some Linux setups you may need extra system deps for X11/OpenGL.
- **Small maps**: the centered “42” pattern is only inserted when the maze is large enough (the code mentions at least `7x5`).

## Resources

### Classic References

- **Prim's Algorithm**: https://en.wikipedia.org/wiki/Prim%27s_algorithm
  - Minimum spanning tree generation algorithm adapted for maze generation
  
- **Breadth-First Search (BFS)**: https://en.wikipedia.org/wiki/Breadth-first_search
  - Fundamental graph search technique for finding the shortest path
  
- **Maze Generation Algorithms**: https://en.wikipedia.org/wiki/Maze_generation_algorithm
  - Comprehensive comparison of maze generation algorithms
  
- **Bitmasking Techniques**: https://www.geeksforgeeks.org/bitmasking-and-dynamic-programming/
  - State representation optimization using bitmasks

### AI Usage

AI was used as a tool to **reduce repetitive and tedious tasks**, while always maintaining complete understanding and responsibility for the generated content:

1. **Docstring and technical documentation generation**
   - Detailed docstring writing in key functions (`load_config`, `run_prim_generator`, `get_solution_path`)
   - Clear explanations of parameters, returns, and algorithms used
   - **Review performed**: Each docstring was validated against the code to ensure accuracy

2. **Code structure and organization**
   - Organization into logical section
   - Descriptive comments in code blocks
   - **Review performed**: The structure was verified to be coherent and facilitate flow understanding

3. **README writing**
   - Document structuring following 42 project standards
   - Algorithm descriptions (Prim, BFS)
   - Usage instructions format
   - **Review performed**: Validation against actual project configuration and present files

4. **Debugging and error analysis**
   - AI was consulted to help understand error messages and trace issues in algorithm logic
   - Assistance in identifying edge cases and potential issues with bitwise operations
   - **Review performed**: All debugging suggestions were manually verified and tested to ensure they actually resolved the issues
   - **Responsibility**: The final fixes were implemented manually after understanding the root cause with the help of AI

5. **Packaging with build**
   python3 -m build
   pip install name.tar.gz/route to name.tar.gz
   
   - Generate a:
      - maze.py:
        from a_maze_ing import A_Maze_ing
        from mlx.mlx import Mlx

        a = Mlx()
        b = A_Maze_ing()
      - MANIFEST.in:
        include a_maze_ing.py
        include config.txt
        include Makefile
        include README*

        recursive-include mlx *.py *.so *.h
      - setup.py:
        from setuptools import setup

        setup(
            name="mazegen",
            version="1.0.1",
            description="Maze generator solver (A-maze-ing 42)",
            py_modules=["a_maze_ing"],
            packages=["mlx"],
            package_data={
                "mlx": ["*.so", "docs/*.h"],  # incluimos librerías y headers
            },
            include_package_data=True,
        )

