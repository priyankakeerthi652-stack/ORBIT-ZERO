"""Core score, stability, and resonance systems for ORBIT ZERO."""


class GameSystems:
    """Track and update the player's score and gameplay resources."""

    def __init__(self):
        """Initialize score and resources to their starting values."""
        self.score = 0
        self.max_stability = 100
        self.stability = self.max_stability
        self.max_resonance = 100
        self.resonance = 0

    def add_score(self, amount):
        """Increase the score by a non-negative amount."""
        self.score += max(0, amount)

    def damage_stability(self, amount):
        """Reduce stability by a non-negative amount, down to zero."""
        self.stability = max(0, self.stability - max(0, amount))

    def restore_stability(self, amount):
        """Restore stability by a non-negative amount, up to its maximum."""
        self.stability = min(
            self.max_stability,
            self.stability + max(0, amount),
        )

    def add_resonance(self, amount):
        """Increase resonance by a non-negative amount, up to its maximum."""
        self.resonance = min(
            self.max_resonance,
            self.resonance + max(0, amount),
        )

    def spend_resonance(self, amount):
        """Spend resonance if enough is available; return whether it succeeded."""
        amount = max(0, amount)
        if self.resonance < amount:
            return False

        self.resonance -= amount
        return True

    def is_game_over(self):
        """Return whether stability has reached zero."""
        return self.stability == 0

    def reset(self):
        """Restore score and resources to their initial values."""
        self.score = 0
        self.stability = self.max_stability
        self.resonance = 0

