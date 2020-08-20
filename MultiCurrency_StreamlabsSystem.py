#---------------------------------------
#   Import Libraries
#---------------------------------------
import logging
from logging.handlers import TimedRotatingFileHandler
import clr
import re
import os
import codecs
import json
import ast
from operator import neg
from ConfigParser import ConfigParser
clr.AddReference("IronPython.SQLite.dll")
import sqlite3
clr.AddReference("websocket-sharp.dll")
from WebSocketSharp import WebSocket

#---------------------------------------
#   [Required] Script Information
#---------------------------------------
ScriptName = "MultiCurrency"
Website = "https://github.com/nossebro/MultiCurrency"
Creator = "nossebro"
Version = "0.1.5"
Description = "Add more currencies with (Streamlabs-like) commands and listening for events to add or remove currency."

#---------------------------------------
#   Script Variables
#---------------------------------------
ScriptSettings = None
LocalAPI = None
Logger = None
LocalSocket = None
LocalSocketIsConnected = False
CurrencyObj = None
ConfigFile = os.path.join(os.path.dirname(__file__), "Config.ini")
SettingsFile = os.path.join(os.path.dirname(__file__), "Settings.json")
UIConfigFile = os.path.join(os.path.dirname(__file__), "UI_Config.json")
APIKeyFile = os.path.join(os.path.dirname(__file__), "API_Key.js")

#---------------------------------------
#   Script Classes
#---------------------------------------
class StreamlabsLogHandler(logging.StreamHandler):
	def emit(self, record):
		try:
			message = self.format(record)
			Parent.Log(ScriptName, message)
			self.flush()
		except (KeyboardInterrupt, SystemExit):
			raise
		except:
			self.handleError(record)

class Settings(object):
	def __init__(self, settingsfile=None):
		defaults = self.DefaultSettings(UIConfigFile)
		try:
			with codecs.open(settingsfile, encoding="utf-8-sig", mode="r") as f:
				settings = json.load(f, encoding="utf-8")
			self.__dict__ = MergeLists(defaults, settings)
		except:
			self.__dict__ = defaults

	def DefaultSettings(self, settingsfile=None):
		defaults = dict()
		with codecs.open(settingsfile, encoding="utf-8-sig", mode="r") as f:
			ui = json.load(f, encoding="utf-8")
		for key in ui:
			try:
				defaults[key] = ui[key]['value']
			except:
				if key != "output_file":
					Parent.Log(ScriptName, "DefaultSettings(): Could not find key {0} in settings".format(key))
		return defaults

	def Reload(self, jsondata):
		self.__dict__ = MergeLists(self.DefaultSettings(UIConfigFile), json.loads(jsondata, encoding="utf-8"))

#---------------------------------------
#   Script Functions
#---------------------------------------
def GetLogger():
	log = logging.getLogger(ScriptName)
	log.setLevel(logging.DEBUG)

	sl = StreamlabsLogHandler()
	sl.setFormatter(logging.Formatter("%(funcName)s(): %(message)s"))
	sl.setLevel(logging.INFO)
	log.addHandler(sl)

	fl = TimedRotatingFileHandler(filename=os.path.join(os.path.dirname(__file__), "info"), when="w0", backupCount=8, encoding="utf-8")
	fl.suffix = "%Y%m%d"
	fl.setFormatter(logging.Formatter("%(asctime)s  %(funcName)s(): %(levelname)s: %(message)s"))
	fl.setLevel(logging.INFO)
	log.addHandler(fl)

	if ScriptSettings.DebugMode:
		dfl = TimedRotatingFileHandler(filename=os.path.join(os.path.dirname(__file__), "debug"), when="h", backupCount=24, encoding="utf-8")
		dfl.suffix = "%Y%m%d%H%M%S"
		dfl.setFormatter(logging.Formatter("%(asctime)s  %(funcName)s(): %(levelname)s: %(message)s"))
		dfl.setLevel(logging.DEBUG)
		log.addHandler(dfl)

	log.debug("Logger initialized")
	return log

def GetAPIKey(apifile=None):
	API = dict()
	try:
		with codecs.open(apifile, encoding="utf-8-sig", mode="r") as f:
			lines = f.readlines()
		matches = re.search(r"\"\s?([0-9a-f]+)\".*\"\s?(ws://[0-9.:]+/\w+)\"", "".join(lines))
		if matches:
			API["Key"] = matches.group(1)
			API["Socket"] = matches.group(2)
			Logger.debug("Got Key ({0}) and Socket ({1}) from API_Key.js".format(matches.group(1), matches.group(2)))
	except:
		Logger.critical("API_Key.js is missing in script folder")
	return API

def MergeLists(x = dict(), y = dict()):
	z = dict()
	for attr in x:
		if attr not in y:
			z[attr] = x[attr]
		else:
			z[attr] = y[attr]
	return z

def UpdateCurrency(caster = str(), currency = str(), command = str(), user = str(), amount = int()):
	global CurrencyObj
	DB = CurrencyObj["Currency"][currency]["Database"].cursor()
	userlist = [ user ]
	group = "viewers"
	action = "addto"
	if user == "+active":
		userlist = Parent.GetActiveUsers()
	elif user == "+viewers":
		userlist = Parent.GetViewerList()
	else:
		group = "user"
	if command == "add":
		if user.startswith("+"):
			Parent.SendTwitchMessage(CurrencyObj["Currency"][currency]["addtoviewers"].format(broadcaster=caster, action="Started", amount=amount, currency=CurrencyObj["Currency"][currency]["Name"], group=user))
			Logger.debug("Adding {0} {1} to {2}".format(amount, currency, ", ".join(userlist)))
		for x in userlist:
			DB.execute("INSERT INTO currency (date, user, currency) VALUES (DATETIME('now'), ?, ?);", (x, amount))
	elif command == "remove":
		action = "removefrom"
		if user.startswith("+"):
			Parent.SendTwitchMessage(CurrencyObj["Currency"][currency]["removefromviewers"].format(broadcaster=caster, action="Started", amount=amount, currency=CurrencyObj["Currency"][currency]["Name"], group=user))
			Logger.debug("Removing {0} {1} to {2}".format(amount, currency, ", ".join(userlist)))
		for x in userlist:
			DB.execute("INSERT INTO currency (date, user, currency) VALUES (DATETIME('now'), ?, ?);", (x, neg(amount)))
	CurrencyObj["Currency"][currency]["Database"].commit()
	if user.startswith("+"):
		Parent.SendTwitchMessage(CurrencyObj["Currency"][currency]["{0}{1}".format(action, group)].format(broadcaster=caster, action="Done", amount=amount, currency=CurrencyObj["Currency"][currency]["Name"], group=user))
	else:
		Parent.SendTwitchMessage(CurrencyObj["Currency"][currency]["{0}{1}".format(action, group)].format(broadcaster=caster, user=user, amount=amount, currency=CurrencyObj["Currency"][currency]["Name"]))

def TransferCurrency(caster = str(), currency = str(), fromuser = str(), touser = str()):
	global CurrencyObj
	DB = CurrencyObj["Currency"][currency]["Database"].cursor()
	DB.execute("UPDATE currency SET user = '{0}' WHERE user == '{1}' COLLATE NOCASE;".format(touser, fromuser))
	CurrencyObj["Currency"][currency]["Database"].commit()
	Parent.SendTwitchMessage("{0} --> Succesfully transferred {1} from {2} to {3}!".format(caster, CurrencyObj["Currency"][currency]["Name"], Parent.GetDisplayName(fromuser), Parent.GetDisplayName(touser)))
	Logger.debug("Transfering all {1} from {2} to {3}".format(amount, currency, fromuser, touser))

#---------------------------------------
#   Chatbot Initialize Function
#---------------------------------------
def Init():
	global ScriptSettings
	ScriptSettings = Settings(SettingsFile)
	global Logger
	Logger = GetLogger()

	global CurrencyObj
	CurrencyObj = dict()
	CurrencyObj["Currency"] = dict()
	config = ConfigParser()
	if not config.read(ConfigFile):
		Logger.warning("Could not read Config.ini")
	if config.has_section("Defaults"):
		CurrencyObj["Defaults"] = dict()
		CurrencyObj["Defaults"].update(config.items("Defaults"))
		config.remove_section("Defaults")
	if config.has_section("Rewards"):
		CurrencyObj["Commands"] = dict()
		CurrencyObj["Commands"].update(config.items("Rewards"))
		config.remove_section("Rewards")
	for x in config.sections():
		CurrencyObj["Currency"][config.get(x, "Command")] = { "Name": x, "Cooldown": config.getint(x, "Cooldown"), "Database": sqlite3.connect(os.path.join(os.path.dirname(__file__), config.get(x, "Database")), check_same_thread = False) }
		DB = CurrencyObj["Currency"][config.get(x, "Command")]["Database"].cursor()
		DB.execute("CREATE TABLE IF NOT EXISTS currency (date text, user text, currency integer);")
		CurrencyObj["Currency"][config.get(x, "Command")]["Database"].commit()
		DB = None
		for y in CurrencyObj["Defaults"]:
			if config.has_option(x, y):
				CurrencyObj["Currency"][config.get(x, "Command")][y] = config.get(x, y)
			else:
				CurrencyObj["Currency"][config.get(x, "Command")][y] = CurrencyObj["Defaults"][y]
	Logger.debug(CurrencyObj)

	global LocalSocket
	global LocalAPI
	LocalAPI = GetAPIKey(APIKeyFile)
	LocalSocket = WebSocket(LocalAPI["Socket"])
	LocalSocket.OnOpen += LocalSocketConnected
	LocalSocket.OnClose += LocalSocketDisconnected
	LocalSocket.OnMessage += LocalSocketEvent
	LocalSocket.OnError += LocalSocketError

	if all (keys in LocalAPI for keys in ("Key", "Socket")):
		LocalSocket.Connect()
	else:
		Logger.critical("API_Key.js missing from script folder")

	Parent.AddCooldown(ScriptName, "LocalSocket", 10)

#---------------------------------------
#   Chatbot Script Unload Function
#---------------------------------------
def Unload():
	global LocalSocket
	if LocalSocket:
		LocalSocket.Close(1000, "Program exit")
		LocalSocket = None
		Logger.debug("LocalSocket Disconnected")
	global CurrencyObj
	for x in CurrencyObj["Currency"]:
		if CurrencyObj["Currency"][x]["Database"]:
			CurrencyObj["Currency"][x]["Database"].close()
			CurrencyObj["Currency"][x]["Database"] = None
	global Logger
	if Logger:
		for handler in Logger.handlers[:]:
			Logger.removeHandler(handler)
		Logger = None

#---------------------------------------
#   Chatbot Save Settings Function
#---------------------------------------
def ReloadSettings(jsondata):
	ScriptSettings.Reload(jsondata)
	Logger.debug("Settings reloaded")

	if LocalSocket and not LocalSocket.IsAlive:
		if all (keys in LocalAPI for keys in ("Key", "Socket")):
			LocalSocket.Connect()

	Parent.BroadcastWsEvent('{0}_UPDATE_SETTINGS'.format(ScriptName.upper()), json.dumps(ScriptSettings.__dict__))
	Logger.debug(json.dumps(ScriptSettings.__dict__), True)

#---------------------------------------
#   Chatbot Execute Function
#---------------------------------------
def Execute(data):
	if data.IsChatMessage() and data.IsFromTwitch():
		global CurrencyObj
		match = re.match(r"!(?P<currency>[\w\d]+)", data.GetParam(0))
		if match and match.group("currency").lower() and match.group("currency").lower() in CurrencyObj["Currency"]:
			currency = match.group("currency").lower()
			DB = CurrencyObj["Currency"][currency]["Database"].cursor()
			# Viewer checks currency status with !<currency>
			if data.GetParamCount() == 1 and not Parent.IsOnCooldown(ScriptName, currency):
				DB.execute("SELECT SUM(currency) AS currency FROM currency WHERE user == '{0}' COLLATE NOCASE;".format(data.User))
				total = int(DB.fetchall()[0][0] or 0)
				Parent.SendTwitchMessage(CurrencyObj["Currency"][currency]["response"].format(user=data.UserName, amount=total, currency=CurrencyObj["Currency"][currency]["Name"]))
				Parent.AddCooldown(ScriptName, currency, CurrencyObj["Currency"][currency]["Cooldown"])
				Logger.debug("Status: user: {0}, currency: {1}, amount: {2}".format(data.User, currency, total))
			# Viewer enters or leaves the queue
			elif "QueueActive" in CurrencyObj["Currency"][currency] and data.GetParamCount() == 3 and data.GetParam(1).lower() == "queue" and data.GetParam(2).lower() in [ "enter", "leave" ] and not Parent.IsOnUserCooldown(ScriptName, currency, data.User):
				if not "Queue" in CurrencyObj["Currency"][currency] or not isinstance(CurrencyObj["Currency"][currency]["Queue"], list):
					CurrencyObj["Currency"][currency]["Queue"] = list()
				if data.GetParam(2).lower() == "enter" and CurrencyObj["Currency"][currency]["QueueActive"]:
					if not data.User in CurrencyObj["Currency"][currency]["Queue"]:
						DB.execute("SELECT SUM(currency) AS currency FROM currency WHERE user == '{0}' COLLATE NOCASE;".format(data.User))
						value = int(DB.fetchall()[0][0] or 0)
						Logger.debug("Enter Queue: user: {0}, currency: {1}, amount: {2}".format(data.User, currency, value))
						if value >= CurrencyObj["Currency"][currency]["QueueCost"]:
							CurrencyObj["Currency"][currency]["Queue"].append(data.User)
							Parent.SendTwitchMessage(CurrencyObj["Currency"][currency]["enterqueue"].format(user=data.UserName, currency=CurrencyObj["Currency"][currency]["Name"], position=len(CurrencyObj["Currency"][currency]["Queue"])))
						else:
							Parent.SendTwitchMessage("{0}: Not enough {1}: {2} ({3} needed)".format(data.UserName, CurrencyObj["Currency"][currency]["Name"], value, CurrencyObj["Currency"][currency]["QueueCost"]))
				elif data.GetParam(2).lower() == "leave":
					if data.User in CurrencyObj["Currency"][currency]["Queue"]:
						Logger.debug("Leave Queue: user: {0}, currency: {1}".format(data.User, currency))
						CurrencyObj["Currency"][currency]["Queue"].remove(data.User)
						Parent.SendTwitchMessage(CurrencyObj["Currency"][currency]["leavequeue"].format(user=data.UserName, currency=CurrencyObj["Currency"][currency]["Name"]))
				Parent.AddUserCooldown(ScriptName, currency, data.User, CurrencyObj["Currency"][currency]["Cooldown"])
			elif data.GetParamCount() == 3 and Parent.HasPermission(data.User, "caster", "") and data.GetParam(2).lower() in [ "stop" , "list" ]:
				# Broadcaster stops the queue
				if data.GetParam(2).lower() == "stop":
					CurrencyObj["Currency"][currency]["QueueActive"] = None
					Parent.SendTwitchMessage(CurrencyObj["Currency"][currency]["closequeue"].format(broadcaster=data.UserName, command=currency, currency=CurrencyObj["Currency"][currency]["Name"]))
					Logger.debug("Stop Queue: currency: {0}, queue: {1}".format(currency, ", ".join(CurrencyObj["Currency"][currency]["Queue"])))
				# Broadcaster lists the queue
				elif data.GetParam(2).lower() == "list":
					if not "Queue" in CurrencyObj["Currency"][currency] or not isinstance(CurrencyObj["Currency"][currency]["Queue"], list) or len(CurrencyObj["Currency"][currency]["Queue"]) == 0:
						Parent.SendTwitchMessage("{0} queue empty!".format(CurrencyObj["Currency"][currency]["Name"]))
					else:
						Parent.SendTwitchMessage("{0} queue: {1}".format(CurrencyObj["Currency"][currency]["Name"], ", ".join(CurrencyObj["Currency"][currency]["Queue"])))
					Logger.debug("List Queue: currency: {0}, queue {1}".format(currency, ", ".join(CurrencyObj["Currency"][currency]["Queue"])))
			elif data.GetParamCount() == 4 and Parent.HasPermission(data.User, "caster", ""):
				# Broadcaster adds or removes currency
				if data.GetParam(1).lower() in [ "add", "remove" ]:
					if isinstance(ast.literal_eval(data.GetParam(3)), int):
						UpdateCurrency(caster=data.UserName, currency=currency, command=data.GetParam(1).lower(), user=data.GetParam(2).replace("@", "").lower(), amount=int(data.GetParam(3)))
					else:
						Parent.SendTwitchMessage("Malformed {0} command".format(currency))
				# Broadcaster transfers currency from one user to another
				elif data.GetParam(1).lower() == "transfer":
					TransferCurrency(caster=data.UserName, currency=currency, fromuser=data.GetParam(2).replace("@", "").lower(), touser=data.GetParam(3).replace("@", "").lower())

				elif data.GetParam(1).lower() == "queue":
					# Broadcaster starts the queue
					if data.GetParam(2).lower() == "start":
						Logger.debug("Start Queue: currency: {0}, cost: {1}".format(currency, data.GetParam(3)))
						if isinstance(ast.literal_eval(data.GetParam(3)), int):
							CurrencyObj["Currency"][currency]["QueueActive"] = True
							CurrencyObj["Currency"][currency]["QueueCost"] = int(data.GetParam(3))
							Parent.SendTwitchMessage(CurrencyObj["Currency"][currency]["openqueue"].format(broadcaster=data.UserName, command=currency, currency=CurrencyObj["Currency"][currency]["Name"], cost=int(data.GetParam(3))))
						else:
							Parent.SendTwitchMessage("Malformed {0} queue command".format(currency))
					# Broadcaster picks
					elif data.GetParam(2).lower() == "pick" and "QueueCost" in CurrencyObj["Currency"][currency]:
						if isinstance(ast.literal_eval(data.GetParam(3)), int):
							length = int(data.GetParam(3))
							if length > len(CurrencyObj["Currency"][currency]["Queue"]):
								length = len(CurrencyObj["Currency"][currency]["Queue"])
							if length == 0:
								Parent.SendTwitchMessage("No users in {0} queue!".format(CurrencyObj["Currency"][currency]["Name"]))
								return
							picks = list()
							Logger.debug("Picks: currency: {0}, picks: {1}, length: {2}, queue: {3}".format(currency, length, len(CurrencyObj["Currency"][currency]["Queue"]), ", ".join(CurrencyObj["Currency"][currency]["Queue"])))
							for user in CurrencyObj["Currency"][currency]["Queue"][:length]:
								Logger.debug("Picked user: {0}".format(user))
								DB.execute("SELECT SUM(currency) AS currency FROM currency WHERE user == '{0}' COLLATE NOCASE;".format(user))
								value = int(DB.fetchall()[0][0] or 0)
								if value >= CurrencyObj["Currency"][currency]["QueueCost"]:
									picks.append(user)
									DB.execute("INSERT INTO currency (date, user, currency) VALUES (DATETIME('now'), ?, ?);", (user, neg(CurrencyObj["Currency"][currency]["QueueCost"])))
								else:
									Logger.info("Can not add {1} to queue, not enough {0}: {1} ({2})".format(CurrencyObj["Currency"][currency]["Name"], user, value))
								CurrencyObj["Currency"][currency]["Queue"].remove(user)
							CurrencyObj["Currency"][currency]["Database"].commit()
							if len(picks) > 0:
								Parent.SendTwitchMessage(CurrencyObj["Currency"][currency]["pickqueue"].format(broadcaster=data.UserName, amount=len(picks), users=", ".join(picks)))
							else:
								Parent.SendTwitchMessage("{0} queue was empty!".format(CurrencyObj["Currency"][currency]["Name"]))
						else:
							Parent.SendTwitchMessage("Malformed {0} queue command".format(currency))

#---------------------------------------
#   Chatbot Tick Function
#---------------------------------------
def Tick():
	global LocalSocketIsConnected
	if not Parent.IsOnCooldown(ScriptName, "LocalSocket") and not LocalSocketIsConnected and all (keys in LocalAPI for keys in ("Key", "Socket")):
		Logger.warning("No EVENT_CONNECTED received from LocalSocket, reconnecting")
		try:
			LocalSocket.Close(1006, "No connection confirmation received")
		except:
			Logger.error("Could not close LocalSocket gracefully")
		LocalSocket.Connect()
		Parent.AddCooldown(ScriptName, "LocalSocket", 10)
	if not Parent.IsOnCooldown(ScriptName, "LocalSocket") and not LocalSocket.IsAlive:
		Logger.warning("LocalSocket seems dead, reconnecting")
		try:
			LocalSocket.Close(1006, "No connection")
		except:
			Logger.error("Could not close LocalSocket gracefully")
		LocalSocket.Connect()
		Parent.AddCooldown(ScriptName, "LocalSocket", 10)

#---------------------------------------
#   LocalSocket Connect Function
#---------------------------------------
def LocalSocketConnected(ws, data):
	global LocalAPI
	Auth = {
		"author": Creator,
		"website": Website,
		"api_key": LocalAPI["Key"],
		"events": [ "TWITCH_REWARD_V1" ]
	}
	ws.Send(json.dumps(Auth))
	Logger.debug("Auth: {0}".format(json.dumps(Auth)))

#---------------------------------------
#   LocalSocket Disconnect Function
#---------------------------------------
def LocalSocketDisconnected(ws, data):
	global LocalSocketIsConnected
	LocalSocketIsConnected = False
	if data.Reason:
		Logger.debug("{0}: {1}".format(data.Code, data.Reason))
	elif data.Code == 1000 or data.Code == 1005:
		Logger.debug("{0}: Normal exit".format(data.Code))
	else:
		Logger.debug("{0}: Unknown reason".format(data.Code))
	if not data.WasClean:
		Logger.warning("Unclean socket disconnect")

#---------------------------------------
#   LocalSocket Error Function
#---------------------------------------
def LocalSocketError(ws, data):
	Logger.error(data.Message)
	if data.Exception:
		Logger.exception(data.Exception)

#---------------------------------------
#   LocalSocket Event Function
#---------------------------------------
def LocalSocketEvent(ws, data):
	if data.IsText:
		event = json.loads(data.Data)
		if "data" in event and isinstance(event["data"], str):
			event["data"] = json.loads(event["data"])
		if event["event"] == "EVENT_CONNECTED":
			global LocalSocketIsConnected
			LocalSocketIsConnected = True
			Logger.info(event["data"]["message"])
		elif event["event"] == "TWITCH_REWARD_V1":
			if event["data"]["reward_id"] in CurrencyObj["Commands"]:
				txt = CurrencyObj["Commands"][event["data"]["reward_id"]].split(" ")
				match = re.match(r"!(?P<currency>[\w\d]+)", txt[0])
				UpdateCurrency(caster=event["data"]["display_name"], currency=match.group("currency").lower(), command=txt[1].lower(), user=event["data"]["user_name"], amount=int(txt[3]))
#		else:
#			Logger.warning("Unhandled event: {0}: {1}".format(event["event"], event["data"]))
