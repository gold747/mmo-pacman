from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import json
import time
import threading
import logging
import sys
import os
import psutil
from datetime import datetime
from game.game_state import GameState
from game.player import Player
from game.ghost import Ghost

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mmo_pacman_secret_key_2024'

# Setup logging with timestamp in logs folder
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
logs_folder = "logs"
os.makedirs(logs_folder, exist_ok=True)  # Create logs folder if it doesn't exist
log_filename = os.path.join(logs_folder, f"mmo_pacman_server_{timestamp}.log")

# Configure logging with file-only for detailed logs, minimal console output
file_handler = logging.FileHandler(log_filename)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.WARNING)  # Only show warnings and errors in console
console_handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))

# Configure root logger
logging.basicConfig(
    level=logging.DEBUG,
    handlers=[file_handler, console_handler]
)

# Suppress SocketIO's verbose logging to console
# Suppress SocketIO console logging completely
logging.getLogger('socketio').setLevel(logging.ERROR)
logging.getLogger('engineio').setLevel(logging.ERROR)

# Create app logger with selective console output
logger = logging.getLogger(__name__)

# Add a console handler specifically for important server messages
server_console = logging.StreamHandler(sys.stdout)
server_console.setLevel(logging.INFO)
server_console.setFormatter(logging.Formatter('[SERVER] %(message)s'))
logger.addHandler(server_console)
logger.setLevel(logging.DEBUG)

print(f"[STARTUP] Server logs: {log_filename}")

# Configure SocketIO with logging disabled for console
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', logger=False, engineio_logger=False)

# Global game state
game_state = GameState()

# Performance monitoring
class PerformanceMonitor:
    def __init__(self):
        self.game_loop_times = []
        self.cpu_percentages = []
        self.memory_usage = []
        self.player_counts = []
        self.last_log_time = time.time()
        self.frame_count = 0
        
    def record_frame_time(self, frame_time):
        self.game_loop_times.append(frame_time)
        self.frame_count += 1
        
        # Keep only last 100 measurements
        if len(self.game_loop_times) > 100:
            self.game_loop_times.pop(0)
    
    def record_system_stats(self, player_count):
        self.cpu_percentages.append(psutil.cpu_percent())
        self.memory_usage.append(psutil.Process().memory_info().rss / 1024 / 1024)  # MB
        self.player_counts.append(player_count)
        
        # Keep only last 60 measurements (1 minute at 1 Hz)
        if len(self.cpu_percentages) > 60:
            self.cpu_percentages.pop(0)
            self.memory_usage.pop(0)
            self.player_counts.pop(0)
    
    def get_stats(self):
        if not self.game_loop_times:
            return {}
        
        avg_frame_time = sum(self.game_loop_times) / len(self.game_loop_times)
        max_frame_time = max(self.game_loop_times)
        fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0
        
        return {
            'fps': round(fps, 1),
            'avg_frame_time': round(avg_frame_time * 1000, 2),  # ms
            'max_frame_time': round(max_frame_time * 1000, 2),  # ms
            'cpu_percent': round(sum(self.cpu_percentages) / len(self.cpu_percentages), 1) if self.cpu_percentages else 0,
            'memory_mb': round(sum(self.memory_usage) / len(self.memory_usage), 1) if self.memory_usage else 0,
            'player_count': self.player_counts[-1] if self.player_counts else 0,
            'total_frames': self.frame_count
        }
    
    def should_log(self):
        return time.time() - self.last_log_time >= 5.0  # Log every 5 seconds
    
    def log_performance(self):
        stats = self.get_stats()
        logger.info(f"[PERFORMANCE] FPS: {stats['fps']}, "
                   f"Frame Time: {stats['avg_frame_time']}ms (max: {stats['max_frame_time']}ms), "
                   f"CPU: {stats['cpu_percent']}%, Memory: {stats['memory_mb']}MB, "
                   f"Players: {stats['player_count']}")
        self.last_log_time = time.time()

perf_monitor = PerformanceMonitor()

@app.route('/')
def index():
    import socket
    import requests
    
    # Get local IP
    try:
        # Try to get external IP
        response = requests.get('https://api.ipify.org', timeout=5)
        server_ip = response.text.strip()
    except:
        try:
            # Fallback to local network IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            server_ip = s.getsockname()[0]
            s.close()
        except:
            server_ip = 'localhost'
    
    server_port = 5000  # Default Flask port
    
    return render_template('index.html', server_ip=server_ip, server_port=server_port)

@socketio.on('connect')
def on_connect(*args):
    logger.info(f'Client {request.sid} connected')
    
@socketio.on('disconnect')
def on_disconnect():
    logger.info(f'[DISCONNECT] Client {request.sid} disconnected')
    # Remove player from game
    if request.sid in game_state.players:
        game_state.remove_player(request.sid)
        emit('player_disconnected', {'player_id': request.sid}, broadcast=True)

@socketio.on('join_game')
def on_join_game(data):
    logger.info(f'[JOIN] Received join_game event from {request.sid} with data: {data}')
    player_name = data.get('name', f'Player_{request.sid[:8]}')
    logger.info(f'[PLAYER] Player name: {player_name}')
    
    # Create new player
    player = Player(request.sid, player_name)
    logger.info(f'[CREATE] Created player: {player.id} with lives: {player.lives}')
    
    # Add player to game state
    success, spawn_pos = game_state.add_player(player)
    logger.info(f'[SPAWN] Add player result - Success: {success}, Spawn pos: {spawn_pos}')
    
    if success:
        player.x, player.y = spawn_pos
        logger.info(f'[POSITION] Player positioned at: {player.x}, {player.y}')
        
        # Send appropriate data based on game state
        if game_state.game_state == 'lobby':
            # Send lobby data
            lobby_data = {
                'player_id': request.sid,
                'lobby_state': game_state.get_lobby_state(),
                'is_host': request.sid == game_state.host_player_id
            }
            emit('lobby_joined', lobby_data)
            
            # Notify all players of updated lobby state
            socketio.emit('lobby_updated', game_state.get_lobby_state(), namespace='/')
        else:
            # Send full game state for active game
            game_data = {
                'player_id': request.sid,
                'spawn_position': {'x': player.x, 'y': player.y},
                'map_data': game_state.map_data,
                'players': game_state.get_players_data(),
                'ghosts': game_state.get_ghosts_data(),
                'pellets': list(game_state.pellets),
                'power_pellets': list(game_state.power_pellets),
                'game_state': game_state.game_state
            }
            logger.info(f'[GAMEDATA] Sending game_joined event with pellets: {len(game_data["pellets"])}, power_pellets: {len(game_data["power_pellets"])}')
            emit('game_joined', game_data)
        
        # Notify other players
        emit('player_joined', {
            'player_id': request.sid,
            'name': player_name,
            'position': {'x': player.x, 'y': player.y},
            'score': player.score
        }, broadcast=True, include_self=False)
        logger.info(f'Player {player_name} successfully joined the game')
    else:
        logger.warning(f'[ERROR] Failed to add player - game full or no spawn points')
        emit('game_full', {'message': 'Game is full. Maximum 30 players allowed.'})

@socketio.on('player_move')
def on_player_move(data):
    if request.sid in game_state.players:
        direction = data.get('direction')
        player = game_state.players[request.sid]
        
        # Process movement and collision detection
        old_x, old_y = player.x, player.y
        moved = game_state.move_player(request.sid, direction)
        
        if moved:
            # Check for pellet collection
            pellet_collected = game_state.check_pellet_collision(request.sid)
            power_pellet_collected = game_state.check_power_pellet_collision(request.sid)
            
            # Broadcast player movement
            # Broadcast player movement to everyone (including sender)
            emit('player_moved', {
                'player_id': request.sid,
                'position': {'x': player.x, 'y': player.y},
                'direction': direction,
                'invincible': player.invincible,
                'is_spectator': getattr(player, 'is_spectator', False)
            }, broadcast=True)
            
            # Handle pellet collection
            if pellet_collected:
                logger.info(f'[PELLET] Player {request.sid} collected pellet at ({int(player.x // 20)}, {int(player.y // 20)}), score: {player.score}')
                emit('pellet_collected', {
                    'player_id': request.sid,
                    'pellet_pos': {'x': int(player.x // 20), 'y': int(player.y // 20)},
                    'score': player.score
                }, broadcast=True)
            
            # Handle power pellet collection
            if power_pellet_collected:
                logger.info(f'Player {request.sid} collected POWER PELLET at ({int(player.x // 20)}, {int(player.y // 20)}), score: {player.score}, power_mode: {player.power_mode}, power_timer: {player.power_timer}')
                emit('power_pellet_collected', {
                    'player_id': request.sid,
                    'pellet_pos': {'x': int(player.x // 20), 'y': int(player.y // 20)},
                    'score': player.score,
                    'power_mode': player.power_mode,
                    'power_timer': player.power_timer
                }, broadcast=True)

@socketio.on('start_game')
def on_start_game():
    """Handle game start request from host"""
    success, message = game_state.start_game(request.sid)
    
    if success:
        # Notify all players that the game has started
        socketio.emit('game_started', {
            'message': message,
            'players': game_state.get_players_data(),
            'ghosts': game_state.get_ghosts_data(),
            'map_data': game_state.map_data,
            'pellets': list(game_state.pellets),
            'power_pellets': list(game_state.power_pellets)
        }, namespace='/')
        logger.info(f"Game started by host {request.sid}")
    else:
        # Send error message to requesting player
        emit('start_game_error', {'error': message})

@socketio.on('get_lobby_state')
def on_get_lobby_state():
    """Send current lobby state to requesting client"""
    emit('lobby_state', game_state.get_lobby_state())

@socketio.on('restart_game')
def handle_restart_game():
    """Handle host restarting the game"""
    player_id = request.sid
    
    if player_id in game_state.players:
        # Verify this player is the host
        if player_id == game_state.host_player_id:
            logger.info(f"[RESTART] Host {player_id} restarting game")
            game_state.waiting_for_restart = False
            
            # Reset game state for new round
            game_state.restart_round()
            
            # Actually start the game immediately
            success, message = game_state.start_game(player_id)
            
            if success:
                # Notify all players that the new round has started
                socketio.emit('game_started', {
                    'message': 'New round started by host!',
                    'players': game_state.get_players_data(),
                    'ghosts': game_state.get_ghosts_data(),
                    'map_data': game_state.map_data,
                    'pellets': list(game_state.pellets),
                    'power_pellets': list(game_state.power_pellets)
                }, namespace='/')
                
                logger.info(f"[RESTART] New round started successfully")
            else:
                logger.error(f"[RESTART] Failed to start new round: {message}")
                socketio.emit('error', {'message': f'Failed to start new round: {message}'}, namespace='/')
            
        else:
            logger.warning(f"[RESTART] Non-host player {player_id} tried to restart game")
            emit('error', {'message': 'Only the host can restart the game'})
    else:
        logger.warning(f"[RESTART] Unknown player {player_id} tried to restart game")

def game_loop():
    """Main game loop that runs continuously"""
    with app.app_context():
        first_round_started = False
        ghost_update_counter = 0  # For reducing ghost update log frequency
        frame_start_time = time.time()
            
        while True:
            try:
                frame_start_time = time.time()
                # Only start round if game is in playing state (not lobby)
                if not first_round_started and len(game_state.players) > 0 and game_state.game_state == 'playing':
                    game_state.start_new_round()
                    first_round_started = True
                    logger.info(f"[ROUND_START] First round started with {len(game_state.players)} players")
                
                # Check round status
                round_end = game_state.check_round_end()
                if round_end:
                    logger.info(f"[ROUND_END] {round_end['message']}")
                    
                    # Always show leaderboard when round ends
                    leaderboard_data = game_state.get_leaderboard()
                    host_id = None
                    for player_id, player in game_state.players.items():
                        if getattr(player, 'is_host', False):
                            host_id = player_id
                            break
                    
                    logger.info(f"[LEADERBOARD] Round ended, showing leaderboard to all players")
                    socketio.emit('round_ended', {
                        'reason': round_end['type'],
                        'message': round_end['message'],
                        'leaderboard': leaderboard_data,
                        'host_id': host_id,
                        'round_status': game_state.get_round_status()
                    }, namespace='/')
                    
                    # Check if we should end the game (no players left)
                    if round_end['type'] == 'no_players' or (round_end['type'] == 'all_dead' and len(game_state.players) == 0):
                        logger.info("[GAME_END] All players gone, ending game")
                        # Don't restart - wait for new players or host action
                        socketio.sleep(30)  # Show leaderboard for 30 seconds
                        continue
                    
                    # Wait for host to restart or timeout after 60 seconds
                    game_state.waiting_for_restart = True
                    restart_timeout = 60
                    elapsed = 0
                    
                    while game_state.waiting_for_restart and elapsed < restart_timeout:
                        socketio.sleep(1)
                        elapsed += 1
                    
                    # If no restart command from host, auto-restart if players remain
                    if game_state.waiting_for_restart and len(game_state.players) > 0:
                        game_state.waiting_for_restart = False
                        logger.info("[AUTO_RESTART] Host didn't restart, auto-restarting round")
                    if len(game_state.players) > 0 and game_state.game_state == 'playing':
                        game_state.start_new_round()
                        socketio.emit('round_started', {
                            'message': 'New round started!',
                            'round_status': game_state.get_round_status(),
                            'players': game_state.get_players_data()
                        }, namespace='/')
                    elif game_state.game_state == 'lobby':
                        # If game ended and we're back in lobby, reset first_round_started
                        first_round_started = False
                
                # Only run game logic when in playing state
                if game_state.game_state == 'playing':
                    # Update ghosts
                    game_state.update_ghosts()
                    
                    # Check ghost collisions with players
                    collisions = game_state.check_ghost_collisions()
                    
                    if collisions:
                        for collision in collisions:
                            if collision['type'] == 'ghost_eaten':
                                logger.info(f"[GHOST_EATEN] Player {collision['player_id']} ate ghost {collision['ghost_id']}! Score: {collision['score']}")
                            elif collision['type'] == 'player_caught':
                                logger.info(f"[PLAYER_CAUGHT] Ghost {collision['ghost_id']} caught player {collision['player_id']}! Lives: {collision['lives']}")
                            elif collision['type'] == 'player_died':
                                logger.info(f"[PLAYER_DIED] Player {collision['player_id']} died to ghost {collision['ghost_id']}! Now spectator")
                            
                            socketio.emit('player_caught', collision, namespace='/')
                    
                    # Check for power mode changes and broadcast
                    for player_id, player in game_state.players.items():
                        if hasattr(player, '_last_power_mode'):
                            if player._last_power_mode != player.power_mode:
                                logger.info(f"[POWER] Player {player_id} power mode changed: {player.power_mode} (timer: {player.power_timer})")
                                socketio.emit('power_mode_changed', {
                                    'player_id': player_id,
                                    'power_mode': player.power_mode,
                                    'power_timer': player.power_timer
                                }, namespace='/')
                        player._last_power_mode = player.power_mode
                    
                    # Broadcast ghost positions
                    if game_state.ghosts:
                        ghost_update_counter += 1
                        socketio.emit('ghosts_updated', {
                            'ghosts': game_state.get_ghosts_data()
                        }, namespace='/')
                        # Only log ghost updates every 50 iterations (5 seconds at 10 FPS)
                        if ghost_update_counter % 50 == 0:
                            logger.debug(f"Ghost update #{ghost_update_counter} sent to {len(game_state.players)} players")
            except Exception as e:
                logger.error(f"[ERROR] Error in game loop: {e}")
                # don't return/continue before tick() runs; we'll fall through to finally
            finally:
                # Only advance timers/state when game is playing
                if game_state.game_state == 'playing':
                    try:
                        game_state.tick()
                    except Exception as tick_err:
                        logger.error(f"[ERROR] Error while ticking game state: {tick_err}")

            # Performance monitoring
            frame_end_time = time.time()
            frame_time = frame_end_time - frame_start_time if 'frame_start_time' in locals() else 0.1
            perf_monitor.record_frame_time(frame_time)
            
            # Record system stats less frequently (every 10 frames)
            if perf_monitor.frame_count % 10 == 0:
                perf_monitor.record_system_stats(len(game_state.players))
            
            # Log performance every 5 seconds
            if perf_monitor.should_log():
                perf_monitor.log_performance()
            
            # Sleep for game tick (10 FPS for server updates)
            time.sleep(0.1)
            frame_start_time = time.time()

if __name__ == '__main__':
    print("[STARTUP] Starting MMO Pacman server...")
    print("[STARTUP] Navigate to http://localhost:5000 to play")
    
    # Start the game loop as a Socket.IO background task to avoid blocking
    socketio.start_background_task(game_loop)
    print("[STARTUP] Game loop started (background task)")

    # Run the server without the Werkzeug reloader (reloader can spawn multiple processes/threads
    # and cause problems in some development environments like VS Code). Turn off debug to
    # prevent the reloader from running; you can enable debug separately if needed.
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, use_reloader=False)