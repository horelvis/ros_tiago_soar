# Copyright (c) 2016 PAL Robotics SL. All Rights Reserved
#
# Permission to use, copy, modify, and/or distribute this software for
# any purpose with or without fee is hereby granted, provided that the
# above copyright notice and this permission notice appear in all
# copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#
# Author:
#   * Sammy Pfeiffer

# System imports
import sys
import time
import os
# ROS imports
import rospy
from actionlib import SimpleActionClient, GoalStatus
from play_motion_msgs.msg import PlayMotionAction, PlayMotionGoal
# Soar imports
PATH_TO_SOAR = "/home/tiago/rapela/Soar/out"
sys.path.append(PATH_TO_SOAR)
import Python_sml_ClientInterface as sml
import cv2
import tiagoObjectDetection as Tiago

SOAR_GP_PATH = "./regras.soar"
object_found = False
search_done = False
object_exists = True

def wait_for_valid_time(timeout):
	"""Wait for a valid time (non-zero), this is important
	when using a simulated clock"""
	# Loop until:
	# * ros master shutdowns
	# * control+C is pressed (handled in is_shutdown())
	# * timeout is achieved
	# * time is valid
	start_time = time.time()
	while not rospy.is_shutdown():
		if not rospy.Time.now().is_zero():
			return
		if time.time() - start_time > timeout:
			rospy.logerr("Timed-out waiting for valid time.")
			exit(0)
		time.sleep(0.1)
	# If control+C is pressed the loop breaks, we can exit
	exit(0)


def get_status_string(status_code):
	return GoalStatus.to_string(status_code)

class SOARInterface:
	def __init__(self):
		pass

	def action(self, comm):
		command_name = comm
		if command_name == "takeoff":
			# out = robot.act(command_name)
			pass

	def sendOK(self):
		return "succeeded"

def define_prohibitions(): #TODISCOVER WTF IS THIS
	pass

def create_kernel():
	kernel = sml.Kernel.CreateKernelInNewThread()
	if not kernel or kernel.HadError():
		print kernel.GetLastErrorDescription()
		exit(1)
	return kernel

def create_agent(kernel, name):
	agent = kernel.CreateAgent("agent")
	if not agent:
		print kernel.GetLastErrorDescription()
		exit(1)
	return agent

def agent_load_productions(agent, path):
	agent.LoadProductions(path)
	if agent.HadError():
		print agent.GetLastErrorDescription()
		exit(1)

def object_load(object_name, pathFolder="./objects"):
	list_names = os.listdir(pathFolder)

	if object_name in list_names:
		return 1
	else:
		return 0

if __name__ == '__main__':
	soar_interface = SOARInterface()
	tiago = Tiago.TiagoObjectDetection()

	print "******************************\n******************************\nNew goal\n******************************\n******************************\n"
	kernel = create_kernel()
	agent = create_agent(kernel, "agent")
	agent_load_productions(agent,SOAR_GP_PATH)
	agent.SpawnDebugger()
	done = 'n'

	kernel.CheckForIncomingCommands()

	# time.sleep(5)

	pInputLink = agent.GetInputLink()
	# pID = agent.CreateIdWME(pInputLink, "helloworld")
	# pID = agent.CreateIdWME(pInputLink, "tiago")
	# agent.Commit()

	# Precisa fazer um run antes de iniciar.
	agent.RunSelf(1)
	agent.Commands()
	while not done == 'y':
		objectName = None
		objectName = raw_input("Write the name of the object to find: ")
		while not search_done:
			# agent.RunSelfTilOutput()
			agent.RunSelf(1)
			agent.Commands()
			numberCommands = agent.GetNumberCommands()
			if (numberCommands):
				command = agent.GetCommand(0)
				command_name = command.GetCommandName()
				command_attr = command.FindByAttribute('name',0)
				command_name = command_attr.GetValueAsString()

				if command_name  == 'init':
					wme_cmd = agent.CreateIdWME(pInputLink, "cmd")
					wme_cmd_name = agent.CreateStringWME(wme_cmd, "name", "search")
					wme_cmd_obj_name = agent.CreateStringWME(wme_cmd, "obj_name", objectName)
					agent.Commit()
					# Precisa dar dois RunSelf. Fazendo um agora e o outro na iteracao normal
					agent.RunSelf(1)
				elif command_name  == 'search':
					o_name = command.FindByAttribute('obj_name',0).GetValueAsString()
					tiago.act(action = "detectObject", objectPath=o_name)

					wme_status = agent.CreateIntWME(pInputLink, "status", tiago.getObjectFoundFlag())
					agent.Commit()
					# Precisa dar dois RunSelf. Fazendo um agora e o outro na iteracao normal
					agent.RunSelf(1)
				elif command_name  == 'presearch':
					object_load_state = object_load(objectName)
					wme_new = agent.CreateIntWME(pInputLink, "new", object_load_state)
					if(object_load_state):
						wme_obj = agent.CreateIdWME(pInputLink, "obj")
						wme_obj_name = agent.CreateStringWME(wme_obj, "name", objectName)
					agent.Commit()
					# Precisa dar dois RunSelf. Fazendo um agora e o outro na iteracao normal
					agent.RunSelf(1)
				elif command_name  == 'presearchresultfound':
					agent.DestroyWME(wme_new)
					agent.Commit()
					agent.RunSelf(1)
				elif command_name  == 'searchresultfound':
					agent.DestroyWME(wme_status)
					agent.Commit()
					search_done = True
					object_found = True
				elif command_name  == 'searchresultnotfound':
					agent.DestroyWME(wme_status)
					agent.Commit()
					search_done = True
					object_found = False
				elif command_name  == 'presearchresultnotfound':
					agent.DestroyWME(wme_new)
					agent.Commit()
					search_done = True
					object_exists = False
				# c = raw_input('continue: ')
			else:
				print("Error. No commands received.")
				c = raw_input('continue: ')
		else:
			agent.DestroyWME(wme_cmd_obj_name)
			agent.DestroyWME(wme_cmd_name)
			agent.DestroyWME(wme_cmd)
			agent.Commit()
		if not object_exists:
			print("Object not exist")
		elif object_found:
			cv2.imshow("Objects to Detect", tiago.getImage())
			cv2.waitKey(30)
			cv2.destroyAllWindows()
			print("FOUND OBJECT")
		else:
			print "Not Found"
		done = raw_input("END? (y/n): ")
		if not done == '':
			object_found = False
			search_done = False
			object_exists = True
		cv2.destroyAllWindows()

	kernel.DestroyAgent(agent)
	kernel.Shutdown()
