# Space Invaders
# By Adam Kilbourne-Quirk 2020-02-22

import os, sys, random, math, time
import turtle

# Required by MacOS to show the window
# turtle.fd(0)
# turtle.speed(0)
# # # Hide default turtle
turtle.ht()
turtle.delay(0)
# # # Improve memory
# # turtle.setundobuffer(1)
turtle.tracer(0, 0)

# Screen
wn = turtle.Screen()
wn.title("Space Invaders")
wn.bgcolor("black")
wn.colormode(255)

class Sprite(turtle.Turtle):
	def __init__(self, shape, color, start_x, start_y, start_hdg):
		turtle.Turtle.__init__(self, shape = shape)
		self.speed(0)
		self.penup()
		self.color(color)
		self.fd(0)
		self.goto(start_x, start_y)
		self.speed = 0
		self.size = 10 # this is the turtle default; find out how to set this
		self.setheading(start_hdg)

	def bounce(self, wall_angle):
		# bounce = 2 * wall - approach
		self.setheading(-self.heading() + 2 * wall_angle) 

	def move(self):
		# boundaries
		b1 = game.border_size - self.size
		b2 = -game.border_size + self.size

		# x-speed reflect
		if self.xcor() > b1 or self.xcor() < b2:
			self.bounce(90)

		# y-speed reflect
		if self.ycor() > b1 or self.ycor() < b2:
			self.bounce(0)

		self.fd(self.speed)

	def distance(self, other):
		x1 = self.xcor()
		x2 = other.xcor()
		y1 = self.ycor()
		y2 = other.ycor()
		return ((x2 - x1)**2 + (y2 - y1)**2)**0.5

	def bearing(self, x1, y1, x2, y2):
		return (math.atan2(y2 - y1, x2 - x1))*180/math.pi

	def brgError(self, brg, hdg):
		# must have range +/- 180
		if self.heading() < 180:
			hdg = self.heading()
		else:
			hdg = self.heading() - 360

		return brg - hdg # TODO: fix this to avoid discontinuity at 180

	def isCollided(self, other):
		if self.distance(other) < self.size + other.size:
			return True
		else:
			return False


class Player(Sprite):
	def __init__(self, shape, color, start_x, start_y, start_hdg):
		Sprite.__init__(self, shape, color, start_x, start_y, start_hdg)
		self.speed = 4
		self.lives = 3
		self.setheading(start_hdg)
		self.maxFwdSpeed = 15
		self.maxRevSpeed = 5
		self.maxTurnSpeed = 22.5

	def turn_left(self):
		self.lt(self.maxTurnSpeed)

	def turn_right(self):
		self.rt(self.maxTurnSpeed)

	def accel(self):
		self.speed += 1
		self.speed = min(self.speed, self.maxFwdSpeed)

	def decel(self):
		self.speed -= 1
		self.speed = max(self.speed, -self.maxRevSpeed)

	def respawn(self):
		self.goto(0, 0)

class Enemy(Sprite):
	def __init__(self, shape, color, start_x=0, start_y=0, start_hdg=0):
		Sprite.__init__(self, shape, color, start_x, start_y, start_hdg)
		self.speed = 4
		self.guidance = 0
		self.maxTurnSpeed = 10
		self.randomSteps = 0
		self.randomTurn = random.randint(-self.maxTurnSpeed, self.maxTurnSpeed)

	def autopilot(self, player):
		# manoeuvers Enemy based on guidance
		# 0: Patrol. Does not maneuver or respond to player.
		# 1: Random. Maneuvers but does not respond to player.
		# 2: Pursuit. Points itself directly at player.
		# 3: Pro-Nav. Tries to aim ahead of player.
		# 4: Avoidance. Moves directly away from player.

		if self.guidance == 1:
			self.randomSteps += 1
			if self.randomSteps > 20:
				self.randomSteps = 0
				self.randomTurn = random.randint(-self.maxTurnSpeed, self.maxTurnSpeed)
			self.lt(self.randomTurn) # don't turn too sharply

		elif self.guidance == 2:
			brg = self.bearing(self.xcor(), self.ycor(), player.xcor(), player.ycor())
			brgError = self.brgError(brg, self.heading())

			command = 0.05 * brgError
			self.lt(max(min(self.maxTurnSpeed, command), -self.maxTurnSpeed))

		elif self.guidance == 3:
			# PN
			# a = N*V*LOS
			N = player.speed/max(self.speed, 1)
			px = N * player.xcor() + math.cos(math.pi/180 * player.heading()) * self.distance(player)
			py = N * player.ycor() + math.sin(math.pi/180 * player.heading()) * self.distance(player)
			brg = self.bearing(self.xcor(), self.ycor(), px, py)
			brgError = self.brgError(brg, self.heading())

			command = 0.5 * brgError
			self.lt(max(min(self.maxTurnSpeed, command), -self.maxTurnSpeed))

			pass

		elif self.guidance == 4:
			brg = self.bearing(self.xcor(), self.ycor(), player.xcor(), player.ycor())
			brgError = self.brgError(brg, self.heading())

			command = 0.05 * (brgError - 180) % 360
			self.rt(max(min(self.maxTurnSpeed, command), -self.maxTurnSpeed))

	def reset(self):
		b = game.border_size - self.size
		self.goto(random.randint(-b, b),random.randint(-b, b))
		self.setheading(random.randint(0, 360))


class Bullet(Sprite):
	def __init__(self, shape, color, start_x, start_y, start_hdg, player_speed=0):
		Sprite.__init__(self, shape, color, start_x, start_y, start_hdg)
		self.shapesize(stretch_wid = 0.3, stretch_len = 0.4, outline=None)
		self.speed = 20 + player.speed
		self.status = False

	def fire(self):
		if not self.status:
			self.status = True
			self.setheading(player.heading())
			self.goto(player.xcor(), player.ycor())


	def move(self):
		if not self.status:
			return
		# boundaries
		b = game.border_size - self.speed

		# OOB
		if not (-b < self.xcor() < b) or not (-b < self.ycor() < b):
			self.status = False
			self.goto(1e6, 1e6)

		self.fd(self.speed)

class Game():
	def __init__(self):
		self.sprites = []
		self.level = 1
		self.score = 0
		self.state = "playing"
		self.pen = turtle.Turtle()
		self.text = turtle.Turtle()

	def drawBorder(self, border_size=350):
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

	def showMessage(self, s):
		self.text.speed(0)
		self.text.color("white")
		self.text.penup()
		self.text.goto(-300, 310)
		self.text.write(s, font=("Arial", 16, "normal"))
		self.text.clear()

# Game Init
border_size = 350
game = Game()
game.drawBorder(border_size)

# Sprites
player = Player("triangle", "blue", 0, -250, 90)
bullet = Bullet("triangle", "yellow", 1e6, 1e6, 0)
game.sprites.append(player)
game.sprites.append(bullet)

color_dict = {0:"red", 1:"purple", 2:"orange red", 3:"green", 4:"brown"}
for i in range(5):
	e = Enemy("square", color_dict[i % 5])
	e.reset()
	e.speed = 2 + i/2
	e.guidance = 2 + i%2

	game.sprites.append(e)

# Keyboard Bindings
turtle.listen()
turtle.onkey(player.turn_left, "Left")
turtle.onkey(player.turn_right, "Right")
turtle.onkey(player.accel, "Up")
turtle.onkey(player.decel, "Down")
turtle.onkey(player.respawn, "r")
turtle.onkey(bullet.fire, "z")

print("Press Ctrl-C to Finish.")

while True:
	turtle.update()
	try:
		b = game.border_size
		for i, sprite in enumerate(game.sprites):
			sprite.move()
			#game.showMessage(player.heading())
			if isinstance(sprite, Enemy):
				sprite.autopilot(player)
				if player.isCollided(sprite):
					player.lives -= 1
					sprite.reset()
				if bullet.isCollided(sprite) or not (-b < sprite.xcor() < b) or not (-b < sprite.ycor() < b):
					sprite.reset()

	except KeyboardInterrupt:
		print("\nThanks For Playing.")
		break
