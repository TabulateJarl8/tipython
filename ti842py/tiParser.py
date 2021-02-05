import re
import logging
import os

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARNING)

def closeOpen(string):
	newString = ""
	# Function for closing open quotation marks/parenthesis
	open = False
	closingChar = ""
	for i, c in enumerate(string):
		if i + 1 == len(string) and c != closingChar:
			# Last character and current character does not close
			if open == True:
				# Append open character to string
				c += closingChar
		# elif c == "," and open == True:
			# Reached a comma with open character
			# newString += closingChar
		elif open == True and c == closingChar:
			# Closing character reached
			open = False
			closingChar = ""
		elif open == False and c == "\"":
			# Opening quote
			open = True
			closingChar = "\""
		elif open == False and c == "(":
			# Opening parenthesis
			open = True
			closingChar = ")"
		newString += c
	return newString

def fixEquals(string):
	# Change = to ==
	return re.sub("(?<![<>!])\=", " == ", string)


class BasicParser(object):
	def __init__(self, basic):
		if isinstance(basic, list):
			self.basic = basic
		elif isinstance(basic, str):
			self.basic = [line.strip() for line in basic.split("\n")]
		else:
			raise TypeError("basic must be list or str, not {}".format(str(type(basic))))

		# Utility Functions
		self.UTILS = {"wait": {"code": [""], "imports": ["import time"], "enabled": False}}
		here = os.path.abspath(os.path.dirname(__file__))
		for file in [file for file in os.listdir(os.path.join(here, "utils")) if os.path.isfile(os.path.join(here, "utils", file))]:
			with open(os.path.join(here, "utils", file)) as f:
				self.UTILS[os.path.splitext(file)[0]] = {}
				self.UTILS[os.path.splitext(file)[0]]["code"] = [line.rstrip() for line in f.readlines() if not line.startswith("import ") and not line.startswith("from ")]
				f.seek(0)
				self.UTILS[os.path.splitext(file)[0]]["imports"] = [line.rstrip() for line in f.readlines() if line.startswith("import ") or line.startswith("from ")]
				self.UTILS[os.path.splitext(file)[0]]["enabled"] = False

	def toPython(self):
		pythonCode = []

		pythonCode += ["def main():"]

		indentLevel = 1
		# indentIncrease increases the indent on the next line
		indentIncrease = False
		# indentDecrease decreases the indent on the current line
		indentDecrease = False
		skipLine = False
		for index, line in enumerate(self.basic):
			statement = ""
			# TODO: Make rules for :, dont fully understand it yet
			if line.startswith("\""):
				# Comments
				statement = "# " + line.lstrip("\"")
			elif skipLine == True:
				skipLine = False
				continue
			elif line == "":
				# Blank
				statement = ""
			# Disp
			elif line.startswith("Disp "):
				statement = re.search("Disp (.*[^)])", line).groups(1)[0]
				statement = "print(" + closeOpen(statement) + ", sep=\"\")"
			# Variables
			elif "->" in line or "→" in line:
				statement = re.split("->|→", line)
				statement.reverse()
				statement = " = ".join(statement)
			# If
			elif line.startswith("If "):
				statement = "if " + line.lstrip("If ")
				statement = fixEquals(statement)
				statement = statement + ":"
				indentIncrease = True
			elif line == "Then":
				continue
			# Elif
			elif line == "Else" and self.basic[index + 1].startswith("If"):
				statement = "elif " + self.basic[index + 1].lstrip("If ")
				statement = fixEquals(statement)
				statement = statement + ":"
				indentDecrease = True
				indentIncrease = True
				skipLine = True
			# Else
			elif line == "Else" and not (self.basic[index + 1].startswith("If")):
				statement = "else:"
				indentDecrease = True
				indentIncrease = True
			elif line == "ClrHome":
				self.UTILS["clear"]["enabled"] = True
				statement = "clear()"
			elif line == "End":
				indentDecrease = True
			# Input
			elif line.startswith("Input"):
				statement = line.split(",")
				if len(statement) > 1:
					if "," in statement[1]:
						statement = statement[1] + " = [toNumber(number) for number in input(" + closeOpen(statement[0][6:]) + ")]"
					else:
						statement = statement[1] + " = toNumber(input(" + closeOpen(statement[0][6:]) + "))"
				else:
					if statement[0].strip() != "Input":
						# No input text
						statement = statement[0][6:] + " = toNumber(input(\"?\"))"
					else:
						statement = "input()"
				self.UTILS["toNumber"]["enabled"] = True
			# For loop
			elif line.startswith("For"):
				args = line[3:].strip("()").split(",")
				statement = "for " + args[0] + " in range(" + args[1] + ", " + args[2]
				if len(args) == 4:
					statement += ", " + args[3]
				statement += "):"
				indentIncrease = True
			# While loop
			elif line.startswith("While "):
				statement = "while " + fixEquals(line[6:]) + ":"
				indentIncrease = True
			# Repeat loop (tests at bottom)
			elif line.startswith("Repeat "):
				statement = ["firstPass = True", "while firstPass == True or " + fixEquals(line[7:]) + ":", "\tfirstPass = False"]
				indentIncrease = True
			# Pause
			elif line.startswith("Pause"):
				args = line[5:].strip().split(",")
				if len(args) <= 1:
					statement = "input("
					if len(args) == 1:
						statement += str(args[0]) + ")"
				else:
					statement = ["print(" + str(args[0]) + ")", "time.sleep(" + args[1] + ")"]
					self.UTILS["wait"]["enabled"] = True
			# Wait
			elif line.startswith("Wait"):
				statement = "time.sleep(" + line[5:] + ")"
				self.UTILS["wait"]["enabled"] = True
			# Stop
			elif line == "Stop":
				statement = "exit()"
			# DelVar
			elif line.startswith("DelVar"):
				statement = "del " + line[7:]
			# Prompt
			elif line.startswith("Prompt"):
				variable = line[7:]
				if "," in variable:
					statement = variable + " = [toNumber(number) for number in input(\"" + variable + "=?\").split(\",\")]"
				else:
					statement = variable + " = toNumber(input(\"" + variable + "=?\"))"
				self.UTILS["toNumber"]["enabled"] = True
			elif line == "getKey":
				statement = "getKey()"
			# Goto (eww)
			elif line.startswith("Goto "):
				statement = "goto .lbl" + line[5:]
				self.UTILS["goto"]["enabled"] = True
			# Lbl
			elif line.startswith("Lbl "):
				statement = "label .lbl" + line[4:]
				self.UTILS["goto"]["enabled"] = True
			# Output
			elif line.startswith("Output("):
				statement = line[7:]
				statement = statement.split(",")
				if statement[-1].count("\"") > 1:
					statement[-1] = re.findall('"([^"]*)"', statement[-1])[0]
				else:
					statement[-1] = statement[-1].strip(" ")[1:]
				statement = "output(" + statement[1].strip(" ") + ", " + statement[0].strip(" ") + ", \"" + statement[-1] + "\")"
				self.UTILS["output"]["enabled"] = True
			else:
				statement = "# UNKNOWN INDENTIFIER: {}".format(line)
				logger.warning("Unknown indentifier on line %s", index)

			# Fix things contained within statement

			if "getKey" in statement:
				# Replace getKey with getKey() if getKey is not inside of quotes
				statement = re.sub(r'(?!\B"[^"]*)getKey(?!\()+(?![^"]*"\B)', "getKey()", statement)
				self.UTILS["getKey"]["enabled"] = True
			if "[theta]" in statement:
				# Replace [theta] with theta if [theta] is not inside of quotes
				statement = re.sub(r'(?!\B"[^"]*)\[theta\](?![^"]*"\B)', "theta", statement)
			if "^" in statement:
				# Convert every ^ not in a string to **
				statement = re.sub(r'(?!\B"[^"]*)\^(?![^"]*"\B)', "**", statement)
			if "–" in statement:
				# Remove long dash if not in string
				statement = re.sub(r'(?!\B"[^"]*)–(?![^"]*"\B)', "-", statement)
			if "getTime" in statement:
				# Replace getTime with getTime() if getTime is not inside of quotes
				statement = re.sub(r'(?!\B"[^"]*)getTime(?!\()+(?![^"]*"\B)', "getTime()", statement)
				self.UTILS["getDateTime"]["enabled"] = True
			if "getDate" in statement:
				# Replace getDate with getDate() if getDate is not inside of quotes
				statement = re.sub(r'(?!\B"[^"]*)getDate(?!\()+(?![^"]*"\B)', "getDate()", statement)
				self.UTILS["getDateTime"]["enabled"] = True

			if indentDecrease == True:
				indentLevel -= 1
				indentDecrease = False

			if isinstance(statement, str):
				pythonCode.append("\t"*indentLevel + statement)
			elif isinstance(statement, list):
				for item in statement:
					pythonCode.append("\t"*indentLevel + item)

			if indentIncrease == True:
				indentLevel += 1
				indentIncrease = False

		# Decorate main with with_goto if goto is used
		if self.UTILS["goto"]["enabled"] == True:
			pythonCode.insert(0, "@with_goto")

		# Add required utility functions
		neededImports = []
		for item in self.UTILS:
			if self.UTILS[item]["enabled"] == True:
				# Add code to new file
				pythonCode = self.UTILS[item]["code"] + pythonCode
				for importedPackage in self.UTILS[item]["imports"]:
					# Have separate list so that all of the imports are at the top
					if not importedPackage in neededImports:
						neededImports.append(importedPackage)
		pythonCode = neededImports + pythonCode

		pythonCode += ["if __name__ == \"__main__\":", "\tmain()"]

		return pythonCode
