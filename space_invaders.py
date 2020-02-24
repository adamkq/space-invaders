# Space Invaders
# By Adam Kilbourne-Quirk 2020-02-22

import os, sys, time, psutil
import math, random
import turtle

# Required by MacOS to show the window
turtle.fd(0)
turtle.speed(30)
# Hide default turtle
turtle.ht()
turtle.delay(0)
# Improve memory
turtle.setundobuffer(1)
turtle.tracer(0)

# Screen
wn = turtle.Screen()
wn.title("Space Invaders")
wn.bgcolor("black")
wn.colormode(255)

class Sprite(turtle.Turtle):
	def __init__(self, shape, color, start_x, start_y, start_hdg):
		turtle.Turtle.__init__(self, shape = shape)
		self.speed(0)
		self.color(color)
		self.penup()

		self.goto(start_x, start_y)
		self.speed = 0
		self.size = 10 # this is the turtle default; find out how to set this
		self.setheading(start_hdg)

	def bounce(self, wall_angle):
		# bounce = 2 * wall - approach
		self.setheading(-self.heading() + 2 * wall_angle) 

	def move(self):
		# boundaries
		b1 = game.border_size - self.size - self.speed/2

		# x-speed reflect
		if not (-b1 < self.xcor() < b1):
			self.bounce(90)

		# y-speed reflect
		if not (-b1 < self.ycor() < b1):
			self.bounce(0)

		self.fd(self.speed)

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

class Player(Sprite):
	def __init__(self, shape, color, start_x, start_y, start_hdg):
		Sprite.__init__(self, shape, color, start_x, start_y, start_hdg)
		self.speed = 4
		self.start_loc = (start_x, start_y, start_hdg)
		self.setheading(self.start_loc[2])
		self.max_fwd_speed = 10
		self.max_rev_speed = 5
		self.max_turn_speed = 22.5
		
		self.start_lives = 3
		self.lives = self.start_lives
		self.start_bombs = 3
		self.bombs = self.start_bombs
		self.rof = 4 # Rate of Fire; bullets per second
		self.time_since_fire = time.time()
		self.is_invuln = False
		self.time_since_invuln = time.time()
		self.time_invuln = 0

	def fire(self):
		if time.time() - self.time_since_fire > 1/max(self.rof, 1e-6):
			self.time_since_fire = time.time()
			bullet = Bullet("triangle", "yellow", self.xcor(), self.ycor(), self.heading(), self.speed)
			bullet.fire()

	def bomb(self):
		if self.bombs < 1:
			return
		if time.time() - self.time_since_fire > 1/max(self.rof, 1e-6):
			self.time_since_fire = time.time()
			for fragment in range(0, 360, 10):
				bullet = Bullet("triangle", "yellow", self.xcor(), self.ycor(), fragment, self.speed)
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
			self.color("blue")
		elif (time.time() - self.time_since_invuln) % flash_interval > flash_interval/2:
			self.color("black")
		else:
			self.color("blue")

	def respawn(self):
		self.penup()
		self.clear()
		self.goto(self.start_loc[0], self.start_loc[1])
		self.setheading(self.start_loc[2])

class Enemy(Sprite):
	def __init__(self, shape="square", color="red", start_x=0, start_y=0, start_hdg=0):
		Sprite.__init__(self, shape, color, start_x, start_y, start_hdg)
		self.aim_pt = turtle.Turtle()
		self.aim_pt.color("white")
		self.aim_pt.ht()

		self.speed = 4
		self.guidance = 0
		self.max_turn_speed = 10

		self.random_steps = 0
		b = game.border_size - int(self.speed)
		self.random_ax = random.randint(-b, b)
		self.random_ay = random.randint(-b, b)

	def autopilot(self, player):
		# manoeuvers Enemy based on guidance
		# 0: Patrol. Does not maneuver or respond to player.
		# 1: Random. Maneuvers but does not respond to player.
		# 2: Pursuit. Points itself directly at player.
		# 3: Pro-Nav. Tries to aim ahead of player.
		# 4: Mirror. Moves to opposite side of space from player.

		px = player.xcor()
		py = player.ycor()
		ax = self.xcor()
		ay = self.ycor()
		if self.guidance == 1:
			self.random_steps = (self.random_steps + 1) % 50
			if self.random_steps == 0:
				b = game.border_size - int(self.speed)
				self.random_ax = random.randint(-b, b)
				self.random_ay = random.randint(-b, b)
			ax = self.random_ax
			ay = self.random_ay

		elif self.guidance == 2:
			ax = px
			ay = py

		elif self.guidance == 3:
			N = player.speed/max(self.speed, 1) * self.distance(px, py)
			ax = px + math.cos(math.pi/180 * player.heading()) * N
			ay = py + math.sin(math.pi/180 * player.heading()) * N

		elif self.guidance == 4:
			ax = -px
			ay = -py

		else:
			return

		if game.show_aim_pts:
			self.draw_aim_pt(ax, ay)
		brg = self.bearing(ax, ay)
		command = 0.5 * self.brg_error(brg)
		self.lt(max(min(self.max_turn_speed, command), -self.max_turn_speed))

	def draw_aim_pt(self, ax, ay):
		self.aim_pt.goto(ax, ay)
		self.aim_pt.clear()
		self.aim_pt.dot()

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

class Prize(Sprite):
	def __init__(self, shape="circle", color="white", start_x=0, start_y=0, start_hdg=0):
		Sprite.__init__(self, shape, color, start_x, start_y, start_hdg)
		self.goto(start_x, start_y)
		self.speed = 0
		self.time_since_respawn = float("-inf")
		self.respawn_interval = 10

	def award(self):
		game.increment_lives(1)
		player.invuln_on(1)
		self.respawn()

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

class Bullet(Sprite):
	def __init__(self, shape, color, start_x, start_y, start_hdg, player_speed=0):
		Sprite.__init__(self, shape, color, start_x, start_y, start_hdg)
		self.shapesize(stretch_wid = 0.3, stretch_len = 0.4, outline=None)
		self.speed = 20 + player.speed
		self.setheading(start_hdg)

	def fire(self):
		self.goto(player.xcor(), player.ycor())
		game.bullets.append(self)

	def move(self):
		# boundaries
		b = game.border_size - self.speed
		if not (-b < self.xcor() < b) or not (-b < self.ycor() < b):
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
	def __init__(self):
		self.non_enemies = []
		self.enemies = []
		self.bullets = []
		self.score = self.highScore = 0
		self.show_aim_pts = True
		self.pen = turtle.Turtle()
		self.text = turtle.Turtle()

	def draw_border(self, border_size=350):
		self.border_size = border_size

		self.pen.speed(0)
		self.pen.color("white")
		self.pen.penup()
		self.pen.setposition(-border_size, -border_size)
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
		if player.lives == 0:
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

# Game Init
border_size = 350
game = Game()
game.draw_border(border_size)

# Sprites
player = Player("triangle", "blue", 0, -250, 90)
prize = Prize()
game.non_enemies.append(player)
game.non_enemies.append(prize)
numEnemies = 5

color_dict = {0:"green", 1:"purple", 2:"orange red", 3:"red", 4:"brown"}
for i in range(numEnemies):
	e = Enemy()
	e.guidance = i % 5
	e.color(color_dict[e.guidance])
	e.speed = 2 + i / 2
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
		turtle.update()
		sprites = game.non_enemies + game.enemies + game.bullets
		for sprite in sprites:
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

	except KeyboardInterrupt:
		break

mem.append(process.memory_info().rss)
print("\nMemory Usage")
print("Start: {}\nEnd:   {}".format(mem[0], mem[1]))
