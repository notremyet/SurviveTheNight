"""Shortest traversable path on the board (including turns)."""
from collections import deque


def find_path(board, furniture, start, goal, max_steps):
    if start == goal or not board.inside(goal) or furniture.is_blocked(goal):
        return None
    queue = deque([(start,)])
    visited = {start}
    while queue:
        path = queue.popleft()
        current = path[-1]
        if current == goal:
            return list(path)
        if len(path) - 1 >= max_steps:
            continue
        for neighbor in board.neighbors(current):
            if neighbor not in visited and not furniture.is_blocked(neighbor):
                visited.add(neighbor)
                queue.append(path + (neighbor,))
    return None


def reachable_cells(board, furniture, start, max_steps=2):
    """Shortest-path distances for tiles reachable without crossing obstacles."""
    distances = {start: 0}
    queue = deque([start])
    while queue:
        current = queue.popleft()
        if distances[current] >= max_steps:
            continue
        for neighbor in board.neighbors(current):
            if neighbor not in distances and not furniture.is_blocked(neighbor):
                distances[neighbor] = distances[current] + 1
                queue.append(neighbor)
    return distances
