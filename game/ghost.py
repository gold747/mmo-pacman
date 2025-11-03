import random
import math

class Ghost:
    def __init__(self, ghost_id, x, y, color):
        self.id = ghost_id
        self.x = x
        self.y = y
        self.color = color
        self.direction = 'up'
        self.speed = 1
        self.home_x = x
        self.home_y = y
        self.target_x = x
        self.target_y = y
        self.move_counter = 0
        self.chase_range = 8  # tiles - medium range for chasing players
        self.current_target = None
        self.previous_x = x
        self.previous_y = y
        self.stuck_counter = 0  # Track how long ghost has been stuck
        self.last_position = (x, y)  # Track last position to detect if stuck
        
    def update(self, map_data, map_width, map_height, tile_size, players=None, invincible_positions=None, other_ghost_positions=None):
        """Update ghost AI and movement"""
        self.move_counter += 1
        
        # Move slower - every 4 ticks instead of 2
        if self.move_counter % 4 != 0:
            return
        
        # Check if ghost is stuck (hasn't moved for several attempts)
        current_position = (self.x, self.y)
        if current_position == self.last_position:
            self.stuck_counter += 1
        else:
            self.stuck_counter = 0
            self.last_position = current_position
        
        # If stuck for too long, request respawn
        if self.stuck_counter >= 20:  # 20 * 4 ticks = 80 ticks without movement
            return 'respawn_needed'
        
        # Store positions for movement checks
        self.invincible_positions = invincible_positions or set()
        self.other_ghost_positions = other_ghost_positions or set()
        
        # Find nearest player within range (chase normal players, flee from power mode players)
        target_info = self.find_nearest_player(players, tile_size)
        
        moved = False
        if target_info:
            action, target_player = target_info
            if action == 'flee':
                # Flee mode - run away from powered player
                best_direction = self.get_direction_away_from_target(target_player, map_data, map_width, map_height, tile_size)
            else:  # action == 'chase'
                # Chase mode - move towards normal player
                best_direction = self.get_direction_to_target(target_player, map_data, map_width, map_height, tile_size)
            
            if best_direction:
                self.move_in_direction(best_direction, map_data, map_width, map_height, tile_size)
                moved = True
            else:
                # If can't move towards/away from target, use random movement
                moved = self.random_movement(map_data, map_width, map_height, tile_size)
        else:
            # Random patrol mode when no players nearby
            moved = self.random_movement(map_data, map_width, map_height, tile_size)
        
        # If we couldn't move at all, increment stuck counter
        if not moved:
            self.stuck_counter += 1
    
    def find_nearest_player(self, players, tile_size):
        """Find the nearest player within range (chase normal players, flee from power mode players)"""
        if not players:
            return None
        
        ghost_tile_x = self.x // tile_size
        ghost_tile_y = self.y // tile_size
        nearest_normal_player = None
        nearest_power_player = None
        min_normal_distance = float('inf')
        min_power_distance = float('inf')
        
        for player in players.values():
            # Skip invincible players - ghosts shouldn't interact with them
            if player.invincible:
                continue
                
            player_tile_x = player.x // tile_size
            player_tile_y = player.y // tile_size
            
            # Calculate Manhattan distance (good for grid-based movement)
            distance = abs(ghost_tile_x - player_tile_x) + abs(ghost_tile_y - player_tile_y)
            
            # Check if player is in power mode
            if hasattr(player, 'power_mode') and player.power_mode:
                # This is a powered player - ghosts should flee from them
                if distance <= self.chase_range and distance < min_power_distance:
                    min_power_distance = distance
                    nearest_power_player = player
            else:
                # Normal player - ghosts can chase them
                if distance <= self.chase_range and distance < min_normal_distance:
                    min_normal_distance = distance
                    nearest_normal_player = player
        
        # Priority: flee from power mode players first, then chase normal players
        if nearest_power_player:
            return ('flee', nearest_power_player)
        elif nearest_normal_player:
            return ('chase', nearest_normal_player)
        
        return None
    
    def get_direction_to_target(self, target_player, map_data, map_width, map_height, tile_size):
        """Calculate best direction to move towards target player"""
        ghost_tile_x = self.x // tile_size
        ghost_tile_y = self.y // tile_size
        target_tile_x = target_player.x // tile_size
        target_tile_y = target_player.y // tile_size
        
        # Calculate direction priorities based on distance to target
        dx = target_tile_x - ghost_tile_x
        dy = target_tile_y - ghost_tile_y
        
        # Create priority list of directions
        directions = []
        
        # Prioritize horizontal movement
        if dx > 0:
            directions.append('right')
        elif dx < 0:
            directions.append('left')
        
        # Prioritize vertical movement
        if dy > 0:
            directions.append('down')
        elif dy < 0:
            directions.append('up')
        
        # Add remaining directions for backup
        all_directions = ['up', 'down', 'left', 'right']
        for direction in all_directions:
            if direction not in directions:
                directions.append(direction)
        
        # Try directions in priority order (without backtracking)
        ghost_blocked = False
        for direction in directions:
            if self.can_move_in_direction(direction, map_data, map_width, map_height, tile_size, allow_backtrack=False):
                return direction
            # Check if we're blocked by another ghost
            elif self._is_blocked_by_ghost(direction, map_data, map_width, map_height, tile_size):
                ghost_blocked = True
        
        # If blocked by ghosts, allow backtracking as a fallback
        if ghost_blocked:
            for direction in directions:
                if self.can_move_in_direction(direction, map_data, map_width, map_height, tile_size, allow_backtrack=True, ghost_blocked=True):
                    return direction
        
        # If still no direction works, try all directions allowing backtracking
        for direction in directions:
            if self.can_move_in_direction(direction, map_data, map_width, map_height, tile_size, allow_backtrack=True):
                return direction
        
        return None
    
    def get_direction_away_from_target(self, target_player, map_data, map_width, map_height, tile_size):
        """Calculate best direction to move away from target player (flee from powered players)"""
        ghost_tile_x = self.x // tile_size
        ghost_tile_y = self.y // tile_size
        target_tile_x = target_player.x // tile_size
        target_tile_y = target_player.y // tile_size
        
        # Calculate direction priorities based on distance to target (opposite of chase)
        dx = target_tile_x - ghost_tile_x
        dy = target_tile_y - ghost_tile_y
        
        # Create priority list of directions to flee
        directions = []
        
        # Prioritize moving away horizontally
        if dx > 0:
            directions.append('left')   # Player is to the right, go left
        elif dx < 0:
            directions.append('right')  # Player is to the left, go right
        
        # Prioritize moving away vertically  
        if dy > 0:
            directions.append('up')     # Player is below, go up
        elif dy < 0:
            directions.append('down')   # Player is above, go down
        
        # Add remaining directions for backup
        all_directions = ['up', 'down', 'left', 'right']
        for direction in all_directions:
            if direction not in directions:
                directions.append(direction)
        
        # Try directions in priority order (without backtracking first)
        ghost_blocked = False
        for direction in directions:
            if self.can_move_in_direction(direction, map_data, map_width, map_height, tile_size, allow_backtrack=False):
                return direction
            # Check if we're blocked by another ghost
            elif self._is_blocked_by_ghost(direction, map_data, map_width, map_height, tile_size):
                ghost_blocked = True
        
        # If blocked by ghosts, allow backtracking as a fallback
        if ghost_blocked:
            for direction in directions:
                if self.can_move_in_direction(direction, map_data, map_width, map_height, tile_size, allow_backtrack=True, ghost_blocked=True):
                    return direction
        
        # If still no direction works, try all directions allowing backtracking
        for direction in directions:
            if self.can_move_in_direction(direction, map_data, map_width, map_height, tile_size, allow_backtrack=True):
                return direction
        
        return None
    
    def _is_blocked_by_ghost(self, direction, map_data, map_width, map_height, tile_size):
        """Check if the given direction is blocked specifically by another ghost"""
        new_x, new_y = self.x, self.y
        
        if direction == 'up':
            new_y -= tile_size
        elif direction == 'down':
            new_y += tile_size
        elif direction == 'left':
            new_x -= tile_size
        elif direction == 'right':
            new_x += tile_size
        
        tile_x = new_x // tile_size
        tile_y = new_y // tile_size
        
        # Check basic validity first
        if not (0 <= tile_x < map_width and 
                0 <= tile_y < map_height and
                map_data[tile_y][tile_x] != 0):
            return False  # Blocked by wall/boundary, not ghost
        
        # Check if blocked by another ghost
        return (hasattr(self, 'other_ghost_positions') and 
                (tile_x, tile_y) in self.other_ghost_positions)
    
    def can_move_in_direction(self, direction, map_data, map_width, map_height, tile_size, allow_backtrack=False, ghost_blocked=False):
        """Check if ghost can move in the specified direction"""
        new_x, new_y = self.x, self.y
        
        if direction == 'up':
            new_y -= tile_size
        elif direction == 'down':
            new_y += tile_size
        elif direction == 'left':
            new_x -= tile_size
        elif direction == 'right':
            new_x += tile_size
        
        # Check if move is valid
        tile_x = new_x // tile_size
        tile_y = new_y // tile_size
        
        # Check basic validity (bounds and walls)
        if not (0 <= tile_x < map_width and 
                0 <= tile_y < map_height and
                map_data[tile_y][tile_x] != 0):  # Not a wall
            return False
        
        # Check if destination tile has an invincible player
        if hasattr(self, 'invincible_positions') and (tile_x, tile_y) in self.invincible_positions:
            return False
        
        # Check if destination tile has another ghost (but allow backtracking if blocked by ghost)
        if hasattr(self, 'other_ghost_positions') and (tile_x, tile_y) in self.other_ghost_positions:
            # If blocked by another ghost, we can consider backtracking as an option
            if not allow_backtrack:
                return False
        
        # Check if this would be backtracking to previous position
        if not allow_backtrack:
            previous_tile_x = self.previous_x // tile_size
            previous_tile_y = self.previous_y // tile_size
            if tile_x == previous_tile_x and tile_y == previous_tile_y:
                # Only allow backtracking if we're blocked by another ghost
                return ghost_blocked
        
        return True
    
    def move_in_direction(self, direction, map_data, map_width, map_height, tile_size):
        """Move ghost in the specified direction"""
        new_x, new_y = self.x, self.y
        
        if direction == 'up':
            new_y -= tile_size
        elif direction == 'down':
            new_y += tile_size
        elif direction == 'left':
            new_x -= tile_size
        elif direction == 'right':
            new_x += tile_size
        
        # Check for warp tunnels first (horizontal wrapping)
        if new_x < 0:  # Moving left off the map
            new_x = (map_width - 1) * tile_size
        elif new_x >= map_width * tile_size:  # Moving right off the map
            new_x = 0
        
        # Validate move
        if self.can_move_in_direction(direction, map_data, map_width, map_height, tile_size):
            # Store previous position before moving
            self.previous_x = self.x
            self.previous_y = self.y
            
            # Move to new position (use potentially warped coordinates)
            self.x = new_x
            self.y = new_y
            self.direction = direction
    
    def random_movement(self, map_data, map_width, map_height, tile_size):
        """Random movement when not chasing players"""
        directions = ['up', 'down', 'left', 'right']
        random.shuffle(directions)
        
        # 70% chance to continue in current direction for smoother movement (if valid without backtracking)
        if random.random() < 0.7 and self.can_move_in_direction(self.direction, map_data, map_width, map_height, tile_size, allow_backtrack=False):
            directions.insert(0, self.direction)
        
        # Try each direction until we find a valid one (prefer no backtracking)
        moved = False
        ghost_blocked = False
        
        for direction in directions:
            if self.can_move_in_direction(direction, map_data, map_width, map_height, tile_size, allow_backtrack=False):
                self.move_in_direction(direction, map_data, map_width, map_height, tile_size)
                moved = True
                break
            elif self._is_blocked_by_ghost(direction, map_data, map_width, map_height, tile_size):
                ghost_blocked = True
        
        # If blocked by ghosts, allow backtracking as fallback
        if not moved and ghost_blocked:
            for direction in directions:
                if self.can_move_in_direction(direction, map_data, map_width, map_height, tile_size, allow_backtrack=True, ghost_blocked=True):
                    self.move_in_direction(direction, map_data, map_width, map_height, tile_size)
                    moved = True
                    break
        
        # If still no movement possible, allow any backtracking as last resort
        if not moved:
            for direction in directions:
                if self.can_move_in_direction(direction, map_data, map_width, map_height, tile_size, allow_backtrack=True):
                    self.move_in_direction(direction, map_data, map_width, map_height, tile_size)
                    moved = True
                    break
        
        return moved
    
    def reset_position(self):
        """Reset ghost to home position (when eaten)"""
        self.previous_x = self.x
        self.previous_y = self.y
        self.x = self.home_x
        self.y = self.home_y
        self.direction = 'up'
        self.stuck_counter = 0  # Reset stuck counter when repositioned
    
    def respawn_at_position(self, new_x, new_y):
        """Respawn ghost at a new position when stuck"""
        self.previous_x = self.x
        self.previous_y = self.y
        self.x = new_x
        self.y = new_y
        self.direction = 'up'
        self.stuck_counter = 0
        self.last_position = (new_x, new_y)
    
    def to_dict(self):
        """Convert ghost to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'position': {'x': self.x, 'y': self.y},
            'color': self.color,
            'direction': self.direction
        }