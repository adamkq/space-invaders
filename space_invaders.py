# Space Invaders
# By Adam Kilbourne-Quirk 2020-02-22

import os, sys, random
import turtle, keyboard

# Required by MacOS to show the window
turtle.fd(0)
turtle.speed(0)
# Hide default turtle
turtle.ht()
# Improve memory
turtle.setundobuffer(1)
# Improve animation speed
turtle.tracer(1)

# Screen
wn = turtle.Screen()
wn.bgcolor("black")
wn.title("Space Invaders")


class Sprite(turtle.Turtle):
	def __init__(self, shape, color, start_x, start_y, border_size=350):
		turtle.Turtle.__init__(self, shape = shape)
		self.speed(0)
		self.penup()
		self.color(color)
		self.fd(0)
		self.goto(start_x, start_y)
		self.speed = 1

	def bounce(self, wall_angle):
		# bounce = 2 * wall - approach
		self.setheading(-self.heading() + 2 * wall_angle) 

	def move(self):
		self.fd(self.speed)
		sprite_size = 10
		# boundaries
		b1 = border_size - sprite_size
		b2 = -border_size + sprite_size

		# x-speed reflect
		if self.xcor() > b1 or self.xcor() < b2:
			self.bounce(90)

		# y-speed reflect
		if self.ycor() > b1 or self.ycor() < b2:
			self.bounce(0)


class Player(Sprite):
	def __init__(self, shape, color, start_x, start_y, border_size=350):
		Sprite.__init__(self, shape, color, start_x, start_y, border_size=350)
		self.speed = 4

	def turn_left(self):
		self.lt(22.5)

	def turn_right(self):
		self.rt(22.5)

	def accel(self):
		self.speed += 1
		self.speed = min(self.speed, 30)

	def decel(self):
		self.speed -= 1
		self.speed = max(self.speed, 0)

class Game():
	def __init__(self):
		self.level = 1
		self.score = 0
		self.state = "playing"
		self.pen = turtle.Turtle()
		self.lives = 3

	def draw_border(self, border_size):
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

	def exit(self):
		sys.exit()
		
# Objects
border_size = 350
game = Game()
game.draw_border(border_size)
player = Player("triangle", "blue", 0, -250, border_size)
player.setheading(90)

# Keyboard Bindings
turtle.listen()
turtle.onkey(player.turn_left, "Left")
turtle.onkey(player.turn_right, "Right")
turtle.onkey(player.accel, "Up")
turtle.onkey(player.decel, "Down")

print("Press Ctrl-C to Finish.")

while True:
	try:
		player.move()
	except KeyboardInterrupt:
		print("\nThanks For Playing.")
		break
