"""Asset-free menus, HUD, and transition overlays for ORBIT ZERO.

Existing drawing interfaces are kept compatible. ``handle_menu_event`` is a
small optional event helper for a main loop to use; it does not create a
display or run a game loop.
"""

from functools import lru_cache

import pygame


_BACKGROUND = (5, 9, 24)
_PANEL = (12, 19, 39)
_PANEL_EDGE = (48, 75, 115)
_TEXT = (234, 243, 255)
_MUTED = (147, 169, 202)
_CYAN = (78, 224, 240)
_PURPLE = (182, 127, 255)
_RED = (255, 99, 119)
_GREEN = (92, 230, 166)
_PHASES = (
    ("Silent Expanse", "The void is listening.", (89, 187, 255)),
    ("Nebula Drift", "A new current bends around you.", (224, 116, 255)),
    ("Fracture Zone", "Reality is beginning to split.", (255, 112, 119)),
    ("Event Horizon", "There may be no return.", (125, 174, 255)),
)
_PHASE_TRANSITION_MS = 2600
_last_phase = None
_phase_changed_at = 0
_STARS = tuple(
    ((index * 73 + 19) % 997 / 997, (index * 137 + 41) % 991 / 991,
     1 + (index % 13 == 0))
    for index in range(64)
)


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


@lru_cache(maxsize=6)
def _backdrop(size: tuple[int, int]) -> pygame.Surface:
    """Build a reusable, low-cost nebula-and-stars background."""
    width, height = size
    surface = pygame.Surface(size)
    if width <= 0 or height <= 0:
        return surface

    for y in range(height):
        blend = y / max(1, height - 1)
        color = (
            int(5 + 10 * blend),
            int(9 + 5 * blend),
            int(24 + 23 * blend),
        )
        pygame.draw.line(surface, color, (0, y), (width, y))

    haze = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.ellipse(
        haze, (99, 56, 190, 24),
        (int(width * 0.08), int(height * 0.16), int(width * 0.58), int(height * 0.38)),
    )
    pygame.draw.ellipse(
        haze, (35, 153, 198, 22),
        (int(width * 0.43), int(height * 0.43), int(width * 0.52), int(height * 0.34)),
    )
    surface.blit(haze, (0, 0))
    for x_ratio, y_ratio, radius in _STARS:
        pygame.draw.circle(
            surface,
            (100 + radius * 15, 132 + radius * 12, 184 + radius * 10),
            (int(width * x_ratio), int(height * y_ratio)),
            radius,
        )
    return surface


def _draw_backdrop(screen: pygame.Surface) -> None:
    screen.blit(_backdrop(screen.get_size()), (0, 0))


def _phase_details(phase: str | int) -> tuple[str, str, tuple[int, int, int]]:
    if isinstance(phase, int) and 0 <= phase < len(_PHASES):
        return _PHASES[phase]
    normalized = str(phase).strip().casefold()
    for details in _PHASES:
        if normalized in (details[0].casefold(), details[0].casefold().replace(" ", "_")):
            return details
    return str(phase), "Reality shifts around you.", _CYAN


def _draw_button(
    screen: pygame.Surface,
    label: str,
    rect: pygame.Rect,
    selected: bool,
) -> None:
    fill = (20, 48, 71) if selected else _PANEL
    edge = _CYAN if selected else _PANEL_EDGE
    pygame.draw.rect(screen, fill, rect, border_radius=9)
    pygame.draw.rect(screen, edge, rect, width=2, border_radius=9)
    _draw_text(
        screen, label, 25, _TEXT if selected else _MUTED, rect.center,
        center=True, bold=selected,
    )


def draw_start_screen(screen: pygame.Surface, selected: int = 0) -> None:
    """Paint the main menu; ``selected`` is 0 for Start and 1 for Quit."""
    _draw_backdrop(screen)
    width, height = screen.get_size()
    center_x = width // 2
    selected = max(0, min(1, selected))

    title_size = max(42, min(86, width // 8))
    _draw_text(
        screen, "ORBIT ZERO", title_size, _TEXT,
        (center_x, int(height * 0.25)), center=True, bold=True,
    )
    pygame.draw.line(
        screen, _CYAN,
        (center_x - min(190, width // 3), int(height * 0.25) + title_size // 2 + 7),
        (center_x + min(190, width // 3), int(height * 0.25) + title_size // 2 + 7),
        2,
    )
    _draw_text(
        screen, "SURVIVE THE COLLAPSE", 23, _CYAN,
        (center_x, int(height * 0.25) + title_size // 2 + 34),
        center=True, bold=True,
    )

    button_width = min(300, max(180, width - 48))
    button_height = 48
    button_x = center_x - button_width // 2
    button_y = max(int(height * 0.49), int(height * 0.41) + 8)
    for index, label in enumerate(("START GAME", "QUIT")):
        _draw_button(
            screen, label,
            pygame.Rect(button_x, button_y + index * 60, button_width, button_height),
            selected == index,
        )

    _draw_text(
        screen, "WASD / ARROWS  MOVE     SPACE  FIRE     SHIFT  GRAVITY PULSE",
        max(15, min(20, width // 42)), _TEXT,
        (center_x, min(height - 54, button_y + 147)), center=True,
    )
    _draw_text(
        screen, "UP / DOWN SELECT     ENTER CONFIRM     ESC QUIT",
        max(14, min(18, width // 48)), _MUTED,
        (center_x, height - 25), center=True,
    )


def handle_menu_event(
    event: pygame.event.Event,
    selected: int = 0,
    *,
    game_over: bool = False,
) -> tuple[int, str | None]:
    """Handle one menu key event; return updated selection and requested action.

    The caller remains responsible for changing game state or quitting.
    Actions are ``"start"``, ``"restart"``, or ``"quit"``.
    """
    selected = max(0, min(1, selected))
    if event.type != pygame.KEYDOWN:
        return selected, None
    if event.key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
        return 1 - selected, None
    if event.key in (pygame.K_ESCAPE,):
        return selected, "quit"
    if game_over and event.key == pygame.K_r:
        return selected, "restart"
    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
        if selected == 1:
            return selected, "quit"
        return selected, "restart" if game_over else "start"
    return selected, None


def _draw_bar(
    screen: pygame.Surface,
    rect: pygame.Rect,
    value: int | float,
    maximum: int | float,
    color: tuple[int, int, int],
) -> None:
    pygame.draw.rect(screen, (31, 43, 66), rect, border_radius=5)
    ratio = 0.0 if maximum <= 0 else max(0.0, min(1.0, value / maximum))
    fill = rect.copy()
    fill.width = round(rect.width * ratio)
    if fill.width > 0:
        pygame.draw.rect(screen, color, fill, border_radius=5)


def draw_hud(
    screen: pygame.Surface,
    score: int,
    stability: int,
    resonance: int,
    phase: str | int,
    wave: int,
    *,
    max_stability: int = 100,
    max_resonance: int = 100,
) -> None:
    """Overlay live score, wave, phase, stability, and resonance values.

    Positional arguments retain the original public interface. Phase changes
    passed here are detected once and displayed briefly without blocking.
    """
    global _last_phase, _phase_changed_at
    now = pygame.time.get_ticks()
    if _last_phase is None:
        _last_phase = phase
    elif phase != _last_phase:
        _last_phase = phase
        _phase_changed_at = now

    width, _ = screen.get_size()
    panel_width = min(500, max(0, width - 32))
    if panel_width <= 0:
        return

    panel = pygame.Rect(16, 16, panel_width, 144)
    pygame.draw.rect(screen, _PANEL, panel, border_radius=11)
    pygame.draw.rect(screen, _PANEL_EDGE, panel, width=2, border_radius=11)
    _draw_text(
        screen, f"SCORE  {max(0, int(score)):06d}", 27, _TEXT,
        (panel.x + 16, panel.y + 10), bold=True,
    )
    phase_name, _, phase_color = _phase_details(phase)
    _draw_text(
        screen, f"WAVE {max(1, int(wave))}  /  {phase_name.upper()}",
        17, phase_color, (panel.x + 16, panel.y + 44), bold=True,
    )

    gap = 18
    bar_width = max(1, (panel.width - 48 - gap) // 2)
    first_x = panel.x + 16
    second_x = first_x + bar_width + gap
    label_y = panel.y + 75
    stability_max = max(1, max_stability)
    resonance_max = max(1, max_resonance)
    stability_value = max(0, min(stability_max, stability))
    resonance_value = max(0, min(resonance_max, resonance))
    _draw_text(
        screen, f"REALITY STABILITY  {stability_value}/{stability_max}",
        15, _TEXT, (first_x, label_y),
    )
    _draw_text(
        screen, f"GRAVITY RESONANCE  {resonance_value}/{resonance_max}",
        15, _TEXT, (second_x, label_y),
    )
    bar_y = panel.y + 105
    stability_color = _GREEN if stability_value > stability_max * 0.3 else _RED
    _draw_bar(
        screen, pygame.Rect(first_x, bar_y, bar_width, 14),
        stability_value, stability_max, stability_color,
    )
    _draw_bar(
        screen, pygame.Rect(second_x, bar_y, bar_width, 14),
        resonance_value, resonance_max, _PURPLE,
    )

    if _phase_changed_at and now - _phase_changed_at < _PHASE_TRANSITION_MS:
        draw_phase_transition(screen, phase)


def draw_hud_for_systems(
    screen: pygame.Surface,
    systems: object,
    phase: str | int,
) -> None:
    """Draw the HUD using the existing GameSystems-compatible attributes."""
    draw_hud(
        screen,
        getattr(systems, "score", 0),
        getattr(systems, "stability", 0),
        getattr(systems, "resonance", 0),
        phase,
        getattr(systems, "wave", 1),
        max_stability=getattr(systems, "max_stability", 100),
        max_resonance=getattr(systems, "max_resonance", 100),
    )


def draw_game_over_screen(
    screen: pygame.Surface,
    final_score: int,
    final_wave: int | None = None,
    selected: int = 0,
) -> None:
    """Paint the game-over menu; ``selected`` is 0 for Restart and 1 for Quit."""
    _draw_backdrop(screen)
    width, height = screen.get_size()
    center_x = width // 2
    selected = max(0, min(1, selected))
    _draw_text(
        screen, "GAME OVER", max(44, min(70, width // 10)), _RED,
        (center_x, int(height * 0.29)), center=True, bold=True,
    )
    _draw_text(
        screen, f"FINAL SCORE  {max(0, int(final_score))}", 31, _TEXT,
        (center_x, int(height * 0.43)), center=True, bold=True,
    )
    if final_wave is not None:
        _draw_text(
            screen, f"WAVE REACHED  {max(1, int(final_wave))}", 22, _MUTED,
            (center_x, int(height * 0.43) + 38), center=True,
        )
    button_width = min(300, max(180, width - 48))
    button_x = center_x - button_width // 2
    button_y = int(height * 0.59)
    for index, label in enumerate(("RESTART", "QUIT")):
        _draw_button(
            screen, label,
            pygame.Rect(button_x, button_y + index * 60, button_width, 48),
            selected == index,
        )
    _draw_text(
        screen, "UP / DOWN SELECT     ENTER CONFIRM     R RESTART     ESC QUIT",
        max(13, min(18, width // 48)), _MUTED,
        (center_x, height - 24), center=True,
    )


def draw_pause_screen(screen: pygame.Surface, selected: int = 0) -> None:
    """Draw a pause overlay for a caller that already manages a paused state."""
    width, height = screen.get_size()
    shade = pygame.Surface((width, height), pygame.SRCALPHA)
    shade.fill((3, 6, 17, 190))
    screen.blit(shade, (0, 0))
    center_x = width // 2
    _draw_text(
        screen, "PAUSED", 58, _TEXT,
        (center_x, int(height * 0.38)), center=True, bold=True,
    )
    button_width = min(280, max(180, width - 48))
    button_x = center_x - button_width // 2
    button_y = int(height * 0.52)
    for index, label in enumerate(("RESUME", "QUIT")):
        _draw_button(
            screen, label,
            pygame.Rect(button_x, button_y + index * 60, button_width, 48),
            max(0, min(1, selected)) == index,
        )


def draw_phase_transition(screen: pygame.Surface, phase: str | int) -> None:
    """Draw the current phase's name and brief transition message."""
    width, height = screen.get_size()
    name, message, accent = _phase_details(phase)
    panel_width = min(560, max(0, width - 32))
    if panel_width <= 0:
        return
    banner = pygame.Rect(0, 0, panel_width, 100)
    banner.center = (width // 2, min(max(112, height // 3), height - 56))
    pygame.draw.rect(screen, _PANEL, banner, border_radius=12)
    pygame.draw.rect(screen, accent, banner, width=2, border_radius=12)
    _draw_text(
        screen, name.upper(), 30, _TEXT,
        (banner.centerx, banner.y + 35), center=True, bold=True,
    )
    _draw_text(
        screen, message, 18, accent,
        (banner.centerx, banner.y + 70), center=True,
    )
