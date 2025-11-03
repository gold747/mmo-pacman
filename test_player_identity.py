#!/usr/bin/env python3
"""
Player Identity Test - Tests for the specific bug where:
1. Two players (A and B) join lobby
2. After restart, host sees only A, B sees both A and B
3. When game starts, both browsers control player A (B disappears)

This test reproduces the exact scenario described by the user.
"""

import asyncio
import socketio
import logging
from datetime import datetime
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PlayerIdentityTester:
    def __init__(self, server_url="http://localhost:8080"):
        self.server_url = server_url
        self.player_a = None
        self.player_b = None
        
    async def run_test(self):
        """Run the player identity test"""
        logger.info("🧪 Starting Player Identity Test...")
        logger.info("Testing scenario: 2 players, restart, check lobby consistency & player identities")
        
        try:
            # Step 1: Create two players (A = host, B = regular player)
            await self._create_players()
            
            # Step 2: Start first game
            logger.info("\n📋 Phase 1: Starting first game...")
            await self._start_first_game()
            
            # Step 3: Restart the game  
            logger.info("\n🔄 Phase 2: Restarting game...")
            await self._restart_game()
            
            # Step 4: Check lobby consistency
            logger.info("\n🔍 Phase 3: Checking lobby consistency...")
            await self._check_lobby_consistency()
            
            # Step 5: Start second game and verify player identities
            logger.info("\n🎮 Phase 4: Starting second game and checking player identities...")
            await self._start_second_game_and_check_identities()
            
            logger.info("\n✅ Player Identity Test Completed!")
            
        except Exception as e:
            logger.error(f"\n❌ Test failed: {e}")
        finally:
            await self._cleanup()
    
    async def _create_players(self):
        """Create Player A (host) and Player B"""
        logger.info("👥 Creating Player A (host) and Player B...")
        
        # Create Player A
        self.player_a = IdentityTestPlayer("PlayerA", is_host=True)
        await self.player_a.connect(self.server_url)
        await asyncio.sleep(0.5)
        
        # Create Player B  
        self.player_b = IdentityTestPlayer("PlayerB", is_host=False)
        await self.player_b.connect(self.server_url)
        await asyncio.sleep(0.5)
        
        logger.info(f"✅ Player A (host): {self.player_a.player_id}")
        logger.info(f"✅ Player B: {self.player_b.player_id}")
    
    async def _start_first_game(self):
        """Start the first game"""
        await self.player_a.start_game()
        await asyncio.sleep(2)  # Let game run briefly
        
        logger.info(f"🎮 First game started. PlayerA sees players: {self.player_a.game_players}")
        logger.info(f"🎮 First game started. PlayerB sees players: {self.player_b.game_players}")
    
    async def _restart_game(self):
        """Restart the game"""
        await self.player_a.restart_game()
        await asyncio.sleep(3)  # Wait for restart to complete
        
        logger.info("🔄 Game restarted - players should be back in lobby")
    
    async def _check_lobby_consistency(self):
        """Check if both players see the same lobby state"""
        # Request lobby state from both players
        await self.player_a.request_lobby_state()
        await self.player_b.request_lobby_state()
        await asyncio.sleep(1)  # Wait for responses
        
        a_lobby = self.player_a.lobby_state
        b_lobby = self.player_b.lobby_state
        
        logger.info(f"🏛️ Player A sees lobby: {len(a_lobby.get('players', []))} players")
        for player in a_lobby.get('players', []):
            logger.info(f"   - {player.get('name', 'Unknown')} (ID: {player.get('id', 'N/A')})")
            
        logger.info(f"🏛️ Player B sees lobby: {len(b_lobby.get('players', []))} players")
        for player in b_lobby.get('players', []):
            logger.info(f"   - {player.get('name', 'Unknown')} (ID: {player.get('id', 'N/A')})")
        
        # Check consistency
        a_player_count = len(a_lobby.get('players', []))
        b_player_count = len(b_lobby.get('players', []))
        
        if a_player_count != b_player_count:
            logger.error(f"❌ LOBBY INCONSISTENCY: Player A sees {a_player_count} players, Player B sees {b_player_count} players")
            return False
        else:
            logger.info("✅ Lobby consistency check passed")
            return True
    
    async def _start_second_game_and_check_identities(self):
        """Start second game and verify each player maintains their identity"""
        await self.player_a.start_game()
        await asyncio.sleep(2)  # Wait for game to start
        
        # Check what players each client controls
        logger.info("🔍 Checking player identities after second game start...")
        
        a_controlled_player = self.player_a.controlled_player_id
        b_controlled_player = self.player_b.controlled_player_id
        
        logger.info(f"🎮 Player A controls: {a_controlled_player}")
        logger.info(f"🎮 Player B controls: {b_controlled_player}")
        
        if a_controlled_player == b_controlled_player:
            logger.error(f"❌ PLAYER IDENTITY BUG: Both players control the same character ({a_controlled_player})")
            return False
        elif not b_controlled_player:
            logger.error("❌ PLAYER IDENTITY BUG: Player B lost their character identity")
            return False
        else:
            logger.info("✅ Player identities are correct")
            return True
    
    async def _cleanup(self):
        """Clean up connections"""
        if self.player_a:
            await self.player_a.disconnect()
        if self.player_b:
            await self.player_b.disconnect()


class IdentityTestPlayer:
    def __init__(self, name, is_host=False):
        self.name = name
        self.is_host = is_host
        self.sio = socketio.AsyncClient()
        self.connected = False
        self.player_id = None
        self.lobby_state = {}
        self.game_players = []
        self.controlled_player_id = None
        
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
        
        @self.sio.event
        async def lobby_joined(data):
            logger.info(f"🎮 {self.name} joined lobby")
            self.player_id = data.get('player_id')
            self.lobby_state = data.get('lobby_state', {})
        
        @self.sio.event
        async def lobby_updated(data):
            logger.info(f"🏛️ {self.name} received lobby update")
            self.lobby_state = data
        
        @self.sio.event
        async def lobby_state(data):
            logger.info(f"📋 {self.name} received lobby state response")
            self.lobby_state = data
        
        @self.sio.event
        async def game_started(data):
            logger.info(f"🚀 {self.name} received game_started")
            self.game_players = data.get('players', {})
            # Find which player this client controls - players is a dict with player_id as key
            if self.player_id in self.game_players:
                self.controlled_player_id = self.player_id
                logger.info(f"🎯 {self.name} found their character: {self.controlled_player_id}")
            else:
                logger.error(f"❌ {self.name} could not find their character in game_players: {list(self.game_players.keys())}")
    
    async def connect(self, server_url):
        """Connect to server and join game"""
        await self.sio.connect(server_url)
        await asyncio.sleep(0.5)
        await self.sio.emit('join_game', {'name': self.name})
        await asyncio.sleep(0.5)
    
    async def start_game(self):
        """Start game (host only)"""
        if self.is_host:
            await self.sio.emit('start_game')
            logger.info(f"🎯 {self.name} (host) started the game")
    
    async def restart_game(self):
        """Restart game (host only)"""
        if self.is_host:
            await self.sio.emit('restart_game')
            logger.info(f"🔄 {self.name} (host) restarted the game")
    
    async def request_lobby_state(self):
        """Request current lobby state"""
        await self.sio.emit('get_lobby_state')
    
    async def disconnect(self):
        """Disconnect from server"""
        if self.connected:
            await self.sio.disconnect()


if __name__ == '__main__':
    print("🧪 Player Identity Test")
    print("This test checks for the bug where:")
    print("- Host and non-host see different lobby states after restart")
    print("- Both players control the same character after game start")
    print("Make sure your MMO Pacman server is running on localhost:8080")
    print()
    
    tester = PlayerIdentityTester()
    asyncio.run(tester.run_test())