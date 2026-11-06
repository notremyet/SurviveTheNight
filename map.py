
import pygame
from settings import *

# Boundary pairs on either side of each wall or door. Derived from the PDF board.
# All internal walls are explicitly represented; only listed gaps are passable doors.
DOORS = [('C2','C3'), ('D1','E1'), ('D4','E4'), ('E1','F1'), ('E4','F4'), ('F2','F3'),
         ('B5','B6'), ('E6','F6'), ('G6','H6')]
WALLS = set()

def edge(a,b): return frozenset((a,b))

def add_wall(a,b): WALLS.add(edge(a,b))

# Bedroom / kitchen: row 2/3 boundary, columns A-D except C door
for c in 'ABCD':
    if c != 'C': add_wall(c+'2',c+'3')
# Central corridor E: doors at D1/E1, D4/E4 and E1/F1, E4/F4.
for r in range(1,6):
    if r not in (1,4):
        add_wall('D'+str(r),'E'+str(r))
        add_wall('E'+str(r),'F'+str(r))
# Living room / hallway boundary: row 2/3, columns F-J except F door
for c in 'FGHIJ':
    if c != 'F': add_wall(c+'2',c+'3')
# Hallway and inaccessible cells boundary: G/H at rows 3-5
for r in (3,4,5): add_wall('G'+str(r),'H'+str(r))
# Kitchen / garage boundary: row 5/6 columns A-E except B door
for c in 'ACDE': add_wall(c+'5',c+'6')
# Garage / hallway boundary: E/F at row 6, E/F at row 7 wall
add_wall('E7','F7')
# Hallway / exit: G/H boundary at row 6 door, row 7 wall
add_wall('G7','H7')

BLOCKED = {f'{c}{r}' for c in 'HIJ' for r in (3,4,5)}
ROOMS = [ ('BEDROOM',(0,0,4,2),(44,54,63)), ('LIVING ROOM',(5,0,5,2),(45,65,52)),
          ('KITCHEN',(0,2,4,3),(49,65,66)), ('HALLWAY',(5,2,2,5),(66,61,51)),
          ('GARAGE',(0,5,5,2),(59,64,57)), ('EXIT',(7,5,3,2),(45,70,56))]

class Board:
    def __init__(self):
        self.locked = set()
    def inside(self, cell):
        x,y=cell_to_xy(cell)
        return 0<=x<COLS and 0<=y<ROWS and cell not in BLOCKED
    def can_step(self,a,b,ignore_locks=False):
        if not self.inside(a) or not self.inside(b): return False
        ax,ay=cell_to_xy(a); bx,by=cell_to_xy(b)
        if abs(ax-bx)+abs(ay-by)!=1: return False
        e=edge(a,b)
        return e not in WALLS and (ignore_locks or e not in self.locked)
    def neighbors(self,cell,ignore_locks=False):
        x,y=cell_to_xy(cell)
        for dx,dy in [(0,-1),(1,0),(0,1),(-1,0)]:
            xx,yy=x+dx,y+dy
            if 0<=xx<COLS and 0<=yy<ROWS:
                other=xy_to_cell((xx,yy))
                if self.can_step(cell,other,ignore_locks): yield other
    def adjacent_locked(self,cell):
        return [d for d in self.locked if cell in d]
    def draw(self,surface,font):
        for name,(x,y,w,h),color in ROOMS:
            pygame.draw.rect(surface,color,(BOARD_X+x*TILE,BOARD_Y+y*TILE,w*TILE,h*TILE))
        for y in range(ROWS):
            for x in range(COLS):
                cell=xy_to_cell((x,y)); rect=pygame.Rect(BOARD_X+x*TILE,BOARD_Y+y*TILE,TILE,TILE)
                if cell in BLOCKED:
                    pygame.draw.rect(surface,(33,35,41),rect)
                    pygame.draw.line(surface,(60,62,68),rect.topleft,rect.bottomright,1)
                pygame.draw.rect(surface,(95,98,100),rect,1)
                surface.blit(font.render(cell,True,(180,185,185)),(rect.x+5,rect.y+4))
                
                # Small yellow labels at bottom-left
                small_font = pygame.font.SysFont("arial", 14)

                if cell in SEARCH:
                    label = "S"
                elif cell in HIDE:
                    label = "H"
                elif cell == EXIT:
                    label = "E"
                else:
                    label = ""

                if label:
                    label_color = (255, 235, 144)
                    label_surface = small_font.render(label, True, label_color)

                    # Bottom-left corner of each tile
                    label_rect = label_surface.get_rect(
                        bottomleft=(rect.left + 6, rect.bottom - 5)
                    )

                    surface.blit(label_surface, label_rect)

        for a,b in WALLS:
            self._draw_edge(surface,a,b,(8,10,12),7)
        # Door openings have thin gold separators; locked doors get a red bar.
        for a,b in DOORS:
            e=edge(a,b)
            self._draw_edge(surface,a,b,(210,170,92) if e not in self.locked else (225,65,65),3 if e not in self.locked else 7)
    def _draw_edge(self,surface,a,b,color,width):
        ax,ay=cell_to_xy(a);bx,by=cell_to_xy(b)
        if ax!=bx:
            x=BOARD_X+max(ax,bx)*TILE; y=BOARD_Y+ay*TILE
            pygame.draw.line(surface,color,(x,y),(x,y+TILE),width)
        else:
            x=BOARD_X+ax*TILE;y=BOARD_Y+max(ay,by)*TILE
            pygame.draw.line(surface,color,(x,y),(x+TILE,y),width)
