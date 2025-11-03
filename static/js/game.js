class MMOPacmanGame {
    constructor() {
        console.log('Initializing MMO Pacman Game...');
        
        // Game state
        this.playerId = null;
        this.players = {};
        this.ghosts = [];
        this.mapData = [];
        this.pellets = new Set();
        this.powerPellets = new Set();
        this.connected = false;
        this.gameOverShown = false; // Flag to prevent repeated game over displays
        
        // Canvas and rendering
        this.canvas = document.getElementById('game-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.tileSize = 20;
        this.viewportX = 0;
        this.viewportY = 0;
        
        // Input handling
        this.keys = {};
        this.lastMoveTime = 0;
        this.moveDelay = 150; // milliseconds
        
        // UI elements
        this.loginScreen = document.getElementById('login-screen');
        this.lobbyScreen = document.getElementById('lobby-screen');
        this.gameScreen = document.getElementById('game-screen');
        this.gameOverScreen = document.getElementById('game-over-screen');
        this.connectionStatus = document.getElementById('connection-status');
        this.connectionText = document.getElementById('connection-text');
        
        // Lobby state
        this.isHost = false;
        this.gameState = 'lobby';
        
        // Initialize
        this.init();
    }
    
    init() {
        console.log('Setting up event listeners...');
        this.setupEventListeners();
        
        console.log('Initializing Socket.IO connection...');
        this.initializeSocket();
        
        console.log('Starting game loop...');
        this.startGameLoop();
    }
    
    initializeSocket() {
        try {
            // Check if io is available
            if (typeof io === 'undefined') {
                console.error('Socket.IO library not loaded!');
                this.connectionText.textContent = 'Socket.IO not loaded';
                this.connectionStatus.className = 'connection-status disconnected';
                return;
            }
            
            console.log('Creating Socket.IO connection...');
            this.socket = io();
            this.setupSocketEvents();
        } catch (error) {
            console.error('Error initializing socket:', error);
            this.connectionText.textContent = 'Connection failed';
            this.connectionStatus.className = 'connection-status disconnected';
        }
    }
    
    setupEventListeners() {
        // Login
        const joinBtn = document.getElementById('join-btn');
        const playerNameInput = document.getElementById('player-name');
        
        joinBtn.addEventListener('click', () => this.joinGame());
        playerNameInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.joinGame();
        });
        
        // Keyboard input
        document.addEventListener('keydown', (e) => {
            this.keys[e.key.toLowerCase()] = true;
            this.handleMovement(e);
        });
        
        document.addEventListener('keyup', (e) => {
            this.keys[e.key.toLowerCase()] = false;
        });
        
        // Restart button
        document.getElementById('restart-btn').addEventListener('click', () => {
            this.showLoginScreen();
        });
        
        // Prevent scrolling with arrow keys
        document.addEventListener('keydown', (e) => {
            if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
                e.preventDefault();
            }
        });
    }
    
    setupSocketEvents() {
        if (!this.socket) {
            console.error('Socket not initialized!');
            return;
        }
        
        this.socket.on('connect', () => {
            console.log('Connected to server with ID:', this.socket.id);
            this.connected = true;
            this.connectionText.textContent = 'Connected';
            this.connectionStatus.className = 'connection-status connected';
        });
        
        this.socket.on('disconnect', () => {
            console.log('Disconnected from server');
            this.connected = false;
            this.connectionText.textContent = 'Disconnected';
            this.connectionStatus.className = 'connection-status disconnected';
        });
        
        this.socket.on('connect_error', (error) => {
            console.error('Connection error:', error);
            this.connected = false;
            this.connectionText.textContent = 'Connection error';
            this.connectionStatus.className = 'connection-status disconnected';
        });
        
        this.socket.on('game_joined', (data) => {
            console.log('Joined game:', data);
            this.playerId = data.player_id;
            this.mapData = data.map_data;
            this.players = data.players;
            this.ghosts = data.ghosts;
            
            // Convert pellets and power pellets to Sets
            this.pellets = new Set(data.pellets.map(p => `${p[0]},${p[1]}`));
            this.powerPellets = new Set(data.power_pellets.map(p => `${p[0]},${p[1]}`));
            
            this.showGameScreen();
            this.updateUI();
            
            // Center camera on player
            const player = this.players[this.playerId];
            if (player) {
                this.centerCameraOnPlayer(player.position);
            }
        });
        
        this.socket.on('game_full', (data) => {
            this.showJoinError('Game is full! Please try again later.');
        });
        
        this.socket.on('player_joined', (data) => {
            this.players[data.player_id] = {
                name: data.name,
                position: data.position,
                score: data.score,
                lives: 3,
                power_mode: false,
                direction: 'right'
            };
            this.updatePlayersList();
        });
        
        this.socket.on('player_disconnected', (data) => {
            delete this.players[data.player_id];
            this.updatePlayersList();
        });
        
        this.socket.on('player_moved', (data) => {
            // Update authoritative position for the moving player
            if (this.players[data.player_id]) {
                this.players[data.player_id].position = data.position;
                this.players[data.player_id].direction = data.direction;
                this.players[data.player_id].invincible = data.invincible || false;
                this.players[data.player_id].is_spectator = data.is_spectator || false;
            }

            // Debug: log when we receive our own movement update
            if (data.player_id === this.playerId) {
                console.log('Received authoritative move for self:', data);
                // Ensure UI reflects new position
                this.updateUI();
            }
        });
        
        this.socket.on('pellet_collected', (data) => {
            const pelletKey = `${data.pellet_pos.x},${data.pellet_pos.y}`;
            this.pellets.delete(pelletKey);
            
            if (this.players[data.player_id]) {
                this.players[data.player_id].score = data.score;
            }
            
            this.updateUI();
        });
        
        this.socket.on('power_pellet_collected', (data) => {
            const pelletKey = `${data.pellet_pos.x},${data.pellet_pos.y}`;
            this.powerPellets.delete(pelletKey);
            
            if (this.players[data.player_id]) {
                this.players[data.player_id].score = data.score;
                this.players[data.player_id].power_mode = data.power_mode || true;
                this.players[data.player_id].power_timer = data.power_timer || 300;
                console.log(`Player ${data.player_id} entered power mode! Timer: ${this.players[data.player_id].power_timer}`);
            }
            
            this.updateUI();
        });
        
        this.socket.on('player_caught', (data) => {
            if (data.type === 'player_died' && data.player_id === this.playerId) {
                // Only show game over once per round
                if (!this.gameOverShown) {
                    console.log('You died! Entering spectator mode...');
                    this.gameOverShown = true;
                    this.showDeathMessage('Game Over!', 'You have no lives left', () => {
                        this.showSpectatorMode();
                    });
                }
            } else if (data.type === 'player_caught') {
                console.log(`Player ${data.player_id} was caught by ghost ${data.ghost_id}, lives: ${data.lives}`);
                console.log(`DEBUG: Respawn position:`, data.respawn_pos);
                if (this.players[data.player_id]) {
                    const oldPos = {...this.players[data.player_id].position};
                    this.players[data.player_id].lives = data.lives;
                    this.players[data.player_id].position = data.respawn_pos;
                    this.players[data.player_id].invincible = data.invincible || false;
                    console.log(`DEBUG: Updated player ${data.player_id} position from`, oldPos, 'to', data.respawn_pos, 'invincible:', data.invincible);
                }
                if (data.player_id === this.playerId) {
                    console.log(`DEBUG: Centering camera on respawn position:`, data.respawn_pos);
                    this.showDeathMessage('You Died!', 'Respawning with 10s invincibility', () => {
                        this.centerCameraOnPlayer(data.respawn_pos);
                    });
                }
            } else if (data.type === 'ghost_eaten') {
                console.log(`Player ${data.player_id} ate ghost ${data.ghost_id}! New score: ${data.score}`);
                if (this.players[data.player_id]) {
                    this.players[data.player_id].score = data.score;
                }
                // Add visual feedback for ghost eating
                if (data.player_id === this.playerId) {
                    this.showGhostEatenFeedback();
                }
            }
            
            this.updateUI();
        });
        
        this.socket.on('ghosts_updated', (data) => {
            this.ghosts = data.ghosts;
        });
        
        this.socket.on('power_mode_changed', (data) => {
            if (this.players[data.player_id]) {
                this.players[data.player_id].power_mode = data.power_mode;
                this.players[data.player_id].power_timer = data.power_timer;
                console.log(`Player ${data.player_id} power mode: ${data.power_mode} (timer: ${data.power_timer})`);
                this.updateUI();
            }
        });
        
        this.socket.on('round_ended', (data) => {
            console.log(`Round ended: ${data.message}`);
            this.showRoundEndLeaderboard(data.message, data.leaderboard, data.host_id);
        });
        
        this.socket.on('round_started', (data) => {
            console.log('New round started!');
            this.players = {};
            // Update players data
            for (const [playerId, playerData] of Object.entries(data.players)) {
                this.players[playerId] = playerData;
            }
            
            // If we were spectating, we're now back in the game
            if (this.playerId && this.players[this.playerId] && !this.players[this.playerId].is_spectator) {
                document.getElementById('game-status').innerHTML = '';
                this.showJoinStatus('New round started! You\'re back in the game!', false);
                setTimeout(() => {
                    document.getElementById('join-status').style.display = 'none';
                }, 3000);
            }
        });
        
        this.socket.on('game_ended', (data) => {
            console.log('Game ended with leaderboard:', data);
            this.showLeaderboard(data.message, data.leaderboard);
        });

        this.socket.on('game_restarted', (data) => {
            console.log('Game restarted by host:', data.message);
            this.hideRoundEndLeaderboard();
            // Don't show "Starting..." message since game_started will be sent immediately
        });

        // Lobby-related handlers
        this.socket.on('lobby_joined', (data) => {
            console.log('Joined lobby:', data);
            this.playerId = data.player_id;
            this.isHost = data.is_host;
            this.gameState = 'lobby';
            this.showLobbyScreen(data.lobby_state);
        });

        this.socket.on('lobby_updated', (data) => {
            console.log('Lobby updated:', data);
            this.updateLobbyDisplay(data);
        });

        this.socket.on('game_started', (data) => {
            console.log('Game started:', data);
            this.gameState = 'playing';
            this.gameOverShown = false; // Reset game over flag for new round
            this.hideRoundEndLeaderboard(); // Hide any overlay from round end
            this.initializeGameFromData(data);
            this.showGameScreen();
        });

        this.socket.on('start_game_error', (data) => {
            console.log('Start game error:', data.error);
            alert(data.error);
        });
    }
    
    joinGame() {
        console.log('Join game clicked!');
        
        const playerName = document.getElementById('player-name').value.trim();
        if (!playerName) {
            this.showJoinError('Please enter a name');
            return;
        }
        
        if (!this.socket || !this.connected) {
            this.showJoinError('Not connected to server. Please wait or refresh the page.');
            console.error('Socket not connected. Socket:', this.socket, 'Connected:', this.connected);
            return;
        }
        
        console.log('Attempting to join game with name:', playerName);
        this.socket.emit('join_game', { name: playerName });
        this.showJoinStatus('Joining game...', false);
    }
    
    handleMovement(e) {
        const now = Date.now();
        if (now - this.lastMoveTime < this.moveDelay) {
            return;
        }
        
        let direction = null;
        
        // WASD or Arrow keys
        if (e.key === 'w' || e.key === 'ArrowUp') {
            direction = 'up';
        } else if (e.key === 's' || e.key === 'ArrowDown') {
            direction = 'down';
        } else if (e.key === 'a' || e.key === 'ArrowLeft') {
            direction = 'left';
        } else if (e.key === 'd' || e.key === 'ArrowRight') {
            direction = 'right';
        }
        
        if (direction && this.playerId) {
            const player = this.players[this.playerId];
            
            // Check if player is in spectator mode
            if (player && player.is_spectator) {
                // Move camera instead of player in spectator mode
                this.handleSpectatorCameraMove(direction);
                this.lastMoveTime = now;
            } else {
                // Normal player movement
                this.socket.emit('player_move', { direction });
                this.lastMoveTime = now;
                
                // Update local player immediately for smooth movement
                if (this.players[this.playerId]) {
                    this.players[this.playerId].direction = direction;
                }
            }
        }
    }
    
    handleSpectatorCameraMove(direction) {
        const moveSpeed = 30; // Pixels per move
        
        switch (direction) {
            case 'up':
                this.viewportY -= moveSpeed;
                break;
            case 'down':
                this.viewportY += moveSpeed;
                break;
            case 'left':
                this.viewportX -= moveSpeed;
                break;
            case 'right':
                this.viewportX += moveSpeed;
                break;
        }
        
        // Ensure camera doesn't go outside map bounds
        if (this.mapData && this.mapData.length > 0) {
            const maxViewportX = (this.mapData[0].length * this.tileSize) - this.canvas.width;
            const maxViewportY = (this.mapData.length * this.tileSize) - this.canvas.height;
            
            this.viewportX = Math.max(0, Math.min(maxViewportX, this.viewportX));
            this.viewportY = Math.max(0, Math.min(maxViewportY, this.viewportY));
        }
    }
    
    centerCameraOnPlayer(position) {
        this.viewportX = position.x - this.canvas.width / 2;
        this.viewportY = position.y - this.canvas.height / 2;
    }
    
    updateCamera() {
        if (this.playerId && this.players[this.playerId]) {
            const player = this.players[this.playerId];
            
            // Don't auto-follow camera in spectator mode (manual control with arrow keys)
            if (player.is_spectator) {
                return;
            }
            
            const playerScreenX = player.position.x - this.viewportX;
            const playerScreenY = player.position.y - this.viewportY;
            
            // Define camera follow boundaries (how close to edge before camera moves)
            const edgeBuffer = 100; // pixels from edge
            const moveSpeed = 0.1; // Camera smoothing factor (0-1, higher = faster)
            
            let targetViewportX = this.viewportX;
            let targetViewportY = this.viewportY;
            
            // Check if player is getting too close to edges and adjust camera
            if (playerScreenX < edgeBuffer) {
                // Player too far left
                targetViewportX = player.position.x - edgeBuffer;
            } else if (playerScreenX > this.canvas.width - edgeBuffer) {
                // Player too far right
                targetViewportX = player.position.x - (this.canvas.width - edgeBuffer);
            }
            
            if (playerScreenY < edgeBuffer) {
                // Player too far up
                targetViewportY = player.position.y - edgeBuffer;
            } else if (playerScreenY > this.canvas.height - edgeBuffer) {
                // Player too far down
                targetViewportY = player.position.y - (this.canvas.height - edgeBuffer);
            }
            
            // Ensure camera doesn't go outside map bounds
            const maxViewportX = (this.mapData[0].length * this.tileSize) - this.canvas.width;
            const maxViewportY = (this.mapData.length * this.tileSize) - this.canvas.height;
            
            targetViewportX = Math.max(0, Math.min(maxViewportX, targetViewportX));
            targetViewportY = Math.max(0, Math.min(maxViewportY, targetViewportY));
            
            // Smoothly interpolate to target position
            this.viewportX += (targetViewportX - this.viewportX) * moveSpeed;
            this.viewportY += (targetViewportY - this.viewportY) * moveSpeed;
        }
    }
    
    startGameLoop() {
        const gameLoop = () => {
            this.update();
            this.render();
            requestAnimationFrame(gameLoop);
        };
        gameLoop();
    }
    
    update() {
        this.updateCamera();
    }
    
    render() {
        // Clear canvas
        this.ctx.fillStyle = '#000000';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        if (!this.mapData.length) return;
        
        // Calculate visible tiles
        const startX = Math.floor(this.viewportX / this.tileSize);
        const startY = Math.floor(this.viewportY / this.tileSize);
        const endX = Math.ceil((this.viewportX + this.canvas.width) / this.tileSize);
        const endY = Math.ceil((this.viewportY + this.canvas.height) / this.tileSize);
        
        // Render map
        this.renderMap(startX, startY, endX, endY);
        
        // Render pellets
        this.renderPellets(startX, startY, endX, endY);
        
        // Render power pellets
        this.renderPowerPellets(startX, startY, endX, endY);
        
        // Render players
        this.renderPlayers();
        
        // Render ghosts
        this.renderGhosts();
        
        // Render UI overlay
        this.renderMiniMap();
    }
    
    renderMap(startX, startY, endX, endY) {
        for (let y = Math.max(0, startY); y < Math.min(this.mapData.length, endY); y++) {
            for (let x = Math.max(0, startX); x < Math.min(this.mapData[0].length, endX); x++) {
                const tileType = this.mapData[y][x];
                const screenX = x * this.tileSize - this.viewportX;
                const screenY = y * this.tileSize - this.viewportY;
                
                if (tileType === 0) { // Wall
                    this.ctx.fillStyle = '#0066ff';
                    this.ctx.fillRect(screenX, screenY, this.tileSize, this.tileSize);
                    
                    // Add border effect
                    this.ctx.strokeStyle = '#0088ff';
                    this.ctx.lineWidth = 1;
                    this.ctx.strokeRect(screenX, screenY, this.tileSize, this.tileSize);
                } else if (tileType === 2) { // Spawn point
                    this.ctx.fillStyle = '#000000';
                    this.ctx.fillRect(screenX, screenY, this.tileSize, this.tileSize);
                }
            }
        }
    }
    
    renderPellets(startX, startY, endX, endY) {
        this.ctx.fillStyle = '#ffff00';
        
        for (let y = Math.max(0, startY); y < Math.min(this.mapData.length, endY); y++) {
            for (let x = Math.max(0, startX); x < Math.min(this.mapData[0].length, endX); x++) {
                const pelletKey = `${x},${y}`;
                if (this.pellets.has(pelletKey)) {
                    const screenX = x * this.tileSize - this.viewportX + this.tileSize / 2;
                    const screenY = y * this.tileSize - this.viewportY + this.tileSize / 2;
                    
                    this.ctx.beginPath();
                    this.ctx.arc(screenX, screenY, 2, 0, Math.PI * 2);
                    this.ctx.fill();
                }
            }
        }
    }
    
    renderPowerPellets(startX, startY, endX, endY) {
        const time = Date.now() / 200;
        const alpha = (Math.sin(time) + 1) / 2 * 0.5 + 0.5; // Pulsing effect
        
        this.ctx.fillStyle = `rgba(255, 255, 0, ${alpha})`;
        
        for (let y = Math.max(0, startY); y < Math.min(this.mapData.length, endY); y++) {
            for (let x = Math.max(0, startX); x < Math.min(this.mapData[0].length, endX); x++) {
                const pelletKey = `${x},${y}`;
                if (this.powerPellets.has(pelletKey)) {
                    const screenX = x * this.tileSize - this.viewportX + this.tileSize / 2;
                    const screenY = y * this.tileSize - this.viewportY + this.tileSize / 2;
                    
                    this.ctx.beginPath();
                    this.ctx.arc(screenX, screenY, 6, 0, Math.PI * 2);
                    this.ctx.fill();
                }
            }
        }
    }
    
    renderPlayers() {
        Object.entries(this.players).forEach(([playerId, player]) => {
            // Don't render spectators
            if (player.is_spectator) {
                return;
            }
            
            const screenX = player.position.x - this.viewportX;
            const screenY = player.position.y - this.viewportY;
            
            // Only render if visible
            if (screenX >= -this.tileSize && screenX <= this.canvas.width &&
                screenY >= -this.tileSize && screenY <= this.canvas.height) {
                
                // Player body (Pacman)
                let alpha = 1; // Default opacity
                if (player.invincible) {
                    // Flash during invincibility (50% opacity alternating)
                    alpha = Math.sin(Date.now() * 0.02) > 0 ? 1 : 0.3;
                }
                
                if (player.power_mode) {
                    let powerColor = [255, 107, 107]; // Red when powered
                    
                    // Flash rapidly when power mode is about to end
                    if (player.power_mode_flashing) {
                        // Faster flashing for warning (between red and normal color)
                        const flashRate = Math.sin(Date.now() * 0.05); // Faster than invincibility flash
                        if (flashRate > 0) {
                            powerColor = [255, 107, 107]; // Keep red color
                        } else {
                            // Flash to normal player color
                            powerColor = playerId === this.playerId ? [255, 255, 0] : [255, 170, 0];
                        }
                    }
                    
                    this.ctx.fillStyle = `rgba(${powerColor[0]}, ${powerColor[1]}, ${powerColor[2]}, ${alpha})`;
                } else {
                    const color = playerId === this.playerId ? [255, 255, 0] : [255, 170, 0];
                    this.ctx.fillStyle = `rgba(${color[0]}, ${color[1]}, ${color[2]}, ${alpha})`;
                }
                
                this.ctx.beginPath();
                
                // Pacman shape with mouth
                const radius = this.tileSize / 2 - 2;
                const centerX = screenX + this.tileSize / 2;
                const centerY = screenY + this.tileSize / 2;
                
                let startAngle = 0.2 * Math.PI;
                let endAngle = 1.8 * Math.PI;
                
                // Adjust mouth direction based on movement
                if (player.direction === 'right') {
                    startAngle = 0.2 * Math.PI;
                    endAngle = 1.8 * Math.PI;
                } else if (player.direction === 'left') {
                    startAngle = 1.2 * Math.PI;
                    endAngle = 0.8 * Math.PI;
                } else if (player.direction === 'up') {
                    startAngle = 1.7 * Math.PI;
                    endAngle = 1.3 * Math.PI;
                } else if (player.direction === 'down') {
                    startAngle = 0.7 * Math.PI;
                    endAngle = 0.3 * Math.PI;
                }
                
                this.ctx.arc(centerX, centerY, radius, startAngle, endAngle);
                this.ctx.lineTo(centerX, centerY);
                this.ctx.fill();
                
                // Player name
                this.ctx.fillStyle = '#ffffff';
                this.ctx.font = '12px Arial';
                this.ctx.textAlign = 'center';
                this.ctx.fillText(player.name, centerX, screenY - 5);
                
                // Lives indicator
                if (playerId === this.playerId) {
                    for (let i = 0; i < player.lives; i++) {
                        this.ctx.fillStyle = '#ff0000';
                        this.ctx.fillRect(screenX + i * 6, screenY + this.tileSize + 5, 4, 4);
                    }
                }
            }
        });
    }
    
    renderGhosts() {
        this.ghosts.forEach(ghost => {
            const screenX = ghost.position.x - this.viewportX;
            const screenY = ghost.position.y - this.viewportY;
            
            // Only render if visible
            if (screenX >= -this.tileSize && screenX <= this.canvas.width &&
                screenY >= -this.tileSize && screenY <= this.canvas.height) {
                
                const centerX = screenX + this.tileSize / 2;
                const centerY = screenY + this.tileSize / 2;
                const radius = this.tileSize / 2 - 2;
                
                // Ghost body
                this.ctx.fillStyle = ghost.color;
                this.ctx.beginPath();
                this.ctx.arc(centerX, centerY - 3, radius, Math.PI, 0);
                this.ctx.rect(centerX - radius, centerY - 3, radius * 2, radius + 3);
                this.ctx.fill();
                
                // Ghost bottom (wavy)
                this.ctx.beginPath();
                const waveWidth = radius * 2 / 3;
                for (let i = 0; i <= 3; i++) {
                    const x = centerX - radius + i * waveWidth;
                    const y = centerY + radius - (i % 2) * 3;
                    if (i === 0) this.ctx.moveTo(x, y);
                    else this.ctx.lineTo(x, y);
                }
                this.ctx.fill();
                
                // Ghost eyes
                this.ctx.fillStyle = '#ffffff';
                this.ctx.beginPath();
                this.ctx.arc(centerX - 4, centerY - 4, 3, 0, Math.PI * 2);
                this.ctx.arc(centerX + 4, centerY - 4, 3, 0, Math.PI * 2);
                this.ctx.fill();
                
                this.ctx.fillStyle = '#000000';
                this.ctx.beginPath();
                this.ctx.arc(centerX - 4, centerY - 4, 1, 0, Math.PI * 2);
                this.ctx.arc(centerX + 4, centerY - 4, 1, 0, Math.PI * 2);
                this.ctx.fill();
            }
        });
    }
    
    renderMiniMap() {
        const miniMapSize = 150;
        const miniMapX = this.canvas.width - miniMapSize - 10;
        const miniMapY = 10;
        
        // Mini map background
        this.ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
        this.ctx.fillRect(miniMapX, miniMapY, miniMapSize, miniMapSize);
        
        this.ctx.strokeStyle = '#ffd700';
        this.ctx.lineWidth = 2;
        this.ctx.strokeRect(miniMapX, miniMapY, miniMapSize, miniMapSize);
        
        if (!this.mapData.length) return;
        
        const scaleX = miniMapSize / (this.mapData[0].length * this.tileSize);
        const scaleY = miniMapSize / (this.mapData.length * this.tileSize);
        const scale = Math.min(scaleX, scaleY);
        
        // Draw mini map walls
        this.ctx.fillStyle = '#0066ff';
        for (let y = 0; y < this.mapData.length; y++) {
            for (let x = 0; x < this.mapData[0].length; x++) {
                if (this.mapData[y][x] === 0) {
                    this.ctx.fillRect(
                        miniMapX + x * this.tileSize * scale,
                        miniMapY + y * this.tileSize * scale,
                        this.tileSize * scale,
                        this.tileSize * scale
                    );
                }
            }
        }
        
        // Draw players on mini map
        Object.entries(this.players).forEach(([playerId, player]) => {
            this.ctx.fillStyle = playerId === this.playerId ? '#ffff00' : '#ffaa00';
            this.ctx.beginPath();
            this.ctx.arc(
                miniMapX + player.position.x * scale + this.tileSize * scale / 2,
                miniMapY + player.position.y * scale + this.tileSize * scale / 2,
                3,
                0,
                Math.PI * 2
            );
            this.ctx.fill();
        });
        
        // Draw viewport indicator
        if (this.playerId && this.players[this.playerId]) {
            this.ctx.strokeStyle = '#ffffff';
            this.ctx.lineWidth = 1;
            this.ctx.strokeRect(
                miniMapX + this.viewportX * scale,
                miniMapY + this.viewportY * scale,
                this.canvas.width * scale,
                this.canvas.height * scale
            );
        }
    }
    
    updateUI() {
        if (this.playerId && this.players[this.playerId]) {
            const player = this.players[this.playerId];
            
            document.getElementById('score').textContent = player.score;
            document.getElementById('lives').textContent = player.lives;
            
            const powerIndicator = document.getElementById('power-indicator');
            if (player.power_mode) {
                powerIndicator.style.display = 'flex';
            } else {
                powerIndicator.style.display = 'none';
            }
        }
        
        document.getElementById('player-count').textContent = Object.keys(this.players).length;
        
        this.updatePlayersList();
        this.updateLeaderboard();
    }
    
    updatePlayersList() {
        const playersList = document.getElementById('players-list');
        playersList.innerHTML = '';
        
        Object.entries(this.players).forEach(([playerId, player]) => {
            const playerItem = document.createElement('div');
            playerItem.className = `player-item ${playerId === this.playerId ? 'self' : ''}`;
            
            playerItem.innerHTML = `
                <span class="player-name">${player.name}</span>
                <span class="player-score">${player.score}</span>
            `;
            
            playersList.appendChild(playerItem);
        });
    }
    
    updateLeaderboard() {
        const leaderboardList = document.getElementById('leaderboard-list');
        leaderboardList.innerHTML = '';
        
        // Sort players by score
        const sortedPlayers = Object.entries(this.players)
            .sort(([,a], [,b]) => b.score - a.score)
            .slice(0, 10); // Top 10
        
        sortedPlayers.forEach(([playerId, player], index) => {
            const leaderboardItem = document.createElement('div');
            leaderboardItem.className = `leaderboard-item ${playerId === this.playerId ? 'self' : ''}`;
            
            const medal = index < 3 ? ['🥇', '🥈', '🥉'][index] : `${index + 1}.`;
            
            leaderboardItem.innerHTML = `
                <span>${medal} ${player.name}</span>
                <span class="player-score">${player.score}</span>
            `;
            
            leaderboardList.appendChild(leaderboardItem);
        });
    }
    
    showLoginScreen() {
        this.loginScreen.style.display = 'block';
        this.gameScreen.style.display = 'none';
        this.gameOverScreen.style.display = 'none';
    }
    
    showGameScreen() {
        this.loginScreen.style.display = 'none';
        this.gameScreen.style.display = 'flex';
        this.gameOverScreen.style.display = 'none';
    }
    
    showDeathMessage(mainText, subText, callback) {
        const deathMessage = document.getElementById('death-message');
        const deathTextEl = deathMessage.querySelector('.death-text');
        const deathSubtextEl = deathMessage.querySelector('.death-subtext');
        const respawnTimerEl = document.getElementById('respawn-timer');
        
        // Set custom text
        deathTextEl.textContent = mainText;
        
        // Show the death message
        deathMessage.style.display = 'flex';
        
        // Start countdown timer
        let countdown = 3;
        respawnTimerEl.textContent = countdown;
        deathSubtextEl.innerHTML = `${subText} <span id="respawn-timer">${countdown}</span>...`;
        
        const countdownInterval = setInterval(() => {
            countdown--;
            const timer = document.getElementById('respawn-timer');
            if (timer) {
                timer.textContent = countdown;
            }
            
            if (countdown <= 0) {
                clearInterval(countdownInterval);
                deathMessage.style.display = 'none';
                if (callback) {
                    callback();
                }
            }
        }, 1000);
    }

    showSpectatorMode() {
        const player = this.players[this.playerId];
        if (player) {
            player.is_spectator = true;
        }
        
        // Show spectator message instead of game over
        this.showJoinStatus('You died! You are now spectating. Wait for next round to play again.', false);
        
        // Continue rendering game but show spectator status with controls info
        document.getElementById('game-status').innerHTML = `
            <div style="background: rgba(255,255,255,0.8); padding: 10px; border-radius: 5px; margin: 10px;">
                <strong>SPECTATOR MODE</strong><br>
                Use arrow keys to move the camera and spectate other players<br>
                <small>Waiting for next round to start...</small>
            </div>
        `;
    }

    showLeaderboard(message, leaderboard) {
        // Create leaderboard HTML
        let leaderboardHTML = `
            <div style="background: rgba(0,0,0,0.9); color: white; padding: 20px; border-radius: 10px; margin: 20px; text-align: center; max-width: 400px; margin: 20px auto;">
                <h2>${message}</h2>
                <table style="width: 100%; margin-top: 20px; border-collapse: collapse;">
                    <thead>
                        <tr style="border-bottom: 2px solid #fff;">
                            <th style="padding: 10px; text-align: left;">#</th>
                            <th style="padding: 10px; text-align: left;">Player</th>
                            <th style="padding: 10px; text-align: right;">Score</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        leaderboard.forEach((player, index) => {
            const rank = index + 1;
            const trophy = rank === 1 ? '🏆' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : '';
            leaderboardHTML += `
                <tr style="border-bottom: 1px solid #666;">
                    <td style="padding: 8px;">${rank}${trophy}</td>
                    <td style="padding: 8px;">${player.name}</td>
                    <td style="padding: 8px; text-align: right; font-weight: bold;">${player.score}</td>
                </tr>
            `;
        });
        
        leaderboardHTML += `
                    </tbody>
                </table>
                <p style="margin-top: 20px; font-style: italic;">New players can join to start a new game!</p>
            </div>
        `;
        
        // Show leaderboard overlay
        document.getElementById('game-status').innerHTML = leaderboardHTML;
        
        // Also show in join status area
        this.showJoinStatus('Game Over! Check the leaderboard above.', false);
    }

    showRoundEndLeaderboard(message, leaderboard, hostId) {
        // Create or update round end leaderboard overlay
        let overlay = document.getElementById('round-end-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'round-end-overlay';
            overlay.className = 'round-end-overlay';
            document.body.appendChild(overlay);
        }

        let leaderboardHTML = `
            <div class="round-end-content">
                <h2>🏁 Round Complete! 🏁</h2>
                <p>${message}</p>
                <div class="leaderboard-final">`;
        
        leaderboard.forEach((player, index) => {
            const rank = index + 1;
            const trophy = rank === 1 ? '🏆' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : '';
            leaderboardHTML += `
                <div class="leaderboard-entry ${player.name === this.playerName ? 'self' : ''}">
                    <span class="rank">${rank}${trophy}</span>
                    <span class="name">${player.name}</span>
                    <span class="score">${player.score} pts</span>
                </div>`;
        });
        
        leaderboardHTML += `</div>`;
        
        // Add host controls if this player is the host
        if (this.playerId === hostId) {
            leaderboardHTML += `
                <div class="host-controls">
                    <button id="play-again-btn" class="btn">🚀 Start New Round</button>
                    <p class="host-info">You are the host - click to start a new round!</p>
                </div>`;
        } else {
            leaderboardHTML += `
                <div class="waiting-info">
                    <p>⏳ Waiting for host to start next round...</p>
                    <p class="auto-restart-info">Auto-restart in 60 seconds if host doesn't restart</p>
                </div>`;
        }
        
        leaderboardHTML += `</div>`;
        overlay.innerHTML = leaderboardHTML;
        overlay.style.display = 'flex';

        // Add play again button handler
        const playAgainBtn = document.getElementById('play-again-btn');
        if (playAgainBtn) {
            playAgainBtn.addEventListener('click', () => {
                this.socket.emit('restart_game');
                playAgainBtn.disabled = true;
                playAgainBtn.textContent = 'Starting...';
            });
        }
    }

    hideRoundEndLeaderboard() {
        const overlay = document.getElementById('round-end-overlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    }

    showGameOver() {
        const player = this.players[this.playerId];
        document.getElementById('final-score').textContent = `Final Score: ${player ? player.score : 0}`;
        
        this.loginScreen.style.display = 'none';
        this.gameScreen.style.display = 'none';
        this.gameOverScreen.style.display = 'block';
    }
    
    showJoinStatus(message, isError) {
        const statusEl = document.getElementById('join-status');
        statusEl.textContent = message;
        statusEl.className = isError ? 'error' : 'success';
        statusEl.style.display = 'block';
    }
    
    showJoinError(message) {
        this.showJoinStatus(message, true);
    }
    
    showGhostEatenFeedback() {
        // Visual feedback when player eats a ghost
        const powerIndicator = document.getElementById('power-indicator');
        if (powerIndicator) {
            powerIndicator.style.animation = 'none';
            powerIndicator.offsetHeight; // Trigger reflow
            powerIndicator.style.animation = 'pulse 0.5s ease-in-out';
        }
    }

    showLobbyScreen(lobbyState) {
        console.log('Showing lobby screen');
        this.loginScreen.style.display = 'none';
        this.gameScreen.style.display = 'none';
        this.gameOverScreen.style.display = 'none';
        this.lobbyScreen.style.display = 'block';
        
        this.updateLobbyDisplay(lobbyState);
        this.setupLobbyControls();
    }

    updateLobbyDisplay(lobbyState) {
        // Update player count
        document.getElementById('lobby-player-count').textContent = lobbyState.player_count;
        
        // Update host status
        const hostStatus = document.getElementById('host-status');
        if (this.isHost) {
            hostStatus.textContent = '👑 You are the host';
            hostStatus.style.color = '#44ff44';
        } else {
            const hostPlayer = lobbyState.players.find(p => p.is_host);
            hostStatus.textContent = hostPlayer ? `👑 Host: ${hostPlayer.name}` : 'No host';
            hostStatus.style.color = '#ffaa00';
        }
        
        // Update players list
        const playersList = document.getElementById('lobby-players-list');
        playersList.innerHTML = '';
        
        lobbyState.players.forEach(player => {
            const playerItem = document.createElement('div');
            playerItem.className = 'lobby-player-item';
            
            const nameSpan = document.createElement('span');
            nameSpan.textContent = player.name;
            if (player.is_host) {
                nameSpan.className = 'lobby-player-host';
                nameSpan.textContent = '👑 ' + player.name;
            }
            
            playerItem.appendChild(nameSpan);
            playersList.appendChild(playerItem);
        });
        
        // Show/hide controls based on host status
        const startButton = document.getElementById('start-game-btn');
        const waitingMessage = document.getElementById('waiting-message');
        
        if (this.isHost) {
            startButton.style.display = 'block';
            waitingMessage.style.display = 'none';
        } else {
            startButton.style.display = 'none';
            waitingMessage.style.display = 'block';
        }
    }

    setupLobbyControls() {
        const startButton = document.getElementById('start-game-btn');
        startButton.onclick = () => {
            console.log('Starting game...');
            this.socket.emit('start_game');
        };
    }

    initializeGameFromData(data) {
        // Initialize game state from server data
        this.mapData = data.map_data;
        this.players = data.players || {};
        this.ghosts = data.ghosts || [];
        
        // Convert pellets and power pellets to coordinate string format
        this.pellets = new Set((data.pellets || []).map(p => `${p[0]},${p[1]}`));
        this.powerPellets = new Set((data.power_pellets || []).map(p => `${p[0]},${p[1]}`));
        
        // Set camera position
        if (this.playerId && this.players[this.playerId]) {
            const player = this.players[this.playerId];
            this.centerCameraOnPlayer(player.position);
        }
    }

    showGameScreen() {
        console.log('Showing game screen');
        this.loginScreen.style.display = 'none';
        this.lobbyScreen.style.display = 'none';
        this.gameOverScreen.style.display = 'none';
        this.gameScreen.style.display = 'block';
        
        // Start the game loop
        this.startGameLoop();
    }
}

// Initialize game when page loads
document.addEventListener('DOMContentLoaded', () => {
    new MMOPacmanGame();
});