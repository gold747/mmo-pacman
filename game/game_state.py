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
        # Session-based MMO properties
        self.round_duration = 300  # 5 minutes per round (in seconds)
        self.round_start_time = 0
        self.round_active = False
        self.max_players = 30
        
        # Large map dimensions (40x30 tiles, each tile is 20px)
        self.map_width = 40
        self.map_height = 30
        self.tile_size = 20
        
        # Generate the map
        self.generate_map()
        self.spawn_pellets()
        self.spawn_ghosts()
        
    def generate_map(self):
        """Generate a large maze suitable for 30 players"""
        # 0 = wall, 1 = path, 2 = spawn point
        self.map_data = []
        
        # Initialize with walls
        for y in range(self.map_height):
            row = []
            for x in range(self.map_width):
                row.append(0)
            self.map_data.append(row)
        
        # Create paths using maze generation algorithm
        self._generate_maze_paths()
        
        # Add spawn points (scattered around the map)
        self.spawn_points = []
        spawn_positions = [
            (1, 1), (38, 1), (1, 28), (38, 28),  # Corners
            (19, 1), (19, 28), (1, 14), (38, 14),  # Mid edges
            (10, 7), (30, 7), (10, 22), (30, 22),  # Quarter points
            (19, 14), (5, 14), (35, 14),  # Center area
            (8, 3), (32, 3), (8, 26), (32, 26),  # Additional spawns
            (14, 10), (26, 10), (14, 19), (26, 19),  # More spawns
            (3, 8), (37, 8), (3, 21), (37, 21),  # Edge spawns
            (11, 14), (29, 14), (19, 7), (19, 22)  # Final spawns
        ]
        
        for x, y in spawn_positions:
            if y < self.map_height and x < self.map_width:
                self.map_data[y][x] = 2
                self.spawn_points.append((x * self.tile_size, y * self.tile_size))
    
    def _generate_maze_paths(self):
        """Generate maze-like paths throughout the map"""
        # Create horizontal corridors
        for y in [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 27]:
            for x in range(1, self.map_width - 1):
                if x % 4 != 2:  # Skip some tiles to create gaps
                    self.map_data[y][x] = 1
        
        # Create vertical corridors
        for x in [1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34, 37]:
            for y in range(1, self.map_height - 1):
                if y % 3 != 0:  # Skip some tiles to create gaps
                    self.map_data[y][x] = 1
        
        # Create additional connecting paths
        paths = [
            # Horizontal connections
            [(8, 2), (31, 2)], [(8, 4), (31, 4)], [(8, 6), (31, 6)],
            [(5, 8), (34, 8)], [(5, 10), (34, 10)], [(5, 12), (34, 12)],
            [(8, 14), (31, 14)], [(8, 16), (31, 16)], [(8, 18), (31, 18)],
            [(5, 20), (34, 20)], [(5, 22), (34, 22)], [(5, 24), (34, 24)],
            [(8, 26), (31, 26)], [(8, 28), (31, 28)],
            
            # Vertical connections
            [(2, 5), (2, 24)], [(6, 3), (6, 26)], [(11, 2), (11, 27)],
            [(15, 3), (15, 26)], [(20, 2), (20, 27)], [(24, 3), (24, 26)],
            [(28, 2), (28, 27)], [(32, 3), (32, 26)], [(36, 5), (36, 24)]
        ]
        
        for path in paths:
            start, end = path
            self._draw_path(start, end)
    
    def _draw_path(self, start, end):
        """Draw a path between two points"""
        x1, y1 = start
        x2, y2 = end
        
        # Draw horizontal line
        if y1 == y2:
            for x in range(min(x1, x2), max(x1, x2) + 1):
                if 0 <= x < self.map_width and 0 <= y1 < self.map_height:
                    self.map_data[y1][x] = 1
        
        # Draw vertical line
        elif x1 == x2:
            for y in range(min(y1, y2), max(y1, y2) + 1):
                if 0 <= x1 < self.map_width and 0 <= y < self.map_height:
                    self.map_data[y][x1] = 1
    
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
        """Spawn ghosts in the center area"""
        ghost_positions = [
            (19 * self.tile_size, 13 * self.tile_size),
            (19 * self.tile_size, 14 * self.tile_size),
            (19 * self.tile_size, 15 * self.tile_size),
            (20 * self.tile_size, 14 * self.tile_size)
        ]
        
        colors = ['red', 'pink', 'cyan', 'orange']
        
        for i, (x, y) in enumerate(ghost_positions):
            ghost = Ghost(f'ghost_{i}', x, y, colors[i])
            self.ghosts.append(ghost)
    
    def add_player(self, player):
        """Add a player to the game"""
        if len(self.players) >= self.max_players:
            return False, None
        
        # Find available spawn point
        spawn_pos = self.get_available_spawn_point()
        if spawn_pos is None:
            return False, None
        
        self.players[player.id] = player
        return True, spawn_pos
    
    def remove_player(self, player_id):
        """Remove a player from the game"""
        if player_id in self.players:
            del self.players[player_id]
    
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
            player.power_timer = 300  # 30 seconds at 10 FPS
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
                if player.power_timer <= 0:
                    player.power_mode = False
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
        
        # Reset pellets (optional - could keep them eaten for continuous play)
        self.generate_pellets()
        
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