import random
import os
import sys
from mlx.mlx import Mlx
from collections import deque


class A_maze_ing():
    """Generate, solve, persist, and visualize mazes.

        The maze is represented as a 2D grid of integers. Each cell uses a
        4-bit wall bitmask:

        - ``NORTH`` = 1
        - ``EAST`` = 2
        - ``SOUTH`` = 4
        - ``WEST`` = 8

        Generation uses Prim's algorithm.

        - When ``PERFECT=true``, the maze is perfect (no cycles).
        - When ``PERFECT=false``, extra passages are opened to introduce
            cycles and allow multiple solutions.

        If the maze is at least 7x5, a centered 7x5 "42" protected pattern is
        inserted. For smaller maps, the pattern is skipped.

        Output files are written as a hex matrix (one hex digit per cell),
        followed by entry/exit coordinates, seed, and one or more solution
        strings.
    """

    # =================================================================
    # 1. Constants and Bitmasking Definitions
    # =================================================================

    # Bits for wall presence
    NORTH, EAST, SOUTH, WEST = 1, 2, 4, 8
    ALL_WALLS = NORTH | EAST | SOUTH | WEST  # 15 (0b1111)
    COLLAPSE_3 = [
        (5, 1),
        (5, 3),
        (1, 3),
    ]

    # Movement structure: (dx, dy, current_cell_bit, neighbor_cell_bit)
    MOVEMENTS = {
        'N': (0, -1, NORTH, SOUTH),
        'E': (1, 0, EAST, WEST),
        'S': (0, 1, SOUTH, NORTH),
        'W': (-1, 0, WEST, EAST)
    }

    # MLX variable definitions:
    ESC = 65307
    KEY_1 = 49
    KEY_2 = 50
    KEY_3 = 51
    CELL_SIZE = 18
    WALL_COLOR = 0xFFFFFF
    BG_COLOR = 0x000000
    ENTRY_COLOR = 0X00FF00
    EXIT_COLOR = 0XFF0000
    PATH_COLOR = 0x0000FF
    # Colors for alternative solutions (only for WFC/non-perfect mazes)
    SOLUTION_1_COLOR = 0x0000FF  # Blue
    SOLUTION_2_COLOR = 0xFFFF00  # Yellow
    SOLUTION_3_COLOR = 0x00FFFF  # Cyan
    # Colors for walls (cycling: white -> pink -> purple -> white)
    WALL_COLOR_WHITE = 0xFFFFFF    # White
    WALL_COLOR_PINK = 0xFF1493     # Pink
    WALL_COLOR_PURPLE = 0x800080   # Purple
    # Loading animation color
    LOADING_COLOR = 0x00FF00       # Green for loading animation

    # =================================================================
    # 2. Main Execution
    # =================================================================

    def __init__(self):
        """Run the complete maze pipeline.

        This initializer acts as the program entry point:

        1. Loads and validates configuration.
        2. Loads an existing maze from ``seeds/<seed>.maze`` when available,
           otherwise generates a new maze.
        3. Solves the maze (BFS) and persists it.
        4. Opens an MLX window to visualize the maze.

        The configuration is read from ``config.txt`` by default, or from the
        path passed as the first CLI argument.
        """
        # Load configuration from file and validate it.
        config_file = sys.argv[1] if len(sys.argv) > 1 else 'config.txt'
        try:
            config = self.load_config(config_file)
            self.validate_config(config)
        except ValueError as e:
            print(e)
            return

        WIDTH = config['WIDTH']
        HEIGHT = config['HEIGHT']
        ENTRY_X, ENTRY_Y = config['ENTRY_X'], config['ENTRY_Y']
        EXIT_X, EXIT_Y = config['EXIT_X'], config['EXIT_Y']
        OUTPUT_FILE = config['OUTPUT_FILE']
        SEED = config['SEED']
        seed_is_new = False
        seed_data = None

        # If SEED is None (empty), generate a random one
        if SEED is None:
            SEED = random.randint(0, 2147483647)  # Max 32-bit integer
            config['SEED'] = SEED
            seed_is_new = True
            seed_status = f"(Generated: {SEED})"
        else:
            path = f"seeds/{SEED}.maze"
            if os.path.isfile(path) is False:
                seed_is_new = True
            seed_status = f"(Fixed: {SEED})"

        seed_data = self.load_seed_file(SEED)

        if seed_data is not None:
            maze_bytes, config, solution_path = seed_data
            WIDTH = config['WIDTH']
            HEIGHT = config['HEIGHT']
            ENTRY_X, ENTRY_Y = config['ENTRY_X'], config['ENTRY_Y']
            EXIT_X, EXIT_Y = config['EXIT_X'], config['EXIT_Y']
            seed_is_new = False
            print(f"--- Seed Found: loading maze from seeds/{SEED}.maze ---")

        print("--- A-Maze-ing Generation Process Initiated ---")
        print(f"Configuration: {WIDTH}x{HEIGHT}, Entry: "
              f"({ENTRY_X},{ENTRY_Y}), Exit: ({EXIT_X},{EXIT_Y})")
        print(f"Seed: {seed_status}")
        is_perfect = config.get('PERFECT', True)
        algo = 'Prim (Perfect)' if is_perfect else 'Prim (Non-Perfect)'
        print(f"Algorithm: {algo}")

        # SET RANDOM SEED ONCE AT THE START FOR REPRODUCIBILITY
        random.seed(SEED)

        # 1. Apply centered pattern (BEFORE maze generation)
        """maze_with_pattern, protected_f_cells, protected_open_cells= (
            self.insert_centered_pattern(WIDTH, HEIGHT))"""
        start_cell_x = int((WIDTH - 7) / 2)
        start_cell_y = int((HEIGHT - 5) / 2)
        print(f"1. Centered pattern created (Start Cell: "
              f"{start_cell_x}, {start_cell_y}).")

        # 2. Generate maze and solve (with retry loop for 3x3 validation)
        max_attempts = 1000
        attempt = 0
        maze_bytes = None
        solution_paths = None

        while maze_bytes is None and attempt < max_attempts:
            attempt += 1

            # Generate a new seed if we're retrying
            if attempt > 1:
                config['SEED'] = random.randint(0, 2147483647)
                SEED = config['SEED']

            # Try to generate maze
            result = self.generate_maze(config)

            # If result is None, validation failed, will retry with new seed
            if result is not None:
                maze_bytes, solution_paths = result

        if maze_bytes is None:
            print(f"✗ ERROR: Failed to generate valid maze after "
                  f"{max_attempts} attempts.")
            return

        num_solutions = len(solution_paths)

        # Print generation info
        if attempt == 1:
            print(f"2. Maze generated using {algo} "
                  "(protecting only 'F' pattern cells).")
        else:
            print(f"2. Maze generated using {algo} (after {attempt} "
                  f"attempts) (protecting only 'F' pattern cells).")

        print(f"3. Solution paths found: {num_solutions} "
              f"(Primary path length: {len(solution_paths[0])}).")

        # 4. Final Save (with seed for reproducibility)
        self.save_to_final_format(
            maze_bytes, WIDTH, HEIGHT, ENTRY_X, ENTRY_Y, EXIT_X,
            EXIT_Y, solution_paths, OUTPUT_FILE, seed=SEED
        )
        print(
            f"--- Process Complete. File saved to: {OUTPUT_FILE} "
            f"(Seed: {SEED}) ---"
        )
        # 4.1 Save seed in seeds/
        if seed_is_new:
            self.check_seeds_dir()
            self.save_seed_file(SEED, config, maze_bytes, solution_paths)
            print(f"--- Process Complete. File saved to: seeds/{SEED}.maze")

        # 5. Render Maze (Use of mlx):
        print(f"--- Printing Result (Seed: {SEED}) ---")
        self.render_maze_mlx(maze_bytes, config, solution_paths)

    @staticmethod
    def load_config(config_file='config.txt'):
        """Load maze configuration from a config file.

        The file uses a ``KEY=VALUE`` format, for example:

        - ``WIDTH=70``
        - ``HEIGHT=40``
        - ``ENTRY=0,0``
        - ``EXIT=19,14``
        - ``OUTPUT_FILE=maze.txt``
        - ``SEED=`` (empty means random)
        - ``PERFECT=true|false``

        Args:
            config_file (str): Path to the configuration file.

        Returns:
            dict: Parsed configuration.

        Raises:
            ValueError: If a line is invalid or an unknown key is found.
        """
        config = {}

        with open(config_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' not in line:
                    raise ValueError(f"Invalid config line: {line}")

                key, value = line.split('=', 1)
                key = key.strip().upper()
                value = value.strip()

                if key in config:
                    raise ValueError(f"Duplicated key {key}")

                if key == 'WIDTH':
                    config['WIDTH'] = int(value)
                elif key == 'HEIGHT':
                    config['HEIGHT'] = int(value)
                elif key == 'ENTRY':
                    try:
                        parts = value.split(',')
                        config['ENTRY_X'] = int(parts[0].strip())
                        config['ENTRY_Y'] = int(parts[1].strip())
                    except ValueError:
                        raise ValueError(
                            f"Entry must be in x,y format '{value}'")
                elif key == 'EXIT':
                    try:
                        parts = value.split(',')
                        config['EXIT_X'] = int(parts[0].strip())
                        config['EXIT_Y'] = int(parts[1].strip())
                    except ValueError:
                        raise ValueError(
                            f"Exit must be in x,y format '{value}'")
                elif key == 'OUTPUT_FILE':
                    config['OUTPUT_FILE'] = value
                elif key == 'SEED':
                    config['SEED'] = int(value) if value else None
                elif key == 'PERFECT':
                    config['PERFECT'] = value.lower() in ('true', '1', 'yes')
                else:
                    raise ValueError(f"Unknown config key '{key}'")

        return config

    @staticmethod
    def validate_config(config):
        """Validate the configuration.

        Args:
            config (dict): Configuration as returned by :meth:`load_config`.

        Raises:
            ValueError: If dimensions or entry/exit coordinates are invalid.

        Notes:
            Maps smaller than 7x5 are allowed, but the centered 7x5 "42"
            pattern is skipped.
        """

        width = config['WIDTH']
        height = config['HEIGHT']

        ex, ey = config['ENTRY_X'], config['ENTRY_Y']
        ox, oy = config['EXIT_X'], config['EXIT_Y']

        # Allow small maps, but the 42 pattern (7x5) will be skipped if
        # the map is smaller.
        if not (1 <= width <= 1024):
            raise ValueError("Width must be between 1 and 1024")
        if not (1 <= height <= 1024):
            raise ValueError("Height must be between 1 and 1024")
        if not (0 <= ex < width and 0 <= ey < height):
            raise ValueError("Entry out of bounds")
        if not (0 <= ox < width and 0 <= oy < height):
            raise ValueError("Exit out of bounds")
        if (ex, ey) == (ox, oy):
            raise ValueError("Entry and exit can not be in the same position")

    @staticmethod
    def load_seed_file(seed):
        """Load a previously generated maze from ``seeds/<seed>.maze``.

        The seed file stores WIDTH/HEIGHT/SEED, the hex matrix, ENTRY/EXIT,
        and one or more PATH= lines.

        Args:
            seed (int): Seed identifier.

        Returns:
            tuple | None: (maze_bytes, config, solution_paths) if found,
            otherwise None.
        """

        path = f"seeds/{seed}.maze"
        if not os.path.exists(path):
            return None

        config = {}
        maze_bytes = []
        solution_path = []

        with open(path, 'r') as f:
            lines = f.read().splitlines()

        config['WIDTH'] = int(lines[0].split('=')[1])
        config['HEIGHT'] = int(lines[1].split('=')[1])
        config['SEED'] = int(lines[2].split('=')[1])

        height = config['HEIGHT']
        maze_hex_lines = lines[3:3 + height]
        for hex_line in maze_hex_lines:
            row = [int(c, 16) for c in hex_line]
            maze_bytes.append(row)

        for line in lines[3 + height:]:

            if line.startswith('ENTRY='):
                parts = line.split('=')[1].split(',')
                config['ENTRY_X'] = int(parts[0])
                config['ENTRY_Y'] = int(parts[1])

            elif line.startswith('EXIT='):
                parts = line.split('=')[1].split(',')
                config['EXIT_X'] = int(parts[0])
                config['EXIT_Y'] = int(parts[1])

            elif line.startswith('PATH='):
                solution_path.append(line.split('=')[1])

        return maze_bytes, config, solution_path

    # =================================================================
    # 3. Maze Generation Algorithm (PRIM)
    # =================================================================

    def add_walls_to_frontier(
            self,
            x,
            y,
            maze,
            W,
            H,
            frontier,
            protected_cells=None):
        """Add candidate walls around a cell to the Prim frontier.

        A neighbor is considered unvisited if:

        - Its current value is ``ALL_WALLS``.
        - It is not in ``protected_cells``.
        """
        if protected_cells is None:
            protected_cells = set()

        for direction, (dx, dy, _, _) in self.MOVEMENTS.items():
            nx, ny = x + dx, y + dy

            if 0 <= nx < W and 0 <= ny < H:
                # Only add if ALL_WALLS and NOT a protected 'F' cell
                if maze[ny][nx] == self.ALL_WALLS and (
                        nx, ny) not in protected_cells:
                    frontier.append((x, y, direction))

    def run_prim_generator(self, WIDTH, HEIGHT, ENTRY_X, ENTRY_Y, SEED,
                           PERFECT, initial_maze=None,
                           protected_cells=None,
                           additional_start_points=None) -> list:
        """Generate a maze grid using Prim's algorithm.

        Prim's Algorithm:
            1. Start from entry cell and mark as visited
            2. Add unvisited neighbors to frontier
            3. Randomly select a wall from frontier
            4. If the wall connects to unvisited cell, carve passage
            5. Add new cell's walls to frontier
            6. Repeat until frontier is empty

        Pattern Support:
            - Respects protected 'F' cells (pattern obstacles)
            - Carves through '0' pattern cells normally
            - Creates guaranteed connection from entry to exit

        Args:
            WIDTH, HEIGHT: Maze dimensions
            ENTRY_X, ENTRY_Y: Starting cell coordinates
            SEED: Random seed for reproducibility
            PERFECT: When True, do not add cycles.
            initial_maze: Pre-initialized maze (with pattern applied)
            protected_cells: Set of (x,y) tuples marking 'F' cells to
                protect
            additional_start_points: List of additional (x,y) tuples to
                start from

        Returns:
            list[list[int]]: 2D wall-bitmask grid.

        Notes:
            The entry cell is always included as a start point.
        """
        # Use random.seed(None) to generate a different sequence each time
        random.seed(SEED)

        if initial_maze is None:
            maze = [[self.ALL_WALLS for _ in range(
                WIDTH)] for _ in range(HEIGHT)]
        else:
            # Use a copy of the initial maze (which has the pattern applied)
            maze = [row[:] for row in initial_maze]

        if protected_cells is None:
            protected_cells = set()

        if additional_start_points is None:
            additional_start_points = []

        frontier = []

        # Collect all starting points (entry must always be included)
        if HEIGHT == 5 and WIDTH == 7:
            all_start_points = ([(ENTRY_X, ENTRY_Y)] +
                                list(additional_start_points))
        else:
            all_start_points = [(ENTRY_X, ENTRY_Y)]

        # Initialize from all starting points
        for start_x, start_y in all_start_points:
            if 0 <= start_x < WIDTH and 0 <= start_y < HEIGHT:
                # Mark cell as visited (carve it out: make it open) if not
                # protected
                if (maze[start_y][start_x] == self.ALL_WALLS and
                        (start_x, start_y) not in protected_cells):
                    if PERFECT is True:
                        maze[start_y][start_x] = maze[start_y][start_x]
                    else:
                        if WIDTH == 7 and HEIGHT == 5:
                            maze[start_y][start_x] = maze[start_y][start_x]
                        else:
                            maze[start_y][start_x] = maze[start_y][start_x]
                self.add_walls_to_frontier(
                    start_x, start_y, maze, WIDTH, HEIGHT, frontier,
                    protected_cells)

        while frontier:
            x1, y1, direction = random.choice(frontier)
            dx, dy, current_bit, opposite_bit = self.MOVEMENTS[direction]
            x2, y2 = x1 + dx, y1 + dy

            if (0 <= x2 < WIDTH and 0 <= y2 < HEIGHT and
                    maze[y2][x2] == self.ALL_WALLS):

                # Only carve if not a protected 'F' cell
                if (x1, y1) not in protected_cells:
                    maze[y1][x1] &= ~current_bit
                if (x2, y2) not in protected_cells:
                    maze[y2][x2] &= ~opposite_bit

                self.add_walls_to_frontier(x2, y2, maze, WIDTH, HEIGHT,
                                           frontier, protected_cells)

            frontier.remove((x1, y1, direction))

        return maze

    def enforce_border_walls(self, maze, W, H):
        """Enforce a solid perimeter by restoring outer border walls.

        This ensures the maze has a closed border.

        Args:
            maze: 2D list of cell values (bitmasked walls)
            W, H: Maze dimensions

        Returns:
            list[list[int]]: Modified maze.
        """

        for x in range(W):
            maze[0][x] |= self.NORTH
            maze[H - 1][x] |= self.SOUTH
        for y in range(H):
            maze[y][0] |= self.WEST
            maze[y][W - 1] |= self.EAST
        return maze

    def check_no_large_empty_spaces(self, maze, W, H, min_size=3):
        """
        Validates that the maze does NOT contain empty rectangular spaces
        of min_size x min_size or larger.

        An "empty space" is defined as a rectangular region where all cells
        have no internal walls (i.e., all 4 passage bits are open).

        Algorithm: O(n²) Maximal Rectangle Detection
            1. Build height matrix: consecutive open cells above each position
            2. For each row, use stack-based algorithm to detect all rectangles
            3. Check if any rectangle >= min_size × min_size
            4. Early exit on first violation found

        Complexity: O(W × H) instead of O(W² × H²)

        Args:
            maze: 2D list of cell values (bitmasked walls)
            W, H: Maze dimensions
            min_size: Minimum rectangle size to check (default: 3)

        Returns:
            Tuple: (is_valid, violations)
            - is_valid: True if no large empty spaces found, False otherwise
            - violations: List of found violations as tuples
            ((x, y, width, height), num_cells)
        """
        violations = []

        # Step 1: Build height matrix (consecutive open cells above each cell)
        height = [[0] * W for _ in range(H)]
        for y in range(H):
            for x in range(W):
                if maze[y][x] == 0:  # Cell is open
                    height[y][x] = 1 if y == 0 else height[y - 1][x] + 1
                else:
                    height[y][x] = 0

        # Step 2: For each row, find all maximal rectangles using stack algo
        for y in range(H):
            stack = []  # Stack of (width, start_x)

            for x in range(W):
                h = height[y][x]
                start_x = x

                # Pop rectangles taller than current height
                while stack:
                    w, sx = stack[-1]
                    if w <= h:
                        break
                    stack.pop()
                    # Check rectangle: width=w, height at row y is
                    # (height[y][x] after pop)
                    rect_width = x - sx
                    rect_height = w
                    if (rect_width >= min_size and
                            rect_height >= min_size):
                        violations.append(
                            ((sx, y - rect_height + 1, rect_width,
                              rect_height), rect_width * rect_height)
                        )
                    start_x = sx

                # Push current height if non-zero
                if h > 0:
                    stack.append((h, start_x))

            # Process remaining stack
            while stack:
                w, sx = stack.pop()
                rect_width = W - sx
                rect_height = w
                if (rect_width >= min_size and
                        rect_height >= min_size):
                    violations.append(
                        ((sx, H - rect_height, rect_width, rect_height),
                         rect_width * rect_height)
                    )

        is_valid = len(violations) == 0
        return is_valid, violations

    # =================================================================
    # 4. Pattern Application
    # =================================================================

    def insert_centered_pattern(self, W, H):
        """Insert the centered 7x5 "42" pattern into a template maze.

        Pattern (7×5):
            F000FFF
            F00000F
            FFF0FFF
            00F0F00
            00F0FFF

        'F' cells: protected (remain ALL_WALLS)
        '0' cells: openable by generator (not protected from carving)

        Returns:
            tuple: ``(maze, protected_f, protected_open, collapse_cells)``.

        Notes:
            This function assumes ``W >= 7`` and ``H >= 5``.
        """
        maze = [[self.ALL_WALLS for _ in range(W)] for _ in range(H)]
        pattern = [
            "F000FFF",
            "F00000F",
            "FFF0FFF",
            "00F0F00",
            "00F0FFF",
        ]
        pw, ph = 7, 5
        start_x = (W - pw) // 2
        start_y = (H - ph) // 2

        protected_f = set()
        protected_open = set()
        collapse_cells = set()

        for dy in range(ph):
            for dx in range(pw):
                x, y = start_x + dx, start_y + dy
                ch = pattern[dy][dx]
                if 0 <= x < W and 0 <= y < H:
                    if ch == 'F':
                        # Keep as ALL_WALLS and protect from carving
                        maze[y][x] = self.ALL_WALLS
                        protected_f.add((x, y))
                    elif ch == '0':
                        # Start as ALL_WALLS but marked as open cells (not
                        # protected)
                        maze[y][x] = self.ALL_WALLS
                        protected_open.add((x, y))

                        if (dx, dy) in self.COLLAPSE_3:
                            collapse_cells.add((x, y))
        return maze, protected_f, protected_open, collapse_cells

    def save_to_final_format(self, maze_bytes, W, H, ENTRY_X, ENTRY_Y,
                             EXIT_X, EXIT_Y, solution_paths, filename,
                             seed=None):
        """Save the maze to the final output format.

        Args:
            maze_bytes: 2D list representing the maze with bitmasked
                wall values
            W, H: Width and height of the maze
            ENTRY_X, ENTRY_Y: Entry point coordinates (0-indexed)
            EXIT_X, EXIT_Y: Exit point coordinates (0-indexed)
            solution_paths: List of direction strings from entry to exit.
                        If single string, converts to list.
            filename: Output file name
            seed: Random seed used (int). Always included for
                reproducibility.

    The output file contains:

    1. Hexadecimal matrix (H lines)
    2. Blank line
    3. Entry coordinates (0-indexed)
    4. Exit coordinates (0-indexed)
    5. Seed
    6. Blank line
    7. One or more solution paths
    """
        # Ensure solution_paths is a list
        if isinstance(solution_paths, str):
            solution_paths = [solution_paths]

        with open(filename, 'w') as f:
            # 1. Hexadecimal Matrix
            for row in maze_bytes:
                hex_row = "".join([f"{cell:X}" for cell in row])
                f.write(hex_row + '\n')

            # 2. Entry/Exit Coordinates (1-based indexing for output file)
            f.write(f"\n{ENTRY_X},{ENTRY_Y}\n")
            f.write(f"{EXIT_X},{EXIT_Y}\n")

            # 3. Seed (always included for reproducibility)
            f.write(f"{seed}\n")

            # 4. Solution Paths (all of them)
            f.write("\n")
            for solution_path in solution_paths:
                f.write(f"{solution_path}\n")

    def save_seed_file(self, seed, config, maze_bytes, solution_paths):
        """Persist a generated maze to ``seeds/<seed>.maze``.

        The file is written with read-only permissions (0444) after creation
        to prevent accidental edits.

        Args:
            seed (int): Seed used to generate the maze.
            config (dict): Maze configuration.
            maze_bytes (list[list[int]]): Bitmask grid.
            solution_paths (list[str] | str): One or more solution strings.
        """
        path = f"seeds/{seed}.maze"

        # If file exists, make it writable first
        if os.path.exists(path):
            os.chmod(path, 0o644)

        # Ensure solution_paths is a list
        if isinstance(solution_paths, str):
            solution_paths = [solution_paths]

        with open(path, 'w') as f:
            f.write(f"WIDTH={config['WIDTH']}\n")
            f.write(f"HEIGHT={config['HEIGHT']}\n")
            f.write(f"SEED={config['SEED']}\n")

            for row in maze_bytes:
                hex_row = "".join([f"{cell:X}" for cell in row])
                f.write(hex_row + '\n')

            f.write(f"ENTRY={config['ENTRY_X']},{config['ENTRY_Y']}\n")
            f.write(f"EXIT={config['EXIT_X']},{config['EXIT_Y']}\n")

            for solution_path in solution_paths:
                f.write(f"PATH={solution_path}\n")

        os.chmod(path, 0o444)

    def check_seeds_dir(self):
        """Ensure the ``seeds/`` directory exists and is a directory.

        Creates the directory with 0755 permissions if missing.

        Raises:
            ValueError: If ``seeds`` exists but is not a directory.
        """
        path = "seeds"

        if not os.path.exists(path):
            os.mkdir(path)
            os.chmod(path, 0o755)
        else:
            if not os.path.isdir(path):
                raise ValueError(
                    "Error: 'seeds' exists but is not a directory")

    # =================================================================
    # 5. Maze Solver (BFS)
    # =================================================================

    def get_solution_path(
            self,
            maze_bytes,
            W,
            H,
            ENTRY_X,
            ENTRY_Y,
            EXIT_X,
            EXIT_Y):
        """Return one shortest path from entry to exit using BFS.

        BFS Algorithm:
            1. Initialize queue with entry cell
            2. Dequeue cell and check all 4 directions (N, S, E, O/W)
            3. For each direction: check if passage exists (no wall bit set)
            4. If valid, mark as visited and add to queue
            5. Track parent pointers to reconstruct path
            6. Continue until exit cell is dequeued
            7. Backtrack through parents to build direction sequence

        Wall Checking:
            - Check maze[y][x] & bit_to_check for wall in current cell
            - If result is 0 (no wall), passage is open
            - Only traverse if passage exists AND neighbor unvisited

        Args:
            maze_bytes: 2D list of cell values (bitmasked walls)
            W, H: Maze dimensions
            ENTRY_X, ENTRY_Y: Starting position (0-indexed)
            EXIT_X, EXIT_Y: Target position (0-indexed)

        Returns:
            String of directions: 'E'=East, 'S'=South, 'N'=North, 'W'=West
            Example: "EESSSESSS" means: East, East, South, South, South,
            East, South, South, South
            Returns "NO_SOLUTION_FOUND" if no path exists (should never
            happen with valid maze)
        """

        father = [[None for _ in range(W)] for _ in range(H)]
        queue = deque([(ENTRY_X, ENTRY_Y)])

        SOLVER_MOVES = {
            'S': (0, 1, self.SOUTH, 'S'),
            'E': (1, 0, self.EAST, 'E'),
            'N': (0, -1, self.NORTH, 'N'),
            'W': (-1, 0, self.WEST, 'W')
        }

        father[ENTRY_Y][ENTRY_X] = (-1, -1, None)

        while queue:
            x, y = queue.popleft()

            if x == EXIT_X and y == EXIT_Y:
                break

            for dir_char, (dx, dy, bit_to_check, _) in SOLVER_MOVES.items():
                nx, ny = x + dx, y + dy

                if 0 <= nx < W and 0 <= ny < H and father[ny][nx] is None:

                    if not (maze_bytes[y][x] & bit_to_check):
                        father[ny][nx] = (x, y, dir_char)
                        queue.append((nx, ny))
        else:
            return "NO_SOLUTION_FOUND"

        path = []
        x, y = EXIT_X, EXIT_Y

        while x != ENTRY_X or y != ENTRY_Y:
            px, py, movement = father[y][x]
            path.append(movement)
            x, y = px, py

        path.reverse()
        return "".join(path)

    def get_all_solution_paths(
            self,
            maze_bytes,
            W,
            H,
            ENTRY_X,
            ENTRY_Y,
            EXIT_X,
            EXIT_Y,
            max_solutions=10):
        """Find multiple distinct paths in a maze with cycles.

        This runs a randomized BFS multiple times to discover alternative
        parent reconstructions.

        Args:
            maze_bytes: 2D list of cell values (bitmasked walls)
            W, H: Maze dimensions
            ENTRY_X, ENTRY_Y: Starting position (0-indexed)
            EXIT_X, EXIT_Y: Target position (0-indexed)
            max_solutions: Maximum number of solutions to find

        Returns:
            list[str]: Unique solution strings, or ``["NO_SOLUTION_FOUND"]``.
        """
        solutions = []

        SOLVER_MOVES = {
            'S': (0, 1, self.SOUTH, 'S'),
            'E': (1, 0, self.EAST, 'E'),
            'N': (0, -1, self.NORTH, 'N'),
            'W': (-1, 0, self.WEST, 'W')
        }

        # Find a path, use different random choices at junctions
        # Increase attempts to find more solutions
        max_attempts = max(max_solutions * 10, 50)
        for attempt in range(max_attempts):
            if len(solutions) >= max_solutions:
                break

            father = [[None for _ in range(W)] for _ in range(H)]
            queue = deque([(ENTRY_X, ENTRY_Y)])
            father[ENTRY_Y][ENTRY_X] = (-1, -1, None)
            found = False

            while queue:
                x, y = queue.popleft()

                if x == EXIT_X and y == EXIT_Y:
                    found = True
                    break

                # Get available moves
                available = []
                for dir_char, (dx, dy, bit_to_check, _) in (
                        SOLVER_MOVES.items()):
                    nx, ny = x + dx, y + dy

                    if (0 <= nx < W and 0 <= ny < H and
                            father[ny][nx] is None and
                            not (maze_bytes[y][x] & bit_to_check)):
                        available.append((dir_char, dx, dy,
                                          bit_to_check, nx, ny))

                # At junctions (multiple options), randomize order ALWAYS
                if len(available) > 1:
                    random.shuffle(available)

                for dir_char, dx, dy, bit_to_check, nx, ny in available:
                    father[ny][nx] = (x, y, dir_char)
                    queue.append((nx, ny))

            if not found:
                continue

            # Reconstruct path
            path = []
            x, y = EXIT_X, EXIT_Y

            while x != ENTRY_X or y != ENTRY_Y:
                px, py, movement = father[y][x]
                path.append(movement)
                x, y = px, py

            path.reverse()
            solution_path = "".join(path)

            if solution_path not in solutions:
                solutions.append(solution_path)

        return solutions if solutions else ["NO_SOLUTION_FOUND"]

    def select_most_different_solutions(self, solutions, entry_x, entry_y,
                                        num_to_select=10):
        """Select a subset of solutions that differ the most.

        Uses Jaccard distance on the set of visited cells of each path to
        choose paths that overlap as little as possible.

        Args:
            solutions (list[str]): Candidate solution strings.
            entry_x (int): Entry X coordinate.
            entry_y (int): Entry Y coordinate.
            num_to_select (int): Maximum number of paths to return.

        Returns:
            list[str]: Selected solution strings.
        """

        def path_to_cells(path, entry_x, entry_y):
            x, y = entry_x, entry_y
            cells = {(x, y)}

            for move in path:
                if move == 'N':
                    y -= 1
                elif move == 'S':
                    y += 1
                elif move == 'E':
                    x += 1
                elif move == 'W':
                    x -= 1
                cells.add((x, y))
            return cells

        def jaccard_distance(a, b):
            return (1 - len(a & b) / len(a | b))

        paths = [path_to_cells(sol, entry_x, entry_y) for sol in solutions]

        selected = [paths[0]]
        selected_index = [0]

        while len(selected) < num_to_select:
            best_index = None
            best_score = -1

            for i, candidate in enumerate(paths):
                if i in selected_index:
                    continue

                score = min(jaccard_distance(candidate, sel)
                            for sel in selected)

                if score > best_score:
                    best_index = i

            if best_index is None:
                break
            selected.append(paths[best_index])
            selected_index.append(best_index)

        return [solutions[i] for i in selected_index]

    # =================================================================
    # 6. Maze Generator setter
    # =================================================================

    def generate_maze(self, config):
        """Generate a maze and compute one or more solutions.

        The generation always uses Prim.

        - ``PERFECT=true``: perfect maze (single solution expected).
        - ``PERFECT=false``: cycles are added by opening extra passages,
            then multiple solutions are searched.

        The centered 7x5 "42" pattern is applied only if the map is at
        least 7x5.

        Args:
                config (dict): Parsed configuration.

        Returns:
                tuple[list[list[int]], list[str]] | None:
                ``(maze, solutions)`` or None if the caller should retry with a
                different seed.
        """
        WIDTH = config['WIDTH']
        HEIGHT = config['HEIGHT']
        ENTRY_X, ENTRY_Y = config['ENTRY_X'], config['ENTRY_Y']
        EXIT_X, EXIT_Y = config['EXIT_X'], config['EXIT_Y']
        SEED = config['SEED']
        PERFECT = config.get('PERFECT', True)

        def find_breaking_walls(maze, WIDTH, HEIGHT, protected):
            poss_walls = []

            for y in range(HEIGHT):
                for x in range(WIDTH):
                    if (x, y) in protected:
                        continue

                    for dx, dy, bit, opp in self.MOVEMENTS.values():
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < WIDTH and 0 <= ny < HEIGHT:
                            if (nx, ny) in protected:
                                continue

                            if (maze[y][x] &
                                    bit) and maze[ny][nx] != self.ALL_WALLS:
                                poss_walls.append((x, y, bit, nx, ny, opp))

            return poss_walls

        def add_cycles(
                maze,
                WIDTH,
                HEIGHT,
                protected,
                extra_doors=10,
                seed=None):
            if seed is not None:
                random.seed(seed)

            walls = find_breaking_walls(maze, WIDTH, HEIGHT, protected)
            random.shuffle(walls)

            opened = 0
            for x, y, bit, nx, ny, opp in walls:
                if opened >= extra_doors:
                    break

                maze[y][x] &= ~bit
                maze[ny][nx] &= ~opp
                opened += 1

        # ===== VALIDATION: Same constraints for both algorithms =====
        # Check dimensions (small maps are allowed, but pattern may be skipped)
        if not (1 <= WIDTH <= 1024):
            raise ValueError("Width must be between 1 and 1024")
        if not (1 <= HEIGHT <= 1024):
            raise ValueError("Height must be between 1 and 1024")

        # Check entry is within bounds
        if not (0 <= ENTRY_X < WIDTH and 0 <= ENTRY_Y < HEIGHT):
            raise ValueError(f"Entry {ENTRY_X},{ENTRY_Y} out of bounds")

        # Check exit is within bounds
        if not (0 <= EXIT_X < WIDTH and 0 <= EXIT_Y < HEIGHT):
            raise ValueError(f"Exit {EXIT_X},{EXIT_Y} out of bounds")

        # Pattern (42) is 7x5. If a map is smaller, skip the pattern.
        use_pattern = (WIDTH >= 7 and HEIGHT >= 5)
        if use_pattern:
            (maze_with_pattern, protected_f_cells, protected_open_cells,
             collapse_cells) = (self.insert_centered_pattern(WIDTH, HEIGHT))
        else:
            # Print this only once per execution (even if generate_maze is
            # retried many times in a loop).
            if not getattr(self, "_warned_small_pattern", False):
                print(
                    "the map is too small for the 42 patern, "
                    " so we follow without it"
                )
                self._warned_small_pattern = True
            maze_with_pattern = [
                [self.ALL_WALLS for _ in range(WIDTH)]
                for _ in range(HEIGHT)
            ]
            protected_f_cells = set()
            protected_open_cells = set()
            collapse_cells = set()

        # Choose algorithm based on PERFECT flag
        if PERFECT:
            additional_starts = set(collapse_cells)
            maze_bytes = self.run_prim_generator(
                WIDTH,
                HEIGHT,
                ENTRY_X,
                ENTRY_Y,
                SEED,
                PERFECT,
                initial_maze=maze_with_pattern,
                protected_cells=protected_f_cells,
                additional_start_points=additional_starts)
            # For perfect mazes: start from entry + all pattern open cells
            maze_bytes = self.enforce_border_walls(maze_bytes,
                                                   WIDTH, HEIGHT)
            # Prim creates perfect mazes, so only one solution typically
            solution_paths = [
                self.get_solution_path(
                    maze_bytes,
                    WIDTH,
                    HEIGHT,
                    ENTRY_X,
                    ENTRY_Y,
                    EXIT_X,
                    EXIT_Y)]

        else:
            # For non-perfect mazes: start from entry + all pattern open cells
            if use_pattern and WIDTH == 7 and HEIGHT == 5:
                additional_starts = set(protected_open_cells)
            else:
                additional_starts = set(collapse_cells)
            maze_bytes = self.run_prim_generator(
                WIDTH,
                HEIGHT,
                ENTRY_X,
                ENTRY_Y,
                SEED,
                PERFECT,
                initial_maze=maze_with_pattern,
                protected_cells=protected_f_cells,
                additional_start_points=additional_starts)
            maze_bytes = self.enforce_border_walls(maze_bytes, WIDTH, HEIGHT)
            # Calculate adaptive extra_doors based on maze size
            total_cells = WIDTH * HEIGHT
            # 5% of cells, minimum 5
            extra_doors = max(5, int(total_cells * 0.05))
            # Protect BOTH F and 0 cells from being closed by add_cycles
            all_protected = protected_f_cells | protected_open_cells
            add_cycles(maze_bytes, WIDTH, HEIGHT, all_protected,
                       extra_doors=extra_doors, seed=SEED)
            # WFC can have multiple solutions
            all_solutions = self.get_all_solution_paths(
                maze_bytes, WIDTH, HEIGHT, ENTRY_X, ENTRY_Y, EXIT_X,
                EXIT_Y, max_solutions=10)
            # Select the most different solutions (up to 3)
            solution_paths = self.select_most_different_solutions(
                all_solutions, ENTRY_X, ENTRY_Y, num_to_select=min(
                    3, len(all_solutions)))

            # For PERFECT=false, ALWAYS ensure at least 2 solutions
            if len(solution_paths) < 1:
                # Retry: not enough solutions found
                return None

        # ===== Validate entry and exit are not in ALL_WALLS cells =====
        # Only apply this check when the 42 pattern is enabled. When the
        # pattern is skipped for small maps, ALL_WALLS is just an
        # uncarved/isolated cell from the generator perspective.
        if use_pattern:
            entry_cell = maze_bytes[ENTRY_Y][ENTRY_X]
            exit_cell = maze_bytes[EXIT_Y][EXIT_X]

            if entry_cell == self.ALL_WALLS:
                raise ValueError(
                    f"Entry at ({ENTRY_X},{ENTRY_Y}) is in an ALL_WALLS"
                    " cell. Entry cannot be in the pattern 42.")
            if exit_cell == self.ALL_WALLS:
                raise ValueError(
                    f"Exit at ({EXIT_X},{EXIT_Y}) is in an ALL_WALLS "
                    "cell. Exit cannot be in the pattern 42.")

        # ===== Validate NO large empty spaces (3x3 or larger) =====
        # If map is smaller than 3x3, this constraint is not applicable.
        if WIDTH >= 3 and HEIGHT >= 3:
            is_valid_spaces, violations = self.check_no_large_empty_spaces(
                maze_bytes, WIDTH, HEIGHT, min_size=3)
            if not is_valid_spaces:
                # Return None to indicate validation failure; caller will
                # retry with a new seed.
                return None

        # ===== Validate SOLVABILITY: maze must be solvable =====
        # Try to find at least one solution using BFS
        test_solution = self.get_solution_path(
            maze_bytes, WIDTH, HEIGHT, ENTRY_X, ENTRY_Y, EXIT_X, EXIT_Y)
        if test_solution == "NO_SOLUTION_FOUND":
            # Maze is not solvable, retry with new seed
            return None

        return maze_bytes, solution_paths

    # =================================================================
    # 7. Render Maze
    # =================================================================

    def render_maze_mlx(self, maze_bytes, config, solution_paths):

        height = config["HEIGHT"]
        width = config["WIDTH"]
        entry_x, entry_y = config["ENTRY_X"], config["ENTRY_Y"]
        exit_x, exit_y = config["EXIT_X"], config["EXIT_Y"]

        mlx_inst = Mlx()
        mlx_ptr = mlx_inst.mlx_init()

        # Margins around the maze
        margin_top = 4 * self.CELL_SIZE      # 4 lines above
        margin_right = 16 * self.CELL_SIZE   # 28 lines to the right
        margin_left = 16 * self.CELL_SIZE    # 28 lines to the left
        margin_bottom = 15 * self.CELL_SIZE  # 15 lines below

        # Original maze size
        maze_w = width * self.CELL_SIZE
        maze_h = height * self.CELL_SIZE

        # Total window size with margins
        win_w = maze_w + margin_left + margin_right
        win_h = maze_h + margin_top + margin_bottom

        # Offset for maze drawing
        maze_offset_x = margin_left
        maze_offset_y = margin_top

        show_solution = False
        path_cells = {}  # Change to dict: {(x,y): color}
        current_maze = [row[:] for row in maze_bytes]
        current_solutions = solution_paths if isinstance(
            solution_paths, list) else [solution_paths]
        current_solution_idx = -1
        current_config = config.copy()
        is_perfect = current_config.get('PERFECT', True)
        wall_color_state = 0  # 0: blanco, 1: rosa, 2: morado

        # ==========================================
        # 1. CREATE THE WINDOW
        # ==========================================
        win = mlx_inst.mlx_new_window(mlx_ptr, win_w, win_h, "A-Maze-Ing")

        # ==========================================
        # 2. SET UP THE IMAGES
        # ==========================================
        def set_images(w, h, color):
            """Creates an image of size w x h completely filled with the
            given color
            """
            img = mlx_inst.mlx_new_image(mlx_ptr, w, h)
            data, bpp, size_line, fmt = mlx_inst.mlx_get_data_addr(img)

            # Fill the entire image (w x h) with the specified color
            for y in range(h):
                for x in range(w):
                    offset = y * size_line + x * (bpp // 8)
                    data[offset] = color & 0xFF
                    data[offset + 1] = (color >> 8) & 0xFF
                    data[offset + 2] = (color >> 16) & 0xFF
                    if bpp == 32:
                        data[offset + 3] = 0xFF
            return img

        bg_img = set_images(self.CELL_SIZE, self.CELL_SIZE,
                            self.BG_COLOR)
        path_img = set_images(self.CELL_SIZE, self.CELL_SIZE,
                              self.PATH_COLOR)
        sol1_img = set_images(self.CELL_SIZE, self.CELL_SIZE,
                              self.SOLUTION_1_COLOR)
        sol2_img = set_images(self.CELL_SIZE, self.CELL_SIZE,
                              self.SOLUTION_2_COLOR)
        sol3_img = set_images(self.CELL_SIZE, self.CELL_SIZE,
                              self.SOLUTION_3_COLOR)
        entry_img = set_images(self.CELL_SIZE, self.CELL_SIZE,
                               self.ENTRY_COLOR)
        exit_img = set_images(self.CELL_SIZE, self.CELL_SIZE,
                              self.EXIT_COLOR)

        # Create initial wall images (white)
        # Thin walls: 1 pixel thickness
        wall_thickness = 1
        wall_h_img = set_images(
            self.CELL_SIZE,
            wall_thickness,
            self.WALL_COLOR_WHITE)
        wall_v_img = set_images(
            wall_thickness,
            self.CELL_SIZE,
            self.WALL_COLOR_WHITE)
        wall_full_img = set_images(
            self.CELL_SIZE,
            self.CELL_SIZE,
            self.WALL_COLOR_WHITE)

        # Create border images - FULL SIZE
        # Horizontal border: width = total maze width, height = 1 pixel
        border_h_img = set_images(
            width * self.CELL_SIZE, 1, self.WALL_COLOR_WHITE)
        # Vertical border: width = 1 pixel, height = total maze height + 2
        # (for north and south)
        border_v_img = set_images(
            1, height * self.CELL_SIZE + 2, self.WALL_COLOR_WHITE)

        # Function to update wall images based on color
        def update_wall_colors(color_idx):
            nonlocal wall_h_img, wall_v_img, wall_full_img, border_h_img
            nonlocal border_v_img
            if color_idx == 0:
                current_color = self.WALL_COLOR_WHITE
            elif color_idx == 1:
                current_color = self.WALL_COLOR_PINK
            else:  # color_idx == 2
                current_color = self.WALL_COLOR_PURPLE

            # Thin walls: 1 pixel thickness
            wall_thickness = 1
            wall_h_img = set_images(
                self.CELL_SIZE, wall_thickness, current_color)
            wall_v_img = set_images(
                wall_thickness, self.CELL_SIZE, current_color)
            wall_full_img = set_images(
                self.CELL_SIZE, self.CELL_SIZE, current_color)

            # Update border images - FULL SIZE
            border_h_img = set_images(width * self.CELL_SIZE, 1, current_color)
            border_v_img = set_images(
                1, height * self.CELL_SIZE + 2, current_color)

        # ==========================================
        # 3. KEYHOOK (KEY 1)
        # ==========================================
        def close_window(param=None):

            mlx_inst.mlx_destroy_window(mlx_ptr, win)
            mlx_inst.mlx_loop_exit(mlx_ptr)

        def on_destroy(param):
            """Callback for when the window is closed with the X"""
            close_window(param)
            return 0

        def path_cells_setter_single(solution, color_idx):
            """
            Draws a single solution with a specific color.
            color_idx: 1 (blue), 2 (yellow), 3 (cyan)
            """
            cx = entry_x
            cy = entry_y

            if (cx, cy) not in path_cells:
                path_cells[(cx, cy)] = color_idx

            for move in solution:
                if move == "N":
                    cy -= 1
                elif move == "S":
                    cy += 1
                elif move == "E":
                    cx += 1
                elif move == "W":
                    cx -= 1

                path_cells[(cx, cy)] = color_idx

        def key_hook(keycode, param):

            nonlocal show_solution, current_maze, current_solutions
            nonlocal current_solution_idx, is_perfect
            nonlocal wall_color_state

            if keycode == self.ESC:
                close_window(param)
            elif keycode == self.KEY_3:  # Key 3: Change wall color
                wall_color_state = (wall_color_state + 1) % 3
                update_wall_colors(wall_color_state)
                # Redraw everything: maze + borders (but not instructions)
                clear_maze_background()
                draw_maze(current_maze)
            elif keycode == self.KEY_2:  # Key 2: Navigate between solutions
                if len(current_solutions) > 1:
                    # WFC: navigate between solutions with different colors
                    num_sols = min(3, len(current_solutions))
                    # Always in "showing" mode for multiple solutions
                    current_solution_idx += 1
                    if current_solution_idx >= num_sols:
                        current_solution_idx = -1
                        path_cells.clear()
                        show_solution = False

                    else:
                        # Display current solution with its color (1=blue,
                        # 2=yellow, 3=cyan)
                        path_cells.clear()
                        color = current_solution_idx + 1
                        path_cells_setter_single(
                            current_solutions[current_solution_idx],
                            color)
                        show_solution = True
                else:
                    # PRIM: toggle show/hide of the only solution
                    show_solution = not show_solution
                    path_cells.clear()
                    if show_solution:
                        path_cells_setter(current_maze,
                                          current_solutions[0])
                    else:
                        path_cells.clear()
                # Only redraw the maze, not the instructions
                draw_maze(current_maze)
            elif keycode == self.KEY_1:  # Key 1: Generate new map
                # Retry loop to ensure valid maze generation
                max_retries = 1000
                attempt = 0
                maze_result = None

                while maze_result is None and attempt < max_retries:
                    attempt += 1
                    current_config['SEED'] = random.randint(0, 2147483647)
                    maze_result = self.generate_maze(current_config)

                if maze_result is None:
                    # Failed after max retries, keep current maze
                    return 0

                current_maze, current_solutions = maze_result
                current_solution_idx = -1
                is_perfect = current_config.get('PERFECT', True)
                self.check_seeds_dir()

                self.save_seed_file(current_config['SEED'], current_config,
                                    current_maze, current_solutions)
                path_cells.clear()
                show_solution = False
                self.save_to_final_format(
                    current_maze, current_config.get("WIDTH"),
                    current_config.get("HEIGHT"),
                    current_config.get("ENTRY_X"),
                    current_config.get("ENTRY_Y"),
                    current_config.get("EXIT_X"),
                    current_config.get("EXIT_Y"),
                    current_solutions, current_config.get("OUTPUT_FILE"),
                    current_config.get("SEED"))
                if not is_perfect and len(current_solutions) > 1:
                    path_cells_setter_single(current_solutions[0],
                                             1)
                else:
                    path_cells_setter(current_maze,
                                      current_solutions[0])
                draw_complete_maze()
            return 0

        mlx_inst._python_ref_std["close_f"] = on_destroy
        mlx_inst._python_ref_std["key_f"] = key_hook

        mlx_inst.mlx_hook(win, 33, 0, on_destroy, None)
        mlx_inst.mlx_key_hook(win, key_hook, None)

        # ==========================================
        # 4. MAZE GENERATOR
        # ==========================================
        def draw_complete_maze():
            """Draws the complete maze: maze, borders and instructions"""
            # Clear the maze background (maze area)
            clear_maze_background()
            # draw_maze() already includes draw_border()
            draw_maze(current_maze)
            draw_instructions()

        def clear_maze_background():
            """Clears the maze area background using images"""
            # Use the background image to clear instead of individual pixels
            for y in range(height):
                for x in range(width):
                    px0 = x * self.CELL_SIZE + maze_offset_x
                    py0 = y * self.CELL_SIZE + maze_offset_y
                    mlx_inst.mlx_put_image_to_window(mlx_ptr, win, bg_img,
                                                     px0, py0)

        def draw_maze(maze_to_draw):
            # Draw each cell
            for y, row in enumerate(maze_to_draw):
                for x, cell in enumerate(row):
                    draw_cell(cell, x, y)

            # Draw borders as integrated wall lines
            draw_integrated_borders()

        def draw_integrated_borders():
            """Draws borders as integrated wall lines into the maze"""
            # Get current wall color based on state
            if wall_color_state == 0:
                border_color = self.WALL_COLOR_WHITE
            elif wall_color_state == 1:
                border_color = self.WALL_COLOR_PINK
            else:
                border_color = self.WALL_COLOR_PURPLE

            wall_thickness = 1

            # North border: horizontal line above the maze
            north_y = maze_offset_y - wall_thickness
            if north_y >= 0:
                for x in range(
                        maze_offset_x,
                        maze_offset_x +
                        width *
                        self.CELL_SIZE):
                    mlx_inst.mlx_pixel_put(
                        mlx_ptr, win, x, north_y, border_color)

            # South border: horizontal line below the maze
            south_y = maze_offset_y + height * self.CELL_SIZE
            for x in range(
                    maze_offset_x,
                    maze_offset_x +
                    width *
                    self.CELL_SIZE):
                mlx_inst.mlx_pixel_put(mlx_ptr, win, x, south_y, border_color)

            # West border: vertical line to the left of the maze
            west_x = maze_offset_x - wall_thickness
            if west_x >= 0:
                for y in range(
                        maze_offset_y -
                        wall_thickness,
                        maze_offset_y +
                        height *
                        self.CELL_SIZE +
                        wall_thickness):
                    mlx_inst.mlx_pixel_put(
                        mlx_ptr, win, west_x, y, border_color)

            # East border: vertical line to the right of the maze
            east_x = maze_offset_x + width * self.CELL_SIZE
            for y in range(
                    maze_offset_y -
                    wall_thickness,
                    maze_offset_y +
                    height *
                    self.CELL_SIZE +
                    wall_thickness):
                mlx_inst.mlx_pixel_put(mlx_ptr, win, east_x, y, border_color)

        def draw_instructions():
            """Draw the instructions in the lower part of the window with
            a light background"""
            # White color for the text
            text_color = 0xFFFFFF

            # Initial Y position: bottom margin - 3 empty lines - 5 text lines.
            # Each text line has approximately 10-14 pixels of height
            line_height = 14
            margin_for_text = 3 * line_height  # 3 empty lines

            # Y position where instructions begin
            start_y = maze_h + margin_top + margin_for_text

            # X position: small margin from the left
            start_x = maze_offset_x + 10

            # Create background for instructions using images (more efficient)
            # Fill the lower area with background images
            bg_start_y = maze_h + margin_top
            for y in range(bg_start_y, win_h, self.CELL_SIZE):
                for x in range(0, win_w, self.CELL_SIZE):
                    # Calculate the size of the area we want to fill
                    img_x = min(self.CELL_SIZE, win_w - x)
                    img_y = min(self.CELL_SIZE, win_h - y)
                    if img_x > 0 and img_y > 0:
                        mlx_inst.mlx_put_image_to_window(mlx_ptr, win, bg_img,
                                                         x, y)

            # Line 1: "Instructions"
            mlx_inst.mlx_string_put(mlx_ptr, win, start_x, start_y, text_color,
                                    "Instructions")

            # Line 2: "-------------"
            mlx_inst.mlx_string_put(
                mlx_ptr,
                win,
                start_x,
                start_y +
                line_height,
                text_color,
                "-------------")

            # Line 3: "1. Generate other map"
            mlx_inst.mlx_string_put(mlx_ptr, win, start_x, start_y + 2 *
                                    line_height, text_color,
                                    "1. Generate other map")

            # Line 4: "2. Show solutions"
            mlx_inst.mlx_string_put(
                mlx_ptr,
                win,
                start_x,
                start_y +
                3 *
                line_height,
                text_color,
                "2. Show solutions")

            # Line 5: "3. Change color of the maze"
            mlx_inst.mlx_string_put(mlx_ptr, win, start_x, start_y + 4 *
                                    line_height, text_color,
                                    "3. Change color of the maze")

        def draw_cell(cell_value, x, y):

            n_ = 0b0001
            e_ = 0b0010
            s_ = 0b0100
            w_ = 0b1000

            px0 = x * self.CELL_SIZE + maze_offset_x
            py0 = y * self.CELL_SIZE + maze_offset_y

            # If the cell has all wall bits (ALL_WALLS) fill the entire cell
            # with the wall color
            if cell_value == self.ALL_WALLS:
                mlx_inst.mlx_put_image_to_window(mlx_ptr, win,
                                                 wall_full_img,
                                                 px0, py0)
                return

            # 1. Draw background first
            mlx_inst.mlx_put_image_to_window(mlx_ptr, win, bg_img, px0, py0)

            # 2. Draw solutions
            if show_solution and (x, y) in path_cells:
                cell_color = path_cells[(x, y)]
                if cell_color == 1:  # Sol 1 - Blue
                    mlx_inst.mlx_put_image_to_window(mlx_ptr, win, sol1_img,
                                                     px0, py0)
                elif cell_color == 2:  # Sol 2 - Yellow
                    mlx_inst.mlx_put_image_to_window(mlx_ptr, win, sol2_img,
                                                     px0, py0)
                elif cell_color == 3:  # Sol 3 - Cyan
                    mlx_inst.mlx_put_image_to_window(mlx_ptr, win, sol3_img,
                                                     px0, py0)
                else:  # Unique solution - Blue
                    mlx_inst.mlx_put_image_to_window(mlx_ptr, win, path_img,
                                                     px0, py0)

            # 3. Draw entry and exit (above solutions)
            if (x, y) == (entry_x, entry_y):
                mlx_inst.mlx_put_image_to_window(mlx_ptr, win, entry_img,
                                                 px0, py0)
            if (x, y) == (exit_x, exit_y):
                mlx_inst.mlx_put_image_to_window(mlx_ptr, win, exit_img,
                                                 px0, py0)

            # 4. Draw walls ON TOP of everything
            wall_thickness = 1

            if cell_value & n_:
                mlx_inst.mlx_put_image_to_window(mlx_ptr, win, wall_h_img,
                                                 px0, py0)
            if cell_value & s_:
                # South wall: at the bottom
                mlx_inst.mlx_put_image_to_window(mlx_ptr, win, wall_h_img,
                                                 px0, py0 + self.CELL_SIZE -
                                                 wall_thickness)
            if cell_value & w_:
                mlx_inst.mlx_put_image_to_window(mlx_ptr, win, wall_v_img,
                                                 px0, py0)
            if cell_value & e_:
                # East wall: on the right side
                mlx_inst.mlx_put_image_to_window(
                    mlx_ptr, win, wall_v_img,
                    px0 + self.CELL_SIZE - wall_thickness, py0)

        def path_cells_setter(maze_to_solve, solution_to_trace):

            cx = entry_x
            cy = entry_y

            path_cells[(cx, cy)] = 0  # Color 0 for unique solution

            for move in solution_to_trace:
                if move == "N":
                    cy -= 1
                elif move == "S":
                    cy += 1
                elif move == "E":
                    cx += 1
                elif move == "W":
                    cx -= 1

                path_cells[(cx, cy)] = 0

        # ==========================================
        # 5. DISPLAY AND MAIN LOOP
        # ==========================================
        # Initialize with first solution displayed
        if len(current_solutions) > 1:
            # Multiple solutions: show first one with its color
            path_cells_setter_single(current_solutions[0], 1)
        else:
            # Single solution: show it
            path_cells_setter(current_maze, current_solutions[0])

        draw_complete_maze()

        mlx_inst.mlx_loop(mlx_ptr)


if __name__ == '__main__':

    maze = A_maze_ing()
