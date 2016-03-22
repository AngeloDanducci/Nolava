#!/usr/bin/python3

import time
import random
import uuid
import html
from wsocket import WSocket
from user import User

# empty string here for all available interfaces, same as socket
ws = WSocket('', 1400, 0)
roles = ['nilrem', 'nissassa', 'derdrom', 'lavicrep', 'anagrom', 'good', 'evil']
stateList = ['not_started', 'choose_team', 'vote_quest', 'quest_success_or_fail', 'assassinate']
state = 'not_started'
users = []
disconnected = []

def htmlEncode(text):
	return html.escape(text)

def initUser(user):
	# ask user their name
	# WSocket.send(user.socket, "request:name")
	pass

def playAs(user, place):
	# Where place is 1-10 on the board
	for u in users:
		if u.place == place:
			# TODO: Tell them they can't be that place
			return
	user.place = place
	user.session = uuid.uuid1()
	# How serious a session token do we need?... http://stackoverflow.com/a/6092448/1450120
	send(user, 'assign:%s' % (user.place))
	send(user, 'session:%s' % (user.session))

def whoami(user):
	# Tell the user everything they should know based on what role they are (including score etc.)
	# This function should be used in two places, when a user reconnects, and when they
	# are first assigned a role
	pass

def send(user, data):
	try:
		WSocket.send(user.socket, data)
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
		except ValueError:
			# If the user is not users trying to remove it creates a value error.
			# catching the error is useful here to not spam users about a disconnect
			# and prevent unintended loops
			pass

def startGame():
	# TODO: assign users a role, pick first team leader
	# all users that have an assigned place
	usersPlaying = [x for x in users if x.place != None]
	random.shuffle(usersPlaying)
	# IMPORTANT! Shuffle users otherwise players that connected earlier are much more likely to
	# be assigned good/evil rather than a unique character
	rolesLeft = list(roles)
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
		send(user, 'assign:%s' % (role))
		if user.place == 1:
			send(user, 'quest:leader')
			for u in users:
				send(u, 'leader:%s' % (user.place))


userId = 1
while True:
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
			user.name = action[1]
			for u in users:
				send(u, '%s:%s' % (user.id, htmlEncode(user.name)))
			pass
		elif action[0] == 'session':
			# If user is trying to reconnect, make sure they are given the correct user object
			sessionId = action[1]
			exists = False
			for u in disconnected:
				if u.session == sessionId:
					exists = True
					users.remove(user)
					users.append(u)
					disconnected.remove(u)
					u.socket = user.socket
			if exists:
				print('Tracked user reconnected.')
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
