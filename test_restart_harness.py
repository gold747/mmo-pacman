#!/usr/bin/env python3
"""
Test Harness for MMO Pacman Game Restart Functionality

This test verifies that:
1. Game can be started successfully
2. Game finishes properly (either by time or elimination)
3. Players return to lobby state
4. Second game can be started without issues
5. All players are retained through multiple game cycles
"""

import asyncio
import json
import time
import logging
from datetime import datetime
import socketio
import requests
from typing import Dict, List, Set

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'restart_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class GameRestartTester:
    def __init__(self, server_url="http://localhost:8080", num_players=5):
        self.server_url = server_url
        self.num_players = num_players
        self.players = {}  # player_id -> TestPlayer
        self.host_id = None
        self.game_cycles_completed = 0
        self.target_cycles = 3  # Test 3 complete game cycles
        
        # Test state tracking
        self.lobby_states = []
        self.game_states = []
        self.round_end_states = []
        self.errors = []
        
    async def run_test(self):
        """Run the complete restart test suite"""
        logger.info(f"🚀 Starting Game Restart Test with {self.num_players} players")
        logger.info(f"Target: {self.target_cycles} complete game cycles")
        
        try:
            # Step 1: Create and connect all players
            await self._create_players()
            await asyncio.sleep(2)  # Allow connections to stabilize
            
            # Step 2: Run multiple game cycles
            for cycle in range(self.target_cycles):
                logger.info(f"\n{'='*50}")
                logger.info(f"🎮 GAME CYCLE {cycle + 1}/{self.target_cycles}")
                logger.info(f"{'='*50}")
                
                success = await self._run_game_cycle(cycle + 1)
                if not success:
                    logger.error(f"❌ Game cycle {cycle + 1} failed!")
                    break
                    
                self.game_cycles_completed += 1
                logger.info(f"✅ Game cycle {cycle + 1} completed successfully")
                
                # Wait between cycles
                if cycle < self.target_cycles - 1:
                    logger.info("⏳ Waiting 3 seconds before next cycle...")
                    await asyncio.sleep(3)
            
            # Step 3: Generate test report
            await self._generate_report()
            
        except Exception as e:
            logger.error(f"❌ Test failed with exception: {e}")
            self.errors.append(f"Test exception: {e}")
        finally:
            await self._cleanup()
    
    async def _create_players(self):
        """Create and connect all test players"""
        logger.info(f"👥 Creating {self.num_players} test players...")
        
        tasks = []
        for i in range(self.num_players):
            player_name = f"TestPlayer{i+1}"
            is_host = (i == 0)  # First player is host
            
            player = TestPlayer(
                player_id=f"player_{i+1}",
                name=player_name,
                server_url=self.server_url,
                is_host=is_host
            )
            
            self.players[player.player_id] = player
            if is_host:
                self.host_id = player.player_id
                
            tasks.append(player.connect())
        
        # Connect all players
        await asyncio.gather(*tasks)
        
        # Verify all connected
        connected_count = sum(1 for p in self.players.values() if p.connected)
        logger.info(f"✅ {connected_count}/{self.num_players} players connected")
        
        if connected_count != self.num_players:
            raise Exception(f"Only {connected_count}/{self.num_players} players connected")
    
    async def _run_game_cycle(self, cycle_num):
        """Run a complete game cycle: lobby -> game -> round end -> back to lobby"""
        try:
            # Phase 1: Verify lobby state
            logger.info(f"📋 Phase 1: Verifying lobby state (Cycle {cycle_num})")
            lobby_success = await self._verify_lobby_state(cycle_num)
            if not lobby_success:
                return False
            
            # Phase 2: Start game
            logger.info(f"🎯 Phase 2: Starting game (Cycle {cycle_num})")
            start_success = await self._start_game()
            if not start_success:
                return False
            
            # Phase 3: Wait for game to finish
            logger.info(f"⏱️ Phase 3: Waiting for round to complete (Cycle {cycle_num})")
            finish_success = await self._wait_for_round_end()
            if not finish_success:
                return False
            
            # Phase 4: Handle restart
            logger.info(f"🔄 Phase 4: Handling restart (Cycle {cycle_num})")
            restart_success = await self._handle_restart()
            if not restart_success:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Game cycle {cycle_num} failed: {e}")
            self.errors.append(f"Cycle {cycle_num} error: {e}")
            return False
    
    async def _verify_lobby_state(self, cycle_num):
        """Verify all players are in lobby state"""
        lobby_players = []
        
        for player_id, player in self.players.items():
            if player.connected and player.game_state == 'lobby':
                lobby_players.append(player_id)
        
        self.lobby_states.append({
            'cycle': cycle_num,
            'timestamp': datetime.now().isoformat(),
            'players_in_lobby': len(lobby_players),
            'total_players': len(self.players),
            'lobby_players': lobby_players
        })
        
        success = len(lobby_players) == len(self.players)
        if success:
            logger.info(f"✅ All {len(lobby_players)} players in lobby state")
        else:
            logger.error(f"❌ Only {len(lobby_players)}/{len(self.players)} players in lobby")
            
        return success
    
    async def _start_game(self):
        """Have the host start the game"""
        if not self.host_id or self.host_id not in self.players:
            logger.error("❌ No valid host found")
            return False
        
        host_player = self.players[self.host_id]
        if not host_player.connected:
            logger.error("❌ Host is not connected")
            return False
        
        # Clear game started flags
        for player in self.players.values():
            player.game_started = False
            player.round_ended = False
        
        # Host starts the game
        await host_player.start_game()
        
        # Wait for game_started event on all players
        max_wait = 10  # seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            started_count = sum(1 for p in self.players.values() if p.game_started)
            if started_count == len(self.players):
                logger.info(f"✅ Game started successfully - all {started_count} players received game_started")
                return True
            
            await asyncio.sleep(0.5)
        
        # Timeout - check what happened
        started_count = sum(1 for p in self.players.values() if p.game_started)
        logger.error(f"❌ Game start timeout - only {started_count}/{len(self.players)} players received game_started")
        return False
    
    async def _wait_for_round_end(self):
        """Wait for the round to end naturally or force end for testing"""
        # For testing, we'll wait a shorter time then force end
        test_round_duration = 15  # seconds for quick testing
        
        logger.info(f"⏳ Waiting up to {test_round_duration} seconds for round to end...")
        start_time = time.time()
        
        while time.time() - start_time < test_round_duration:
            ended_count = sum(1 for p in self.players.values() if p.round_ended)
            if ended_count == len(self.players):
                logger.info(f"✅ Round ended naturally - all {ended_count} players received round_ended")
                return True
            
            await asyncio.sleep(1)
        
        # Force end by eliminating all players or waiting for time
        logger.info("⏰ Test timeout reached, round should end soon...")
        
        # Wait a bit more for natural end
        extra_wait = 10
        while time.time() - start_time < test_round_duration + extra_wait:
            ended_count = sum(1 for p in self.players.values() if p.round_ended)
            if ended_count == len(self.players):
                logger.info(f"✅ Round ended - all {ended_count} players received round_ended")
                return True
            await asyncio.sleep(1)
        
        ended_count = sum(1 for p in self.players.values() if p.round_ended)
        logger.error(f"❌ Round end timeout - only {ended_count}/{len(self.players)} players received round_ended")
        return False
    
    async def _handle_restart(self):
        """Handle the restart process"""
        # Wait a moment for players to settle in round end state
        await asyncio.sleep(2)
        
        # Host should restart the game
        host_player = self.players[self.host_id]
        if not host_player.connected:
            logger.error("❌ Host disconnected during restart")
            return False
        
        # Clear flags for next cycle
        for player in self.players.values():
            player.game_started = False
            player.round_ended = False
        
        await host_player.restart_game()
        
        # Wait for players to return to lobby state
        max_wait = 10
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            lobby_count = sum(1 for p in self.players.values() if p.game_state == 'lobby')
            if lobby_count == len(self.players):
                logger.info(f"✅ Restart successful - all {lobby_count} players back in lobby")
                return True
            
            await asyncio.sleep(0.5)
        
        lobby_count = sum(1 for p in self.players.values() if p.game_state == 'lobby')
        logger.error(f"❌ Restart failed - only {lobby_count}/{len(self.players)} players in lobby")
        return False
    
    async def _generate_report(self):
        """Generate comprehensive test report"""
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 GAME RESTART TEST REPORT")
        logger.info(f"{'='*60}")
        
        # Overall results
        success_rate = (self.game_cycles_completed / self.target_cycles) * 100
        logger.info(f"✅ Completed Cycles: {self.game_cycles_completed}/{self.target_cycles} ({success_rate:.1f}%)")
        logger.info(f"❌ Errors: {len(self.errors)}")
        
        # Player retention
        final_connected = sum(1 for p in self.players.values() if p.connected)
        retention_rate = (final_connected / self.num_players) * 100
        logger.info(f"👥 Player Retention: {final_connected}/{self.num_players} ({retention_rate:.1f}%)")
        
        # Detailed results
        if self.errors:
            logger.error("\n🚨 ERRORS ENCOUNTERED:")
            for i, error in enumerate(self.errors, 1):
                logger.error(f"  {i}. {error}")
        
        # Lobby state analysis
        logger.info(f"\n📋 LOBBY STATE ANALYSIS:")
        for state in self.lobby_states:
            logger.info(f"  Cycle {state['cycle']}: {state['players_in_lobby']}/{state['total_players']} players in lobby")
        
        # Final verdict
        if self.game_cycles_completed == self.target_cycles and len(self.errors) == 0:
            logger.info(f"\n🎉 TEST PASSED: All {self.target_cycles} game cycles completed successfully!")
        else:
            logger.error(f"\n💥 TEST FAILED: Only {self.game_cycles_completed}/{self.target_cycles} cycles completed with {len(self.errors)} errors")
    
    async def _cleanup(self):
        """Cleanup all connections"""
        logger.info("🧹 Cleaning up connections...")
        
        tasks = []
        for player in self.players.values():
            if player.connected:
                tasks.append(player.disconnect())
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info("✅ Cleanup completed")


class TestPlayer:
    def __init__(self, player_id, name, server_url, is_host=False):
        self.player_id = player_id
        self.name = name
        self.server_url = server_url
        self.is_host = is_host
        
        # Connection state
        self.sio = socketio.AsyncClient()
        self.connected = False
        
        # Game state
        self.game_state = 'disconnected'  # 'lobby', 'playing', 'round_end'
        self.game_started = False
        self.round_ended = False
        self.score = 0
        self.lives = 3
        
        # Setup event handlers
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        @self.sio.event
        async def connect():
            logger.info(f"🔗 {self.name} connected")
            self.connected = True
        
        @self.sio.event
        async def disconnect():
            logger.info(f"🔌 {self.name} disconnected")
            self.connected = False
            self.game_state = 'disconnected'
        
        @self.sio.event
        async def lobby_joined(data):
            logger.info(f"🎮 {self.name} joined lobby")
            self.game_state = 'lobby'
        
        @self.sio.event
        async def game_started(data):
            logger.info(f"🚀 {self.name} received game_started")
            self.game_started = True
            self.game_state = 'playing'
        
        @self.sio.event
        async def round_ended(data):
            logger.info(f"🏁 {self.name} received round_ended: {data.get('message', 'N/A')}")
            self.round_ended = True
            self.game_state = 'round_end'
        
        @self.sio.event
        async def player_caught(data):
            self.lives = data.get('lives', self.lives)
            logger.debug(f"👻 {self.name} caught by ghost! Lives: {self.lives}")
        
        @self.sio.event
        async def error(data):
            logger.error(f"⚠️ {self.name} received error: {data}")
    
    async def connect(self):
        """Connect to the server and join the game"""
        try:
            await self.sio.connect(self.server_url)
            await asyncio.sleep(0.5)  # Allow connection to stabilize
            
            # Join the game
            await self.sio.emit('join_game', {'name': self.name})
            await asyncio.sleep(0.5)  # Allow join to process
            
            return True
        except Exception as e:
            logger.error(f"❌ {self.name} failed to connect: {e}")
            return False
    
    async def start_game(self):
        """Start the game (host only)"""
        if not self.is_host:
            logger.warning(f"⚠️ {self.name} is not host, cannot start game")
            return False
        
        try:
            await self.sio.emit('start_game')
            logger.info(f"🎯 {self.name} (host) started the game")
            return True
        except Exception as e:
            logger.error(f"❌ {self.name} failed to start game: {e}")
            return False
    
    async def restart_game(self):
        """Restart the game (host only)"""
        if not self.is_host:
            logger.warning(f"⚠️ {self.name} is not host, cannot restart game")
            return False
        
        try:
            await self.sio.emit('restart_game')
            logger.info(f"🔄 {self.name} (host) restarted the game")
            # Reset state for new game
            self.game_state = 'lobby'
            return True
        except Exception as e:
            logger.error(f"❌ {self.name} failed to restart game: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from the server"""
        try:
            if self.connected:
                await self.sio.disconnect()
        except Exception as e:
            logger.error(f"❌ {self.name} disconnect error: {e}")


async def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='MMO Pacman Restart Test Harness')
    parser.add_argument('--server', default='http://localhost:8080', help='Server URL')
    parser.add_argument('--players', type=int, default=5, help='Number of test players')
    parser.add_argument('--cycles', type=int, default=3, help='Number of game cycles to test')
    
    args = parser.parse_args()
    
    # Verify server is running
    try:
        response = requests.get(args.server, timeout=5)
        logger.info(f"✅ Server is accessible at {args.server}")
    except Exception as e:
        logger.error(f"❌ Cannot reach server at {args.server}: {e}")
        return
    
    # Run the test
    tester = GameRestartTester(
        server_url=args.server,
        num_players=args.players
    )
    tester.target_cycles = args.cycles
    
    await tester.run_test()


if __name__ == '__main__':
    asyncio.run(main())