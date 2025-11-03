class Player:
    def __init__(self, player_id, name):
        self.id = player_id
        self.name = name
        self.x = 0
        self.y = 0
        self.direction = 'right'
        self.score = 0
        self.lives = 3  # Normal gameplay with 3 lives
        self.power_mode = False
        self.power_timer = 0
        self.invincible = False
        self.invincibility_timer = 0
        self.is_spectator = False
        self.death_time = 0
        self.power_mode_flashing = False  # True when power mode is about to end
        
    def to_dict(self):
        """Convert player to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'position': {'x': self.x, 'y': self.y},
            'direction': self.direction,
            'score': self.score,
            'lives': self.lives,
            'power_mode': self.power_mode,
            'power_mode_flashing': self.power_mode_flashing,
            'invincible': self.invincible,
            'is_spectator': self.is_spectator
        }