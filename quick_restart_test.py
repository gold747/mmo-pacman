#!/usr/bin/env python3
"""
Quick Restart Test - Tests the basic restart functionality

Run this while your MMO Pacman server is running to test if the restart fix works.
"""

import asyncio
import socketio
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def quick_restart_test():
    """Quick test to verify restart functionality"""
    sio = socketio.AsyncClient()
    
    @sio.event
    async def connect():
        logger.info("✅ Connected to server")
    
    @sio.event  
    async def game_joined(data):
        logger.info("✅ Joined game")
    
    @sio.event
    async def lobby_updated(data):
        logger.info(f"✅ Lobby updated: {len(data.get('players', []))} players")
    
    @sio.event
    async def game_started(data):
        logger.info("✅ Game started!")
    
    @sio.event
    async def round_ended(data):
        logger.info(f"✅ Round ended: {data.get('message', 'N/A')}")
    
    try:
        # Connect and join
        await sio.connect('http://localhost:8080')
        await sio.emit('join_game', {'name': 'RestartTester'})
        await asyncio.sleep(1)
        
        # Test cycle 1
        logger.info("🎯 Starting first game...")
        await sio.emit('start_game')
        await asyncio.sleep(3)  # Let it run briefly
        
        logger.info("🔄 Restarting game...")
        await sio.emit('restart_game')
        await asyncio.sleep(2)  # Wait for reset
        
        # Test cycle 2
        logger.info("🎯 Starting second game...")
        await sio.emit('start_game')
        await asyncio.sleep(2)
        
        logger.info("✅ Restart test completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
    finally:
        await sio.disconnect()

if __name__ == '__main__':
    print("🧪 Running Quick Restart Test...")
    print("Make sure your MMO Pacman server is running on localhost:8080")
    print()
    asyncio.run(quick_restart_test())