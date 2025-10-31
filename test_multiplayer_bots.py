#!/usr/bin/env python3
"""
MMO Pacman Bot Testing Tool

This script creates multiple automated bot clients to test multiplayer functionality.
Each bot will connect, join the game, and simulate random movement.
"""

import socketio
import time
import random
import threading
import asyncio
import logging
from datetime import datetime

class PacmanBot:
    def __init__(self, bot_id, server_url="http://localhost:5000"):
        self.bot_id = bot_id
        self.bot_name = f"Bot_{bot_id:02d}"
        self.server_url = server_url
        self.sio = socketio.Client()
        self.connected = False
        self.in_game = False
        self.position = {'x': 0, 'y': 0}
        self.score = 0
        self.lives = 3
        self.is_spectator = False
        self.directions = ['up', 'down', 'left', 'right']
        self.current_direction = random.choice(self.directions)
        self.setup_event_handlers()
        
    def setup_event_handlers(self):
        @self.sio.event
        def connect():
            print(f"[{self.bot_name}] Connected to server")
            self.connected = True
            # Join game after a short delay
            time.sleep(random.uniform(0.1, 1.0))
            self.join_game()
            
        @self.sio.event  
        def disconnect():
            print(f"[{self.bot_name}] Disconnected from server")
            self.connected = False
            self.in_game = False
            
        @self.sio.event
        def game_joined(data):
            print(f"[{self.bot_name}] Joined game! Spawn position: {data.get('spawn_position')}")
            self.in_game = True
            self.position = data.get('spawn_position', {'x': 0, 'y': 0})
            
        @self.sio.event
        def join_failed(data):
            print(f"[{self.bot_name}] Failed to join game: {data.get('message')}")
            
        @self.sio.event
        def player_caught(data):
            if data.get('player_id') == self.sio.sid:
                if data.get('type') == 'player_died':
                    print(f"[{self.bot_name}] Died! Entering spectator mode")
                    self.is_spectator = True
                elif data.get('type') == 'player_caught':
                    print(f"[{self.bot_name}] Caught by ghost! Lives: {data.get('lives')}")
                    self.lives = data.get('lives', self.lives)
                    if 'respawn_pos' in data:
                        self.position = data['respawn_pos']
                        
        @self.sio.event
        def round_started(data):
            print(f"[{self.bot_name}] New round started!")
            self.is_spectator = False
            self.lives = 3
            
        @self.sio.event
        def game_ended(data):
            print(f"[{self.bot_name}] Game ended! Leaderboard shown")
            
        @self.sio.event
        def player_moved(data):
            # Update our position if it's us
            if data.get('player_id') == self.sio.sid:
                self.position = data.get('position', self.position)
                
        @self.sio.event
        def pellet_collected(data):
            if data.get('player_id') == self.sio.sid:
                self.score = data.get('score', self.score)
                print(f"[{self.bot_name}] Collected pellet! Score: {self.score}")
    
    def join_game(self):
        if self.connected:
            print(f"[{self.bot_name}] Attempting to join game...")
            self.sio.emit('join_game', {'name': self.bot_name})
    
    def move_randomly(self):
        """Make random moves to simulate player behavior"""
        while self.connected:
            try:
                if self.in_game and not self.is_spectator:
                    # Occasionally change direction (20% chance)
                    if random.random() < 0.2:
                        self.current_direction = random.choice(self.directions)
                    
                    # Send move command
                    self.sio.emit('player_move', {'direction': self.current_direction})
                    
                # Move every 200-500ms for realistic gameplay
                time.sleep(random.uniform(0.2, 0.5))
                
            except Exception as e:
                print(f"[{self.bot_name}] Error in movement: {e}")
                break
    
    def start(self):
        """Connect and start the bot"""
        try:
            print(f"[{self.bot_name}] Starting bot...")
            self.sio.connect(self.server_url)
            
            # Start movement in a separate thread
            movement_thread = threading.Thread(target=self.move_randomly, daemon=True)
            movement_thread.start()
            
            return True
        except Exception as e:
            print(f"[{self.bot_name}] Failed to start: {e}")
            return False
    
    def stop(self):
        """Stop the bot and disconnect"""
        print(f"[{self.bot_name}] Stopping bot...")
        if self.connected:
            self.sio.disconnect()

class BotManager:
    def __init__(self, server_url="http://localhost:5000", parallel_startup=True, fast_mode=False):
        self.server_url = server_url
        self.bots = []
        self.parallel_startup = parallel_startup
        self.fast_mode = fast_mode
        
    def create_bots(self, count):
        """Create and start multiple bots"""
        startup_mode = "parallel" if self.parallel_startup else "sequential"
        print(f"Creating {count} bots in {startup_mode} mode...")
        
        # Create all bots first
        for i in range(count):
            bot = PacmanBot(i + 1, self.server_url)
            self.bots.append(bot)
        
        if self.parallel_startup:
            self._start_bots_parallel()
        else:
            self._start_bots_sequential()
    
    def _start_bots_parallel(self):
        """Start all bots in parallel using threads"""
        print(f"Starting {len(self.bots)} bots in parallel...")
        start_time = time.time()
        
        # Start all bots in parallel using threads
        start_threads = []
        for i, bot in enumerate(self.bots):
            thread = threading.Thread(target=self._start_bot_with_delay, args=(bot, i, self.fast_mode), daemon=True)
            start_threads.append(thread)
            thread.start()
        
        # Wait for all connection attempts to complete (max 15 seconds)
        for thread in start_threads:
            thread.join(timeout=15)
        
        # Count successful connections
        connected_count = sum(1 for bot in self.bots if bot.connected)
        elapsed_time = time.time() - start_time
        print(f"Parallel startup complete in {elapsed_time:.1f}s: {connected_count}/{len(self.bots)} bots connected!")
    
    def _start_bots_sequential(self):
        """Start bots one by one with delays"""
        print(f"Starting {len(self.bots)} bots sequentially...")
        start_time = time.time()
        
        for i, bot in enumerate(self.bots):
            if bot.start():
                print(f"Bot {i + 1} ({bot.bot_name}) connected successfully")
            else:
                print(f"Bot {i + 1} ({bot.bot_name}) failed to connect")
                
            # Small delay between bot connections
            time.sleep(random.uniform(0.1, 0.3))
        
        connected_count = sum(1 for bot in self.bots if bot.connected)
        elapsed_time = time.time() - start_time
        print(f"Sequential startup complete in {elapsed_time:.1f}s: {connected_count}/{len(self.bots)} bots connected!")
    
    def _start_bot_with_delay(self, bot, index, fast_mode=False):
        """Helper method to start a bot with a small random delay"""
        # Adjust delay based on mode
        if fast_mode:
            time.sleep(random.uniform(0.01, 0.05))  # Minimal delay for fast mode
        else:
            time.sleep(random.uniform(0.05, 0.2))   # Standard delay
        
        try:
            if bot.start():
                print(f"Bot {index + 1} ({bot.bot_name}) connected successfully")
            else:
                print(f"Bot {index + 1} ({bot.bot_name}) failed to connect")
        except Exception as e:
            print(f"Bot {index + 1} ({bot.bot_name}) startup error: {e}")
        
    def stop_all_bots(self):
        """Stop all bots"""
        print("Stopping all bots...")
        for bot in self.bots:
            bot.stop()
        self.bots.clear()
        print("All bots stopped")
        
    def get_bot_status(self):
        """Get status of all bots"""
        connected = sum(1 for bot in self.bots if bot.connected)
        in_game = sum(1 for bot in self.bots if bot.in_game)
        spectators = sum(1 for bot in self.bots if bot.is_spectator)
        
        return {
            'total_bots': len(self.bots),
            'connected': connected,
            'in_game': in_game,
            'spectators': spectators
        }

def main():
    """Main testing function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='MMO Pacman Bot Tester')
    parser.add_argument('--bots', '-b', type=int, default=5, 
                        help='Number of bots to create (default: 5)')
    parser.add_argument('--url', '-u', type=str, default='http://localhost:5000',
                        help='Server URL (default: http://localhost:5000)')
    parser.add_argument('--duration', '-d', type=int, default=60,
                        help='Test duration in seconds (default: 60)')
    parser.add_argument('--sequential', '-s', action='store_true',
                        help='Start bots sequentially instead of parallel (default: parallel)')
    parser.add_argument('--fast', '-f', action='store_true',
                        help='Fast parallel startup with minimal delays')
    
    args = parser.parse_args()
    
    startup_mode = "Sequential" if args.sequential else "Parallel"
    speed_mode = " (Fast)" if args.fast else ""
    
    print("=" * 50)
    print("MMO PACMAN MULTIPLAYER BOT TESTER")
    print("=" * 50)
    print(f"Server: {args.url}")
    print(f"Bots: {args.bots}")
    print(f"Duration: {args.duration} seconds")
    print(f"Startup: {startup_mode}{speed_mode}")
    print("=" * 50)
    
    manager = BotManager(args.url, parallel_startup=not args.sequential, fast_mode=args.fast)
    
    try:
        # Create and start bots
        manager.create_bots(args.bots)
        
        # Monitor bots for specified duration
        start_time = time.time()
        while time.time() - start_time < args.duration:
            status = manager.get_bot_status()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                  f"Bots: {status['connected']}/{status['total_bots']} connected, "
                  f"{status['in_game']} playing, {status['spectators']} spectating")
            
            time.sleep(5)  # Status update every 5 seconds
            
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Test error: {e}")
    finally:
        manager.stop_all_bots()
        print("Test completed!")

if __name__ == "__main__":
    main()