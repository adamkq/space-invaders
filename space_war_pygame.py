# Space War in pg
# By Adam Kilbourne-Quirk 2020-02-25

import os, sys, time, psutil
import math, random
import pygame as pg

'''
Notes:
co-ords from top left
colors are RGBA tuples. Specific color tuples given by: pg.Color("name")
Dictionary of colors given by pg.color.THECOLORS

The process of redrawing the background is called "Blitting"
A pygame 'surface' object takes the place of an image file, for primitive shapes.

Keycodes: http://thepythongamebook.com/en:glossary:p:pygame:keycodes

How to rotate:
https://kidscancode.org/blog/2016/08/pygame_shmup_part_6/


'''

# Initialisation
pg.init()

# Non-fullscreen mode is very slow on Mac
FULLSCREEN = True

if FULLSCREEN:
    # flags only work in fullscreen
    wn = pg.display.set_mode((1440, 900), pg.FULLSCREEN | pg.HWSURFACE | pg.DOUBLEBUF)
else:
    wn = pg.display.set_mode((800, 600), pg.RESIZABLE)

pg.display.set_caption("Space War")

background = pg.Surface(wn.get_size())
background = background.convert()
background.fill(pg.Color("gray"))


class Actor:
    def __init__(self, start_x, start_y, start_hdg=0, velocity=0, width=50, height=50, color=(255,255,255)):
        self.x = start_x
        self.y = start_y
        self.hdg = start_hdg
        self.w = width
        self.h = height
        self.color = color
        self.vel = velocity

        # alpha flag allows rotation
        self.surf = pg.Surface((self.w, self.h)).convert()
        #self.surf.fill(self.color)
        C = (int(self.w / 2), int(self.h / 2))
        r = int(self.w / 2)
        pg.draw.polygon(self.surf, self.color, ((50, 50), (20, 40), (40, 20)))
    def draw(self):
        pass

    def surface(self):
        return self.surf

    def get_rect(self):
        return pg.Rect(self.x, self.y, self.w, self.h)

    def rotate(self, angle):
        # degrees
        self.surf = pg.transform.rotate(self.surf, angle)


    def move(self, keys):
        if keys[pg.K_LEFT]:
            self.x -= self.vel
        if keys[pg.K_RIGHT]:
            self.x += self.vel
        if keys[pg.K_UP]:
            self.y -= self.vel
        if keys[pg.K_DOWN]:
            self.y += self.vel
        if keys[pg.K_r]:
            self.rotate(45)

        self.x = max(min(self.x, wn_x - self.w - b_offset), b_offset)
        self.y = max(min(self.y, wn_y - self.h - b_offset), b_offset)

def redraw():
    pass
actor = Actor(50, 50, 0, 10, 50, 50, pg.Color("cyan"))
wn_x, wn_y = wn.get_size()
b_offset = 10
t = pg.time.Clock()
for _ in vars(pg.key):
    print(_)

run = True
while run:
    pg.time.delay(1)

    # Poll
    keys = pg.key.get_pressed()
    if keys[pg.K_ESCAPE]:
        break
    for event in pg.event.get():
        if event.type == pg.QUIT:
            run = False

    # Update
    actor.move(keys)

    actor.draw()

    # Draw, Back to Front
    wn.blit(background, (0, 0))
    wn.blit(actor.surface(), actor.get_rect())

    # Show
    pg.display.flip()

    # Timing
    t.tick()
    #print(t.get_fps())

pg.quit()