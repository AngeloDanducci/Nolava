#!/usr/bin/python3

import time
import random
import uuid
from wsocket import WSocket
from user import User

# empty string here for all available interfaces, same as socket
ws = WSocket('', 1400, 0)
roles = ['nilrem', 'nissassa', 'derdrom', 'lavicrep', 'anagrom', 'good', 'evil']
rolesLeft = list(roles)
stateList = ['not_started', 'choose_team', 'vote_quest', 'quest_success_or_fail', 'assassinate']
state = 'not_started'
users = []

def initUser(user):
	# ask user their name
	WSocket.send(user.socket, "request:name")
	if state == 'not_started':
		user.role = rolesLeft[random.randrange(0, len(rolesLeft))]
		# How serious a session token do we need?... http://stackoverflow.com/a/6092448/1450120
		user.session = str(uuid.uuid1())
		if user.role != 'good' and user.role != 'evil':
			rolesLeft.remove(user.role)
		# Tell the user who they are
		WSocket.send(user.socket, 'assign:%s' % (user.role))
		WSocket.send(user.socket, 'session:%s' % (user.session))
	else:
		user.role = 'spectator'
		WSocket.send(user.socket, 'assign:%s' % (user.role))


while True:
	client = ws.accept()
	if client is not None:
		# figure out who they are and add to list
		user = User(client)
		initUser(user)
		users.append(user)

	# For each client, see if they sent anything
	for user in users:
		recvd = WSocket.recv(user, 4096)
		if recvd is None:
			continue
		print("Received %s" % recvd)
		# If they did send something, send it to every client
		# THIS IS THE POINT WHERE WE WILL BE INSPECTING USER INPUT
		# TO SEE IF IT'S A CHAT MESSAGE, AN ATTEMPT AT MAKING A GAME
		# MOVE/VOTE/WHATEVER. IN THE CASE OF A MESSAGE, IT DATA WILL
		# BE SENT TO EVERYONE

		# first, get action (should seperate into ['action', 'value'])
		action = recvd.split(':', 1)

		if action[0] == 'chat':
			print("chat:%s:%s" % (u.name if not None else u.id, action[1]))
			for u in users:
				WSocket.send(u.socket, "chat:%s:%s" % (u.name if not None else u.id, action[1]))
		elif action[0] == 'vote':
			# Should be either reject/approve or success/fail depending on what vote is for
			pass
		elif action[0] == 'name':
			# When someone updates their name, tell everyone
			# Could potentially be abused? TODO: rate limit? only allow once?
			for u in users:
				WSocket.send(u.socket, '%s:%s' % (user.id, user.name))
			pass
		elif action[0] == 'whoami':
			# If the client reconnects, the browser won't "remember" who is who
			# so remind them
			pass
