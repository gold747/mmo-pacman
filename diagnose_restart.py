#!/usr/bin/env python3
"""
Quick Restart Diagnostic Script

This script helps identify common restart issues by monitoring
the game state transitions and socket events.
"""

import asyncio
import json
import time
import logging
from datetime import datetime
import socketio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RestartDiagnostic:
    def __init__(self, server_url="http://localhost:8080"):
        self.server_url = server_url
        self.sio = socketio.AsyncClient()
        self.events_received = []
        self.state_transitions = []
        self.current_state = "disconnected"
        
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup comprehensive event monitoring"""
        
        @self.sio.event
        async def connect():
            self._log_event("connect", "Connected to server")
            self._transition_state("connected")
        
        @self.sio.event
        async def disconnect():
            self._log_event("disconnect", "Disconnected from server")
            self._transition_state("disconnected")
        
        @self.sio.event
        async def game_joined(data):
            self._log_event("game_joined", f"Joined game: {data}")
            self._transition_state("lobby")
        
        @self.sio.event
        async def game_started(data):
            self._log_event("game_started", f"Game started: {data}")
            self._transition_state("playing")
        
        @self.sio.event
        async def round_ended(data):
            self._log_event("round_ended", f"Round ended: {data}")
            self._transition_state("round_end")
        
        @self.sio.event
        async def lobby_state(data):
            self._log_event("lobby_state", f"Lobby update: {data}")
        
        @self.sio.event
        async def start_game_error(data):
            self._log_event("start_game_error", f"Start error: {data}")
        
        @self.sio.event
        async def restart_game_error(data):
            self._log_event("restart_game_error", f"Restart error: {data}")
        
        # Catch all other events
        @self.sio.event
        async def catch_all(event, *args):
            if event not in ['connect', 'disconnect', 'game_joined', 'game_started', 'round_ended', 'lobby_state']:
                self._log_event(event, f"Other event: {args}")
    
    def _log_event(self, event_name, message):
        """Log an event with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.events_received.append({
            'timestamp': timestamp,
            'event': event_name,
            'message': message,
            'state': self.current_state
        })
        logger.info(f"[{timestamp}] {event_name}: {message} (state: {self.current_state})")
    
    def _transition_state(self, new_state):
        """Track state transitions"""
        old_state = self.current_state
        self.current_state = new_state
        
        transition = {
            'timestamp': datetime.now().strftime("%H:%M:%S.%f")[:-3],
            'from': old_state,
            'to': new_state
        }
        self.state_transitions.append(transition)
        
        if old_state != new_state:
            logger.info(f"🔄 State transition: {old_state} → {new_state}")
    
    async def run_diagnostic(self):
        """Run the diagnostic test"""
        logger.info("🔍 Starting Restart Diagnostic")
        
        try:
            # Connect and join
            await self.sio.connect(self.server_url)
            await asyncio.sleep(1)
            
            await self.sio.emit('join_game', {'name': 'DiagnosticPlayer'})
            await asyncio.sleep(2)
            
            logger.info("🎯 Starting first game...")
            await self.sio.emit('start_game')
            await asyncio.sleep(5)  # Let game run briefly
            
            logger.info("🏁 Waiting for round to end...")
            await asyncio.sleep(10)  # Wait for natural end or timeout
            
            logger.info("🔄 Attempting restart...")
            await self.sio.emit('restart_game')
            await asyncio.sleep(3)
            
            logger.info("🎯 Starting second game...")
            await self.sio.emit('start_game')
            await asyncio.sleep(3)
            
            logger.info("📊 Generating diagnostic report...")
            self._generate_report()
            
        except Exception as e:
            logger.error(f"❌ Diagnostic failed: {e}")
        finally:
            await self.sio.disconnect()
    
    def _generate_report(self):
        """Generate diagnostic report"""
        logger.info("\n" + "="*50)
        logger.info("📊 RESTART DIAGNOSTIC REPORT")
        logger.info("="*50)
        
        # Event summary
        event_counts = {}
        for event in self.events_received:
            event_counts[event['event']] = event_counts.get(event['event'], 0) + 1
        
        logger.info("📋 EVENT SUMMARY:")
        for event, count in event_counts.items():
            logger.info(f"  {event}: {count}")
        
        # State transitions
        logger.info("\n🔄 STATE TRANSITIONS:")
        for transition in self.state_transitions:
            logger.info(f"  {transition['timestamp']}: {transition['from']} → {transition['to']}")
        
        # Look for issues
        issues = []
        
        # Check for multiple game_started events
        game_started_count = event_counts.get('game_started', 0)
        if game_started_count < 2:
            issues.append(f"Expected 2 game_started events, got {game_started_count}")
        
        # Check for round_ended events
        round_ended_count = event_counts.get('round_ended', 0)
        if round_ended_count < 1:
            issues.append("No round_ended events received")
        
        # Check state progression
        expected_states = ['disconnected', 'connected', 'lobby', 'playing']
        if len(self.state_transitions) < len(expected_states):
            issues.append("Incomplete state progression")
        
        # Report issues
        if issues:
            logger.error("\n🚨 ISSUES DETECTED:")
            for issue in issues:
                logger.error(f"  ❌ {issue}")
        else:
            logger.info("\n✅ No obvious issues detected")
        
        # Detailed event log
        logger.info(f"\n📝 DETAILED EVENT LOG ({len(self.events_received)} events):")
        for event in self.events_received:
            logger.info(f"  [{event['timestamp']}] {event['event']}: {event['message']}")


async def main():
    diagnostic = RestartDiagnostic()
    await diagnostic.run_diagnostic()

if __name__ == '__main__':
    asyncio.run(main())