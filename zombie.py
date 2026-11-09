"""
zombie.py - Zombie AI for Survive the Night (person 2)

The game is turn based on the 10x7 house grid. Each round the player spends
their actions, then main.py calls ``zombies.take_turn(...)`` once. Every frame
main.py also calls ``update(dt)``, ``draw_overlay(...)`` and ``draw(...)`` so
zombies glide between cells instead of teleporting.

AI = finite state machine

    PATROL --hears a noise--> INVESTIGATE --sees player--> CHASE
       ^                        |    ^                       |
       +--gives up after N rounds    +-----loses sight-------+

    CHASE and standing next to the player -> ATTACK (damage, ends its turn)

Senses
  * Sight: up to SIGHT_RANGE cells inside a 120 degree cone in front of the
    zombie, blocked by walls and closed doors (ray march between cell
    centres). A cell right next to the zombie is always noticed. A player
    hiding in a wardrobe is never seen.
  * Hearing: every noise has a loudness = how many steps the sound travels
    through open doorways (walls stop it). A zombie in range walks over to
    check the loudest noise it heard.

Movement uses breadth first search (shortest path on the grid) around walls,
furniture, other zombies and the player.

API for the rest of the team
  zombies.make_noise(cell, loudness, source)    # walk / run / search / noise maker
  events = zombies.take_turn(player_cell, player_hidden)
  zombies.occupied(cell)                         # block the player from walking into a zombie
  zombies.noise_level, zombies.alerted, zombies.busy
"""

import math
import random
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import pygame

from settings import COLS, ROWS, cell_to_xy, xy_to_cell
from map import ROOMS

# ---------------------------------------------------------------- tuning
SIGHT_RANGE = 3.5        # cells, centre to centre
FOV_COS = 0.5            # cos(60 deg) -> 120 degree vision cone
PATROL_STEPS = 1         # cells moved per round in each state
INVESTIGATE_STEPS = 1
CHASE_STEPS = 2
ATTACK_DAMAGE = 1
LINGER_ROUNDS = 2        # rounds spent looking around before giving up
DETOUR_LIMIT = 3         # extra cells a zombie will walk to get around another zombie
MOVE_SPEED = 3.5         # animation only: cells per second
HIT_FX_TIME = 0.9        # seconds the bite marks stay on screen
SPAWN_TIME = 0.8         # seconds the "rising from the ground" frame is shown

# Loudness = how many steps a sound travels through the house.
NOISE_WALK = 1
NOISE_SEARCH = 2
NOISE_RUN = 3
NOISE_MAKER = 6

PATROL = "patrol"
INVESTIGATE = "investigate"
CHASE = "chase"

DIRS = [(0, -1), (1, 0), (0, 1), (-1, 0)]   # clockwise: up, right, down, left

DEFAULT_SPAWNS = [
    # Guards the hallway and the living room, i.e. the way to the exit.
    {"cell": "G5", "patrol": ["G5", "F3", "G1", "J2", "G1", "F3"], "facing": (0, -1)},
    # Shambles between the garage and the kitchen.
    {"cell": "E7", "patrol": ["E7", "A6", "B5", "C4", "B5", "A6"], "facing": (-1, 0)},
]

# The team's zombie art: zombie_<down|up|left|right>_<stand|walk|attack>.png
# plus zombie_spawn.png. If any pose is missing, a placeholder zombie is drawn
# with pygame shapes instead.
ASSET_DIR = Path(__file__).resolve().parent / "assets" / "zombie"


# ---------------------------------------------------------------- grid helpers
def _cell(x, y):
    return xy_to_cell((x, y))


def _in_grid(x, y):
    return 0 <= x < COLS and 0 <= y < ROWS


def bfs_path(board, start, goal, blocked=frozenset()):
    """Shortest path from start to goal as a list of cells (start excluded).

    Cells in ``blocked`` cannot be entered, except the goal itself, so a
    zombie can plan a path towards a cell that somebody is standing on.
    Returns None when the goal cannot be reached.
    """
    if start == goal:
        return []
    came_from = {start: None}
    queue = deque([start])
    while queue:
        current = queue.popleft()
        if current == goal:
            break
        for nxt in board.neighbors(current):
            if nxt in came_from or (nxt in blocked and nxt != goal):
                continue
            came_from[nxt] = current
            queue.append(nxt)
    if goal not in came_from:
        return None
    path = []
    node = goal
    while node != start:
        path.append(node)
        node = came_from[node]
    path.reverse()
    return path


def sound_reach(board, origin, loudness):
    """{cell: steps} for every cell a sound reaches. Walls stop it, doorways don't."""
    dist = {origin: 0}
    queue = deque([origin])
    while queue:
        current = queue.popleft()
        if dist[current] >= loudness:
            continue
        for nxt in board.neighbors(current, ignore_locks=True):
            if nxt not in dist:
                dist[nxt] = dist[current] + 1
                queue.append(nxt)
    return dist


def _open_edge(board, a, b):
    return board.can_step(_cell(*a), _cell(*b))


def has_line_of_sight(board, a, b):
    """March along the line between two cell centres. Fails if the line
    crosses a wall, a closed door or a sealed-off cell."""
    ax, ay = cell_to_xy(a)
    bx, by = cell_to_xy(b)
    steps = max(abs(bx - ax), abs(by - ay)) * 8
    px, py = ax, ay
    for i in range(1, steps + 1):
        t = i / steps
        cx = math.floor(ax + (bx - ax) * t + 0.5)
        cy = math.floor(ay + (by - ay) * t + 0.5)
        if (cx, cy) == (px, py):
            continue
        dx, dy = cx - px, cy - py
        if dx and dy:
            # The line passes a corner: it is visible if either way round is open.
            ok = False
            for via in ((px + dx, py), (px, py + dy)):
                if (_in_grid(*via) and _open_edge(board, (px, py), via)
                        and _open_edge(board, via, (cx, cy))):
                    ok = True
                    break
        else:
            ok = _open_edge(board, (px, py), (cx, cy))
        if not ok:
            return False
        px, py = cx, cy
    return True


# ---------------------------------------------------------------- data
@dataclass
class Noise:
    cell: str
    loudness: int
    source: str = ""


@dataclass
class ZombieEvent:
    kind: str            # "spotted", "heard", "lost", "gave_up", "attack"
    zombie: "Zombie"
    damage: int = 0


# ---------------------------------------------------------------- zombie
class Zombie:
    def __init__(self, cell, patrol=None, facing=(0, 1)):
        self.cell = cell
        self.patrol = list(patrol or [])
        self.patrol_index = 0
        self.facing = facing
        self.state = PATROL
        self.target = None        # cell being chased / investigated / wandered to
        self.linger = 0
        self.path = []            # current plan, shown in the F1 debug overlay
        self.visible_cells = set()

        # animation state
        x, y = cell_to_xy(cell)
        self.draw_x, self.draw_y = float(x), float(y)
        self.move_queue = deque()
        self.walk_time = 0.0
        self.lunge = 0.0          # 1 -> 0 while the attack plays
        self.attack_queued = False  # wait for the last walk frame before attacking
        self.attack_fx_ready = False
        self.attack_target = None
        self.icon_pop = 0.0       # 1 -> 0 when "!" or "?" appears
        self.spawn_time = SPAWN_TIME
        self.steps_this_turn = 0
        self.step_badge = 0

    # senses
    def can_see(self, board, target):
        zx, zy = cell_to_xy(self.cell)
        tx, ty = cell_to_xy(target)
        dx, dy = tx - zx, ty - zy
        dist = math.hypot(dx, dy)
        if dist == 0:
            return True
        if dist > SIGHT_RANGE:
            return False
        if dist > 1.01:
            fx, fy = self.facing
            if (dx * fx + dy * fy) / dist < FOV_COS:
                return False
        return has_line_of_sight(board, self.cell, target)

    def compute_visible(self, board):
        self.visible_cells = set()
        for y in range(ROWS):
            for x in range(COLS):
                cell = _cell(x, y)
                if board.inside(cell) and self.can_see(board, cell):
                    self.visible_cells.add(cell)

    # movement
    def step_to(self, cell):
        x0, y0 = cell_to_xy(self.cell)
        x1, y1 = cell_to_xy(cell)
        self.facing = (x1 - x0, y1 - y0)
        self.cell = cell
        self.move_queue.append((x1, y1))
        self.steps_this_turn += 1
        if self.path and self.path[0] == cell:
            self.path = self.path[1:]     # keep only the cells still ahead

    def face(self, cell):
        zx, zy = cell_to_xy(self.cell)
        tx, ty = cell_to_xy(cell)
        dx, dy = tx - zx, ty - zy
        if dx and abs(dx) >= abs(dy):
            self.facing = (1 if dx > 0 else -1, 0)
        elif dy:
            self.facing = (0, 1 if dy > 0 else -1)

    def turn_clockwise(self):
        self.facing = DIRS[(DIRS.index(self.facing) + 1) % 4]

    def queue_attack(self, target):
        """Show the bite only after reaching the adjacent tile visually."""
        self.face(target)
        self.attack_target = target
        self.attack_queued = True

    @property
    def busy(self):
        return bool(self.move_queue) or self.attack_queued or self.lunge > 0

    def update(self, dt):
        if self.move_queue:
            tx, ty = self.move_queue[0]
            dx, dy = tx - self.draw_x, ty - self.draw_y
            dist = math.hypot(dx, dy)
            step = MOVE_SPEED * dt
            if dist <= step:
                self.draw_x, self.draw_y = float(tx), float(ty)
                self.move_queue.popleft()
                self.step_badge += 1
            else:
                self.draw_x += dx / dist * step
                self.draw_y += dy / dist * step
            self.walk_time += dt
        # Walk animation finishes before the attack pose begins.
        if not self.move_queue and self.attack_queued:
            self.attack_queued = False
            self.lunge = 1.0
            self.attack_fx_ready = True
        else:
            self.lunge = max(0.0, self.lunge - dt * 3)
        self.icon_pop = max(0.0, self.icon_pop - dt * 4)
        self.spawn_time = max(0.0, self.spawn_time - dt)


# ---------------------------------------------------------------- manager
class ZombieManager:
    def __init__(self, board, furniture=None, spawns=None, seed=None):
        self.board = board
        self.furniture = furniture
        self.spawns = spawns or DEFAULT_SPAWNS
        self.rng = random.Random(seed)
        self.debug = False        # F1: paths, targets and state names
        self.show_vision = False  # blind zombies: no vision tint
        self._frames = None
        self._frame_size = None
        self._font = None
        self._small_font = None
        self.reset()

    def reset(self):
        self.zombies = [Zombie(**spec) for spec in self.spawns]
        self.noises = []
        self.noise_level = 0      # loudest noise made this round (for the HUD)
        self._rings = []          # [cell, loudness, age]
        self._hits = []           # [cell, age]
        for z in self.zombies:
            z.visible_cells.clear()

    # ---- API used by the other modules
    def make_noise(self, cell, loudness, source=""):
        if loudness <= 0:
            return
        self.noises.append(Noise(cell, loudness, source))
        self.noise_level = max(self.noise_level, loudness)
        self._rings.append([cell, loudness, 0.0])

    def occupied(self, cell):
        return any(z.cell == cell for z in self.zombies)

    @property
    def busy(self):
        return any(z.busy for z in self.zombies)

    @property
    def alerted(self):
        return any(z.state == CHASE for z in self.zombies)

    def take_turn(self, player_cell, player_hidden=False, priority_noise=None, hide_escape=False):
        """Run one zombie phase. Returns a list of ZombieEvent."""
        events = []
        heard = [(n, sound_reach(self.board, n.cell, n.loudness)) for n in self.noises]
        for z in self.zombies:
            z.steps_this_turn = 0
            z.step_badge = 0
            if hide_escape and player_hidden and self._evacuate_room(z, player_cell):
                continue
            self._zombie_turn(z, player_cell, player_hidden, heard, events, priority_noise)
            z.visible_cells.clear()
        # The Remote influences THIS Zombie Turn only. Never carry its
        # investigation target into the next turn, even when unreachable.
        # Do not erase normal sightings or investigations of player sounds.
        for z in self.zombies:
            maker_target = getattr(z, "noise_maker_target", None)
            if maker_target is not None:
                z.noise_maker_target = None
                if z.state == INVESTIGATE and z.target == maker_target:
                    z.state = PATROL
                    z.target = None
        self.noises.clear()
        self.noise_level = 0
        return events

    def _room_for(self, cell):
        x, y = cell_to_xy(cell)
        for name, (rx, ry, rw, rh), _ in ROOMS:
            if rx <= x < rx + rw and ry <= y < ry + rh:
                return name
        return None

    def _evacuate_room(self, z, hidden_cell):
        """If a zombie shares the hiding room, leave via a legal path, with no step cap."""
        room = self._room_for(hidden_cell)
        if room is None or self._room_for(z.cell) != room:
            return False
        furniture = set(getattr(self.furniture, "blocked_cells", set()))
        occupied = {other.cell for other in self.zombies if other is not z}
        candidates = []
        for y in range(ROWS):
            for x in range(COLS):
                cell = _cell(x, y)
                if (self.board.inside(cell) and self._room_for(cell) != room
                        and cell not in furniture and cell not in occupied
                        and cell != hidden_cell):
                    path = bfs_path(self.board, z.cell, cell,
                                    furniture | occupied | {hidden_cell})
                    if path is not None:
                        candidates.append((len(path), cell, path))
        if not candidates:
            return False
        _, _, path = min(candidates)
        for step in path:
            z.step_to(step)
        z.state = PATROL
        z.target = None
        z.noise_maker_target = None
        return True

    # ---- AI
    def _zombie_turn(self, z, player_cell, hidden, heard, events, priority_noise=None):
        """Move using only sound this zombie can hear through passable edges.

        Logical positions are planned now; queue_attack delays the visual bite
        until the zombie finishes drawing its queued movement path.
        """
        audible = [(noise, reach) for noise, reach in heard if z.cell in reach]
        normal = max((n for n, _ in audible if n.source != "noise_maker"),
                     key=lambda n: n.loudness, default=None)
        budget = max((int(n.loudness) for n, _ in audible), default=0)
        maker_cell = priority_noise[0] if priority_noise is not None else None
        maker_audible = (maker_cell is not None and
                         any(n.source == "noise_maker" and n.cell == maker_cell
                             for n, _ in audible))
        if maker_audible and budget > 0:
            maker_path = bfs_path(self.board, z.cell, maker_cell,
                                  set(getattr(self.furniture, "blocked_cells", set()))
                                  | {o.cell for o in self.zombies if o is not z}
                                  | {player_cell})
            if maker_path is not None:
                self._set_state(z, INVESTIGATE, maker_cell, events)
                # Approach the device within the current turn's movement budget.
                for _ in range(min(budget, len(maker_path))):
                    nxt = self._next_step(z, maker_cell, player_cell)
                    if nxt is None:
                        break
                    z.step_to(nxt)
                budget = max(0, budget - z.steps_this_turn)
        if normal is not None and not hidden:
            self._set_state(z, INVESTIGATE, normal.cell, events)
            for _ in range(budget):
                # A bite consumes one remaining movement step. An edge, not
                # proximity alone, decides whether an attack is legal.
                if self.board.can_step(z.cell, player_cell):
                    z.queue_attack(player_cell)
                    events.append(ZombieEvent("attack", z, ATTACK_DAMAGE))
                    return
                nxt = self._next_step(z, normal.cell, player_cell)
                if nxt is None:
                    break
                z.step_to(nxt)
        elif not maker_audible:
            # No audible sound: follow the normal patrol, one grid step.
            self._set_state(z, PATROL, None, events)
            goal = self._goal(z)
            nxt = self._next_step(z, goal, player_cell)
            if nxt is not None:
                z.step_to(nxt)

    def _set_state(self, z, state, target, events):
        if state != z.state:
            z.icon_pop = 1.0
            if state == CHASE:
                kind = "spotted"
            elif state == INVESTIGATE:
                kind = "lost" if z.state == CHASE else "heard"
            else:
                kind = "gave_up"
            events.append(ZombieEvent(kind, z))
        z.state = state
        z.target = target
        if state != PATROL:
            z.linger = LINGER_ROUNDS

    def _loudest_heard(self, z, heard):
        best, best_key = None, None
        for noise, reach in heard:
            if z.cell in reach:
                key = (noise.loudness, -reach[z.cell])
                if best_key is None or key >= best_key:   # ties: newest noise wins
                    best, best_key = noise, key
        return best

    def _goal(self, z):
        if z.state in (CHASE, INVESTIGATE):
            return z.target
        if z.patrol:
            if z.cell == z.patrol[z.patrol_index]:
                self._advance_patrol(z)
            return z.patrol[z.patrol_index]
        # No route: wander to random nearby cells.
        if z.target is None or z.target == z.cell:
            z.target = self._random_nearby(z.cell, 5)
        return z.target

    def _advance_patrol(self, z):
        if z.patrol:
            z.patrol_index = (z.patrol_index + 1) % len(z.patrol)
        else:
            z.target = None

    def _random_nearby(self, cell, radius):
        reach = sound_reach(self.board, cell, radius)
        options = [c for c in reach if c != cell and not self._static_blocked(c)]
        return self.rng.choice(options) if options else cell

    def _static_blocked(self, cell):
        return self.furniture is not None and self.furniture.is_blocked(cell)

    def _next_step(self, z, goal, player_cell):
        if goal is None:
            return None
        furniture = getattr(self.furniture, "blocked_cells", set())
        others = {o.cell for o in self.zombies if o is not z}
        blocked = set(furniture) | others | {player_cell}
        around = bfs_path(self.board, z.cell, goal, blocked)
        through = bfs_path(self.board, z.cell, goal, blocked - others)
        # Another zombie in the way: walk around it only if that is not much
        # longer, otherwise wait behind it (it will usually move next turn).
        if around is not None and (through is None or len(around) <= len(through) + DETOUR_LIMIT):
            path = around
        else:
            path = through
        z.path = path or []
        if not path or path[0] in blocked:
            return None
        return path[0]

    # ---- per frame
    def update(self, dt):
        # The first frame (or a frame after the window was dragged) can report a
        # huge dt; cap it so animations never skip.
        dt = min(dt, 0.05)
        for z in self.zombies:
            z.update(dt)
        for z in self.zombies:
            if z.attack_fx_ready:
                self._hits.append([z.attack_target, 0.0])
                z.attack_fx_ready = False
        for ring in self._rings:
            ring[2] += dt
        self._rings = [r for r in self._rings if r[2] < 1.0]
        for hit in self._hits:
            hit[1] += dt
        self._hits = [h for h in self._hits if h[1] < HIT_FX_TIME]

    def draw_overlay(self, surface, get_cell_center):
        """Floor layer: vision cones, noise rings, debug paths. Draw before the player."""
        cx0, cy0, tw, th = self._geometry(get_cell_center)

        if self.show_vision:
            for z in self.zombies:
                alpha = 55 if z.state == CHASE else 35
                tint = pygame.Surface((tw, th), pygame.SRCALPHA)
                tint.fill((255, 50, 50, alpha))
                for cell in z.visible_cells:
                    x, y = get_cell_center(cell)
                    surface.blit(tint, (x - tw // 2, y - th // 2))

        for cell, loudness, age in self._rings:
            x, y = get_cell_center(cell)
            radius = max(4, int(tw * (0.3 + loudness * age)))
            alpha = int(200 * (1 - age))
            ring = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(ring, (255, 240, 170, alpha), (radius + 2, radius + 2), radius, 3)
            surface.blit(ring, (x - radius - 2, y - radius - 2))

        if self.debug:
            font = self._get_small_font()
            for z in self.zombies:
                points = [self._to_px(cx0, cy0, tw, th, z.draw_x, z.draw_y)]
                points += [get_cell_center(c) for c in z.path]
                if len(points) > 1:
                    pygame.draw.lines(surface, (255, 220, 80), False, points, 2)
                for p in points[1:]:
                    pygame.draw.circle(surface, (255, 220, 80), p, 4)
                if z.target:
                    tx, ty = get_cell_center(z.target)
                    pygame.draw.line(surface, (255, 120, 60), (tx - 8, ty - 8), (tx + 8, ty + 8), 3)
                    pygame.draw.line(surface, (255, 120, 60), (tx - 8, ty + 8), (tx + 8, ty - 8), 3)
                label = z.state.upper()
                if z.state == INVESTIGATE:
                    label += f" ({z.linger})"
                text = font.render(label, True, (255, 255, 255))
                px, py = self._to_px(cx0, cy0, tw, th, z.draw_x, z.draw_y)
                bg = pygame.Surface((text.get_width() + 8, text.get_height() + 2), pygame.SRCALPHA)
                bg.fill((0, 0, 0, 170))
                surface.blit(bg, (px - bg.get_width() // 2, py + th * 0.36))
                surface.blit(text, (px - text.get_width() // 2, py + th * 0.36 + 1))

    def draw(self, surface, get_cell_center):
        """Zombies, alert icons and bite effects. Draw after the player."""
        cx0, cy0, tw, th = self._geometry(get_cell_center)
        frames = self._get_frames((int(tw * 0.95), int(th * 0.92)))

        for z in sorted(self.zombies, key=lambda zz: zz.draw_y):
            px, py = self._to_px(cx0, cy0, tw, th, z.draw_x, z.draw_y)
            if z.lunge > 0:
                push = math.sin(z.lunge * math.pi) * tw * 0.28
                px += z.facing[0] * push
                py += z.facing[1] * push
            moving = bool(z.move_queue)
            if moving:
                py -= abs(math.sin(z.walk_time * 14)) * 3

            image = self._pick_frame(frames, z, moving)
            w, h = image.get_size()
            if frames["kind"] == "pose":
                # Front-view character: feet near the bottom of its cell.
                feet = py + th * 0.42
                shadow = pygame.Surface((int(tw * 0.5), int(th * 0.16)), pygame.SRCALPHA)
                pygame.draw.ellipse(shadow, (0, 0, 0, 90), shadow.get_rect())
                surface.blit(shadow, shadow.get_rect(center=(round(px), round(feet - 3))))
                rect = image.get_rect(midbottom=(round(px), round(feet)))
            else:
                shadow = pygame.Surface((int(w * 0.7), int(h * 0.5)), pygame.SRCALPHA)
                pygame.draw.ellipse(shadow, (0, 0, 0, 80), shadow.get_rect())
                surface.blit(shadow, shadow.get_rect(center=(px + 3, py + 6)))
                rect = image.get_rect(center=(round(px), round(py)))
            surface.blit(image, rect)

            # Show how many grid cells this zombie travelled this turn.
            badge = self._get_small_font().render(str(z.step_badge), True, (255, 255, 255))
            bx, by = round(px), min(rect.top, round(py - th * 0.45)) - 24
            pygame.draw.circle(surface, (35, 38, 49), (bx, by), 14)
            pygame.draw.circle(surface, (244, 200, 86), (bx, by), 14, 2)
            surface.blit(badge, badge.get_rect(center=(bx, by)))


        for cell, age in self._hits:
            x, y = get_cell_center(cell)
            alpha = int(255 * (1 - age / HIT_FX_TIME))
            claw = pygame.Surface((tw, th), pygame.SRCALPHA)
            for i in (-1, 0, 1):
                ox = i * tw * 0.16
                pygame.draw.line(claw, (120, 0, 0, alpha),
                                 (tw * 0.32 + ox, th * 0.2), (tw * 0.54 + ox, th * 0.8), 9)
                pygame.draw.line(claw, (240, 40, 40, alpha),
                                 (tw * 0.32 + ox, th * 0.2), (tw * 0.54 + ox, th * 0.8), 5)
            surface.blit(claw, (x - tw // 2, y - th // 2))

    # ---- drawing helpers
    @staticmethod
    def _geometry(get_cell_center):
        ax, ay = get_cell_center("A1")
        bx, by = get_cell_center("B2")
        return ax, ay, bx - ax, by - ay

    @staticmethod
    def _to_px(cx0, cy0, tw, th, gx, gy):
        return cx0 + gx * tw, cy0 + gy * th

    def _get_font(self):
        if self._font is None:
            self._font = pygame.font.SysFont("arial", 24, bold=True)
        return self._font

    def _get_small_font(self):
        if self._small_font is None:
            self._small_font = pygame.font.SysFont("arial", 13, bold=True)
        return self._small_font

    def _draw_icon(self, surface, x, y, z):
        chase = z.state == CHASE
        color = (235, 50, 50) if chase else (250, 210, 60)
        scale = 1 + 0.6 * z.icon_pop
        r = int(13 * scale)
        pygame.draw.circle(surface, (20, 20, 20), (int(x), int(y)), r + 2)
        pygame.draw.circle(surface, color, (int(x), int(y)), r)
        text = self._get_font().render("!" if chase else "?", True, (255, 255, 255) if chase else (40, 30, 10))
        if scale != 1:
            text = pygame.transform.smoothscale(
                text, (int(text.get_width() * scale), int(text.get_height() * scale)))
        surface.blit(text, text.get_rect(center=(int(x), int(y) + 1)))

    def _get_frames(self, box):
        if self._frames is None or self._frame_size != box:
            self._frames = _load_sprite_frames(box) or _make_placeholder_frames(int(min(box) * 0.98))
            self._frame_size = box
        return self._frames

    @staticmethod
    def _pick_frame(frames, z, moving):
        if frames["kind"] == "topdown":
            seq = frames[z.facing]
            return seq[int(z.walk_time * 8) % len(seq)] if moving else seq[0]
        if z.spawn_time > 0 and frames.get("spawn"):
            return frames["spawn"]
        poses = frames[z.facing]
        if z.lunge > 0:
            return poses["attack"]
        if moving:                         # 2-frame walk cycle: walk, stand, walk, ...
            return poses["walk"] if int(z.walk_time * 6) % 2 == 0 else poses["stand"]
        return poses["stand"]


# ---------------------------------------------------------------- sprites
DIR_NAMES = {(0, 1): "down", (0, -1): "up", (-1, 0): "left", (1, 0): "right"}
POSES = ("stand", "walk", "attack")


def _load_sprite_frames(box):
    """Load the team's zombie art. Every pose was drawn on the same canvas, so
    one scale for all of them keeps the character the same size in every pose."""
    paths = {(d, p): ASSET_DIR / f"zombie_{name}_{p}.png" for d, name in DIR_NAMES.items() for p in POSES}
    if not all(path.exists() for path in paths.values()):
        return None
    images = {key: pygame.image.load(str(path)).convert_alpha() for key, path in paths.items()}
    ref_w, ref_h = images[((0, 1), "stand")].get_size()
    ratio = min(box[0] / ref_w, box[1] / ref_h)

    def fit(img):
        return pygame.transform.smoothscale(
            img, (max(1, round(img.get_width() * ratio)), max(1, round(img.get_height() * ratio))))

    frames = {"kind": "pose"}
    for (direction, pose), img in images.items():
        frames.setdefault(direction, {})[pose] = fit(img)
    spawn = ASSET_DIR / "zombie_spawn.png"
    frames["spawn"] = fit(pygame.image.load(str(spawn)).convert_alpha()) if spawn.exists() else None
    return frames


def _make_placeholder_frames(size):
    """Top-down zombie made of shapes, arms reaching forward. 4 walk frames x 4 directions."""
    skin, skin_dark = (124, 168, 96), (70, 104, 58)
    shirt, shirt_dark = (92, 78, 104), (56, 46, 66)
    c = size / 2
    base = []
    for i in range(4):
        swing = math.sin(i / 4 * 2 * math.pi) * size * 0.07
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        arm_w = max(4, int(size * 0.13))
        arm_len = size * 0.34
        for side, s in ((-1, swing), (1, -swing)):
            rect = pygame.Rect(int(c + side * size * 0.21 - arm_w / 2), int(c),
                               arm_w, int(arm_len + s))
            pygame.draw.rect(surf, skin_dark, rect.inflate(3, 3), border_radius=arm_w // 2)
            pygame.draw.rect(surf, skin, rect, border_radius=arm_w // 2)
        body = pygame.Rect(0, 0, int(size * 0.6), int(size * 0.34))
        body.center = (int(c), int(c - size * 0.04))
        pygame.draw.ellipse(surf, shirt_dark, body.inflate(4, 4))
        pygame.draw.ellipse(surf, shirt, body)
        head = (int(c), int(c + size * 0.02))
        r = int(size * 0.16)
        pygame.draw.circle(surf, skin_dark, head, r + 2)
        pygame.draw.circle(surf, skin, head, r)
        for side in (-1, 1):
            eye = (int(c + side * r * 0.45), int(head[1] + r * 0.5))
            pygame.draw.circle(surf, (225, 35, 35), eye, max(2, int(size * 0.035)))
        base.append(surf)
    angles = {(0, 1): 0, (1, 0): 90, (0, -1): 180, (-1, 0): -90}
    frames = {"kind": "topdown"}
    for facing, angle in angles.items():
        frames[facing] = [pygame.transform.rotate(f, angle) for f in base]
    return frames
