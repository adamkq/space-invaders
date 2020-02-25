# Space Invaders
# By Adam Kilbourne-Quirk 2020-02-22

import os, sys, time, psutil
import math, random
import turtle

class Sprite(turtle.Turtle):
	def __init__(self, shape, color, start_x, start_y, start_hdg):
		turtle.Turtle.__init__(self, shape = shape)
		self.color(color)
		self.penup()

		self.goto(start_x, start_y)
		self.setheading(start_hdg)
		self.size = 10 # this is the turtle default; find out how to set this


	def distance(self, x, y):
		x1 = self.xcor()
		y1 = self.ycor()
		return ((x - x1)**2 + (y - y1)**2)**0.5

	def bearing(self, x, y):
		x1 = self.xcor()
		y1 = self.ycor()
		return (math.atan2(y - y1, x - x1))*180/math.pi

	def brg_error(self, brg):
		# must have range +/- 180
		if self.heading() < 180:
			hdg = self.heading()
		else:
			hdg = self.heading() - 360

		return brg - hdg # TODO: fix this to avoid discontinuity at 180

	def is_collided(self, other):
		if self.distance(other.xcor(), other.ycor()) < self.size + other.size:
			return True
		else:
			return False

class Character(Sprite):
	def __init__(self, shape, color, start_x, start_y, start_hdg=0, speed=0, max_turn_speed=0):
		Sprite.__init__(self, shape, color, start_x, start_y, start_hdg)
		self.speed = speed
		self.max_turn_speed = max_turn_speed

	def bounce(self, wall_angle):
		# bounce = 2 * wall - approach
		self.setheading(-self.heading() + 2 * wall_angle)

	def move(self):
		# boundaries
		bounds = game.border_size - self.size - self.speed / 2

		# x-speed reflect
		if not (-bounds < self.xcor() < bounds):
			self.bounce(90)

		# y-speed reflect
		if not (-bounds < self.ycor() < bounds):
			self.bounce(0)

		self.fd(self.speed)

	def respawn(self):
		self.penup()
		self.clear()
		while True:
			b = game.border_size - self.size
			x = random.randint(-b, b)
			y = random.randint(-b, b)
			if player.distance(x, y) > game.border_size/4:
				break
		self.goto(x, y)
		self.setheading(random.randint(0, 360))

class Player(Character):
	def __init__(self, shape, color, start_x, start_y, start_hdg, speed=4, max_turn_speed=22.5):
		Character.__init__(self, shape, color, start_x, start_y, start_hdg, speed, max_turn_speed)
		self.start_loc = (start_x, start_y, start_hdg)
		self.start_color = color
		self.max_fwd_speed = 10
		self.max_rev_speed = 5
		
		self.start_lives = 3
		self.lives = self.start_lives
		self.start_bombs = 3
		self.bombs = self.start_bombs
		self.rof = 4 # Rate of Fire; bullets per second
		self.bullet_speed = 30
		self.time_since_fire = time.time()
		self.is_invuln = False
		self.time_since_invuln = time.time()
		self.time_invuln = 0

	def fire(self):
		if time.time() - self.time_since_fire > 1/max(self.rof, 1e-6):
			self.time_since_fire = time.time()
			bullet_speed = self.speed + self.bullet_speed
			bullet = Bullet("triangle", "yellow", self.xcor(), self.ycor(), self.heading(), bullet_speed)
			bullet.fire()

	def bomb(self):
		if self.bombs < 1:
			return
		if time.time() - self.time_since_fire > 1/max(self.rof, 1e-6):
			self.time_since_fire = time.time()
			for fragment in range(0, 360, 10):
				bullet = Bullet("triangle", "yellow", self.xcor(), self.ycor(), fragment, self.bullet_speed)
				bullet.fire()
			self.bombs -= 1
			game.show_score()

	def turn_left(self):
		self.lt(self.max_turn_speed)

	def turn_right(self):
		self.rt(self.max_turn_speed)

	def accel(self):
		self.speed += 1
		self.speed = min(self.speed, self.max_fwd_speed)

	def decel(self):
		self.speed -= 1
		self.speed = max(self.speed, -self.max_rev_speed)

	def invuln_on(self, seconds):
		if not self.is_invuln:
			self.time_since_invuln = time.time()
		self.is_invuln = True
		self.time_invuln += seconds

	def invuln_off(self):
		flash_interval = 0.2
		if not self.is_invuln:
			return
		elif time.time() - self.time_since_invuln > self.time_invuln:
			self.is_invuln = False
			self.time_invuln = 0
			self.color(self.start_color)
		elif (time.time() - self.time_since_invuln) % flash_interval > flash_interval/2:
			self.color("black")
		else:
			self.color(self.start_color)

	def respawn(self):
		self.penup()
		self.clear()
		self.goto(self.start_loc[0], self.start_loc[1])
		self.setheading(self.start_loc[2])

class Enemy(Character):
	def __init__(self, shape="square", color="red", start_x=0, start_y=0, start_hdg=0, speed=4, max_turn_speed=10):
		Character.__init__(self, shape, color, start_x, start_y, start_hdg, speed, max_turn_speed)
		self.aim_pt = turtle.Turtle()
		self.aim_pt.color("white")
		self.aim_pt.ht()

		self.guidance = 0
		self.random_steps = 0
		b = game.border_size - int(self.speed)
		self.ax_rand = random.randint(-b, b)
		self.ay_rand = random.randint(-b, b)
		self.dist_prev = 0

	def autopilot(self, player):
		'''
		Pick a pt to navigate to based on guidance
		0: Patrol. Does not maneuver or respond to player.
		1: Random. Maneuvers but does not respond to player.
		2: Pursuit. Points directly at player.
		3: Pro-Nav. Aims ahead of player.
		4: Mirror. Moves to opposite side of space from player.
		5: Avoidance. Moves away from player.
		'''
		px = player.xcor()
		py = player.ycor()
		ax = self.xcor()
		ay = self.ycor()
		bounds = game.border_size - 2 * self.size
		if self.guidance == 1:
			self.random_steps = (self.random_steps + 1) % 50
			if self.random_steps == 0:
				self.ax_rand = random.randint(-bounds, bounds)
				self.ay_rand = random.randint(-bounds, bounds)
			ax = self.ax_rand
			ay = self.ay_rand

		elif self.guidance == 2:
			ax = px
			ay = py

		elif self.guidance == 3:
			'''
			PN aims ahead of the player to 'close the triangle' formed by the Player, Enemy, and aimpoint.
			The aimpoint pt is a point in the direction the player is moving such that the Enemy will reach it at the 
			same time as the player if both do not turn. Using the rule of cosines:
			 c**2 = a**2 + b**2 -2*a*b*cos(C)
			Substituting:
			0. C = angle between player heading and player bearing
			1. a = player.dist(enemy)
			2. b = player.dist(pt)
			3. c = enemy.dist(pt) = b / N
			b**2/N**2 = a**2 + b**2 - 2abcos(C)
			b**2/N**2 - b**2 + 2abcos(C) = a**2
			b**2(1/N**2 - 1) + b(2acos(C)) - a**2 = 0
			
			Solve quadratic eqn with coeffs:
			c0 = -a**2
			c1 = 2acos(C)
			c2 = 1/N**2 - 1
			'''
			p_dist = self.distance(px, py)
			N = player.speed/max(self.speed, 1)

			# check if player is moving
			# if not, aim directly at it
			if N == 0:
				ax = px
				ay = py
			# if yes, pre-empt it
			else:
				C = player.brg_error(player.bearing(ax, ay))
				c0 = -(p_dist ** 2)
				c1 = 2 * p_dist * math.cos(math.pi / 180 * C)
				c2 = 1/(N**2) - 1


				if c2 == 0 or not (-90 < C < 90):
					aim_dist = N * p_dist
				else:
					temp = c1**2 - 4 * c2 * c0
					# avoid complex numbers
					temp = max(temp, 0)
					b1 = (-c1 + temp**0.5) / (2 * c2)
					b2 = (-c1 - temp**0.5) / (2 * c2)
					aim_dist = max(min(b1, b2), 0)

				ax = px + math.cos(math.pi / 180 * player.heading()) * aim_dist
				ay = py + math.sin(math.pi / 180 * player.heading()) * aim_dist

		elif self.guidance == 4:
			ax = -px
			ay = -py

		elif self.guidance == 5:
			'''
			pick corner by quadrant
			'''
			corners = [(-bounds, -bounds), (bounds, -bounds), (bounds, bounds), (-bounds, bounds)]
			corner_max = corners[1]

			for corner in corners:
				if player.distance(corner[0], corner[1]) > player.distance(corner_max[0], corner_max[1]):
					corner_max = corner
			ax = corner_max[0]
			ay = corner_max[1]

		else:
			return

		ax = max(min(bounds, ax), -bounds)
		ay = max(min(bounds, ay), -bounds)
		if game.show_aim_pts:
			self.draw_aim_pt(ax, ay)
		brg = self.bearing(ax, ay)
		command = 0.5 * self.brg_error(brg)
		self.lt(max(min(self.max_turn_speed, command), -self.max_turn_speed))

	def draw_aim_pt(self, ax, ay):
		self.aim_pt.goto(ax, ay)
		self.aim_pt.clear()
		self.aim_pt.dot()

class Prize(Character):
	def __init__(self, shape="circle", color="white", start_x=0, start_y=0):
		Character.__init__(self, shape, color, start_x, start_y)
		self.time_since_respawn = float("-inf")
		self.respawn_interval = 10

	def award(self):
		game.increment_lives(1)
		player.invuln_on(1)
		self.respawn()

class Bullet(Sprite):
	def __init__(self, shape, color, start_x, start_y, start_hdg, speed):
		Sprite.__init__(self, shape, color, start_x, start_y, start_hdg)
		self.shapesize(stretch_wid = 0.3, stretch_len = 0.4, outline=None)
		self.speed = speed

	def fire(self):
		self.goto(player.xcor(), player.ycor())
		game.bullets.append(self)

	def move(self):
		# boundaries
		bounds = game.border_size - self.speed / 2
		if not (-bounds < self.xcor() < bounds) or not (-bounds < self.ycor() < bounds):
			self.goto(-370, self.ycor())
			self.__del__()
		else:
			self.fd(self.speed)

	def __del__(self):
		try:
			game.bullets.remove(self)
			self.reset()
		except:
			pass

class Game():
	def __init__(self, player_can_die=False, show_aim_pts=True, num_enemies=6, border_size=350):
		self.non_enemies = []
		self.enemies = []
		self.bullets = []
		self.score = self.highScore = 0
		self.player_can_die = player_can_die
		self.show_aim_pts = show_aim_pts
		self.num_enemies = num_enemies
		self.border_size = border_size

		self.pen = turtle.Turtle()
		self.text = turtle.Turtle()
		self.time_delta = 1/30

	def draw_border(self, border_size=350):
		self.pen.speed(0)
		self.pen.color("white")
		self.pen.penup()
		self.pen.setposition(-self.border_size, -self.border_size)
		self.pen.pendown()
		self.pen.pensize(3)
		for side in range(4):
			self.pen.fd(border_size*2)
			self.pen.lt(90)
		self.pen.ht()

	def increment_score(self, score):
		temp = self.score
		self.score += score
		self.highScore = max(self.score, self.highScore)
		if score > 0 and self.score//1000 - temp//1000 > 0:
			player.bombs += 1
		game.show_score()

	def increment_lives(self, lives):
		player.lives += lives
		if player.lives < 1 and self.player_can_die:
			game.reset_game()
		game.show_score()

	def reset_game(self):
		player.lives = player.start_lives
		self.score = 0
		player.bombs = player.start_bombs
		sprites = game.non_enemies + game.enemies
		for sprite in sprites:
			sprite.respawn()
		game.show_score()

	def show_score(self):
		self.text.speed(0)
		self.text.color("white")
		self.text.penup()
		self.text.goto(-300, 360)
		s = "Score: {0:<5}\t Lives: {1:<5}\t Bombs: {2:<5}\t High Score: {3:<5}".format(str(self.score), str(player.lives), str(player.bombs), str(self.highScore))
		self.text.clear()
		self.text.write(s, font=("Arial", 16, "normal"))

	def exit_game(self):
		turtle.bye()

# Turtle setup
turtle.fd(0)
turtle.speed(30)
turtle.ht()
turtle.delay(0)
turtle.setundobuffer(1)
turtle.tracer(0)

# Screen
wn = turtle.Screen()
wn.title("Space Invaders")
wn.bgcolor("black")
wn.colormode(255)

# Game Init
game = Game()
game.draw_border()

# Sprites
player = Player("triangle", "cyan", 0, -250, 90)
prize = Prize()
game.non_enemies.append(player)
game.non_enemies.append(prize)

color_dict = {0:"green", 1:"lightgreen", 2:"orange red", 3:"red", 4:"brown", 5:"purple"}
for i in range(game.num_enemies):
	e = Enemy()
	e.guidance = i % 6
	e.color(color_dict[e.guidance % len(color_dict)])
	e.speed = min(2 + i / 2, 5)
	game.enemies.append(e)

# Reset
game.reset_game()

# Keyboard Bindings
turtle.listen()
turtle.onkey(player.turn_left, "Left")
turtle.onkey(player.turn_right, "Right")
turtle.onkey(player.accel, "Up")
turtle.onkey(player.decel, "Down")
turtle.onkey(player.respawn, "r")
turtle.onkey(player.fire, "z")
turtle.onkey(player.bomb, "space")
turtle.onkey(game.exit_game, "q")

print("Press Q or Ctrl-C to Finish.")
mem = []
process = psutil.Process(os.getpid())
mem.append(process.memory_info().rss)

while True:
	try:
		t1 = time.time()
		turtle.update()
		sprites = game.non_enemies + game.enemies + game.bullets
		for i, sprite in enumerate(sprites):
			sprite.move()
			if isinstance(sprite, Player):
				player.invuln_off()
				if player.is_collided(prize):
					prize.award()
			if isinstance(sprite, Enemy):
				# if collided with player or bullet or OOB, respawn
				sprite.autopilot(player)
				if player.is_collided(sprite) and not player.is_invuln:
					game.increment_lives(-1)
					sprite.respawn()
					player.invuln_on(3)
				for bullet in game.bullets:
					if bullet.is_collided(sprite):
						game.increment_score(100)
						sprite.respawn()
				b = game.border_size
				if not (-b < sprite.xcor() < b) or not (-b < sprite.ycor() < b):
					sprite.respawn()
		t2 = time.time()
		game.time_delta = t2 - t1
	except KeyboardInterrupt:
		break

mem.append(process.memory_info().rss)
print("\nMemory Usage")
print("Start: {}\nEnd:   {}".format(mem[0], mem[1]))
