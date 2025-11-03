import random
import math
import logging
from .player import Player
from .ghost import Ghost

class GameState:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.players = {}
        self.ghosts = []
        self.pellets = set()
        self.power_pellets = set()
        # Game state properties
        self.game_state = 'lobby'  # 'lobby', 'playing', 'round_end'
        self.host_player_id = None  # First player to join becomes host
        self.round_duration = 300  # 5 minutes per round (in seconds)
        self.round_start_time = 0
        self.round_active = False
        self.waiting_for_restart = False
        self.max_players = 30
        
        # Extra large map dimensions (80x60 tiles, each tile is 20px) - 4x bigger than original
        self.map_width = 80
        self.map_height = 60
        self.tile_size = 20
        
        # Generate the map
        self.generate_map()
        self.spawn_pellets()
        self.spawn_ghosts()
        
    def generate_map(self):
        """Generate a random symmetrical maze with <30% walls and no enclosed spaces"""
        # 0 = wall, 1 = path, 2 = spawn point
        self.map_data = []
        
        # Initialize with walls
        for y in range(self.map_height):
            row = []
            for x in range(self.map_width):
                row.append(0)
            self.map_data.append(row)
        
        # Generate symmetrical random maze
        self._generate_symmetrical_maze()
        
        # Add spawn points (only on walkable paths)
        self.spawn_points = []
        # Collect all walkable positions first
        walkable_positions = []
        for y in range(self.map_height):
            for x in range(self.map_width):
                if self.map_data[y][x] == 1:  # Walkable path
                    walkable_positions.append((x, y))
        
        # Select spawn points from walkable positions, distributed across the map
        if walkable_positions:
            # Try to get well-distributed spawn points
            spawn_candidates = []
            
            # Divide map into regions and try to get spawn points from each
            regions = [
                # Top-left quarter
                [(x, y) for x, y in walkable_positions if x < self.map_width//2 and y < self.map_height//2],
                # Top-right quarter
                [(x, y) for x, y in walkable_positions if x >= self.map_width//2 and y < self.map_height//2],
                # Bottom-left quarter
                [(x, y) for x, y in walkable_positions if x < self.map_width//2 and y >= self.map_height//2],
                # Bottom-right quarter
                [(x, y) for x, y in walkable_positions if x >= self.map_width//2 and y >= self.map_height//2],
            ]
            
            # Get spawn points from each region
            points_per_region = 8  # 32 total spawn points across 4 regions
            for region in regions:
                if region:
                    # Sample points from this region, ensuring they're spread out
                    region_spawns = []
                    for _ in range(points_per_region):
                        if region:
                            # Find a point that's not too close to existing spawns
                            for _ in range(10):  # Try up to 10 times
                                candidate = random.choice(region)
                                # Check if it's far enough from existing spawn points
                                too_close = False
                                for existing_x, existing_y in spawn_candidates:
                                    distance = ((candidate[0] - existing_x) ** 2 + (candidate[1] - existing_y) ** 2) ** 0.5
                                    if distance < 3:  # Minimum distance between spawn points
                                        too_close = True
                                        break
                                if not too_close:
                                    spawn_candidates.append(candidate)
                                    region.remove(candidate)  # Don't reuse this position
                                    break
                            else:
                                # If we can't find a well-spaced point, just take any remaining one
                                if region:
                                    spawn_candidates.append(region.pop())
            
            # If we don't have enough spawn points, add more from remaining walkable positions
            remaining_walkable = [pos for pos in walkable_positions if pos not in spawn_candidates]
            while len(spawn_candidates) < 32 and remaining_walkable:
                spawn_candidates.append(remaining_walkable.pop(0))
            
            # Convert to spawn points and mark on map
            for x, y in spawn_candidates:
                self.map_data[y][x] = 2
                self.spawn_points.append((x * self.tile_size, y * self.tile_size))
    
    def _generate_symmetrical_maze(self):
        """Create 3x3 grid of Pac-Man mazes for 30 players"""
        import json
        import os
        
        try:
            # Load the base static maze layout
            maze_path = os.path.join(os.path.dirname(__file__), '..', 'static_maze.json')
            with open(maze_path, 'r') as f:
                maze_data = json.load(f)
            
            base_map = maze_data['data']
            base_height = len(base_map)
            base_width = len(base_map[0]) if base_height > 0 else 0
            
            # Create 3x3 grid with 1 row/column spacing between each maze
            spacing = 1
            self.map_height = (base_height * 3) + (spacing * 2)  # 3 mazes + 2 spacers
            self.map_width = (base_width * 3) + (spacing * 2)   # 3 mazes + 2 spacers
            
            # Initialize the large map with walls
            self.map_data = [[0 for _ in range(self.map_width)] for _ in range(self.map_height)]
            
            # Place the 3x3 grid of mazes
            for grid_row in range(3):
                for grid_col in range(3):
                    # Calculate starting position for this maze copy
                    start_y = grid_row * (base_height + spacing)
                    start_x = grid_col * (base_width + spacing)
                    
                    # Copy the base maze to this position
                    for y in range(base_height):
                        for x in range(base_width):
                            if (start_y + y < self.map_height and 
                                start_x + x < self.map_width):
                                self.map_data[start_y + y][start_x + x] = base_map[y][x]
            
            # Create connecting corridors between maze sections
            self._create_connecting_corridors(base_width, base_height, spacing)
            
            print(f"Created 3x3 maze grid: {self.map_width}x{self.map_height}")
            
        except Exception as e:
            print(f"Error creating 3x3 maze grid: {e}")
            print("Falling back to procedural generation")
            self._generate_fallback_maze()
    
    def _create_connecting_corridors(self, base_width, base_height, spacing):
        """Create corridors connecting the 3x3 maze grid"""
        # Horizontal corridors (connecting left-right) - make them wider
        for grid_row in range(3):
            y_center = grid_row * (base_height + spacing) + base_height // 2
            
            # Connect maze 0-1 and 1-2 in this row
            for grid_col in range(2):
                x_start = (grid_col + 1) * base_width + grid_col * spacing
                x_end = x_start + spacing
                
                # Create wider horizontal corridor (3 tiles high)
                for y_offset in range(-1, 2):
                    corridor_y = y_center + y_offset
                    if 0 <= corridor_y < self.map_height:
                        for x in range(x_start, x_end):
                            if 0 <= x < self.map_width:
                                self.map_data[corridor_y][x] = 1  # Path
                
                # Ensure connection to mazes left and right
                # Connect to maze on left
                maze_left_x = (grid_col + 1) * base_width + grid_col * spacing - 1
                if 0 <= maze_left_x < self.map_width:
                    for y_offset in range(-1, 2):
                        corridor_y = y_center + y_offset
                        if 0 <= corridor_y < self.map_height:
                            self.map_data[corridor_y][maze_left_x] = 1  # Path
                
                # Connect to maze on right
                maze_right_x = x_end
                if 0 <= maze_right_x < self.map_width:
                    for y_offset in range(-1, 2):
                        corridor_y = y_center + y_offset
                        if 0 <= corridor_y < self.map_height:
                            self.map_data[corridor_y][maze_right_x] = 1  # Path
        
        # Vertical corridors (connecting top-bottom) - make them wider and ensure connection
        for grid_col in range(3):
            x_center = grid_col * (base_width + spacing) + base_width // 2
            
            # Connect maze row 0-1 and 1-2 in this column
            for grid_row in range(2):
                y_start = (grid_row + 1) * base_height + grid_row * spacing
                y_end = y_start + spacing
                
                # Create wider vertical corridor (3 tiles wide)
                for x_offset in range(-1, 2):
                    corridor_x = x_center + x_offset
                    if 0 <= corridor_x < self.map_width:
                        for y in range(y_start, y_end):
                            if 0 <= y < self.map_height:
                                self.map_data[y][corridor_x] = 1  # Path
                
                # Ensure connection to mazes above and below
                # Connect to maze above
                maze_above_y = grid_row * (base_height + spacing) + base_height - 1
                if 0 <= maze_above_y < self.map_height:
                    for x_offset in range(-1, 2):
                        corridor_x = x_center + x_offset
                        if 0 <= corridor_x < self.map_width:
                            self.map_data[maze_above_y][corridor_x] = 1  # Path
                
                # Connect to maze below  
                maze_below_y = (grid_row + 1) * (base_height + spacing)
                if 0 <= maze_below_y < self.map_height:
                    for x_offset in range(-1, 2):
                        corridor_x = x_center + x_offset
                        if 0 <= corridor_x < self.map_width:
                            self.map_data[maze_below_y][corridor_x] = 1  # Path
        
        # Create warp tunnels at the edges (horizontal wrapping)
        for grid_row in range(3):
            warp_y = grid_row * (base_height + spacing) + base_height // 2
            if 0 <= warp_y < self.map_height:
                # Left edge warp entrance (clear path to edge)
                for x in range(3):
                    if 0 <= x < self.map_width:
                        self.map_data[warp_y][x] = 1
                
                # Right edge warp entrance (clear path to edge)
                for x in range(self.map_width - 3, self.map_width):
                    if 0 <= x < self.map_width:
                        self.map_data[warp_y][x] = 1
    
    def _scale_maze(self, scale_factor):
        """Scale the maze to fit the target dimensions without changing map size"""
        original_height = len(self.map_data)
        original_width = len(self.map_data[0]) if original_height > 0 else 0
        
        # Create new map with same target dimensions
        scaled_map = [[0 for _ in range(self.map_width)] for _ in range(self.map_height)]
        
        # Scale the maze data to fit target dimensions
        for y in range(self.map_height):
            for x in range(self.map_width):
                # Map to original coordinates
                if original_width > 0 and original_height > 0:
                    orig_x = int(x * original_width / self.map_width)
                    orig_y = int(y * original_height / self.map_height)
                    
                    # Get tile value (with bounds checking)
                    if orig_y < original_height and orig_x < original_width:
                        scaled_map[y][x] = self.map_data[orig_y][orig_x]
                    else:
                        scaled_map[y][x] = 0  # Wall for out-of-bounds areas
                else:
                    scaled_map[y][x] = 1  # Default to path if no original data
        
        self.map_data = scaled_map
    
    def _generate_fallback_maze(self):
        """Fallback maze generation if JSON loading fails"""
        # Initialize the map with proper dimensions first
        self.map_data = [[1 for _ in range(self.map_width)] for _ in range(self.map_height)]
        
        # Simple maze - just outer walls and open center
        for y in range(self.map_height):
            for x in range(self.map_width):
                if (x == 0 or x == self.map_width - 1 or 
                    y == 0 or y == self.map_height - 1):
                    self.map_data[y][x] = 0  # Wall
                else:
                    self.map_data[y][x] = 1  # Path
    
    def _create_classic_pacman_maze(self):
        """Create a classic Pac-Man style maze like the reference image"""
        # Initialize all tiles as walls
        for y in range(self.map_height):
            for x in range(self.map_width):
                self.map_data[y][x] = 0  # Wall
        
        # Create the maze pattern based on classic Pac-Man design
        self._create_outer_corridor()
        self._create_main_horizontal_corridors()
        self._create_main_vertical_corridors()
        self._create_corner_areas()
        self._create_central_area_with_ghost_house()
        self._create_connecting_passages()
        
        # Mirror left half to right half for symmetry
        self._mirror_left_to_right()
        
        # Add spawn points after maze creation
        self._place_spawn_points()
    
    def _create_outer_corridor(self):
        """Create the outer perimeter corridor"""
        # Top corridor
        for x in range(1, self.map_width - 1):
            self.map_data[1][x] = 1
        
        # Bottom corridor  
        for x in range(1, self.map_width - 1):
            self.map_data[self.map_height - 2][x] = 1
        
        # Left corridor
        for y in range(1, self.map_height - 1):
            self.map_data[y][1] = 1
        
        # Right corridor
        for y in range(1, self.map_height - 1):
            self.map_data[y][self.map_width - 2] = 1
    
    def _create_main_horizontal_corridors(self):
        """Create main horizontal corridors through the maze"""
        # Upper horizontal corridor
        upper_y = self.map_height // 4
        for x in range(1, self.map_width - 1):
            self.map_data[upper_y][x] = 1
        
        # Middle horizontal corridor (avoid ghost house area)
        middle_y = self.map_height // 2
        center_x = self.map_width // 2
        for x in range(1, center_x - 4):
            self.map_data[middle_y][x] = 1
        for x in range(center_x + 5, self.map_width - 1):
            self.map_data[middle_y][x] = 1
        
        # Lower horizontal corridor
        lower_y = (self.map_height * 3) // 4
        for x in range(1, self.map_width - 1):
            self.map_data[lower_y][x] = 1
    
    def _create_main_vertical_corridors(self):
        """Create main vertical corridors"""
        # Left quarter vertical corridor
        left_x = self.map_width // 4
        for y in range(1, self.map_height - 1):
            self.map_data[y][left_x] = 1
        
        # Right quarter vertical corridor (will be mirrored)
        # Only create on left half, mirroring will handle right side
        pass
    
    def _create_corner_areas(self):
        """Create the corner rectangular areas with internal paths"""
        # Top-left corner area
        self._create_corner_block(3, 3, 8, 6)
        
        # Bottom-left corner area  
        self._create_corner_block(3, self.map_height - 9, 8, 6)
        
        # Middle-left area
        self._create_corner_block(3, self.map_height // 2 - 4, 6, 8)
    
    def _create_corner_block(self, start_x, start_y, width, height):
        """Create a corner block with internal maze structure"""
        # Create outer border of paths
        # Top edge
        for x in range(start_x, start_x + width):
            if 0 <= x < self.map_width and 0 <= start_y < self.map_height:
                self.map_data[start_y][x] = 1
        
        # Bottom edge
        for x in range(start_x, start_x + width):
            bottom_y = start_y + height - 1
            if 0 <= x < self.map_width and 0 <= bottom_y < self.map_height:
                self.map_data[bottom_y][x] = 1
        
        # Left edge
        for y in range(start_y, start_y + height):
            if 0 <= start_x < self.map_width and 0 <= y < self.map_height:
                self.map_data[y][start_x] = 1
        
        # Right edge
        for y in range(start_y, start_y + height):
            right_x = start_x + width - 1
            if 0 <= right_x < self.map_width and 0 <= y < self.map_height:
                self.map_data[y][right_x] = 1
        
        # Create internal maze pattern (simple grid)
        for y in range(start_y + 2, start_y + height - 2, 2):
            for x in range(start_x + 2, start_x + width - 2, 2):
                if 0 <= x < self.map_width and 0 <= y < self.map_height:
                    self.map_data[y][x] = 1
                    # Connect horizontally
                    if x + 1 < start_x + width - 1:
                        self.map_data[y][x + 1] = 1
    
    def _create_central_area_with_ghost_house(self):
        """Create the central area with ghost house"""
        center_x = self.map_width // 2
        center_y = self.map_height // 2
        
        # Create ghost house (6x4)
        house_width, house_height = 6, 4
        house_start_x = center_x - house_width // 2
        house_start_y = center_y - house_height // 2
        
        # Clear ghost house area (make it paths)
        for y in range(house_start_y, house_start_y + house_height):
            for x in range(house_start_x, house_start_x + house_width):
                if 0 <= x < self.map_width and 0 <= y < self.map_height:
                    self.map_data[y][x] = 1
        
        # Create entrance to ghost house (top center)
        entrance_x = center_x
        entrance_y = house_start_y - 1
        if 0 <= entrance_x < self.map_width and 0 <= entrance_y < self.map_height:
            self.map_data[entrance_y][entrance_x] = 1
        
        # Create path above the ghost house entrance
        for y in range(entrance_y - 3, entrance_y):
            if 0 <= entrance_x < self.map_width and 0 <= y < self.map_height:
                self.map_data[y][entrance_x] = 1
    
    def _create_connecting_passages(self):
        """Create passages that connect different areas"""
        # Vertical connectors from horizontal corridors
        quarter_y = self.map_height // 4
        half_y = self.map_height // 2  
        three_quarter_y = (self.map_height * 3) // 4
        
        # Connect areas at strategic points (only on left half)
        connection_points = [
            self.map_width // 6,
            self.map_width // 3,
            (self.map_width * 5) // 12
        ]
        
        for x in connection_points:
            if x < self.map_width // 2:  # Only left half
                # Connect upper and middle
                for y in range(quarter_y + 1, half_y):
                    if 0 <= x < self.map_width and 0 <= y < self.map_height:
                        self.map_data[y][x] = 1
                
                # Connect middle and lower  
                for y in range(half_y + 1, three_quarter_y):
                    if 0 <= x < self.map_width and 0 <= y < self.map_height:
                        self.map_data[y][x] = 1
    
    def _mirror_left_to_right(self):
        """Mirror the left half to the right half for symmetry"""
        for y in range(self.map_height):
            for x in range(self.map_width // 2):
                mirror_x = self.map_width - 1 - x
                self.map_data[y][mirror_x] = self.map_data[y][x]
    
    def _place_spawn_points(self):
        """Place spawn points in corners and strategic locations"""
        self.spawn_points = []
        
        # Corner spawn points
        spawn_locations = [
            (2, 2),  # Top-left
            (2, self.map_height - 3),  # Bottom-left
            (self.map_width - 3, 2),  # Top-right
            (self.map_width - 3, self.map_height - 3),  # Bottom-right
        ]
        
        # Add more spawn points along corridors
        quarter_y = self.map_height // 4
        three_quarter_y = (self.map_height * 3) // 4
        
        additional_spawns = [
            (self.map_width // 6, quarter_y),
            (self.map_width // 3, quarter_y),
            (self.map_width * 2 // 3, quarter_y),
            (self.map_width * 5 // 6, quarter_y),
            (self.map_width // 6, three_quarter_y),
            (self.map_width // 3, three_quarter_y),
            (self.map_width * 2 // 3, three_quarter_y),
            (self.map_width * 5 // 6, three_quarter_y),
        ]
        
        all_spawn_locations = spawn_locations + additional_spawns
        
        # Validate and add spawn points
        for spawn_x, spawn_y in all_spawn_locations:
            if (0 <= spawn_x < self.map_width and 
                0 <= spawn_y < self.map_height and
                self.map_data[spawn_y][spawn_x] == 1):  # Must be on a path
                
                self.map_data[spawn_y][spawn_x] = 2  # Mark as spawn point
                self.spawn_points.append((spawn_x * self.tile_size, spawn_y * self.tile_size))
    
    def _create_all_paths(self):
        """Start with all tiles as paths, then selectively add walls"""
        for y in range(self.map_height):
            for x in range(self.map_width):
                self.map_data[y][x] = 1  # All paths initially
    
    def _create_outer_walls(self):
        """Create outer border walls"""
        # Top and bottom walls
        for x in range(self.map_width):
            self.map_data[0][x] = 0  # Top wall
            self.map_data[self.map_height - 1][x] = 0  # Bottom wall
        
        # Left and right walls (except tunnel areas)
        for y in range(self.map_height):
            self.map_data[y][0] = 0  # Left wall
            self.map_data[y][self.map_width - 1] = 0  # Right wall
    
    def _create_ghost_house(self):
        """Create central ghost house (accessible to ghosts)"""
        center_x = self.map_width // 2
        center_y = self.map_height // 2
        
        # Create ghost house area (6x4 box in center)
        house_width = 6
        house_height = 4
        
        start_x = center_x - house_width // 2
        start_y = center_y - house_height // 2
        
        # Clear area for ghost house (use regular paths, not special tiles)
        for y in range(start_y, start_y + house_height):
            for x in range(start_x, start_x + house_width):
                if 0 <= y < self.map_height and 0 <= x < self.map_width:
                    self.map_data[y][x] = 1  # Regular path, not special tile
        
        # Create walls around ghost house (but with multiple entrances)
        for y in range(start_y - 1, start_y + house_height + 1):
            for x in range(start_x - 1, start_x + house_width + 1):
                if 0 <= y < self.map_height and 0 <= x < self.map_width:
                    if (y == start_y - 1 or y == start_y + house_height or 
                        x == start_x - 1 or x == start_x + house_width):
                        self.map_data[y][x] = 0  # Wall
        
        # Create multiple entrances to ghost house so ghosts don't get trapped
        # Top entrance
        entrance_x = center_x
        entrance_y = start_y - 1
        if 0 <= entrance_y < self.map_height and 0 <= entrance_x < self.map_width:
            self.map_data[entrance_y][entrance_x] = 1  # Path
            
        # Left entrance
        entrance_x = start_x - 1
        entrance_y = center_y
        if 0 <= entrance_y < self.map_height and 0 <= entrance_x < self.map_width:
            self.map_data[entrance_y][entrance_x] = 1  # Path
            
        # Right entrance  
        entrance_x = start_x + house_width
        entrance_y = center_y
        if 0 <= entrance_y < self.map_height and 0 <= entrance_x < self.map_width:
            self.map_data[entrance_y][entrance_x] = 1  # Path
    
    def _create_main_corridors(self):
        """Create main corridor structure with guaranteed connectivity"""
        # Create main horizontal corridor through center (avoiding ghost house)
        center_y = self.map_height // 2
        for x in range(1, self.map_width - 1):
            # Skip ghost house area but ensure paths around it
            center_x = self.map_width // 2
            if not (center_x - 4 <= x <= center_x + 4):
                self.map_data[center_y][x] = 1
        
        # Create paths around ghost house
        ghost_center_x = self.map_width // 2
        ghost_center_y = self.map_height // 2
        
        # Horizontal paths above and below ghost house
        for x in range(ghost_center_x - 5, ghost_center_x + 6):
            if 0 <= x < self.map_width:
                self.map_data[ghost_center_y - 4][x] = 1  # Above ghost house
                self.map_data[ghost_center_y + 4][x] = 1  # Below ghost house
        
        # Vertical paths left and right of ghost house
        for y in range(ghost_center_y - 4, ghost_center_y + 5):
            if 0 <= y < self.map_height:
                self.map_data[y][ghost_center_x - 5] = 1  # Left of ghost house
                self.map_data[y][ghost_center_x + 5] = 1  # Right of ghost house
        
        # Create additional strategic corridors
        corridor_y_positions = [8, 22, 38, 52]  # Evenly spaced horizontal corridors
        
        for y in corridor_y_positions:
            if y < self.map_height:
                for x in range(1, self.map_width - 1):
                    # Always create paths but skip ghost house interior
                    if not (ghost_center_x - 3 <= x <= ghost_center_x + 3 and ghost_center_y - 2 <= y <= ghost_center_y + 2):
                        self.map_data[y][x] = 1
        
        # Create main vertical corridors
        corridor_x_positions = [6, 15, 25, self.map_width - 26, self.map_width - 16, self.map_width - 7]
        
        for x in corridor_x_positions:
            if 0 <= x < self.map_width:
                for y in range(1, self.map_height - 1):
                    # Skip ghost house interior only
                    if not (ghost_center_x - 3 <= x <= ghost_center_x + 3 and ghost_center_y - 2 <= y <= ghost_center_y + 2):
                        self.map_data[y][x] = 1
    
    def _add_strategic_walls(self):
        """Add strategic walls that create interesting gameplay without isolating areas"""
        ghost_center_x = self.map_width // 2
        ghost_center_y = self.map_height // 2
        
        # Add small wall segments that create bottlenecks but maintain connectivity
        # Only work on left half (will be mirrored)
        
        # Create some single-wall bottlenecks in corridors
        bottleneck_positions = [
            (5, 10), (8, 16), (12, 8), (15, 20),   # Upper area
            (6, 35), (10, 42), (18, 38), (22, 45)  # Lower area  
        ]
        
        for x, y in bottleneck_positions:
            if (x < self.map_width // 2 and 0 <= y < self.map_height):
                # Only place wall if it doesn't create isolated areas
                if self._is_safe_wall_placement(x, y):
                    self.map_data[y][x] = 0
        
        # Add small L-shaped wall formations for complexity
        l_shapes = [
            [(7, 6), (8, 6), (8, 7)],           # Small L in upper area
            [(14, 12), (14, 13), (15, 13)],     # Small L in upper-middle  
            [(9, 28), (10, 28), (10, 29)],      # Small L avoiding ghost house
            [(20, 40), (21, 40), (21, 41)]      # Small L in lower area
        ]
        
        for l_shape in l_shapes:
            # Check if entire L-shape can be placed safely
            safe_to_place = True
            for x, y in l_shape:
                if (x >= self.map_width // 2 or y >= self.map_height or 
                    not self._is_safe_wall_placement(x, y)):
                    safe_to_place = False
                    break
            
            # Place the entire L-shape if safe
            if safe_to_place:
                for x, y in l_shape:
                    self.map_data[y][x] = 0
    
    def _is_safe_wall_placement(self, wall_x, wall_y):
        """Check if placing a wall here would create isolated areas"""
        # Temporarily place the wall
        original = self.map_data[wall_y][wall_x]
        self.map_data[wall_y][wall_x] = 0
        
        # Count connected components around this wall
        connected_areas = []
        checked_positions = set()
        
        # Check each adjacent walkable position
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            adj_x, adj_y = wall_x + dx, wall_y + dy
            if (0 <= adj_x < self.map_width and 0 <= adj_y < self.map_height):
                if (self.map_data[adj_y][adj_x] == 1 and (adj_x, adj_y) not in checked_positions):
                    # Flood fill from this position
                    area = set()
                    self._flood_fill(adj_x, adj_y, area)
                    if area:
                        connected_areas.append(area)
                        checked_positions.update(area)
        
        # Restore original state
        self.map_data[wall_y][wall_x] = original
        
        # Safe to place wall if all adjacent areas are still connected (1 or 0 components)
        return len(connected_areas) <= 1
    
    def _create_tunnels(self):
        """Create horizontal tunnels (warp zones) on left and right edges"""
        # Create tunnel at middle height
        tunnel_y = self.map_height // 2
        
        # Clear tunnel paths
        self.map_data[tunnel_y][0] = 1  # Left tunnel entrance
        self.map_data[tunnel_y][1] = 1  # Path from left
        self.map_data[tunnel_y][self.map_width - 1] = 1  # Right tunnel entrance
        self.map_data[tunnel_y][self.map_width - 2] = 1  # Path from right
        
        # Ensure connection to main maze
        for x in range(2, 6):  # Left side connection
            self.map_data[tunnel_y][x] = 1
        for x in range(self.map_width - 6, self.map_width - 2):  # Right side connection  
            self.map_data[tunnel_y][x] = 1
    
    def _mirror_for_symmetry(self):
        """Mirror left half to right half for left-right symmetry"""
        mid_x = self.map_width // 2
        
        for y in range(self.map_height):
            for x in range(mid_x):
                mirror_x = self.map_width - 1 - x
                self.map_data[y][mirror_x] = self.map_data[y][x]
    
    def _mirror_quadrants(self):
        """Mirror the top-left quadrant to create full symmetrical map"""
        quad_width = self.map_width // 2
        quad_height = self.map_height // 2
        
        # Mirror horizontally (left-right symmetry)
        for y in range(quad_height):
            for x in range(quad_width):
                mirror_x = self.map_width - 1 - x
                self.map_data[y][mirror_x] = self.map_data[y][x]
        
        # Mirror vertically (top-bottom symmetry) for the full width
        for y in range(quad_height):
            for x in range(self.map_width):
                mirror_y = self.map_height - 1 - y
                self.map_data[mirror_y][x] = self.map_data[y][x]
    
    def _ensure_connectivity(self):
        """Ensure all areas are connected and remove enclosed spaces"""
        # Multiple passes to ensure complete connectivity
        for iteration in range(5):  # Up to 5 iterations to fix connectivity
            # Find the largest connected component
            largest_area = self._find_largest_connected_area()
            if not largest_area:
                self._create_emergency_paths()
                continue
            
            # Find all isolated areas and connect them
            isolated_areas = self._find_isolated_areas(largest_area)
            
            if not isolated_areas:
                break  # All areas are connected
            
            # Connect each isolated area to the main area
            for area in isolated_areas:
                if area:  # Make sure area is not empty
                    start_x, start_y = next(iter(area))  # Get first point from area
                    self._connect_to_main_area(start_x, start_y, largest_area)
                    # Update largest area to include newly connected area
                    largest_area.update(area)
        
        # Additional pass to break up any remaining wall clusters
        self._break_wall_clusters()
    
    def _find_largest_connected_area(self):
        """Find the largest connected area of walkable tiles"""
        all_walkable = set()
        for y in range(self.map_height):
            for x in range(self.map_width):
                if self.map_data[y][x] == 1:
                    all_walkable.add((x, y))
        
        if not all_walkable:
            return set()
        
        largest_area = set()
        
        while all_walkable:
            # Start flood fill from an unvisited walkable tile
            start_x, start_y = next(iter(all_walkable))
            current_area = set()
            self._flood_fill(start_x, start_y, current_area)
            
            # Remove visited tiles from remaining tiles
            all_walkable -= current_area
            
            # Update largest area if current is bigger
            if len(current_area) > len(largest_area):
                largest_area = current_area
        
        return largest_area
    
    def _find_isolated_areas(self, main_area):
        """Find all areas isolated from the main connected area"""
        all_walkable = set()
        for y in range(self.map_height):
            for x in range(self.map_width):
                if self.map_data[y][x] == 1:
                    all_walkable.add((x, y))
        
        # Remove main area tiles
        remaining_tiles = all_walkable - main_area
        isolated_areas = []
        
        while remaining_tiles:
            # Start new isolated area
            start_x, start_y = next(iter(remaining_tiles))
            area = set()
            self._flood_fill(start_x, start_y, area)
            
            if area:  # Only add non-empty areas
                isolated_areas.append(area)
                remaining_tiles -= area
        
        return isolated_areas
    
    def _break_wall_clusters(self):
        """Break up large clusters of walls to improve connectivity"""
        for y in range(2, self.map_height - 2, 3):
            for x in range(2, self.map_width - 2, 3):
                # Check if we have a large wall cluster
                wall_count = 0
                for dy in range(-1, 2):
                    for dx in range(-1, 2):
                        if self.map_data[y + dy][x + dx] == 0:
                            wall_count += 1
                
                # If mostly walls, create a path through the center
                if wall_count >= 7:  # 7 out of 9 tiles are walls
                    # Skip ghost house area
                    center_x = self.map_width // 2
                    center_y = self.map_height // 2
                    if not (center_x - 4 <= x <= center_x + 4 and center_y - 3 <= y <= center_y + 3):
                        self.map_data[y][x] = 1  # Create path
    
    def _flood_fill(self, start_x, start_y, visited):
        """Iterative flood fill algorithm to find connected areas (avoids recursion depth issues)"""
        stack = [(start_x, start_y)]
        
        while stack:
            x, y = stack.pop()
            
            # Skip if already visited or out of bounds
            if (x, y) in visited or x < 0 or x >= self.map_width or y < 0 or y >= self.map_height:
                continue
            
            # Skip if not a walkable path
            if self.map_data[y][x] != 1:
                continue
            
            # Mark as visited
            visited.add((x, y))
            
            # Add neighboring cells to stack
            stack.append((x + 1, y))
            stack.append((x - 1, y))
            stack.append((x, y + 1))
            stack.append((x, y - 1))
    
    def _connect_to_main_area(self, start_x, start_y, main_area):
        """Connect an isolated area to the main connected area"""
        # Find the closest point in main area
        min_distance = float('inf')
        target_x, target_y = None, None
        
        for mx, my in main_area:
            distance = abs(mx - start_x) + abs(my - start_y)  # Manhattan distance
            if distance < min_distance:
                min_distance = distance
                target_x, target_y = mx, my
        
        if target_x is not None:
            # Create path from start to target
            self._create_path(start_x, start_y, target_x, target_y)
    
    def _create_path(self, x1, y1, x2, y2):
        """Create a path between two points"""
        # Simple L-shaped path
        current_x, current_y = x1, y1
        
        # Move horizontally first
        while current_x != x2:
            self.map_data[current_y][current_x] = 1
            current_x += 1 if current_x < x2 else -1
        
        # Then move vertically
        while current_y != y2:
            self.map_data[current_y][current_x] = 1
            current_y += 1 if current_y < y2 else -1
        
        # Ensure target is walkable
        self.map_data[y2][x2] = 1
    
    def _adjust_wall_density(self):
        """Ensure walls are less than 30% of total spaces"""
        total_cells = self.map_width * self.map_height
        current_walls = sum(row.count(0) for row in self.map_data)
        wall_percentage = current_walls / total_cells
        
        if wall_percentage > 0.30:
            # Too many walls, convert some to paths while maintaining symmetry
            target_walls_to_remove = int((wall_percentage - 0.28) * total_cells)
            removed = 0
            
            quad_width = self.map_width // 2
            quad_height = self.map_height // 2
            
            # Only modify the top-left quadrant, then mirror
            for y in range(1, quad_height - 1):
                for x in range(1, quad_width - 1):
                    if removed >= target_walls_to_remove // 4:  # Quarter of total since we'll mirror
                        break
                    if self.map_data[y][x] == 0 and random.random() > 0.5:
                        self.map_data[y][x] = 1
                        removed += 1
                if removed >= target_walls_to_remove // 4:
                    break
            
            # Re-mirror the changes
            self._mirror_quadrants()
    
    def _final_connectivity_pass(self):
        """Final pass to ensure no enclosed spaces remain"""
        # Run connectivity check one more time
        self._ensure_connectivity()
        
    def _create_emergency_paths(self):
        """Create basic cross paths if no walkable areas exist"""
        center_x = self.map_width // 2
        center_y = self.map_height // 2
        
        # Horizontal corridor
        for x in range(1, self.map_width - 1):
            self.map_data[center_y][x] = 1
        
        # Vertical corridor
        for y in range(1, self.map_height - 1):
            self.map_data[y][center_x] = 1
    

    
    def spawn_pellets(self):
        """Spawn pellets following Pac-Man design principles"""
        self.pellets = set()
        self.power_pellets = set()
        
        # Regular pellets on all walkable path tiles
        for y in range(self.map_height):
            for x in range(self.map_width):
                if self.map_data[y][x] == 1:  # Path tile
                    self.pellets.add((x, y))
        
        # Strategic power pellet placement (4 energizers in corners + extras for large map)
        corner_power_pellets = [
            (3, 3),                                    # Top-left corner
            (self.map_width - 4, 3),                  # Top-right corner  
            (3, self.map_height - 4),                 # Bottom-left corner
            (self.map_width - 4, self.map_height - 4) # Bottom-right corner
        ]
        
        # Additional strategic power pellets for larger map
        extra_power_pellets = [
            (self.map_width // 4, self.map_height // 3),     # Upper-left strategic
            (3 * self.map_width // 4, self.map_height // 3), # Upper-right strategic
            (self.map_width // 4, 2 * self.map_height // 3), # Lower-left strategic  
            (3 * self.map_width // 4, 2 * self.map_height // 3), # Lower-right strategic
        ]
        
        all_power_positions = corner_power_pellets + extra_power_pellets
        
        for x, y in all_power_positions:
            if (0 <= x < self.map_width and 0 <= y < self.map_height):
                # Find nearest walkable position if exact position isn't walkable
                best_pos = self._find_nearest_walkable(x, y, radius=3)
                if best_pos:
                    px, py = best_pos
                    self.power_pellets.add((px, py))
                    # Remove regular pellet at power pellet location
                    self.pellets.discard((px, py))
    
    def _find_nearest_walkable(self, target_x, target_y, radius=2):
        """Find nearest walkable position within radius"""
        for r in range(radius + 1):
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    x, y = target_x + dx, target_y + dy
                    if (0 <= x < self.map_width and 0 <= y < self.map_height):
                        if self.map_data[y][x] == 1:  # Walkable
                            return (x, y)
        return None
    
    def spawn_ghosts(self):
        """Initial spawn of ghosts - minimum 20"""
        colors = ['red', 'pink', 'cyan', 'orange', 'yellow', 'green', 'purple', 'blue', 
                 'brown', 'gray', 'lime', 'navy', 'teal', 'silver', 'maroon', 'olive',
                 'crimson', 'darkred', 'darkblue', 'darkgreen']
        
        # Spawn initial 20 ghosts
        for i in range(20):
            spawn_pos = self.get_ghost_spawn_position()
            color = colors[i % len(colors)]
            ghost = Ghost(f'ghost_{i}', spawn_pos[0], spawn_pos[1], color)
            self.ghosts.append(ghost)
            
        self.logger.info(f"Initially spawned {len(self.ghosts)} ghosts")
    
    def maintain_ghost_count(self):
        """Ensure there are at least 20 ghosts and as many as active players"""
        active_player_count = len([p for p in self.players.values() if not p.is_spectator])
        current_ghost_count = len(self.ghosts)
        
        # Minimum 20 ghosts, but scale with players if more than 20
        target_ghost_count = max(20, active_player_count)
        
        if target_ghost_count > current_ghost_count:
            # Add more ghosts
            colors = ['red', 'pink', 'cyan', 'orange', 'yellow', 'green', 'purple', 'blue', 
                     'brown', 'gray', 'lime', 'navy', 'teal', 'silver', 'maroon', 'olive',
                     'crimson', 'darkred', 'darkblue', 'darkgreen', 'darkorange', 'darkviolet',
                     'indigo', 'magenta', 'turquoise', 'gold', 'coral', 'salmon', 'khaki', 'plum']
            
            for i in range(current_ghost_count, target_ghost_count):
                # Find a good spawn position for new ghost
                spawn_pos = self.get_ghost_spawn_position()
                color = colors[i % len(colors)]
                ghost = Ghost(f'ghost_{i}', spawn_pos[0], spawn_pos[1], color)
                self.ghosts.append(ghost)
                self.logger.info(f"Added ghost {i} at position {spawn_pos} - Total ghosts: {len(self.ghosts)}")
        
        # Never reduce ghost count during a game session to maintain difficulty
        
    def get_ghost_spawn_position(self):
        """Get a suitable random spawn position for a new ghost, at least 10 tiles from any player"""
        min_distance_from_players = 10 * self.tile_size  # 10 tiles minimum distance
        min_distance_from_ghosts = 3 * self.tile_size   # 3 tiles minimum distance from other ghosts
        
        # Get all walkable positions
        walkable_positions = []
        for y in range(1, self.map_height - 1):
            for x in range(1, self.map_width - 1):
                if self.map_data[y][x] != 0:  # Not a wall
                    walkable_positions.append((x * self.tile_size, y * self.tile_size))
        
        # Shuffle for random selection
        random.shuffle(walkable_positions)
        
        # Find a position that meets distance requirements
        for spawn_x, spawn_y in walkable_positions:
            valid_position = True
            
            # Check distance from all active players (not spectators)
            for player in self.players.values():
                if not player.is_spectator:
                    player_distance = ((spawn_x - player.x) ** 2 + (spawn_y - player.y) ** 2) ** 0.5
                    if player_distance < min_distance_from_players:
                        valid_position = False
                        break
            
            if not valid_position:
                continue
            
            # Check distance from existing ghosts
            for ghost in self.ghosts:
                ghost_distance = ((spawn_x - ghost.x) ** 2 + (spawn_y - ghost.y) ** 2) ** 0.5
                if ghost_distance < min_distance_from_ghosts:
                    valid_position = False
                    break
            
            if valid_position:
                return (spawn_x, spawn_y)
        
        # Fallback: if no position meets all requirements, use center area
        center_x = self.map_width // 2
        center_y = self.map_height // 2
        return (center_x * self.tile_size, center_y * self.tile_size)
    
    def add_player(self, player):
        """Add a player to the game/lobby"""
        if len(self.players) >= self.max_players:
            return False, None
        
        # First player becomes the host
        if not self.players:
            self.host_player_id = player.id
            player.is_host = True
            self.logger.info(f"Player {player.id} is now the host")
        else:
            player.is_host = False
        
        # Find available spawn point
        spawn_pos = self.get_available_spawn_point()
        if spawn_pos is None:
            return False, None
        
        # If game is in lobby, mark player as spectator initially
        if self.game_state == 'lobby':
            player.is_spectator = True
        
        self.players[player.id] = player
        
        # Maintain ghost count to match active players (only if game is playing)
        if self.game_state == 'playing':
            self.maintain_ghost_count()
        
        return True, spawn_pos
    
    def remove_player(self, player_id):
        """Remove a player from the game"""
        if player_id in self.players:
            # If host leaves, assign new host
            if player_id == self.host_player_id:
                # Clear host flag from leaving player
                if player_id in self.players:
                    self.players[player_id].is_host = False
                
                remaining_players = [pid for pid in self.players.keys() if pid != player_id]
                self.host_player_id = remaining_players[0] if remaining_players else None
                if self.host_player_id:
                    # Set host flag for new host
                    self.players[self.host_player_id].is_host = True
                    self.logger.info(f"Player {self.host_player_id} is now the new host")
            
            del self.players[player_id]
            # Note: We intentionally don't reduce ghost count here to maintain difficulty
    
    def start_game(self, player_id):
        """Start the game - only the host can do this"""
        if player_id != self.host_player_id:
            return False, "Only the host can start the game"
        
        if self.game_state != 'lobby':
            return False, "Game is not in lobby state"
        
        if len(self.players) < 1:
            return False, "Need at least 1 player to start"
        
        # Start the game
        self.game_state = 'playing'
        self.start_new_round()
        
        # Make all players active (remove spectator status)
        for player in self.players.values():
            player.is_spectator = False
            player.lives = 3
            player.score = 0
            player.power_mode = False
            player.power_timer = 0
            
            # Grant 10 seconds of invincibility on game start
            player.invincible = True
            player.invincibility_timer = 100  # 10 seconds at 10 FPS
            
            # Respawn all players
            spawn_pos = self.get_available_spawn_point()
            if spawn_pos:
                player.x, player.y = spawn_pos
                self.logger.info(f"Player {player.id} spawned at {spawn_pos} with 10s invincibility")
        
        self.logger.info(f"Game started by host {player_id} with {len(self.players)} players")
        return True, "Game started!"
    
    def get_lobby_state(self):
        """Get current lobby information"""
        return {
            'state': self.game_state,
            'host_id': self.host_player_id,
            'player_count': len(self.players),
            'max_players': self.max_players,
            'players': [
                {
                    'id': pid,
                    'name': player.name,
                    'is_host': pid == self.host_player_id
                }
                for pid, player in self.players.items()
            ]
        }
    
    def get_available_spawn_point(self):
        """Get an available spawn point"""
        # Try to find a spawn point not occupied by other players
        occupied_positions = {(p.x, p.y) for p in self.players.values()}
        
        for spawn_pos in self.spawn_points:
            if spawn_pos not in occupied_positions:
                return spawn_pos
        
        # If all spawn points are occupied, use a random one
        return random.choice(self.spawn_points) if self.spawn_points else (20, 20)
    
    def move_player(self, player_id, direction):
        """Move a player in the specified direction"""
        if player_id not in self.players:
            return False
        
        player = self.players[player_id]
        new_x, new_y = player.x, player.y
        
        # Calculate new position based on direction
        if direction == 'up':
            new_y -= self.tile_size
        elif direction == 'down':
            new_y += self.tile_size
        elif direction == 'left':
            new_x -= self.tile_size
        elif direction == 'right':
            new_x += self.tile_size
        else:
            return False
        
        # Check for warp tunnels first (horizontal wrapping)
        if new_x < 0:  # Moving left off the map
            # Warp to right side
            new_x = (self.map_width - 1) * self.tile_size
            tile_x = new_x // self.tile_size
            tile_y = new_y // self.tile_size
            if (0 <= tile_y < self.map_height and 
                self.map_data[tile_y][tile_x] != 0):  # Not a wall
                player.x = new_x
                player.y = new_y
                player.direction = direction
                return True
        elif new_x >= self.map_width * self.tile_size:  # Moving right off the map
            # Warp to left side
            new_x = 0
            tile_x = new_x // self.tile_size
            tile_y = new_y // self.tile_size
            if (0 <= tile_y < self.map_height and 
                self.map_data[tile_y][tile_x] != 0):  # Not a wall
                player.x = new_x
                player.y = new_y
                player.direction = direction
                return True
        
        # Check normal bounds and collision
        tile_x = new_x // self.tile_size
        tile_y = new_y // self.tile_size
        
        if (0 <= tile_x < self.map_width and 
            0 <= tile_y < self.map_height and
            self.map_data[tile_y][tile_x] != 0):  # Not a wall
            
            player.x = new_x
            player.y = new_y
            player.direction = direction
            return True
        
        return False
    
    def check_pellet_collision(self, player_id):
        """Check if player collected a pellet"""
        if player_id not in self.players:
            return False
        
        player = self.players[player_id]
        tile_x = player.x // self.tile_size
        tile_y = player.y // self.tile_size
        
        if (tile_x, tile_y) in self.pellets:
            self.pellets.remove((tile_x, tile_y))
            player.score += 10
            return True
        
        return False
    
    def check_power_pellet_collision(self, player_id):
        """Check if player collected a power pellet"""
        if player_id not in self.players:
            return False
        
        player = self.players[player_id]
        tile_x = player.x // self.tile_size
        tile_y = player.y // self.tile_size
        
        if (tile_x, tile_y) in self.power_pellets:
            self.power_pellets.remove((tile_x, tile_y))
            player.score += 50
            player.power_mode = True
            player.power_timer = 100  # 10 seconds at 10 FPS
            player.power_mode_flashing = False  # Reset flashing when starting power mode
            return True
        
        return False
    
    def update_ghosts(self):
        """Update ghost positions and AI"""
        # Get positions of invincible players
        invincible_positions = set()
        for player in self.players.values():
            if player.invincible:
                player_tile_x = player.x // self.tile_size
                player_tile_y = player.y // self.tile_size
                invincible_positions.add((player_tile_x, player_tile_y))
        
        # Update ghosts sequentially to ensure real-time collision avoidance
        ghosts_to_respawn = []
        for i, ghost in enumerate(self.ghosts):
            # Get current positions of all other ghosts (including those that have already moved this frame)
            other_ghost_positions = set()
            for j, other_ghost in enumerate(self.ghosts):
                if j != i:  # Exclude current ghost
                    other_tile_x = other_ghost.x // self.tile_size
                    other_tile_y = other_ghost.y // self.tile_size
                    other_ghost_positions.add((other_tile_x, other_tile_y))
            
            update_result = ghost.update(self.map_data, self.map_width, self.map_height, self.tile_size, self.players, invincible_positions, other_ghost_positions)
            
            # Check if ghost needs to be respawned due to being stuck
            if update_result == 'respawn_needed':
                ghosts_to_respawn.append(ghost)
        
        # Respawn stuck ghosts at new locations
        for ghost in ghosts_to_respawn:
            new_x, new_y = self.get_ghost_spawn_position()
            ghost.respawn_at_position(new_x, new_y)
            print(f"Respawned stuck ghost {ghost.id} at position ({new_x//self.tile_size}, {new_y//self.tile_size})")
    
    def check_ghost_collisions(self):
        """Check for collisions between ghosts and players"""
        self.logger.debug(f"check_ghost_collisions called - Players: {len(self.players)}, Ghosts: {len(self.ghosts)}")
        collisions = []
        collided_ghosts = set()  # Track which ghosts have already collided this frame
        
        for ghost in self.ghosts:
            # Skip if this ghost already collided this frame
            if ghost.id in collided_ghosts:
                continue
                
            for player_id, player in self.players.items():
                # Check if ghost and player are on same tile or very close
                ghost_tile_x = ghost.x // self.tile_size
                ghost_tile_y = ghost.y // self.tile_size
                player_tile_x = player.x // self.tile_size
                player_tile_y = player.y // self.tile_size
                
                # Also check for close proximity (within same tile or adjacent)
                distance_x = abs(ghost.x - player.x)
                distance_y = abs(ghost.y - player.y)
                collision_threshold = self.tile_size * 0.8  # 80% of tile size
                
                if (ghost_tile_x == player_tile_x and ghost_tile_y == player_tile_y) or \
                   (distance_x < collision_threshold and distance_y < collision_threshold):
                    
                    # Mark this ghost as collided to prevent multiple collisions
                    collided_ghosts.add(ghost.id)
                    
                    if player.power_mode and player.power_timer > 0:
                        # Player eats ghost - only if player actually has power mode active
                        player.score += 200
                        ghost.reset_position()
                        collisions.append({
                            'type': 'ghost_eaten',
                            'player_id': player_id,
                            'ghost_id': ghost.id,
                            'score': player.score
                        })
                        self.logger.debug(f"Player {player_id} ate ghost {ghost.id}! Power timer: {player.power_timer}")
                    elif not player.invincible:
                        # Ghost catches player (only if not invincible)
                        self.logger.debug(f"COLLISION DETECTED - Player {player_id} hit by ghost {ghost.id}")
                        self.logger.debug(f"BEFORE - Lives: {player.lives}, Invincible: {player.invincible}, Timer: {getattr(player, 'invincibility_timer', 0)}")
                        
                        player.lives -= 1
                        player.invincible = True
                        player.invincibility_timer = 30  # 3 seconds at 10 FPS
                        
                        if player.lives <= 0:
                            # Player becomes spectator
                            player.is_spectator = True
                            player.death_time = 0  # Will be set by server
                            collisions.append({
                                'type': 'player_died',
                                'player_id': player_id,
                                'ghost_id': ghost.id
                            })
                            self.logger.debug(f"Player {player_id} DIED! Now spectator")
                        else:
                            # Respawn player
                            old_pos = (player.x, player.y)
                            spawn_pos = self.get_available_spawn_point()
                            player.x, player.y = spawn_pos
                            # Grant 10 seconds of invincibility after respawn
                            player.invincible = True
                            player.invincibility_timer = 100  # 10 seconds at 10 FPS
                            self.logger.debug(f"Player {player_id} RESPAWNED from {old_pos} to {spawn_pos} with 10s invincibility")
                            collisions.append({
                                'type': 'player_caught',
                                'player_id': player_id,
                                'ghost_id': ghost.id,
                                'lives': player.lives,
                                'respawn_pos': {'x': player.x, 'y': player.y},
                                'invincible': True,
                                'invincibility_timer': player.invincibility_timer
                            })
                        self.logger.debug(f"Ghost {ghost.id} caught player {player_id}! Lives remaining: {player.lives}, invincible: {player.invincible}")
                    else:
                        self.logger.debug(f"Player {player_id} is invincible (timer: {player.invincibility_timer}), ignoring ghost {ghost.id} collision")
                    
                    # Break to prevent this ghost from colliding with multiple players
                    break
        
        # Maintain ghost count after collision processing (in case players became spectators)
        if collisions:  # Only if there were collisions to optimize performance
            self.maintain_ghost_count()
        
        return collisions

    def tick(self):
        """Periodic per-tick updates (timers etc). Called every server tick.

        Separated from collision detection so timers always advance even if a
        previous step raises an exception. This prevents players from staying
        invincible forever when an error happens earlier in the loop.
        """
        for player in self.players.values():
            if player.power_mode:
                player.power_timer -= 1
                
                # Check if we should start flashing (last 3 seconds = 30 ticks)
                if player.power_timer <= 30 and player.power_timer > 0:
                    player.power_mode_flashing = True
                else:
                    player.power_mode_flashing = False
                
                if player.power_timer <= 0:
                    player.power_mode = False
                    player.power_mode_flashing = False
                    self.logger.debug(f"Player {player.id} power mode expired")

            if player.invincible:
                old_timer = player.invincibility_timer
                player.invincibility_timer -= 1
                if player.invincibility_timer <= 0:
                    player.invincible = False
                    self.logger.debug(f"Player {player.id} invincibility expired (was {old_timer}, now {player.invincibility_timer})")
                elif player.invincibility_timer % 10 == 0:  # Log every second
                    self.logger.debug(f"Player {player.id} invincible for {player.invincibility_timer} more ticks")
    
    def get_players_data(self):
        """Get all player data for broadcasting"""
        return {
            player_id: {
                'name': player.name,
                'position': {'x': player.x, 'y': player.y},
                'direction': player.direction,
                'score': player.score,
                'lives': player.lives,
                'power_mode': player.power_mode,
                'power_mode_flashing': getattr(player, 'power_mode_flashing', False),
                'power_timer': getattr(player, 'power_timer', 0),
                'invincible': getattr(player, 'invincible', False),
                'invincibility_timer': getattr(player, 'invincibility_timer', 0),
                'is_spectator': getattr(player, 'is_spectator', False)
            }
            for player_id, player in self.players.items()
        }
    
    def start_new_round(self):
        """Start a new round - revive all spectators and reset game state"""
        import time
        self.round_start_time = time.time()
        self.round_active = True
        
        # Revive all spectators
        for player in self.players.values():
            if getattr(player, 'is_spectator', False):
                player.is_spectator = False
                player.lives = 3
                player.invincible = False
                player.invincibility_timer = 0
                # Spawn them at a new position
                spawn_pos = self.get_available_spawn_point()
                player.x, player.y = spawn_pos
        
        # Ensure ghost count matches active players for the new round
        self.maintain_ghost_count()
        
        # Reset pellets (optional - could keep them eaten for continuous play)
        self.spawn_pellets()
        
        self.logger.info(f"New round started! Duration: {self.round_duration} seconds")
        return True
    
    def restart_round(self):
        """Restart the current round (reset positions, pellets, etc.)"""
        # Reset waiting flag
        self.waiting_for_restart = False
        
        # Regenerate pellets and power pellets
        self.spawn_pellets()
        
        # Reset and respawn ghosts
        self.ghosts.clear()
        self.spawn_ghosts()
        
        # Reset all players to spawn points
        for player in self.players.values():
            spawn_pos = self.get_available_spawn_point()
            player.x = spawn_pos[0]
            player.y = spawn_pos[1]
            player.power_mode = False
            player.power_timer = 0
            player.invincible = True
            player.invincible_timer = 10.0
            player.death_timer = 0
        
        # Start new round
        self.start_new_round()
    
    def check_round_end(self):
        """Check if round should end and return end reason"""
        import time
        current_time = time.time()
        
        if not self.round_active:
            return None
            
        # Check time-based end
        if current_time - self.round_start_time >= self.round_duration:
            self.round_active = False
            return {'type': 'time_up', 'message': 'Time\'s up! Round ended.'}
        
        # Check if all players are spectators
        active_players = [p for p in self.players.values() if not getattr(p, 'is_spectator', False)]
        if len(active_players) == 0 and len(self.players) > 0:
            self.round_active = False
            return {'type': 'all_dead', 'message': 'All players eliminated! Round ended.'}
        
        # Check if no players left at all (everyone disconnected)
        if len(self.players) == 0:
            self.round_active = False
            return {'type': 'no_players', 'message': 'No players remaining. Game ended.', 'show_leaderboard': True}
        
        # Check if all pellets eaten
        if len(self.pellets) == 0 and len(self.power_pellets) == 0:
            self.round_active = False
            return {'type': 'pellets_cleared', 'message': 'All pellets collected! Round ended.'}
            
        return None
    
    def get_round_status(self):
        """Get current round information"""
        import time
        current_time = time.time()
        
        if not self.round_active:
            return {
                'active': False,
                'time_remaining': 0,
                'active_players': 0,
                'spectators': len([p for p in self.players.values() if getattr(p, 'is_spectator', False)])
            }
        
        time_remaining = max(0, self.round_duration - (current_time - self.round_start_time))
        active_players = len([p for p in self.players.values() if not getattr(p, 'is_spectator', False)])
        spectators = len([p for p in self.players.values() if getattr(p, 'is_spectator', False)])
        
        return {
            'active': True,
            'time_remaining': int(time_remaining),
            'active_players': active_players,
            'spectators': spectators
        }
    
    def get_ghosts_data(self):
        """Get all ghost data for broadcasting"""
        return [
            {
                'id': ghost.id,
                'position': {'x': ghost.x, 'y': ghost.y},
                'color': ghost.color,
                'direction': ghost.direction
            }
            for ghost in self.ghosts
        ]
    
    def get_leaderboard(self):
        """Get leaderboard data sorted by score"""
        leaderboard = []
        for player_id, player in self.players.items():
            leaderboard.append({
                'name': player.name,
                'score': player.score,
                'is_spectator': getattr(player, 'is_spectator', False)
            })
        
        # Sort by score (highest first)
        leaderboard.sort(key=lambda x: x['score'], reverse=True)
        return leaderboard
    
    def _validate_map(self):
        """Validate the generated map against all criteria"""
        import json
        
        # Create JSON representation of the map
        map_json = {
            'width': self.map_width,
            'height': self.map_height,
            'data': self.map_data,
            'validation': {}
        }
        
        # Test 1: Check symmetry (left-right and top-bottom)
        is_lr_symmetric = self._check_left_right_symmetry()
        is_tb_symmetric = self._check_top_bottom_symmetry()
        
        # Test 2: Check wall density (<30%)
        wall_count = sum(row.count(0) for row in self.map_data)
        total_tiles = self.map_width * self.map_height
        wall_percentage = (wall_count / total_tiles) * 100
        
        # Test 3: Check for enclosed areas (all paths should be connected)
        has_no_enclosed_areas = self._check_no_enclosed_areas()
        
        # Test 4: Check minimum connectivity (all walkable areas connected)
        all_connected = self._check_full_connectivity()
        
        # Store validation results
        map_json['validation'] = {
            'left_right_symmetric': is_lr_symmetric,
            'top_bottom_symmetric': is_tb_symmetric,
            'wall_percentage': round(wall_percentage, 2),
            'wall_percentage_valid': wall_percentage < 30,
            'no_enclosed_areas': has_no_enclosed_areas,
            'all_connected': all_connected,
            'overall_valid': (is_lr_symmetric and is_tb_symmetric and 
                            wall_percentage < 30 and has_no_enclosed_areas and all_connected)
        }
        
        # Save JSON for debugging
        try:
            with open('map_validation.json', 'w') as f:
                json.dump(map_json, f, indent=2)
        except Exception as e:
            print(f"Could not save validation JSON: {e}")
        
        # Print validation results
        print(f"Validation Results:")
        print(f"  Left-Right Symmetric: {is_lr_symmetric}")
        print(f"  Top-Bottom Symmetric: {is_tb_symmetric}")
        print(f"  Wall Percentage: {wall_percentage:.1f}% (target: <30%)")
        print(f"  No Enclosed Areas: {has_no_enclosed_areas}")
        print(f"  All Connected: {all_connected}")
        print(f"  Overall Valid: {map_json['validation']['overall_valid']}")
        
        return map_json['validation']['overall_valid']
    
    def _check_left_right_symmetry(self):
        """Check if map is symmetric left-right"""
        for y in range(self.map_height):
            for x in range(self.map_width // 2):
                mirror_x = self.map_width - 1 - x
                if self.map_data[y][x] != self.map_data[y][mirror_x]:
                    return False
        return True
    
    def _check_top_bottom_symmetry(self):
        """Check if map is symmetric top-bottom"""
        for y in range(self.map_height // 2):
            for x in range(self.map_width):
                mirror_y = self.map_height - 1 - y
                if self.map_data[y][x] != self.map_data[mirror_y][x]:
                    return False
        return True
    
    def _check_no_enclosed_areas(self):
        """Check that there are no fully enclosed areas"""
        visited = set()
        areas = []
        
        # Find all connected components
        for y in range(self.map_height):
            for x in range(self.map_width):
                if (x, y) not in visited and self.map_data[y][x] == 1:
                    area = set()
                    self._flood_fill(x, y, area)
                    if area:
                        areas.append(area)
                        visited.update(area)
        
        # If more than one connected component, we have enclosed areas
        return len(areas) <= 1
    
    def _check_full_connectivity(self):
        """Check that all walkable areas are connected"""
        # Find first walkable position
        start_x, start_y = None, None
        for y in range(self.map_height):
            for x in range(self.map_width):
                if self.map_data[y][x] == 1:
                    start_x, start_y = x, y
                    break
            if start_x is not None:
                break
        
        if start_x is None:
            return False  # No walkable areas
        
        # Count reachable positions
        reachable = set()
        self._flood_fill(start_x, start_y, reachable)
        
        # Count total walkable positions
        total_walkable = sum(row.count(1) for row in self.map_data)
        
        return len(reachable) == total_walkable