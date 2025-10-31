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
        """Generate a random, symmetrical maze with proper connectivity"""
        # Step 1: Create base pattern in top-left quadrant
        self._create_base_quadrant()
        
        # Step 2: Mirror to create full symmetrical map
        self._mirror_quadrants()
        
        # Step 3: Ensure connectivity and remove enclosed spaces
        self._ensure_connectivity()
        
        # Step 4: Adjust wall density to be less than 30%
        self._adjust_wall_density()
        
        # Step 5: Final connectivity check
        self._final_connectivity_pass()
    
    def _create_base_quadrant(self):
        """Create random maze pattern in top-left quadrant (will be mirrored)"""
        # Work with the top-left quarter of the map
        quad_width = self.map_width // 2
        quad_height = self.map_height // 2
        
        # Start with some guaranteed paths
        # Horizontal paths
        for y in range(1, quad_height, 4):
            for x in range(1, quad_width):
                if random.random() > 0.3:  # 70% chance of path
                    self.map_data[y][x] = 1
        
        # Vertical paths
        for x in range(1, quad_width, 4):
            for y in range(1, quad_height):
                if random.random() > 0.3:  # 70% chance of path
                    self.map_data[y][x] = 1
        
        # Add random connecting paths
        for y in range(2, quad_height - 1, 2):
            for x in range(2, quad_width - 1, 2):
                if random.random() > 0.4:  # 60% chance of path
                    self.map_data[y][x] = 1
                    
        # Ensure central corridors for connectivity
        center_x = quad_width // 2
        center_y = quad_height // 2
        
        # Main cross corridors
        for x in range(1, quad_width):
            self.map_data[center_y][x] = 1
        for y in range(1, quad_height):
            self.map_data[y][center_x] = 1
    
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
        """Ensure all areas are connected using flood fill"""
        # Find the first walkable cell
        start_x, start_y = None, None
        for y in range(1, self.map_height - 1):
            for x in range(1, self.map_width - 1):
                if self.map_data[y][x] == 1:
                    start_x, start_y = x, y
                    break
            if start_x is not None:
                break
        
        if start_x is None:
            # No paths exist, create basic cross pattern
            self._create_emergency_paths()
            return
        
        # Flood fill to find connected areas
        visited = set()
        self._flood_fill(start_x, start_y, visited)
        
        # Find unconnected walkable areas and connect them
        for y in range(1, self.map_height - 1):
            for x in range(1, self.map_width - 1):
                if self.map_data[y][x] == 1 and (x, y) not in visited:
                    # Found unconnected area, create path to main area
                    self._connect_to_main_area(x, y, visited)
    
    def _flood_fill(self, x, y, visited):
        """Flood fill algorithm to find connected areas"""
        if (x, y) in visited or x < 0 or x >= self.map_width or y < 0 or y >= self.map_height:
            return
        if self.map_data[y][x] != 1:  # Not a walkable path
            return
        
        visited.add((x, y))
        
        # Check 4 directions
        self._flood_fill(x + 1, y, visited)
        self._flood_fill(x - 1, y, visited)
        self._flood_fill(x, y + 1, visited)
        self._flood_fill(x, y - 1, visited)
    
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
        """Spawn pellets on all walkable tiles"""
        self.pellets = set()
        self.power_pellets = set()
        
        # Regular pellets on all path tiles
        for y in range(self.map_height):
            for x in range(self.map_width):
                if self.map_data[y][x] == 1:  # Path tile
                    self.pellets.add((x, y))
        
        # Power pellets at strategic locations
        power_pellet_positions = [
            (2, 2), (37, 2), (2, 27), (37, 27),  # Corners
            (19, 7), (19, 22),  # Center vertical
            (7, 14), (32, 14)  # Center horizontal
        ]
        
        for x, y in power_pellet_positions:
            if 0 <= x < self.map_width and 0 <= y < self.map_height:
                if self.map_data[y][x] == 1:
                    self.power_pellets.add((x, y))
                    # Remove regular pellet if it exists
                    self.pellets.discard((x, y))
    
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
            self.logger.info(f"Player {player.id} is now the host")
        
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
                remaining_players = [pid for pid in self.players.keys() if pid != player_id]
                self.host_player_id = remaining_players[0] if remaining_players else None
                if self.host_player_id:
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
            player.invincible = False
            player.invincibility_timer = 0
            
            # Respawn all players
            spawn_pos = self.get_available_spawn_point()
            if spawn_pos:
                player.x, player.y = spawn_pos
        
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
        
        # Check bounds and collision
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
        for ghost in self.ghosts:
            ghost.update(self.map_data, self.map_width, self.map_height, self.tile_size, self.players)
    
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
                            self.logger.debug(f"Player {player_id} RESPAWNED from {old_pos} to {spawn_pos}")
                            collisions.append({
                                'type': 'player_caught',
                                'player_id': player_id,
                                'ghost_id': ghost.id,
                                'lives': player.lives,
                                'respawn_pos': {'x': player.x, 'y': player.y}
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