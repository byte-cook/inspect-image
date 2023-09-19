#!/usr/bin/env python3

from xml.etree import ElementTree
import xmlutil
import argparse
import os
import logging
import re
from collections import namedtuple

"""
History:
2015-01-15   initial version
2023-09-16   refactoring

"""

RULE_REGEX = "regex"
RULE_NUMBERING = "numbering"

RULE_ERROR = "error"
RULE_WARN = "warn"
RULE_INFO = "info"

# global variable for all messages
messages = []

class Message:
    def __init__(self, pathElement, rule):
        self.pathElement = pathElement
        self.rule = rule

class ImageProfile:
    """Image profile definition."""
    def __init__(self):
        self.name = None
        self.description = None
        self.paths = list()
        self.variables = list()
    def print_profile(self):
        print(" {0:<15}: {1}".format("Profile", self.name))
        print(" {0:<15}: {1}".format("Description", self.description))
        for path in self.paths:
            print(" {0:<15}: {1}".format("Path", path))
        for var in self.variables:
            print(" {0:<15}: {1}".format("Variable", var.name))

class ImageVariable:
    """Image variable is a named component of a path (e.g. artist, album)."""
    def __init__(self):
        self.name = None
        self.rules = list()
        self.pattern = ".*"

class ImageVariableRule:
    """Rule define the structure of an image variable (e.g. lower case)."""
    def __init__(self):
        self.type = None
        self.value = None
        self.message = None
        self.severity = None
        self.invertMatch = False

class PathElement:
    """Path element connects a file to an image variable."""
    def __init__(self):
        self.path = None
        self.variable = None
        self.value = None
        self.file = None
        self.parentPath = None
        self.realPath = None
    def print_element(self):
        print(" {0:<15}: {1}".format("Path", self.path))
        print(" {0:<15}: {1}".format("Variable", self.variable.name))
        print(" {0:<15}: {1}".format("Value", self.value))
        print(" {0:<15}: {1}".format("File", self.file))
        print(" {0:<15}: {1}".format("Parent Path", self.parentPath))
        print(" {0:<15}: {1}".format("Real Path", self.realPath))
        print()

def inspect_image(rootDir, profile, args):
    """Inspects an image."""
    if not os.path.exists(rootDir) or not os.path.isdir(rootDir):
        raise Exception("Illegal directory: " + rootDir)
    
    pathElements = _get_path_elements(rootDir, profile, args)
    _validate_rules(pathElements, profile, args)

def _get_files(rootDir):
    """Returns all files and folders."""
    dirList = list()
    fileList = list()

    top = os.path.abspath(rootDir)
    # read recursive
    for (root, dirs, files) in os.walk(top):
        for d in dirs:
            d = os.path.join(root, d)
            dirList.append(d)
        for f in files:
            f = os.path.join(root, f)
            fileList.append(f)
    # remove duplicates
    dirList = set(dirList)
    fileList = set(fileList)
    return dirList, fileList
    
def _get_path_elements(rootDir, profile, args):
    """Returns path elements containing all required information to validate image rules."""
    rootDir = os.path.abspath(rootDir)
    rootDir = os.path.normcase(rootDir)
    (dirList, fileList) = _get_files(rootDir)
    logging.debug("Root: " + rootDir)
    
    # convert files to relative paths
    files = list()
    for file in fileList:
        relativePath = file.replace(rootDir, "")
        relativePath = relativePath.replace(os.sep, "/")
        files.append(relativePath)
    
    matchingFiles = set()
    pathElements = list()
    # apply for each file
    for file in files:
        logging.debug("== Find path for file: " + file)
        for path in profile.paths:
            if file in matchingFiles:
                # do not use different paths for the same file
                break
            
            if path.count("/") != file.count("/"):
                # skip if number of folders differs
                continue
            
            logging.debug("Path: " + path)
            for var in profile.variables:
                logging.debug("Variable: " + var.name)
                if not var.name in path:
                    # skip if path does not contain variable
                    continue
                # create extraction pattern
                pattern = re.escape(path)
                variablesByLength = sorted(profile.variables, key=lambda x: len(x.name))
                variablesByLength.reverse()
                for v in variablesByLength:
                    if v == var:
                        pattern = pattern.replace(var.name, "("+var.pattern+")", 1)
                    else:
                        pattern = pattern.replace(v.name, v.pattern)
                logging.debug("Pattern: " + pattern)
                
                # apply pattern
                result = re.search(pattern, file, re.IGNORECASE)
                if result:
                    logging.debug(file + ": " + result.group(1))
                    # create path element
                    e = PathElement()
                    e.path = path
                    e.file = file
                    e.variable = var 
                    e.value = result.group(1)
                    # get parent/real path
                    parentPath = ""
                    folderCount = pattern.split("(" + var.pattern + ")", 1)[0].count("/")
                    folders = e.file.split("/")[1:]
                    for i in range(0, folderCount - 1):
                        parentPath += "/" + folders[i]
                    e.parentPath = parentPath
                    realPath = ""
                    for i in range(0, folderCount):
                        realPath += "/" + folders[i]
                    e.realPath = realPath
                    pathElements.append(e)
                    matchingFiles.add(file)
                    # print rule
                    patternRule = ImageVariableRule()
                    patternRule.message = var.name
                    patternRule.severity = RULE_INFO
                    _add_message(e, patternRule, args)
                else:
                    logging.debug(f'Path does not match')
                    break
            
            logging.debug("")
    # print all elements
    for e in pathElements:
#        e.print_element()
#        print()
        pass
    
    # print files without matching path
    fileRule = ImageVariableRule()
    fileRule.message = "No matching path found"
    fileRule.severity = RULE_ERROR
    for file in files:
        if file not in matchingFiles:
            e = PathElement()
            e.path = ""
            e.file = file
            e.value = ""
            _add_message(e, fileRule, args)
    # print dirs without files
    dirRule = ImageVariableRule()
    dirRule.message = "Empty directory found"
    dirRule.severity = RULE_ERROR
    for dir in dirList:
        if len(os.listdir(dir)) == 0:
            relativePath = dir.replace(rootDir, "")
            relativePath = relativePath.replace(os.sep, "/")
            e = PathElement()
            e.path = ""
            e.file = relativePath
            e.value = ""
            _add_message(e, dirRule, args)
    return pathElements

def _validate_rules(pathElements, profile, args):
    """Validates image rules."""
    for var in profile.variables:
        logging.debug("Variable: " + var.name)
        for rule in var.rules:
            logging.debug("Rule Type: " + rule.type)
            if rule.type == RULE_REGEX:
                _validate_rule_regex(var, rule, pathElements, profile, args)
            elif rule.type == RULE_NUMBERING:
                _validate_rule_numbering(var, rule, pathElements, profile, args)

def _validate_rule_regex(variable, rule, pathElements, profile, args):
    #logging.getLogger().setLevel(logging.DEBUG)
    it = filter(lambda e: e.variable == variable, pathElements)
    for e in it:
        #e.print_element()
        logging.debug("Value: " + e.value)
        logging.debug("Rule: " + rule.value)
        result = re.search(rule.value, e.value)
#        if rule.value == "Copy":
#            print(e.value)
#            print(rule.value)

        error = not result if rule.invertMatch else result
        if error:
            _add_message(e, rule, args)
#        else:
#            print("{0:<50.50} {1:<6} {2:>20.20} {3}".format(e.file, "OK", e.value, e.path))
    logging.getLogger().setLevel(logging.INFO)
        
def _validate_rule_numbering(variable, rule, pathElements, profile, args):
    #logging.getLogger().setLevel(logging.DEBUG)
    it = filter(lambda e: e.variable == variable, pathElements)
    #it = sorted(it, key=lambda e: e.parentPath)
    it = sorted(it, key=lambda e: e.file)
    #it = sorted(it, key=lambda e: e.path)
    parentPath = None
    realPath = None
    index = 1
    for e in it:
        logging.debug(e.variable.name)
        logging.debug(e.file)
        # ignore equal real path (same files/folders)
        if realPath == e.realPath:
            continue
        realPath = e.realPath
        # reset for other parents
        if parentPath != e.parentPath:
            parentPath = e.parentPath
            index = 1
        # compare numbers
        logging.debug("Compare: " + e.value + " == " + str(index))
        if int(e.value) != index:
            _add_message(e, rule, args)
            # update to current number
            index = int(e.value)
        index += 1
    logging.getLogger().setLevel(logging.INFO)

def _add_message(pathElement, rule, args):
    """Adds a message to print."""
    if not args.verbose and rule.severity == RULE_INFO:
        return
    
    t = Message(pathElement, rule)
    messages.append(t)

def _print_messages(args):
    """Prints messages to standard out."""
    it = sorted(messages, key=lambda m: m.pathElement.file)
    for msg in it:
        pathElement = msg.pathElement
        rule = msg.rule
        if args.list:
            print("{1:<6} {2}".format(pathElement.file, rule.severity.upper(), pathElement.value, rule.message, pathElement.path))
            print("       {3}".format(pathElement.file, rule.severity.upper(), pathElement.value, rule.message, pathElement.path))
            print("       {0}".format(pathElement.file, rule.severity.upper(), pathElement.value, rule.message, pathElement.path))
            print()
        else:
            print("{0:<50.50} {1:<6} {2:<30.30}  {3:<30.30} {4}".format(pathElement.file, rule.severity.upper(), pathElement.value, rule.message, pathElement.path))

def parse_xml_file(file):
    """Parses the xml file."""
    tree = ElementTree.parse(file)
    root = tree.getroot()
    
    rulesMap = dict()
    for rulesNode in root.findall("rules"):
        name = xmlutil.parse_xml_attrib(rulesNode, "name", required=True)
        rules = _parse_rules(rulesNode)
        rulesMap[name] = rules
        
    profiles = list()
    for profileNode in root.findall("profile"):
        profile = ImageProfile()
        profile.name = xmlutil.parse_xml_attrib(profileNode, "name", required=True)
        profile.description = xmlutil.parse_xml_attrib(profileNode, "description")
        profile.paths = xmlutil.parse_xml_tag_list(profileNode, "path")
        for varNode in profileNode.findall("variable"):
            variable = ImageVariable()
            variable.name = xmlutil.parse_xml_attrib(varNode, "name", required=True)
            pattern = xmlutil.parse_xml_attrib(varNode, "pattern", required=False)
            if pattern is not None:
                variable.pattern = pattern
            # rules
            rules = _parse_rules(varNode)
            variable.rules.extend(rules)
            # global rules
            for rulesNode in varNode.findall("rules"):
                name = xmlutil.parse_xml_attrib(rulesNode, "ref", required=True)
                if name not in rulesMap:
                    raise Exception("Illegal rules reference: " + name)
                variable.rules.extend(rulesMap[name])
                    
            profile.variables.append(variable)
        profiles.append(profile)
    return profiles

def _parse_rules(node):
    rules = list()
    for ruleNode in node.findall("rule"):
        rule = ImageVariableRule()
        rule.type = xmlutil.parse_xml_attrib(ruleNode, "type", required=True)
        if rule.type not in (RULE_REGEX, RULE_NUMBERING):
            raise Exception("Illegal rule type: " + rule.type)
        rule.value = xmlutil.parse_xml_attrib(ruleNode, "value")
        invert = xmlutil.parse_xml_attrib(ruleNode, "invert", default="false")
        rule.invertMatch = invert in ("True", "true")
        rule.message = xmlutil.parse_xml_attrib(ruleNode, "message", default="Rule failed")
        rule.severity = xmlutil.parse_xml_attrib(ruleNode, "severity", default=RULE_ERROR)
        if rule.severity not in (RULE_ERROR, RULE_WARN):
            raise Exception("Illegal rule severity: " + rule.severity)
        rules.append(rule)
    return rules

def print_available_profiles(profiles):
    print('Available image profiles: ')
    for p in profiles:
        print(f' {p.name:<15}: {p.description}')

def _findProfileDefinitionFile(fileName):
    """Searches for a file using following order:
    1. in $home directory: ~/.tools/<fileName>
    2. in script folder: <scriptDir>/<fileName>
    """
    fileCandidates = []
    fileCandidates.append(os.path.join(os.path.expanduser("~user"), ".tools", fileName))
    fileCandidates.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), fileName))

    for f in fileCandidates:
        if os.path.exists(f): 
            return f
    return None

def main(argv=None):
    try:
        parser = argparse.ArgumentParser(description='Inspect Image: Checks images for naming or structural problems.', formatter_class=argparse.RawTextHelpFormatter)
        parser.add_argument('--debug', help='activate DEBUG logging', action='store_true')
        parser.add_argument("-v", "--verbose", action="store_true", help="print verbose output")
        parser.add_argument("-l", "--list", action="store_true", help="use list output")
        parser.add_argument("-p", "--profilehelp", action="store_true", dest="profilehelp", help="show all details of the specified profile")
        parser.add_argument("profile", nargs="?", help="name of the image profile")
        parser.add_argument("dir", nargs="?", help="root directory", default=".")
        args = parser.parse_args(argv)
        
        # init logging
        level = logging.DEBUG if args.debug else logging.WARNING
        logging.basicConfig(format='%(levelname)s: %(message)s', level=level, force=True)

        # read profile        
        file = _findProfileDefinitionFile(fileName="ii.xml")
        if os.path.exists(file):
            profiles = parse_xml_file(file)
        else:
            exit("Definition file not found: " + file)
        
        if args.profile is None:
            # No profile given
            print_available_profiles(profiles)
            exit(0)

        # find given profile
        profile = None    
        for p in profiles:
            if p.name == args.profile:
                profile = p
                break
        if profile is None:
            print("Profile does not exist: "  + args.profile)
            print()
            print_available_profiles(profiles)
            exit(1)
        if args.profilehelp:
            print("Definition file: " + file)
            print()
            profile.print_profile()
            exit(0)
        
        inspect_image(args.dir, profile, args)
        _print_messages(args)
        
    except Exception as e:
        print(e)
        logging.debug(type(e))
        if args.debug:
            traceback.print_exc()
        exit(1)

if __name__ == '__main__':
    main()
