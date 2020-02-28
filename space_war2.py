"""
Space War 2
By Adam Kilbourne-Quirk 2020-02-27

User features compared to previous:

Multiple players
Player autopilot
More weapons
Status effects apply to more agents

Code features compared to previous:

Geometry now done by separate class
Cleaner inheritances
Similar params moved to tuples for cleaner code
"""

import os, sys, time, psutil, gc
import math, random
import turtle
from collections import namedtuple


class Geometry:
    Point = namedtuple('Point', 'x y hdg')

    @staticmethod
    def dist(pt1, pt2):
        """
		Euclidean distance between 2 points
		"""
        return ((pt2.x - pt1.x) ** 2 + (pt2.y - pt1.y) ** 2) ** 0.5

    @staticmethod
    def brg(pt1, pt2):
        """
		Bearing from pt1 to pt2, with reference right = 0 degrees, CCW
		"""
        return (math.atan2(pt2.y - pt1.y, pt2.x - pt1.x)) * 180 / math.pi

    @staticmethod
    def brg_relative(pt1, pt2):
        """
		Difference between pt1 heading and its bearing to pt2
		Use the cross product: sin(C) = cross(a, b) / [mag(a) * mag(b)]
		"""

        x1 = math.cos(math.pi / 180 * pt1.hdg)
        y1 = math.sin(math.pi / 180 * pt1.hdg)
        x2 = pt2.x - pt1.x
        y2 = pt2.y - pt1.y
        d = Geometry.dist(pt1, pt2)
        if d == 0:
            sin_C = 0
        else:
            sin_C = (x1 * y2 - x2 * y1) / d
        return math.asin(sin_C) * 180 / math.pi

    @staticmethod
    def is_collided(sprite1, sprite2):
        """
		Simple collision between 2 sprites based on size. Sizes can be negative.
		"""

        bounds = sprite1.size + sprite2.size
        if Geometry.dist(sprite1.get_pos(), sprite2.get_pos()) < bounds:
            return True
        return False

    @staticmethod
    def is_in_rect(sprite, pt1, pt2):
        """
        Checks if sprite is in the rectangle defined by the two points. Ignores sprite size.
        """
        pt = sprite.get_pos()
        if min(pt1.x, pt2.x) < pt.x < max(pt1.x, pt2.x) and min(pt1.y, pt2.y) < pt.y < max(pt1.y, pt2.y):
            return True
        return False

class SpaceWar:
    def __init__(self, running=True, frame_rate=30):
        turtle.speed(frame_rate)
        self.running = running
        self.sprites = []
        self.bounds_x = 800  # based on window size
        self.bounds_y = 450  # based on window size
        self.bounds_ul = Geometry.Point(-self.bounds_x, self.bounds_y, 0)
        self.bounds_lr = Geometry.Point(self.bounds_x, -self.bounds_y, 0)

    def reset(self):
        pass

    def update_sprites(self):
        for sprite in self.sprites:
            if sprite.active:
                sprite.update()
                # bounds check
                if not Geometry.is_in_rect(sprite, self.bounds_ul, self.bounds_lr):
                    sprite.respawn()
                if isinstance(sprite, Player):
                    if sprite.status_invuln.active:
                        pass
                    # check if enemies collided w/ player
                    elif any([Geometry.is_collided(sprite, e) for e in self.sprites if isinstance(e, Enemy)]):
                        sprite.set_status_invuln(3)
                        sprite.respawn()

                if isinstance(sprite, Projectile):
                    for e in self.sprites:
                        if isinstance(e, Enemy) and Geometry.is_collided(e, sprite):
                            e.respawn()
                            if isinstance(sprite, Bomb):
                                sprite.detonate()



    def update_text(self):
        pass

    def show_player_scores(self):
        pass

    def exit_game(self):
        turtle.bye()
        self.running = False


class Sprite(turtle.Turtle):
    """
	Top-level class for drawing basic sprites

	Inner Classes:
	Image: for setting sprite shape and color together
	Status: for tracking temporary true/false attributes of an instance. Statuses are then checked by
		the update function of the class. Default tuple values are finnicky in Python, but most constructors should use:
		(active, duration, time_activated) = (False, 0, float('-inf'))
	"""

    Image = namedtuple('Image', [
        'shape',
        'color'
    ])
    Status = namedtuple('Status', [
        'active',
        'duration',
        'time_activated'
    ])

    def __init__(self, pos, image, size=10, active=True):
        turtle.Turtle.__init__(self, shape=image[0])
        self.penup()
        self.set_pos(pos)

        self.active = active
        self.spawn_time = time.time()
        self.color(image.color)
        self.size = size

        self.status_flashing = Sprite.Status(False, 0., float('-inf'))
        self.start_color = image.color

    def set_pos(self, pos=Geometry.Point(0, 0, 0)):
        self.goto(pos.x, pos.y)
        self.setheading(pos.hdg)

    def get_pos(self):
        return Geometry.Point(self.xcor(), self.ycor(), self.heading())

    def set_status_flashing(self, seconds=3):
        self.status_flashing = Sprite.Status(True, seconds, time.time())

    def update(self):
        if self.status_flashing.active:
            # deactivate
            if time.time() - self.status_flashing.time_activated > self.status_flashing.duration:
                self.status_flashing = Sprite.Status(False, 0., float('-inf'))
                self.color(self.start_color)
            # still active
            else:
                flash_interval = 0.2
                if (time.time() - self.status_flashing.time_activated) % flash_interval > flash_interval / 2:
                    self.color("black")
                else:
                    self.color(self.start_color)


class Agent(Sprite):
    """
	Class for sprites which can respawn or navigate to targets or respond to keyboard input.

	Inner Classes:
	SpeedLimits: defines limits on how fast the Agent can move forward, backward, or rotationally.
		The intent is for these to remain the same throughout the game, so there shouldn't be an issue using tuples.
		Max rev speed should be a negative number in most cases.
	"""

    SpeedLimits = namedtuple('SpeedLimits', [
        'max_fwd_speed',
        'max_rev_speed',
        'max_turn_speed'
    ])

    def __init__(self, pos, image, speed=0, respawn_delay=0, speed_limits=SpeedLimits(15, -5, 22.5), lives=3, rof=4):
        Sprite.__init__(self, pos, image)
        # general params
        self.speed = speed
        self.respawn_pt = pos
        self.respawn_delay = respawn_delay
        self.speed_limits = speed_limits
        self.lives = lives
        self.status_cant_move = Agent.Status(False, 0., float('-inf'))

        # agent targets itself to start; targeting requires high-level logic and may change over time, so it
        # will be done with a separate method
        # aim pt drawing will be done with a high-level turtle
        self.target = self
        self.guidance_mode = 0
        self.aim_pt = pos

        # keeps the agent from firing a weapon until a certain amount of time has passed
        self.status_cant_fire = Agent.Status(False, 0., float('-inf'))
        self.rof = rof
        self.bullet_speed = 30

    def update(self):
        if not self.status_cant_move.active:
            self.move()
        if self.status_cant_fire.active:
            if time.time() - self.status_cant_fire.time_activated > self.status_cant_fire.duration:
                self.status_cant_fire = Agent.Status(False, 0., float('-inf'))

        super().update()

    def move(self):
        """
        Presently, sprites can only move in the direction they are facing. I may change this by adding 'drift' behavior
        to make agents move more like an actual spacecraft.
        """
        self.speed = max(min(self.speed, self.speed_limits.max_fwd_speed), self.speed_limits.max_rev_speed)
        self.fd(self.speed)

    def respawn(self):
        self.set_pos(self.respawn_pt)

        # TODO: move guidance and autopilot functions here

    def fire_bullet(self):
        if not self.status_cant_fire.active:
            self.status_cant_fire = Sprite.Status(True, 1 / max(self.rof, 1e-6), time.time())
            bullet_img = Sprite.Image("triangle","yellow")
            bullet_speed = self.speed + self.bullet_speed
            bullet = Bullet(self.get_pos(), bullet_img, self, bullet_speed)
            game.sprites.append(bullet)

    def fire_bounce(self):
        if not self.status_cant_fire.active:
            self.status_cant_fire = Sprite.Status(True, 1 / max(self.rof, 1e-6), time.time())
            bullet_img = Sprite.Image("circle", "magenta")
            bullet_speed = self.speed + self.bullet_speed / 2
            bullet = Bullet(self.get_pos(), bullet_img, self, bullet_speed, 20)
            game.sprites.append(bullet)

    def fire_bomb(self):
        if not self.status_cant_fire.active:
            self.status_cant_fire = Sprite.Status(True, 1 / max(self.rof, 1e-6), time.time())
            bullet_img = Sprite.Image("circle", "red")
            bullet_speed = self.bullet_speed
            bullet = Bomb(self.get_pos(), bullet_img, self, bullet_speed)
            game.sprites.append(bullet)

class Player(Agent):
    def __init__(self, pos=Geometry.Point(0, -100, 90), image=Sprite.Image("triangle", "cyan"), speed=4,
                 respawn_delay=0,
                 speed_limits=Agent.SpeedLimits(15, -5, 22.5), lives=3, rof=4):
        Agent.__init__(self, pos, image, speed, respawn_delay, speed_limits, lives, rof)
        self.score = 0
        self.high_score = 0
        self.bombs = 3
        self.status_invuln = Player.Status(False, 0., float('-inf'))
        self.is_on_autopilot = False

    def update(self):
        if self.status_invuln.active:
            if time.time() - self.status_invuln.time_activated > self.status_invuln.duration:
                self.status_invuln = Player.Status(False, 0., float('-inf'))
        super().update()

    def turn_left(self):
        self.lt(self.speed_limits.max_turn_speed)

    def turn_right(self):
        self.rt(self.speed_limits.max_turn_speed)

    def accel(self):
        self.speed += 1

    def decel(self):
        self.speed -= 1

    def set_status_invuln(self, seconds):
        self.status_invuln = Player.Status(True, seconds, time.time())
        self.set_status_flashing(seconds)


class Enemy(Agent):
    color_dict = {0: "green", 1: "lightgreen", 2: "orange red", 3: "red", 4: "brown", 5: "blue"}

    def __init__(self, pos=Geometry.Point(0, 0, 0), image=Sprite.Image("square", "red"), speed=4, respawn_delay=0,
                 speed_limits=Agent.SpeedLimits(8, 0, 10), lives=1, rof=0.5):
        Agent.__init__(self, pos, image, speed, respawn_delay, speed_limits, lives, rof)
        # TODO: fix color/guidance dependency
        self.color(Enemy.color_dict[self.guidance_mode % len(Enemy.color_dict)])
        self.status_scattered = Enemy.Status(False, 0., float('-inf'))
        self.guidance_mode_start = self.guidance_mode
        self.random_steps = 50

    def update(self):
        if self.status_scattered.active:
            # try to deactivate
            if time.time() - self.status_scattered.time_activated > self.status_scattered.duration:
                self.status_scattered = Sprite.Status(False, 0., float('-inf'))
                self.set_guidance(self.guidance_mode_start)
                self.speed *= 2
        self.guidance()
        self.autopilot()
        self.weapons()

        super().update()

    def set_guidance(self, guidance_mode):
        self.guidance_mode = guidance_mode
        self.color(Enemy.color_dict[guidance_mode % len(Enemy.color_dict)])

    def guidance(self):
        """
        Pick a pt to navigate to based on guidance mode
        0: Patrol. Does not maneuver or respond to player.
        1: Random. Maneuvers but does not respond to player.
        2: Pursuit. Points directly at player.
        3: Pro-Nav. Aims ahead of player.
        4: Mirror. Moves to opposite side of space from player.
        5: Avoidance. Moves away from player.
        """
        px, py, p_hdg = self.target.get_pos()
        ax, ay, a_hdg = self.get_pos()

        if self.guidance_mode == 1:
            ax = self.aim_pt.x + random.randint(-10, 10)
            ay = self.aim_pt.y + random.randint(-10, 10)
        elif self.guidance_mode == 2:
            """
            aim at player
            """
            ax = px
            ay = py

        elif self.guidance_mode == 3:
            """
            PN aims ahead of the player to 'close the triangle' formed by the Player, Enemy, and aimpoint.
            The aimpoint pt is a point in the direction the player is moving such that the Enemy will reach it at the 
            same time as the player if both do not turn. Using the rule of cosines:
             c**2 = a**2 + b**2 -2ab*cos(C)
            Substituting:
            0. C = angle between player heading and player bearing
            1. a = player.dist(enemy)
            2. b = player.dist(pt)
            3. c = enemy.dist(pt) = b / N
            b**2/N**2 = a**2 + b**2 - 2ab*cos(C)
            b**2/N**2 - b**2 + 2ab*cos(C) = a**2
            b**2(1/N**2 - 1) + b(2a*cos(C)) - a**2 = 0

            Solve quadratic eqn with coeffs:
            c0 = -a**2
            c1 = 2a*cos(C)
            c2 = 1/N**2 - 1

            When N = 1, c = b, and the equation becomes linear:
            b = a/2cos(C), C != +/- 90
            """
            p_dist = Geometry.dist(self.get_pos(), self.target.get_pos())
            N = self.target.speed / max(self.speed, 1)
            aim_dist = 0

            # if player is not moving, aim directly at it
            if abs(N) > 0:
                c0 = -(p_dist ** 2)
                c1 = 2 * p_dist * math.cos(math.pi / 180 * Geometry.brg_relative(self.get_pos(), self.target.get_pos()))
                c2 = 1 / (N ** 2) - 1

                # N == +/-1; edge case
                if abs(c2) < 1e-6:
                    aim_dist = -c0 / c1
                else:
                    temp = c1 ** 2 - 4 * c2 * c0
                    # avoid complex numbers
                    temp = max(temp, 0)
                    b1 = (-c1 + temp ** 0.5) / (2 * c2)
                    b2 = (-c1 - temp ** 0.5) / (2 * c2)
                    aim_dist = max(min(b1, b2), 0)
                if self.target.speed < 0:
                    aim_dist *= -1

            ax = px + math.cos(math.pi / 180 * self.target.heading()) * aim_dist
            ay = py + math.sin(math.pi / 180 * self.target.heading()) * aim_dist

        elif self.guidance_mode == 4:
            """
            move towards opposite side of the area
            """
            ax = -px
            ay = -py

        elif self.guidance_mode == 5:
            """
            move directly away from player
            """
            ax = 2 * ax - px
            ay = 2 * ay - py

        self.aim_pt = Geometry.Point(ax, ay, 0)

    def autopilot(self):
        command = 0.5 * Geometry.brg_relative(self.get_pos(), self.aim_pt)
        self.lt(max(min(self.speed_limits.max_turn_speed, command), -self.speed_limits.max_turn_speed))

    def weapons(self):
        pa = self.get_pos()
        pt = self.target.get_pos()
        if abs(Geometry.brg_relative(pa, pt)) < 3:
            if Geometry.dist(pa, pt) < self.size * 6:
                self.fire_bounce()
            else:
                self.fire_bullet()

    def set_status_scattered(self, seconds=3):
        self.status_scattered = Enemy.Status(True, seconds, time.time())
        self.set_guidance(5)
        self.speed *= 0.5


class Prize(Agent):
    pass

class Projectile(Sprite):
    def __init__(self, pos, image, fired_by=None, speed=30, bounces=0):
        Sprite.__init__(self, pos, image)
        self.speed = speed
        self.fired_by = fired_by
        self.bounces = bounces

    def update(self):
        super().update()

    def respawn(self):
        self.goto(1000, 1000)
        self.active = False
        self.clear()
        try:
            game.sprites.remove(self)
        except:
            pass
        gc.collect()

    def wall_hit(self):
        pass

class Bullet(Projectile):
    def __init__(self, pos, image, fired_by=None, speed=30, bounces=0):
        Projectile.__init__(self, pos, image, fired_by, speed, bounces)
        self.shapesize(stretch_wid=0.3, stretch_len=0.4, outline=None)
        self.size = 2
        self.lifetime = 30 # seconds

    def update(self):
        self.move()
        super().update()

    def move(self):
        self.fd(self.speed)

class Bomb(Projectile):
    def __init__(self, pos, image, fired_by=None, speed=10, bounces=0):
        Projectile.__init__(self, pos, image, fired_by, speed, bounces)
        self.size = 10
        self.lifetime = 5 # seconds
        self.speed_decay = 0.9 # how quickly does the bomb slow down
        self.fragments = 20 # how many bullets does it make
        self.set_status_flashing(self.lifetime - 1)

    def update(self):
        # conditions to detonate
        if time.time() - self.spawn_time > self.lifetime or self.bounces < 0:
            self.detonate()
        self.move()
        super().update()

    def move(self):
        self.speed *= self.speed_decay
        self.fd(self.speed)

    def detonate(self):
        for fragment in range(0, 360, int(360/self.fragments)):
            bullet_img = Sprite.Image("triangle","yellow")
            bullet_hdg = Geometry.Point(self.get_pos().x, self.get_pos().y, fragment)
            bullet = Bullet(bullet_hdg, bullet_img, self.fired_by)
            game.sprites.append(bullet)
        self.respawn()

class Wall(Sprite):
    pass
# Turtle setup
turtle.fd(0)
turtle.ht()
turtle.delay(0)
turtle.setundobuffer(1)
turtle.tracer(0)

# Screen
wn = turtle.Screen()
wn.setup(width=1.0, height=1.0)
wn.title("Space War")
wn.bgcolor("black")
wn.colormode(255)

# Sprites

game = SpaceWar()
player = Player()
game.sprites.append(player)
for i in range(6):
    enemy = Enemy()
    enemy.set_guidance(i)
    enemy.speed = 2 + i/2
    enemy.target = player
    game.sprites.append(enemy)

# Keys
turtle.onkey(game.exit_game, "q")

turtle.onkey(player.turn_left, "Left")
turtle.onkey(player.turn_right, "Right")
turtle.onkey(player.accel, "Up")
turtle.onkey(player.decel, "Down")
turtle.onkey(player.set_status_flashing, "f")
turtle.onkey(player.respawn, "r")
turtle.onkey(player.fire_bullet, "z")
turtle.onkey(player.fire_bounce, "x")
turtle.onkey(player.fire_bomb, "space")

turtle.onkey(enemy.set_status_scattered, "s")
turtle.listen()

while game.running:
    t1 = time.time()
    game.update_sprites()
    turtle.update()
    t2 = time.time()
