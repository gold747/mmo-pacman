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
        
    def update(self, map_data, map_width, map_height, tile_size, players=None):
        """Update ghost AI and movement"""
        self.move_counter += 1
        
        # Move slower - every 4 ticks instead of 2
        if self.move_counter % 4 != 0:
            return
        
        # Find nearest player within chase range
        target_player = self.find_nearest_player(players, tile_size)
        
        if target_player:
            # Chase mode - move towards the target player
            best_direction = self.get_direction_to_target(target_player, map_data, map_width, map_height, tile_size)
            if best_direction:
                self.move_in_direction(best_direction, map_data, map_width, map_height, tile_size)
            else:
                # If can't move towards target, use random movement
                self.random_movement(map_data, map_width, map_height, tile_size)
        else:
            # Random patrol mode when no players nearby
            self.random_movement(map_data, map_width, map_height, tile_size)
    
    def find_nearest_player(self, players, tile_size):
        """Find the nearest player within chase range"""
        if not players:
            return None
        
        ghost_tile_x = self.x // tile_size
        ghost_tile_y = self.y // tile_size
        nearest_player = None
        min_distance = float('inf')
        
        for player in players.values():
            player_tile_x = player.x // tile_size
            player_tile_y = player.y // tile_size
            
            # Calculate Manhattan distance (good for grid-based movement)
            distance = abs(ghost_tile_x - player_tile_x) + abs(ghost_tile_y - player_tile_y)
            
            # Check if player is within chase range and closer than current nearest
            if distance <= self.chase_range and distance < min_distance:
                min_distance = distance
                nearest_player = player
        
        return nearest_player
    
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
        
        # Try directions in priority order
        for direction in directions:
            if self.can_move_in_direction(direction, map_data, map_width, map_height, tile_size):
                return direction
        
        return None
    
    def can_move_in_direction(self, direction, map_data, map_width, map_height, tile_size):
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
        
        return (0 <= tile_x < map_width and 
                0 <= tile_y < map_height and
                map_data[tile_y][tile_x] != 0)  # Not a wall
    
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
        
        # Validate move
        if self.can_move_in_direction(direction, map_data, map_width, map_height, tile_size):
            self.x = new_x
            self.y = new_y
            self.direction = direction
    
    def random_movement(self, map_data, map_width, map_height, tile_size):
        """Random movement when not chasing players"""
        directions = ['up', 'down', 'left', 'right']
        random.shuffle(directions)
        
        # 70% chance to continue in current direction for smoother movement
        if random.random() < 0.7 and self.can_move_in_direction(self.direction, map_data, map_width, map_height, tile_size):
            directions.insert(0, self.direction)
        
        # Try each direction until we find a valid one
        for direction in directions:
            if self.can_move_in_direction(direction, map_data, map_width, map_height, tile_size):
                self.move_in_direction(direction, map_data, map_width, map_height, tile_size)
                break
    
    def reset_position(self):
        """Reset ghost to home position (when eaten)"""
        self.x = self.home_x
        self.y = self.home_y
        self.direction = 'up'
    
    def to_dict(self):
        """Convert ghost to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'position': {'x': self.x, 'y': self.y},
            'color': self.color,
            'direction': self.direction
        }