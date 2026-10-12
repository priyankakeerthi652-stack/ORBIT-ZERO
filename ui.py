"""Asset-free Pygame screens and HUD for ORBIT ZERO.

Public drawing functions:
    draw_start_screen(screen) -> None
    draw_hud(screen, score, stability, resonance, phase, wave) -> None
    draw_game_over_screen(screen, final_score) -> None
    draw_phase_transition(screen, phase) -> None

Call ``pygame.display.flip()`` in the main loop after drawing a screen.
The HUD is an overlay; the other screen functions paint the full display.
"""

from functools import lru_cache

import pygame


_BACKGROUND = (7, 11, 27)
_PANEL = (17, 25, 49)
_PANEL_EDGE = (52, 75, 112)
_TEXT = (232, 240, 255)
_MUTED = (151, 171, 205)
_CYAN = (76, 224, 238)
_PURPLE = (177, 120, 255)
_RED = (255, 91, 111)
_GREEN = (93, 231, 166)


@lru_cache(maxsize=16)
def _font(size: int, bold: bool = False) -> pygame.font.Font:
    if not pygame.font.get_init():
        pygame.font.init()
    font = pygame.font.Font(None, size)
    font.set_bold(bold)
    return font


def _draw_text(
    screen: pygame.Surface,
    text: str,
    size: int,
    color: tuple[int, int, int],
    position: tuple[int, int],
    *,
    center: bool = False,
    bold: bool = False,
) -> pygame.Rect:
    image = _font(size, bold).render(text, True, color)
    rect = image.get_rect()
    if center:
        rect.center = position
    else:
        rect.topleft = position
    screen.blit(image, rect)
    return rect


def _draw_stars(screen: pygame.Surface) -> None:
    width, height = screen.get_size()
    for x_ratio, y_ratio, radius in (
        (0.08, 0.18, 1),
        (0.18, 0.78, 2),
        (0.31, 0.23, 1),
        (0.43, 0.84, 1),
        (0.57, 0.12, 2),
        (0.68, 0.72, 1),
        (0.79, 0.28, 1),
        (0.9, 0.61, 2),
        (0.95, 0.12, 1),
        (0.12, 0.52, 1),
    ):
        pygame.draw.circle(
            screen,
            (94, 119, 162),
            (int(width * x_ratio), int(height * y_ratio)),
            radius,
        )


def _draw_bar(
    screen: pygame.Surface,
    rect: pygame.Rect,
    value: int,
    color: tuple[int, int, int],
) -> None:
    pygame.draw.rect(screen, (34, 45, 70), rect, border_radius=5)
    ratio = max(0.0, min(1.0, value / 100))
    fill = rect.copy()
    fill.width = round(rect.width * ratio)
    if fill.width > 0:
        pygame.draw.rect(screen, color, fill, border_radius=5)


def draw_start_screen(screen: pygame.Surface) -> None:
    """Draw the title screen and the controls expected by the game."""
    screen.fill(_BACKGROUND)
    _draw_stars(screen)
    width, height = screen.get_size()

    _draw_text(
        screen,
        "ORBIT ZERO",
        80,
        _TEXT,
        (width // 2, height // 3),
        center=True,
        bold=True,
    )
    _draw_text(
        screen,
        "SURVIVE THE COLLAPSE",
        25,
        _CYAN,
        (width // 2, height // 3 + 54),
        center=True,
        bold=True,
    )

    controls = (
        ("WASD / ARROWS", "Move"),
        ("SPACE", "Fire"),
        ("SHIFT", "Gravity pulse"),
        ("ENTER", "Start"),
        ("ESC", "Quit"),
    )
    first_y = height // 2 + 12
    for index, (key, action) in enumerate(controls):
        y = first_y + index * 34
        _draw_text(screen, key, 23, _CYAN, (width // 2 - 150, y), bold=True)
        _draw_text(screen, action, 23, _TEXT, (width // 2 + 20, y))

    _draw_text(
        screen,
        "Hold the line between realities.",
        22,
        _MUTED,
        (width // 2, height - 45),
        center=True,
    )


def draw_hud(
    screen: pygame.Surface,
    score: int,
    stability: int,
    resonance: int,
    phase: str | int,
    wave: int,
) -> None:
    """Overlay score, resource bars, phase, and wave on the current frame.

    Call as ``draw_hud(screen, systems.score, systems.stability,
    systems.resonance, phase, wave)``.
    """
    screen_width, _ = screen.get_size()
    panel_width = min(520, max(0, screen_width - 32))
    if panel_width == 0:
        return

    panel = pygame.Rect(16, 16, panel_width, 132)
    pygame.draw.rect(screen, _PANEL, panel, border_radius=10)
    pygame.draw.rect(screen, _PANEL_EDGE, panel, width=2, border_radius=10)

    _draw_text(screen, f"SCORE  {score:06d}", 27, _TEXT, (panel.x + 16, panel.y + 12), bold=True)
    phase_label = _font(18, bold=True).render(
        f"PHASE {phase}  /  WAVE {wave}", True, _MUTED
    )
    screen.blit(phase_label, (panel.right - phase_label.get_width() - 16, panel.y + 46))

    gap = 16
    bar_width = max(1, (panel.width - 48) // 2)
    first_x = panel.x + 16
    second_x = first_x + bar_width + gap
    label_y = panel.y + 70
    _draw_text(screen, f"REALITY STABILITY  {stability}%", 17, _TEXT, (first_x, label_y))
    _draw_text(
        screen,
        f"GRAVITY RESONANCE  {resonance}%",
        17,
        _TEXT,
        (second_x, label_y),
    )
    bar_y = panel.y + 98
    _draw_bar(screen, pygame.Rect(first_x, bar_y, bar_width, 15), stability, _GREEN if stability > 30 else _RED)
    _draw_bar(
        screen,
        pygame.Rect(second_x, bar_y, bar_width, 15),
        resonance,
        _PURPLE,
    )


def draw_game_over_screen(screen: pygame.Surface, final_score: int) -> None:
    """Draw the game-over screen with final score and restart instructions."""
    screen.fill(_BACKGROUND)
    _draw_stars(screen)
    width, height = screen.get_size()
    _draw_text(
        screen,
        "REALITY COLLAPSED",
        58,
        _RED,
        (width // 2, height // 3),
        center=True,
        bold=True,
    )
    _draw_text(
        screen,
        f"FINAL SCORE  {final_score}",
        34,
        _TEXT,
        (width // 2, height // 2),
        center=True,
        bold=True,
    )
    _draw_text(
        screen,
        "Press ENTER or R to restart",
        25,
        _CYAN,
        (width // 2, height // 2 + 58),
        center=True,
    )
    _draw_text(
        screen,
        "Press ESC to quit",
        21,
        _MUTED,
        (width // 2, height // 2 + 96),
        center=True,
    )


def draw_phase_transition(screen: pygame.Surface, phase: str | int) -> None:
    """Draw a brief phase banner; the caller controls how long it is shown."""
    width, _ = screen.get_size()
    label = f"PHASE {phase}"
    text = _font(34, bold=True).render(label, True, _TEXT)
    banner = pygame.Rect(0, 0, text.get_width() + 64, 72)
    banner.center = (width // 2, 190)
    pygame.draw.rect(screen, _PANEL, banner, border_radius=12)
    pygame.draw.rect(screen, _CYAN, banner, width=2, border_radius=12)
    screen.blit(text, text.get_rect(center=banner.center))