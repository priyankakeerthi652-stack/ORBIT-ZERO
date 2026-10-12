"""Core score, wave, stability, and resonance systems for ORBIT ZERO."""


class GameSystems:
    """Track score, progression, and gameplay resources."""

    _SCORE_PER_WAVE = 1000

    def __init__(self) -> None:
        """Initialize score and resources to their starting values."""
        self.max_stability = 100
        self.max_resonance = 100
        self.reset()

    def add_score(self, amount: int) -> None:
        """Increase the score by a non-negative amount and advance waves."""
        if amount < 0:
            raise ValueError("Score increase must be non-negative.")
        if self.game_state != "playing":
            return

        self.score += amount
        self.wave = self.score // self._SCORE_PER_WAVE + 1

    def damage_stability(self, amount: int) -> None:
        """Reduce stability by a non-negative amount, ending the run at zero."""
        if amount < 0:
            raise ValueError("Stability damage must be non-negative.")
        if self.game_state != "playing":
            return

        self.stability = max(0, self.stability - amount)
        if self.stability == 0:
            self.game_state = "game_over"

    def restore_stability(self, amount: int) -> None:
        """Restore stability by a non-negative amount, up to its maximum."""
        if amount < 0:
            raise ValueError("Stability recovery must be non-negative.")
        if self.game_state == "playing":
            self.stability = min(self.max_stability, self.stability + amount)

    def add_resonance(self, amount: int) -> None:
        """Increase resonance by a non-negative amount, up to its maximum."""
        if amount < 0:
            raise ValueError("Resonance increase must be non-negative.")
        if self.game_state == "playing":
            self.resonance = min(self.max_resonance, self.resonance + amount)

    def spend_resonance(self, amount: int) -> bool:
        """Spend resonance if enough is available; return whether it succeeded."""
        if amount < 0:
            raise ValueError("Resonance cost must be non-negative.")
        if self.game_state != "playing" or self.resonance < amount:
            return False

        self.resonance -= amount
        return True

    def is_game_over(self) -> bool:
        """Return whether stability has reached zero."""
        return self.game_state == "game_over"

    def pause(self) -> bool:
        """Pause an active run and report whether it was paused."""
        if self.game_state != "playing":
            return False
        self.game_state = "paused"
        return True

    def resume(self) -> bool:
        """Resume a paused run and report whether it was resumed."""
        if self.game_state != "paused":
            return False
        self.game_state = "playing"
        return True

    def reset(self) -> None:
        """Restore score, wave, state, and resources to their initial values."""
        self.score = 0
        self.wave = 1
        self.stability = self.max_stability
        self.resonance = 0
        self.game_state = "playing"
