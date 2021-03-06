# Space Invaders
# By Adam Kilbourne-Quirk 2020-02-22

import os, sys, time, psutil, queue
import math, random
import turtle

class Sprite(turtle.Turtle):
	def __init__(self, shape, color, start_x, start_y, start_hdg):
		turtle.Turtle.__init__(self, shape = shape)
		self.color(color)
		self.penup()

		self.goto(start_x, start_y)
		self.setheading(start_hdg)
		self.size = 10 # used for collisions

	def distance(self, x, y):
		x1 = self.xcor()
		y1 = self.ycor()
		return ((x - x1)**2 + (y - y1)**2)**0.5

	def bearing(self, x, y):
		x1 = self.xcor()
		y1 = self.ycor()
		return (math.atan2(y - y1, x - x1))*180/math.pi

	def brg_error(self, x, y):
		'''
		use the cross product to a) avoid discontinuity at +/- 180 and b) take the sign/pointing direction into account
		sin(C) = cross(a, b) / [mag(a) * mag(b)]
		'''
		x1 = math.cos(math.pi / 180 * self.heading())
		y1 = math.sin(math.pi / 180 * self.heading())
		x2 = x - self.xcor()
		y2 = y - self.ycor()
		dist = self.distance(x, y)
		if dist == 0:
			sin_C = 0
		else:
			sin_C = (x1 * y2 - x2 * y1) / dist

		return math.asin(sin_C) * 180 / math.pi

	def is_collided(self, other):
		bounds = self.size + other.size
		# check bounding box
		if (self.xcor() - other.xcor() < bounds) or (self.ycor() - other.ycor() < bounds):
			# check more precisely
			if self.distance(other.xcor(), other.ycor()) < bounds:
				return True
		return False

class Actor(Sprite):
	def __init__(self, shape, color, start_x, start_y, start_hdg=0, speed=0, max_turn_speed=0):
		Sprite.__init__(self, shape, color, start_x, start_y, start_hdg)
		self.speed = speed
		self.max_turn_speed = max_turn_speed

	def move(self):
		# boundaries
		bx = game.border_size_x
		by = game.border_size_y

		if not (-bx < self.xcor() < bx) or not (-by < self.ycor() < by):
			self.respawn()

		self.fd(self.speed)

	def respawn(self):
		self.penup()
		self.clear()
		while True:
			bx = game.border_size_x - self.size
			by = game.border_size_y - self.size
			x = random.randint(-bx, bx)
			y = random.randint(-by, by)
			if player.distance(x, y) > game.border_size_y/4:
				break
		self.goto(x, y)
		self.setheading(random.randint(0, 360))

	def closing_speed(self, actor):
		'''
		This function requires a speed attribute, which is why it isn't in the Sprite class
		v_close = dot(v_rel, d_rel)/mag(d_rel)
		'''
		v1x = self.speed * math.cos(math.pi / 180 * self.heading())
		v1y = self.speed * math.sin(math.pi / 180 * self.heading())
		v2x = actor.speed * math.cos(math.pi / 180 * actor.heading())
		v2y = actor.speed * math.sin(math.pi / 180 * actor.heading())
		dx = actor.xcor() - self.xcor()
		dy = actor.ycor() - self.ycor()
		vx = v2x - v1x
		vy = v2y - v1y
		return (vx * dx + vy * dy)/self.distance(actor.xcor(), actor.ycor())

class Player(Actor):
	def __init__(self, shape, color, start_x, start_y, start_hdg, speed=4, max_turn_speed=22.5):
		Actor.__init__(self, shape, color, start_x, start_y, start_hdg, speed, max_turn_speed)
		self.start_loc = (start_x, start_y, start_hdg)
		self.start_color = color
		self.max_fwd_speed = 10
		self.max_rev_speed = 5
		
		self.start_lives = 3
		self.lives = self.start_lives
		self.start_bombs = 3
		self.bombs = self.start_bombs
		self.rof = 4 # Rate of Fire; bullets per second
		self.bullet_speed = 20
		self.bullet_bounces = 50
		self.time_since_fire = float('-inf')
		self.is_invuln = False
		self.time_since_invuln = float('-inf')
		self.time_invuln = 0

	def autopilot(self):
		'''
		Will implement in pygame version of this game. Does the following:
		- If number of lives are below a threshold, navigate to the prize.
		- If above threshold, hunt down enemies
		- Avoid collision with hotwalls and enemies.
		- If enemy collision imminent, or average distance to enemies is low, use a bomb
		'''
		pass

	def fire_bullet(self):
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

	def fire_bounce(self):
		if time.time() - self.time_since_fire > 1/max(self.rof, 1e-6):
			self.time_since_fire = time.time()
			bullet_speed = self.speed + self.bullet_speed/2
			bullet = Bullet("circle", "magenta", self.xcor(), self.ycor(), self.heading(), bullet_speed,
							self.bullet_bounces)
			bullet.fire()

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

	def increment_lives(self, lives, set_invuln=True):
		if lives > 0 or (lives < 0 and not self.is_invuln) or not set_invuln:
			self.lives += lives
		if self.lives < 1 and game.options["player_can_die"]:
			game.reset_game()
		if set_invuln:
			self.invuln_on(3)
		game.show_score()

	def invuln_on(self, seconds):
		if not self.is_invuln:
			self.time_since_invuln = time.time()
		self.is_invuln = True
		self.time_invuln = seconds

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

class Enemy(Actor):
	def __init__(self, shape="square", color="red", start_x=0, start_y=0, start_hdg=0, speed=4, max_turn_speed=5):
		Actor.__init__(self, shape, color, start_x, start_y, start_hdg, speed, max_turn_speed)
		self.color_dict = {0: "green", 1: "lightgreen", 2: "orange red", 3: "red", 4: "brown", 5: "blue"}
		self.aim_pt = turtle.Turtle()
		self.aim_pt.color("white")
		self.aim_pt.ht()
		self.bx = game.border_size_x - self.size
		self.by = game.border_size_y - self.size

		self.target = player

		# target a random actor, for giggles
		if game.options["all_enemies_aim_rand"]:
			self.target = random.choice(game.get_actors())
		self.guidance = 0
		self.random_steps = 0
		self.ax = self.xcor()
		self.ay = self.ycor()
		self.ax_rand = random.randint(-bx, bx)
		self.ay_rand = random.randint(-by, by)
		self.scattered = False
		self.time_since_scatter = float('-inf')
		self.time_scatter = 0

	def set_guidance(self, guidance_mode):
		self.guidance = guidance_mode
		self.color(self.color_dict[guidance_mode % len(self.color_dict)])

	def scatter(self, t):
		self.time_scatter = t
		self.time_since_scatter = time.time()
		if not self.scattered:
			self.start_guidance = self.guidance
			self.scattered = True
			self.set_guidance(5)
			self.speed *= 0.5

	def update_aim_pt(self):
		'''
		Pick a pt to navigate to based on guidance
		0: Patrol. Does not maneuver or respond to player.
		1: Random. Maneuvers but does not respond to player.
		2: Pursuit. Points directly at player.
		3: Pro-Nav. Aims ahead of player.
		4: Mirror. Moves to opposite side of space from player.
		5: Avoidance. Moves away from player.
		'''
		if game.options["all_enemies_speed_match"]:
			self.speed = abs(player.speed)

		# stop scattering
		if self.scattered and time.time() - self.time_since_scatter > self.time_scatter:
			self.set_guidance(self.start_guidance)
			self.scattered = False
			self.speed *= 2
		px = self.target.xcor()
		py = self.target.ycor()
		ax = self.xcor()
		ay = self.ycor()

		if self.guidance == 1:
			self.random_steps = (self.random_steps + 1) % 50
			if self.random_steps == 0:
				self.ax_rand = random.randint(-self.bx, self.bx)
				self.ay_rand = random.randint(-self.by, self.by)
			ax = self.ax_rand
			ay = self.ay_rand
		elif self.guidance == 2:
			'''
			aim at player
			'''
			ax = px
			ay = py

		elif self.guidance == 3:
			'''
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
			'''
			p_dist = self.distance(px, py)
			N = self.target.speed/max(self.speed, 1)
			aim_dist = 0

			# if player is not moving, aim directly at it
			if abs(N) > 0:
				c0 = -(p_dist ** 2)
				c1 = 2 * p_dist * math.cos(math.pi / 180 * self.target.brg_error(ax, ay))
				c2 = 1/(N**2) - 1

				# N == +/-1; edge case
				if abs(c2) < 1e-6:
					aim_dist = -c0 / c1
				else:
					temp = c1**2 - 4 * c2 * c0
					# avoid complex numbers
					temp = max(temp, 0)
					b1 = (-c1 + temp**0.5) / (2 * c2)
					b2 = (-c1 - temp**0.5) / (2 * c2)
					aim_dist = max(min(b1, b2), 0)
				if self.target.speed < 0:
					aim_dist *= -1

			ax = px + math.cos(math.pi / 180 * self.target.heading()) * aim_dist
			ay = py + math.sin(math.pi / 180 * self.target.heading()) * aim_dist

		elif self.guidance == 4:
			'''
			move towards opposite side of the area
			'''
			ax = -px
			ay = -py

		elif self.guidance == 5:
			'''
			move directly away from player
			'''
			ax = 2 * ax - px
			ay = 2 * ay - py

		self.ax = max(min(self.bx, ax), -self.bx)
		self.ay = max(min(self.by, ay), -self.by)
		if game.options["show_aim_pts"]:
			self.draw_aim_pt(self.ax, self.ay)


	def autopilot(self):
		command = 0.5 * self.brg_error(self.ax, self.ay)
		self.lt(max(min(self.max_turn_speed, command), -self.max_turn_speed))

	def draw_aim_pt(self, ax, ay):
		self.aim_pt.goto(ax, ay)
		self.aim_pt.clear()
		self.aim_pt.dot()

	def respawn(self):
		if game.options["all_enemies_aim_rand"]:
			self.target = random.choice(game.get_actors())
		super().respawn()

class Prize(Actor):
	def __init__(self, shape="circle", color="white", start_x=0, start_y=0):
		Actor.__init__(self, shape, color, start_x, start_y)
		self.time_since_respawn = float("-inf")
		self.respawn_interval = 10

	def scatter_enemies(self, t):
		for e in game.get_actors():
			if isinstance(e, Enemy):
				e.scatter(t)

	def award(self):
		player.increment_lives(1)
		player.invuln_on(6)
		self.scatter_enemies(6)
		self.respawn()

class Bullet(Sprite):
	def __init__(self, shape, color, start_x, start_y, start_hdg, speed, bounces=0):
		Sprite.__init__(self, shape, color, start_x, start_y, start_hdg)
		self.shapesize(stretch_wid = 0.3, stretch_len = 0.4, outline=None)
		self.speed = speed
		self.bounces = bounces
		self.size = 5
		self.max_lifetime = 20
		self.spawn_time = time.time()

	def fire(self):
		self.goto(player.xcor(), player.ycor())
		game.bullets.append(self)

	def move(self):
		# boundaries
		bx = game.border_size_x
		by = game.border_size_y

		if time.time() - self.spawn_time > self.max_lifetime or not (-bx < self.xcor() < bx) or not (-by < self.ycor() < by):
			self.__del__()

		self.fd(self.speed)

	def bounces(self):
		return self.bounces

	def wall_hit(self, wall=None):
		if wall and wall.bounce_mode < 4:
			self.bounces -= 1
		elif wall and wall.bounce_mode == 6:
			self.bounces += 1
		if self.bounces < 0:
			self.__del__()

	def __del__(self):
		try:
			self.reset()
			game.bullets.remove(self)
		except:
			pass

class Wall(Sprite):
	def __init__(self, x1, y1, x2, y2, bounce_mode=0):
		Sprite.__init__(self, "classic", "black", x1, y1, 0)
		self.ht()

		self.x1 = x1
		self.y1 = y1
		self.x2 = x2
		self.y2 = y2
		self.angle = self.bearing(x2, y2)
		self.size = 0
		self.bounce_mode = bounce_mode


	def draw(self):
		color_dict = {0: "white", 1: "gray", 2: "pink", 3: "cyan", 4: "yellow", 5: "blue", 6: "red"}
		color = color_dict[self.bounce_mode % len(color_dict)]
		self.pen = turtle.Turtle()
		self.pen.color(color)
		self.pen.penup()
		self.pen.setposition(self.x1, self.y1)
		self.pen.pendown()
		self.pen.pensize(3)
		self.pen.lt(self.angle)
		self.pen.fd(max(self.distance(self.x2, self.y2), 1))
		self.pen.penup()
		self.pen.ht()

	def dist_point_line(self, px, py):
		dx = self.x2 - self.x1
		dy = self.y2 - self.y1
		return abs(dy * px - dx * py + self.x2 * self.y1 - self.y2 * self.x1) / math.sqrt(dx ** 2 + dy ** 2)

	def is_collided(self, actor):
		s = actor.size + abs(actor.speed)/2

		# avoid phenomenon where player sticks to the wall and oscillates
		if self.bounce_mode == 1:
			s *= 1.3
		x_max = max(self.x1, self.x2)
		x_min = min(self.x1, self.x2)
		y_max = max(self.y1, self.y2)
		y_min = min(self.y1, self.y2)
		px = actor.xcor()
		py = actor.ycor()

		# actor is in bounding box of wall
		if (x_min - s < px < x_max + s) and (y_min - s < py < y_max + s):
			# actor is actually touching wall
			if self.dist_point_line(px, py) < s:
				return True
		return False

	def bounce_standard(self, actor):
		actor.setheading(-actor.heading() + 2 * self.angle)

	def bounce(self, actor):
		'''
		bounce modes:
		0: standard: 2 * wall - approach. Block all sprites.
		1: slow down: standard, but divide player speed by 2
		2: semi-random: standard, but with a less predictable heading
		3: allow actors through
		4: allow bullets through
		5: warp: send actor to location which is the reflection of their current spot about
			a line parallel to the wall and through the center of the screen. Do not change heading
		6. hot wall: kill actors, add bounce to bullets
		'''
		if self.bounce_mode == 1:
			self.bounce_standard(actor)
			if isinstance(actor, Player):
				actor.speed *= 0.5
		elif self.bounce_mode == 2:
			self.bounce_standard(actor)
			bounds = min(60, abs(int(actor.heading() - self.angle)))
			actor.setheading(actor.heading() + random.randint(-bounds, bounds))

		elif self.bounce_mode == 3:
			if isinstance(actor, Bullet):
				self.bounce_standard(actor)

		elif self.bounce_mode == 4:
			if isinstance(actor, Actor):
				self.bounce_standard(actor)

		elif self.bounce_mode == 5:
			# find reflected point of actor
			# m = -a/b = (y2 - y1)/(x2 - x1) = tan(self.angle)
			# b = 1
			px = actor.xcor()
			py = actor.ycor()
			ax = self.x2 - self.x1
			ay = self.y2 - self.y1
			dist_to_center = self.dist_point_line(0, 0)
			dist_to_warp = abs(ay * px - ax * py) / math.sqrt(ax ** 2 + ay ** 2)

			if dist_to_warp > dist_to_center:
				dist_to_warp += player.size
			else:
				dist_to_warp -= player.size

			# the reflection will produce 2 pts: 1 in bounds and 1 out of bounds.
			# go to the point that is in bounds.
			ax1 = px + math.cos(math.pi / 180 * (self.angle + 90)) * dist_to_warp * 2
			ay1 = py + math.sin(math.pi / 180 * (self.angle + 90)) * dist_to_warp * 2
			ax2 = px + math.cos(math.pi / 180 * (self.angle - 90)) * dist_to_warp * 2
			ay2 = py + math.sin(math.pi / 180 * (self.angle - 90)) * dist_to_warp * 2
			if ax1**2 + ay1**2 < ax2**2 + ay2**2:
				ax = ax1
				ay = ay1
			else:
				ax = ax2
				ay = ay2
			actor.goto(ax, ay)

		elif self.bounce_mode == 6:
			self.bounce_standard(actor)
			if isinstance(actor, Player):
				player.increment_lives(-1)
			elif isinstance(actor, Enemy):
				actor.respawn()
		else:
			self.bounce_standard(actor)

class SpaceWar():
	def __init__(self, border_size_x, border_size_y, options):
		self.options = options
		self.actors = []
		self.bullets = []
		self.walls = []
		self.score = self.highScore = 0

		self.active = True
		self.border_size_x = border_size_x
		self.border_size_y = border_size_y

		self.text1 = turtle.Turtle()
		self.text2 = turtle.Turtle()
		self.bkgnd = turtle.Turtle()
		self.text1.ht()
		self.text2.ht()
		self.bkgnd.ht()
		self.time_delta = 1/30
		self.frame_time_queue = queue.Queue(5)

	def update(self):
		# actors
		for i, actor in enumerate(self.actors):
			if isinstance(actor, Player):
				actor.move()
				actor.invuln_off()
				if actor.is_collided(prize):
					prize.award()
			if isinstance(actor, Enemy):
				actor.update_aim_pt()
				# if collided with player or bullet or OOB, respawn
				if self.options["enemies_can_move"]:
					actor.move()
					actor.autopilot()
				if player.is_collided(actor):
					if actor.scattered:
						self.increment_score(actor)
						actor.respawn()
					else:
						if not player.is_invuln:
							player.increment_lives(-1)
							actor.respawn()

			for wall in game.walls:
				if wall.is_collided(actor):
					wall.bounce(actor)

		# bullets
		for i, bullet in enumerate(self.bullets):
			bullet.move()
			for j, actor in enumerate(self.actors):
				if isinstance(actor, Enemy) and actor.is_collided(bullet):
					self.increment_score(actor, bullet)
					actor.respawn()
			for j, wall in enumerate(self.walls):
				if wall.is_collided(bullet):
					wall.bounce(bullet)
					bullet.wall_hit(wall)

	def maf_frame_rate(self, td):
		'''
		Determines the frame rate using a moving average filter to smooth out irregular execution.
		'''
		if self.frame_time_queue.full():
			td_oldest = self.frame_time_queue.get()
		else:
			td_oldest = self.time_delta
		self.time_delta += (td - td_oldest) / self.frame_time_queue.maxsize

	def make_border(self):
		bx = self.border_size_x
		by = self.border_size_y
		wall1 = Wall(-bx, -by, -bx, by, 5)
		wall2 = Wall(-bx, by, bx, by, 2)
		wall3 = Wall(bx, by, bx, -by, 5)
		wall4 = Wall(bx, -by, -bx, -by,1)
		self.walls.extend([wall1, wall2, wall3, wall4])

	def draw_walls(self):
		for wall in game.walls:
			if game.options["all_walls_bounce_mode"] >= 0:
				wall.bounce_mode = game.options["all_walls_bounce_mode"]
			wall.draw()

	def draw_background(self):
		self.bkgnd.speed(0)
		self.bkgnd.color("white")
		bx = self.border_size_x
		by = self.border_size_y
		for _ in range(int(bx/4)):
			self.bkgnd.penup()
			self.bkgnd.goto(random.randint(-bx, bx), random.randint(-by, by))
			self.bkgnd.dot(random.randint(1,3))

	def make_enemies(self, num_enemies):
		for i in range(num_enemies):
			e = Enemy()
			if len(self.options["allowed_enemy_guidance_modes"]) > 0:
				e.set_guidance(random.choice(self.options["allowed_enemy_guidance_modes"]))
			else:
				e.set_guidance(i % 6)
			e.speed = min(2 + i / 2, 5)
			self.actors.append(e)

	def toggle_enemy_movement(self):
		self.options["enemies_can_move"] ^= 1

	def get_actors(self):
		return self.actors

	def increment_score(self, enemy, bullet=None):
		if bullet and bullet.bounces > 1:
			score = 10
		else:
			score = 100
		temp = self.score
		self.score += score
		self.highScore = max(self.score, self.highScore)
		if score > 0 and self.score//1000 - temp//1000 > 0:
			player.bombs += 1
		game.show_score()

	def reset_game(self):
		player.lives = player.start_lives
		self.score = 0
		player.bombs = player.start_bombs
		for actor in game.actors:
			actor.respawn()
		for bullet in game.bullets:
			bullet.__del__()
		game.show_score()

	def show_score(self):
		self.text1.speed(0)
		self.text1.color("white")
		self.text1.penup()
		s = "Score: {0:<5}\t Lives: {1:<5}\t Bombs: {2:<5}\t High Score: {3:<5}".format(str(self.score),
																						str(player.lives),
																						str(player.bombs),
																						str(self.highScore))
		self.text1.goto(-self.border_size_x * 0.5 + 100, self.border_size_y + 10)
		self.text1.clear()
		self.text1.write(s, font=("Arial", 16, "normal"))

	def show_controls(self):
		self.text2.speed(0)
		self.text2.color("white")
		self.text2.penup()
		s1 = "Respawn: {0:<5}\t Cannon: {1:<5}\t Bouncy Ball: {2:<5}\t Bomb: {3:<5}\t".format("R", "Z", "X", "Space")
		s2 = "Toggle Enemy Move: {0:<5}\t Quit: {1:<5}".format("P", "Q")
		s = s1 + s2
		self.text2.goto(-self.border_size_x * 0.5 + 50, -self.border_size_y - 25)
		self.text2.clear()
		self.text2.write(s, font=("Arial", 14, "normal"))

	def exit_game(self):
		turtle.bye()
		self.active = False

# Turtle setup
turtle.fd(0)
turtle.speed(30)
turtle.ht()
turtle.delay(0)
turtle.setundobuffer(1)
turtle.tracer(0)

# Screen
wn = turtle.Screen()
wn.setup(width = 1.0, height = 1.0)
wn.title("Space War")
wn.bgcolor("black")
wn.colormode(255)

# Game Init options and walls

options_trivial = {
	"player_can_die":False,
	"all_walls_bounce_mode":5,
	"allowed_enemy_guidance_modes":[0],
	"all_enemies_speed_match":False,
	"all_enemies_aim_rand":True,
	"enemies_can_move":False,
	"show_aim_pts":True
}

options_easy = {
	"player_can_die":True,
	"all_walls_bounce_mode":4,
	"allowed_enemy_guidance_modes":[0, 1, 4],
	"all_enemies_speed_match":False,
	"all_enemies_aim_rand":False,
	"enemies_can_move":True,
	"show_aim_pts":True
}

options_standard = {
	"player_can_die":True,
	"all_walls_bounce_mode":-1,
	"allowed_enemy_guidance_modes":[],
	"all_enemies_speed_match":False,
	"all_enemies_aim_rand":False,
	"enemies_can_move":True,
	"show_aim_pts":False
}

options_hard = {
	"player_can_die":True,
	"all_walls_bounce_mode":1,
	"allowed_enemy_guidance_modes":[2, 3, 4, 5],
	"all_enemies_speed_match":False,
	"all_enemies_aim_rand":False,
	"enemies_can_move":True,
	"show_aim_pts":False
}

options_diabolical = {
	"player_can_die":True,
	"all_walls_bounce_mode":6,
	"allowed_enemy_guidance_modes":[2, 3],
	"all_enemies_speed_match":True,
	"all_enemies_aim_rand":False,
	"enemies_can_move":True,
	"show_aim_pts":False
}

options_test = {
	"player_can_die": False,
	"all_walls_bounce_mode": -1,
	"allowed_enemy_guidance_modes": [1],
	"all_enemies_speed_match": True,
	"all_enemies_aim_rand": False,
	"enemies_can_move": True,
	"show_aim_pts": True
}

game_options = [options_trivial, options_easy, options_standard, options_hard, options_diabolical, options_test]

if len(sys.argv) > 1:
	option = int(sys.argv[1])
	game = SpaceWar(800, 450, game_options[option])
else:
	game = SpaceWar(800, 450, options_standard)
bx = game.border_size_x
by = game.border_size_y
wall1 = Wall(-bx/2, -by/2, -bx/2, by/2, 6)
wall2 = Wall(bx/2, -by/2, bx/2, by/2, 4)
wall3 = Wall(-bx/3, by/2, bx/3, by/2, 3)
wall4 = Wall(-bx/3, -by/2, bx/3, -by/2, 3)

game.make_border()
game.walls.extend([wall1, wall2, wall3, wall4])
game.draw_background()
game.draw_walls()
game.show_controls()

# Actor Sprites
player = Player("triangle", "cyan", 0, -100, 90)
prize = Prize()
game.actors.append(player)
game.actors.append(prize)
game.make_enemies(12)

# Reset
game.reset_game()

# Keyboard Bindings
turtle.listen()
turtle.onkey(player.turn_left, "Left")
turtle.onkey(player.turn_right, "Right")
turtle.onkey(player.accel, "Up")
turtle.onkey(player.decel, "Down")
turtle.onkey(player.respawn, "r")
turtle.onkey(player.fire_bullet, "z")
turtle.onkey(player.fire_bounce, "x")
turtle.onkey(player.bomb, "space")

turtle.onkey(game.exit_game, "q")
turtle.onkey(game.toggle_enemy_movement, "p")

mem = []
process = psutil.Process(os.getpid())
mem.append(process.memory_info().rss)

while game.active:
	t1 = time.time()
	game.update()
	turtle.update()
	t2 = time.time()

print("\nStats:")
print("High Score: {}".format(game.highScore))
mem.append(process.memory_info().rss)
print("\nMemory Usage (MB):")
print("Start: {}\nEnd:   {}".format(round(mem[0]/1e6, 1), round(mem[1]/1e6, 1)))