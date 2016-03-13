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
rolesLeft = list(roles)
stateList = ['not_started', 'choose_team', 'vote_quest', 'quest_success_or_fail', 'assassinate']
state = 'not_started'
users = []

def htmlEncode(text):
	return html.escape(text)

def initUser(user):
	# ask user their name
	# WSocket.send(user.socket, "request:name")
	pass

def play_as(user, place):
	# Where place is 1-10 on the board
	for u in users:
		if u.place == place:
			# TODO: Tell them they can't be that place
			return
	user.place = place
	user.session = uuid.uuid1()
	# How serious a session token do we need?... http://stackoverflow.com/a/6092448/1450120
	user.role = rolesLeft[random.randrange(0, len(rolesLeft))]
	if user.role != 'good' and user.role != 'evil':
		rolesLeft.remove(user.role)
	WSocket.send(user.socket, 'assign,%s:%s' % (user.place, user.role))
	WSocket.send(user.socket, 'session:%s' % (user.session))
	whoami(user)

def whoami(user):
	# Tell the user everything they should know based on what role they are
	# This function should be used in two places, when a user reconnects, and when they
	# are first assigned a role
	pass

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
				WSocket.send(u.socket, "chat:%s:%s" % (htmlEncode(user.name), htmlEncode(action[1])))
		elif action[0] == 'vote':
			# Should be either reject/approve or success/fail depending on what vote is for
			pass
		elif action[0] == 'name':
			# When someone updates their name, tell everyone
			# Could potentially be abused? TODO: rate limit? only allow once?
			# Check for duplicate name?
			user.name = action[1]
			for u in users:
				WSocket.send(u.socket, '%s:%s' % (user.id, htmlEncode(user.name)))
			pass
		elif action[0] == 'join':
			# User will ask to join as id# (1-10) which corresponds to their position in the board
			# Make sure to check if the id is taken...
			play_as(user, action[1])
		elif action[0] == 'whoami':
			# If the client reconnects, the browser won't "remember" who is who
			# so remind them
			whoami(user)
