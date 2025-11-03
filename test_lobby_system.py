"""
Test suite for the lobby system functionality
Tests that the game does not start until the host presses "Start Game"
"""
import unittest
import time
import threading
from unittest.mock import patch, MagicMock
import socketio
from flask import Flask

# Import the main app and game state
import sys
import os
sys.path.append(os.path.dirname(__file__))

from app import app, socketio as server_socketio
from game.game_state import GameState

class TestLobbySystem(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test"""
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # Create test clients
        self.host_client = socketio.SimpleClient()
        self.player_client = socketio.SimpleClient()
        self.spectator_client = socketio.SimpleClient()
        
        # Start server in background thread
        self.server_thread = threading.Thread(
            target=lambda: server_socketio.run(app, port=5002, debug=False, use_reloader=False)
        )
        self.server_thread.daemon = True
        self.server_thread.start()
        time.sleep(1)  # Give server time to start
        
        # Reset game state
        from game.game_state import game_state
        game_state.reset()

    def tearDown(self):
        """Clean up after each test"""
        try:
            if self.host_client.connected:
                self.host_client.disconnect()
            if self.player_client.connected:
                self.player_client.disconnect()
            if self.spectator_client.connected:
                self.spectator_client.disconnect()
        except:
            pass

    def test_game_starts_in_lobby_state(self):
        """Test that game initializes in lobby state"""
        from game.game_state import game_state
        self.assertEqual(game_state.state, 'lobby', "Game should start in lobby state")

    def test_multiple_players_join_lobby(self):
        """Test that multiple players can join the lobby without starting the game"""
        try:
            # Connect host
            self.host_client.connect('http://localhost:5002')
            self.host_client.emit('join_game', {'name': 'Host Player'})
            host_response = self.host_client.receive(timeout=2)
            
            # Connect additional player
            self.player_client.connect('http://localhost:5002')
            self.player_client.emit('join_game', {'name': 'Player 2'})
            player_response = self.player_client.receive(timeout=2)
            
            # Verify both are in lobby
            self.assertEqual(host_response[0], 'lobby_joined', "Host should join lobby")
            self.assertEqual(player_response[0], 'lobby_joined', "Player should join lobby")
            
            # Verify game state is still lobby
            from game.game_state import game_state
            self.assertEqual(game_state.state, 'lobby', "Game should remain in lobby state")
            
        except Exception as e:
            self.fail(f"Failed to test multiple players joining lobby: {e}")

    def test_game_does_not_auto_start(self):
        """Test that game does not automatically start when players join"""
        try:
            # Connect multiple players
            self.host_client.connect('http://localhost:5002')
            self.host_client.emit('join_game', {'name': 'Host Player'})
            
            self.player_client.connect('http://localhost:5002')
            self.player_client.emit('join_game', {'name': 'Player 2'})
            
            # Wait a bit to see if game auto-starts
            time.sleep(2)
            
            # Verify game is still in lobby
            from game.game_state import game_state
            self.assertEqual(game_state.state, 'lobby', 
                           "Game should not auto-start when players join")
            
        except Exception as e:
            self.fail(f"Failed to test game auto-start prevention: {e}")

    def test_non_host_cannot_start_game(self):
        """Test that non-host players cannot start the game"""
        try:
            # Connect host first
            self.host_client.connect('http://localhost:5002')
            self.host_client.emit('join_game', {'name': 'Host Player'})
            
            # Connect non-host player
            self.player_client.connect('http://localhost:5002')
            self.player_client.emit('join_game', {'name': 'Player 2'})
            
            # Try to start game as non-host
            self.player_client.emit('start_game', {})
            
            # Wait for potential response
            time.sleep(1)
            
            # Verify game is still in lobby
            from game.game_state import game_state
            self.assertEqual(game_state.state, 'lobby', 
                           "Non-host should not be able to start game")
            
        except Exception as e:
            self.fail(f"Failed to test non-host start prevention: {e}")

    def test_host_can_start_game(self):
        """Test that host can successfully start the game"""
        try:
            # Connect as host
            self.host_client.connect('http://localhost:5002')
            self.host_client.emit('join_game', {'name': 'Host Player'})
            
            # Wait for lobby join confirmation
            time.sleep(0.5)
            
            # Start game as host
            self.host_client.emit('start_game', {})
            
            # Wait for game to start
            time.sleep(1)
            
            # Verify game state changed to playing
            from game.game_state import game_state
            self.assertEqual(game_state.state, 'playing', 
                           "Host should be able to start the game")
            
        except Exception as e:
            self.fail(f"Failed to test host game start: {e}")

    def test_lobby_state_with_spectators(self):
        """Test that spectators don't affect lobby state"""
        try:
            # Connect host
            self.host_client.connect('http://localhost:5002')
            self.host_client.emit('join_game', {'name': 'Host Player'})
            
            # Connect spectator (simulated by connecting but not joining)
            self.spectator_client.connect('http://localhost:5002')
            
            # Wait a bit
            time.sleep(1)
            
            # Verify game is still in lobby
            from game.game_state import game_state
            self.assertEqual(game_state.state, 'lobby', 
                           "Spectators should not affect lobby state")
            
        except Exception as e:
            self.fail(f"Failed to test lobby with spectators: {e}")

    def test_game_state_transitions(self):
        """Test proper game state transitions from lobby to playing"""
        try:
            from game.game_state import game_state
            
            # Verify initial state
            self.assertEqual(game_state.state, 'lobby', "Should start in lobby")
            
            # Connect and start game
            self.host_client.connect('http://localhost:5002')
            self.host_client.emit('join_game', {'name': 'Host Player'})
            time.sleep(0.5)
            
            self.host_client.emit('start_game', {})
            time.sleep(1)
            
            # Verify state transition
            self.assertEqual(game_state.state, 'playing', "Should transition to playing")
            
        except Exception as e:
            self.fail(f"Failed to test game state transitions: {e}")

class TestLobbyIntegration(unittest.TestCase):
    """Integration tests for lobby system"""
    
    def test_multiple_clients_scenario(self):
        """Test a complete scenario with multiple clients"""
        print("\n🎮 Testing multi-client lobby scenario...")
        
        clients = []
        try:
            # Create multiple clients
            for i in range(3):
                client = socketio.SimpleClient()
                client.connect('http://localhost:5002')
                client.emit('join_game', {'name': f'Player{i+1}'})
                clients.append(client)
                time.sleep(0.2)
            
            # Verify all in lobby
            from game.game_state import game_state
            self.assertEqual(game_state.state, 'lobby', "All players should be in lobby")
            
            # Host starts game
            clients[0].emit('start_game', {})
            time.sleep(1)
            
            # Verify game started
            self.assertEqual(game_state.state, 'playing', "Game should be playing")
            
            print("✅ Multi-client scenario passed!")
            
        except Exception as e:
            self.fail(f"Multi-client scenario failed: {e}")
        finally:
            for client in clients:
                try:
                    client.disconnect()
                except:
                    pass

def run_lobby_tests():
    """Run all lobby system tests"""
    print("🧪 Starting Lobby System Tests...")
    print("="*50)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestLobbySystem))
    suite.addTests(loader.loadTestsFromTestCase(TestLobbyIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("="*50)
    if result.wasSuccessful():
        print("🎉 All lobby tests PASSED!")
    else:
        print(f"❌ {len(result.failures)} test(s) FAILED")
        print(f"💥 {len(result.errors)} test(s) had ERRORS")
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_lobby_tests()
    exit(0 if success else 1)