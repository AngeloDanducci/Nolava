#!/usr/bin/python3

import time
import random
import uuid
import html
import re
from wsocket import WSocket
from user import User

# empty string here for all available interfaces, same as socket, 0 for timeout
ws = WSocket('', 1400, 0)
allRoles = ['nilrem', 'nissassa', 'derdrom', 'lavicrep', 'anagrom', 'good', 'evil']
stateList = ['not_started', 'choose_team', 'vote_quest', 'quest_success_or_fail', 'assassinate']
state = 'not_started'
timerStart = None # DateTime
timerLength = 60 # seconds
leaderPlace = 0
users = []
disconnected = []
sessions = {}
roles = {'nilrem':None, 'nissassa':None, 'derdrom':None, 'lavicrep':None, 'anagrom':None, 'good':[], 'evil':[]}

def htmlEncode(text):
	return html.escape(text)

def initUser(user):
	# ask user their name
	# WSocket.send(user.socket, "request:name")
	pass

def playAs(user, place):
	# Where place is 1-10 on the board
	global sessions
	if user.place != None:
		# User already has a position
		send(user, 'error:%s %s' % ('You are already place in position', user.place))
	if state == 'not_started':
		for u in users:
			if u.place == place:
				# TODO: Tell them they can't be that place
				send(user, 'error:%s' % ('Someone already has that position'))
				return
		user.place = int(place)
		user.session = uuid.uuid1()
		# How serious a session token do we need?... http://stackoverflow.com/a/6092448/1450120
		send(user, 'assign:%s' % (user.place))
		send(user, 'session:%s' % (user.session))
		sessions[user.session] = user
	else:
		send(user, 'error:%s' % ('Sorry, the game has started'))

def whoami(user):
	# Tell the user everything they should know based on what role they are (including score etc.)
	# This function should be used in two places, when a user reconnects, and when they
	# are first assigned a role
	print('whoami')
	send(user, 'state:%s' % (state))

	send(user, 'assign:%s' % (user.place))
	send(user, 'assign:%s' % (user.role))

	if user.role == 'nilrem':
		# Sees all evil players except derdrom
		notifyEvilPlayers(user, False)
	elif user.role == 'lavicrep':
		# Knows who Merlin is, (but Morgana is also shown as Merlin)
		# use queue of messages to randomize the order
		queue = []
		if roles['anagrom'] != None:
			queue.append('place:%s:%s:%s' % (roles['anagrom'].place, roles['anagrom'].name, 'nilrem'))
		if roles['nilrem'] != None:
			queue.append('place:%s:%s:%s' % (roles['anagrom'].place, roles['anagrom'].name, 'nilrem'))

		random.shuffle(queue)
		for msg in queue:
			send(user, msg)
	elif user.role == 'derdrom' or user.role == 'anagrom' or user in roles['evil']:
		notifyEvilPlayers(user, True)

	# Finally, notify the user of all spots that are taken... Useful if the game is still joinable and whatnot
	for u in [x for x in users if x.place != None]:
		send(user, 'place:%s:%s' % (u.place, u.name))

	# TODO also show quest leader and score!


def notifyEvilPlayers(user, includeDerdrom):
	# In order to prevent the client from being like "Hey, the guy who's sent last is the assassin"
	# queue the messages in a list and randomize them...
	queue = []
	for u in roles['evil']:
		queue.append('place:%s:%s:%s' % (u.place, u.name, u.role))

	if includeDerdrom and roles['derdrom'] != None:
		queue.append('place:%s:%s:%s' % (roles['derdrom'].place, roles['derdrom'].name, 'derdrom'))

	if roles['anagrom'] != None:
		queue.append('place:%s:%s:%s' % (roles['anagrom'].place, roles['anagrom'].name, 'anagrom'))

	if roles['nissassa'] != None:
		queue.append('place:%s:%s:%s' % (roles['nissassa'].place, roles['nissassa'].name, 'nissassa'))

	random.shuffle(queue)	
	for msg in queue:
		send(user, msg)


def send(user, data):
	try:
		WSocket.send(user.socket, data)
		return True
	except:
		# If we couldn't send data to a user, remove them from list of users,
		# add to disconnected list, and notify everyone else the user disconnected
		try:
			users.remove(user)
			# Save the user if they have a session (which means they are playing)
			if user.session != None:
				disconnected.append(user)
			for u in users:
				send(u, '%s:%s' % ('disconnected', user.name))

			return False
		except ValueError:
			# If the user is not users trying to remove it creates a value error.
			# catching the error is useful here to not spam users about a disconnect
			# and prevent unintended loops
			return False

def startGame():
	# Give all users that have an assigned place a role and start the first round
	# all users that have an assigned place
	global roles
	usersPlaying = [x for x in users if x.place != None]
	random.shuffle(usersPlaying)
	# IMPORTANT! Shuffle users otherwise players that connected earlier are much more likely to
	# be assigned good/evil rather than a unique character
	rolesLeft = list(allRoles)
	rolesLeft.remove('evil')
	rolesLeft.remove('good')

	while len(usersPlaying) > 0:
		if len(usersPlaying) > len(rolesLeft):
			# if there are more players left than unique roles, assign
			# randomly either a unique role or good/evil
			if random.getrandbits(1):
				role = random.choice(rolesLeft)
				rolesLeft.remove(role)
			else:
				role = random.choice(['evil', 'good'])
		else:
			role = random.choice(rolesLeft)
			rolesLeft.remove(role)

		user = usersPlaying.pop(0)
		user.role = role
		send(user, 'assign:%s' % (role))
		if role == 'evil' or role == 'good':
			roles[role].append(user)
		else:
			roles[role] = user

	startRound()
	for user in users:
		whoami(user)

def numOrInf(x):
	if not x:
		return 99999999999
	else:
		return x

def startRound():
	# Assign new leader, start timer
	global leaderPlace
	global state

	for u in users:
		u.teamLeader = False
		u.teamMember = False

	state = 'choose_team'
	leaderPlace = leaderPlace + 1
	#newLeader = next(x for x in users if x.place == leaderPlace)
	newLeader = min(users, key=lambda x: numOrInf(x.place))

	newLeader.teamLeader = True
	send(newLeader, 'quest:leader')

	for user in users:
		send(user, 'leader:%s' % (leaderPlace))

	startTimer()

def gameAction(action):
	# Does specific things for the game as a whole, such as starting it
	if action == 'start' and state == 'not_started':
		startGame()
	#elif action == 'pause':

def startTimer():
	global timerStart
	timerStart = time.time()
	for user in users:
		send(user, 'timer:%s' % (timerLength))

def roundTimeIsUp():
	# Check if the time has elapsed and update data structures
	global timerStart
	if timerStart != None:
		if time.time() > timerStart + timerLength:
			timerStart = None
			return True
	return False

def doDefaultTimeOut():
	# TODO: Do whatever default actions shold be done here, the timer has elapsed
	if state == 'choose_team':
		# TODO: Pick team for leader randomly
		pass
	elif state == 'vote_quest':
		# TODO: Have undecided votes default
		pass
	elif state == 'quest_success_or_fail':
		# TODO: Have undecided votes default
		pass

try:
	userId = 1
	while True:
		if roundTimeIsUp():
			doDefaultTimeOut()

		client = ws.accept()
		if client is not None:
			# figure out who they are and add to list
			user = User(client, userId)
			userId = userId + 1
			initUser(user)
			users.append(user)

		# For each client, see if they sent anything
		for user in users:
			recvd = WSocket.recv(user.socket, 4096)
			if recvd is None:
				continue

			# If they did send something, send it to every client
			# THIS IS THE POINT WHERE WE WILL BE INSPECTING USER INPUT
			# TO SEE IF IT'S A CHAT MESSAGE, AN ATTEMPT AT MAKING A GAME
			# MOVE/VOTE/WHATEVER. IN THE CASE OF A MESSAGE, IT WILL
			# BE SENT TO EVERYONE

			# first, get action (should seperate into ['action', 'value'])
			action = recvd.decode('utf-8').split(':', 1)

			if action[0] == 'chat':
				for u in users:
					send(u, "chat:%s:%s" % (htmlEncode(user.name), htmlEncode(action[1])))
			elif action[0] == 'name':
				# When someone updates their name, tell everyone
				# Could potentially be abused? TODO: rate limit? only allow once?
				# Check for duplicate name?
				regex = r'(\w+).*'
				match = re.match(regex, action[1])
				if match:
					user.name = match.group(1)
					for u in users:
						send(u, '%s:%s' % (user.id, htmlEncode(user.name)))
				pass
			elif action[0] == 'game':
				gameAction(action[1])
			elif action[0] == 'session':
				# If user is trying to reconnect, make sure they are given the correct user object
				sessionId = action[1]
				if sessionId in sessions:
					print('Tracked user reconnected.')
					sessions[sessionId] = user
					if user in disconnected:
						disconnected.remove(user)
						users.append(user)
				else:
					print('Untracked user connected with sessionId = %s' % (sessionId))
			elif action[0] == 'vote':
				# Should be either reject/approve or success/fail depending on what vote is for
				pass
			elif action[0] == 'join':
				# User will ask to join as id# (1-10) which corresponds to their position in the board
				# Make sure to check if the id is taken...
				playAs(user, action[1])
			elif action[0] == 'whoami':
				# If the client reconnects, the browser won't "remember" who is who
				# so remind them
				whoami(user)
except KeyboardInterrupt:
	print('\nKeyboardInterrupt.\nCleaning up and exiting')
	for user in users:
		user.socket.close()
	ws.close()
