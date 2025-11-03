#!/usr/bin/env python3
"""
MMO Pacman Bot Simulation Script
Simulates multiple players connecting and playing the game
"""

import asyncio
import random
import time
import json
import logging
from datetime import datetime
import socketio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [BOT] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

class PacmanBot:
    def __init__(self, bot_id, server_url='http://localhost:5000'):
        self.bot_id = bot_id
        self.name = f"Bot{bot_id:02d}"
        self.server_url = server_url
        self.sio = socketio.AsyncClient()
        self.connected = False
        self.in_game = False
        self.player_data = {}
        self.game_state = 'disconnected'
        self.last_move_time = 0
        self.move_directions = ['up', 'down', 'left', 'right']
        self.current_direction = random.choice(self.move_directions)
        self.movement_pattern = 'random'  # 'random', 'aggressive', 'cautious'
        self.stats = {
            'moves_sent': 0,
            'pellets_eaten': 0,
            'deaths': 0,
            'score': 0
        }
        
        # Set up event handlers
        self.setup_event_handlers()
    
    def setup_event_handlers(self):
        @self.sio.event
        async def connect():
            logger.info(f"{self.name} connected to server")
            self.connected = True
            # Join the game
            await self.sio.emit('join_game', {'name': self.name})
        
        @self.sio.event
        async def disconnect():
            logger.info(f"{self.name} disconnected from server")
            self.connected = False
            self.in_game = False
        
        @self.sio.event
        async def game_joined(data):
            logger.info(f"{self.name} joined game successfully")
            self.in_game = True
            self.game_state = 'lobby'
        
        @self.sio.event
        async def game_started(data):
            logger.info(f"{self.name} game started")
            self.game_state = 'playing'
            self.player_data = data.get('players', {}).get(self.sio.sid, {})
        
        @self.sio.event
        async def round_ended(data):
            logger.info(f"{self.name} round ended: {data.get('reason', 'unknown')}")
            self.game_state = 'round_ended'
        
        @self.sio.event
        async def player_moved(data):
            # Update our position if it's us
            if data.get('player_id') == self.sio.sid:
                self.player_data.update({
                    'position': data.get('position', {}),
                    'direction': data.get('direction', self.current_direction)
                })
        
        @self.sio.event
        async def player_caught(data):
            if data.get('player_id') == self.sio.sid:
                if data.get('type') == 'player_died':
                    logger.info(f"{self.name} died and became spectator")
                    self.stats['deaths'] += 1
                    self.game_state = 'spectator'
        
        @self.sio.event
        async def pellet_eaten(data):
            if data.get('player_id') == self.sio.sid:
                self.stats['pellets_eaten'] += 1
                self.stats['score'] = data.get('score', self.stats['score'])
        
        @self.sio.event
        async def error(data):
            logger.warning(f"{self.name} received error: {data.get('message', 'unknown error')}")
    
    async def connect_to_server(self):
        """Connect to the game server"""
        try:
            await self.sio.connect(self.server_url)
            return True
        except Exception as e:
            logger.error(f"{self.name} failed to connect: {e}")
            return False
    
    async def disconnect_from_server(self):
        """Disconnect from the game server"""
        if self.connected:
            await self.sio.disconnect()
    
    async def send_movement(self):
        """Send a movement command"""
        if not self.in_game or self.game_state != 'playing':
            return
        
        current_time = time.time()
        if current_time - self.last_move_time < 0.2:  # Rate limit movements
            return
        
        # Choose movement direction based on bot behavior pattern
        direction = self.choose_movement_direction()
        
        try:
            await self.sio.emit('move_player', {'direction': direction})
            self.current_direction = direction
            self.last_move_time = current_time
            self.stats['moves_sent'] += 1
        except Exception as e:
            logger.error(f"{self.name} failed to send movement: {e}")
    
    def choose_movement_direction(self):
        """Choose movement direction based on bot personality"""
        if self.movement_pattern == 'random':
            # 70% chance to continue in current direction, 30% chance to change
            if random.random() < 0.7:
                return self.current_direction
            else:
                return random.choice(self.move_directions)
        
        elif self.movement_pattern == 'aggressive':
            # Change direction more frequently (aggressive exploration)
            if random.random() < 0.5:
                return self.current_direction
            else:
                return random.choice(self.move_directions)
        
        elif self.movement_pattern == 'cautious':
            # Stick to current direction more often
            if random.random() < 0.9:
                return self.current_direction
            else:
                return random.choice(self.move_directions)
        
        return random.choice(self.move_directions)
    
    async def bot_behavior_loop(self):
        """Main bot behavior loop"""
        while self.connected:
            try:
                if self.game_state == 'playing':
                    # Send movement commands
                    await self.send_movement()
                    
                    # Random delay between actions
                    await asyncio.sleep(random.uniform(0.1, 0.3))
                
                elif self.game_state == 'lobby':
                    # Wait in lobby
                    await asyncio.sleep(1)
                
                elif self.game_state == 'round_ended':
                    # Wait for next round
                    await asyncio.sleep(2)
                
                elif self.game_state == 'spectator':
                    # Wait as spectator
                    await asyncio.sleep(5)
                
                else:
                    await asyncio.sleep(1)
            
            except Exception as e:
                logger.error(f"{self.name} behavior loop error: {e}")
                await asyncio.sleep(1)
    
    def get_stats(self):
        """Get bot statistics"""
        return {
            'name': self.name,
            'connected': self.connected,
            'game_state': self.game_state,
            'stats': self.stats.copy()
        }

class BotManager:
    def __init__(self, num_bots=30, server_url='http://localhost:5000'):
        self.num_bots = num_bots
        self.server_url = server_url
        self.bots = []
        self.running = False
        self.start_time = None
        
    async def create_bots(self):
        """Create bot instances"""
        logger.info(f"Creating {self.num_bots} bots...")
        
        # Create bots with different behavior patterns
        behavior_patterns = ['random', 'aggressive', 'cautious']
        
        for i in range(self.num_bots):
            bot = PacmanBot(i + 1, self.server_url)
            # Assign behavior pattern
            bot.movement_pattern = behavior_patterns[i % len(behavior_patterns)]
            self.bots.append(bot)
        
        logger.info(f"Created {len(self.bots)} bots")
    
    async def connect_all_bots(self):
        """Connect all bots to the server"""
        logger.info("Connecting all bots...")
        
        connection_tasks = []
        for bot in self.bots:
            connection_tasks.append(bot.connect_to_server())
        
        # Connect bots in batches to avoid overwhelming the server
        batch_size = 5
        for i in range(0, len(connection_tasks), batch_size):
            batch = connection_tasks[i:i + batch_size]
            results = await asyncio.gather(*batch, return_exceptions=True)
            
            # Log connection results
            for j, result in enumerate(results):
                bot_index = i + j
                if bot_index < len(self.bots):
                    if isinstance(result, Exception):
                        logger.error(f"Bot {bot_index + 1} connection failed: {result}")
                    elif result:
                        logger.info(f"Bot {bot_index + 1} connected successfully")
            
            # Small delay between batches
            if i + batch_size < len(connection_tasks):
                await asyncio.sleep(1)
        
        connected_count = sum(1 for bot in self.bots if bot.connected)
        logger.info(f"{connected_count}/{len(self.bots)} bots connected")
    
    async def start_bot_behaviors(self):
        """Start behavior loops for all connected bots"""
        logger.info("Starting bot behavior loops...")
        
        behavior_tasks = []
        for bot in self.bots:
            if bot.connected:
                behavior_tasks.append(asyncio.create_task(bot.bot_behavior_loop()))
        
        logger.info(f"Started {len(behavior_tasks)} bot behavior loops")
        return behavior_tasks
    
    async def monitor_performance(self):
        """Monitor bot and server performance"""
        logger.info("Starting performance monitoring...")
        
        while self.running:
            try:
                # Count bot states
                states = {}
                total_moves = 0
                total_pellets = 0
                total_deaths = 0
                
                for bot in self.bots:
                    if bot.connected:
                        state = bot.game_state
                        states[state] = states.get(state, 0) + 1
                        total_moves += bot.stats['moves_sent']
                        total_pellets += bot.stats['pellets_eaten']
                        total_deaths += bot.stats['deaths']
                
                # Log performance metrics
                uptime = time.time() - self.start_time if self.start_time else 0
                logger.info(f"[MONITOR] Uptime: {uptime:.1f}s, "
                           f"Connected: {sum(1 for b in self.bots if b.connected)}/{len(self.bots)}, "
                           f"States: {states}, "
                           f"Total moves: {total_moves}, pellets: {total_pellets}, deaths: {total_deaths}")
                
                await asyncio.sleep(10)  # Monitor every 10 seconds
            
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(5)
    
    async def run_simulation(self, duration_seconds=None):
        """Run the bot simulation"""
        logger.info(f"Starting bot simulation with {self.num_bots} bots")
        self.start_time = time.time()
        self.running = True
        
        try:
            # Create and connect bots
            await self.create_bots()
            await self.connect_all_bots()
            
            # Start bot behaviors and monitoring
            behavior_tasks = await self.start_bot_behaviors()
            monitor_task = asyncio.create_task(self.monitor_performance())
            
            # Run simulation
            if duration_seconds:
                logger.info(f"Running simulation for {duration_seconds} seconds")
                await asyncio.sleep(duration_seconds)
            else:
                logger.info("Running simulation indefinitely (Ctrl+C to stop)")
                try:
                    await asyncio.gather(*behavior_tasks, monitor_task)
                except KeyboardInterrupt:
                    logger.info("Simulation interrupted by user")
        
        except Exception as e:
            logger.error(f"Simulation error: {e}")
        
        finally:
            self.running = False
            await self.cleanup()
    
    async def cleanup(self):
        """Clean up bot connections"""
        logger.info("Cleaning up bot connections...")
        
        disconnect_tasks = []
        for bot in self.bots:
            if bot.connected:
                disconnect_tasks.append(bot.disconnect_from_server())
        
        if disconnect_tasks:
            await asyncio.gather(*disconnect_tasks, return_exceptions=True)
        
        logger.info("Bot simulation cleanup completed")

async def main():
    """Main simulation entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='MMO Pacman Bot Simulation')
    parser.add_argument('--bots', type=int, default=30, help='Number of bots to simulate (default: 30)')
    parser.add_argument('--server', type=str, default='http://localhost:5000', help='Server URL')
    parser.add_argument('--duration', type=int, help='Simulation duration in seconds (default: run indefinitely)')
    
    args = parser.parse_args()
    
    bot_manager = BotManager(num_bots=args.bots, server_url=args.server)
    
    try:
        await bot_manager.run_simulation(duration_seconds=args.duration)
    except KeyboardInterrupt:
        logger.info("Simulation stopped by user")
    except Exception as e:
        logger.error(f"Simulation failed: {e}")

if __name__ == '__main__':
    asyncio.run(main())