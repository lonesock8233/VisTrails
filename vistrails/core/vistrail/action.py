############################################################################
##
## Copyright (C) 2006-2007 University of Utah. All rights reserved.
##
## This file is part of VisTrails.
##
## This file may be used under the terms of the GNU General Public
## License version 2.0 as published by the Free Software Foundation
## and appearing in the file LICENSE.GPL included in the packaging of
## this file.  Please review the following to ensure GNU General Public
## Licensing requirements will be met:
## http://www.opensource.org/licenses/gpl-license.php
##
## If you are unsure which license is appropriate for your use (for
## instance, you are interested in developing a commercial derivative
## of VisTrails), please contact us at vistrails@sci.utah.edu.
##
## This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
## WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.
##
############################################################################
""" This module defines the Class Action and its subclasses:
   - Action
   - AddModuleAction
   - DeleteModuleAction
   - ChangeParameterAction
   - AddConnectionAction
   - DeleteConnectionAction
   - MoveModuleAction
   - DeleteFunctionAction
   - ChangeAnnotationAction
   - DeleteAnnotationAction
   - AddModulePortAction
   - DeleteModulePortAction

"""
from core.utils import abstract, VistrailsInternalError
from core.utils.uxml import named_elements
from core.vistrail.module import Module
from core.vistrail.connection import Connection
from core.vistrail.port import Port, PortEndPoint
from core.vistrail.module_param import ModuleParam, VistrailModuleType
from core.vistrail.module_function import ModuleFunction
from core.data_structures import Point
from core.modules.module_registry import registry, ModuleRegistry
from core.utils import report_stack
import copy

################################################################################

class Action(object):
    """ Base class for a Action.

    A Vistrail action needs to know three things, behavior-wise: 

   - how to perform (that is, how to change a certain pipeline) 

   - how to serialize (that is, given an XML parent element,
     how to add itself to it)

   - how to parse (that is, given an XML parent element, how to
     extract the action information
     
     """
    createFromXMLDispatch = {}
    
    def __init__(self, timestep=0, parent=0, date=None, user=None, notes=None):
        """ __init__(timestep=0, parent=0, date=None, user=None, 
                     notes=None) -> Action
        Action constructor. 
        Keyword Arguments:
         - timestep: int
         - parent: int
         - date: str
         - user: str
         - notes: str

        """
        self.timestep = timestep
        self.parent = parent
	self.date = date
	self.user = user
        self.notes = notes

    def perform(self, pipeline):
        """ perform(pipeline) -> None 
        Abstract method called for each subclassed action when an action is 
        performed on a given pipeline. 
        
        """
        abstract()

    def serialize(self,dom,element):
        """ serialize(dom,element) -> None  
        Abstract method called to convert the object to an XML representation. 
        
        """
        abstract()

    def __str__(self):
        """__str__() -> str 
        Returns a string representation of an action object.

        """
        msg = "<<timestep='%s' parent='%s' date='%s' user='%s' notes='%s'>>"
        return  msg % (self.timestep,
                       self.parent,
                       self.date,
                       self.user,
                       self.notes)

    @staticmethod
    def createFromXML(action, version=None):
        """ createFromXML(action,version=None) -> Action 
        Static method that given an action XML element, creates a specific 
        Action object according to action.what attribute.

        """
        att = action.getAttribute('what')
        return Action.createFromXMLDispatch[att](action,version)
       
    @staticmethod
    def getParameter(element):
        """getParameter(element) -> ModuleParam 
        Static method that constructs a ModuleParam object given an xml element.

        """
        p = ModuleParam()
        p.name = element.getAttribute('name')
        p.type = str(named_elements(element, 
                                    'type').next().firstChild.nodeValue)
        p.strValue = str(named_elements(element, 
                                        'val').next().firstChild.nodeValue)
        return p
    
    @staticmethod
    def getFunction(element):
        """getFunction(element) -> ModuleFunction 
        Static method that constructs a ModuleFunction object given 
        an xml element. 

        """
        f = ModuleFunction()
        (f.name, f.returnType) = [str(element.getAttribute(x))
                            for x in ['name', 'returnType']]
        f.params = [Action.getParameter(param) for
                    param in named_elements(element, 'param')]
        return f

    @staticmethod
    def getModule(element):
        """getModule(element) -> Module 
        Static method that constructs a Module object given an xml element.

        """
        m = Module()
        (m.name, cache, id, x, y) = [str(element.getAttribute(x))
                                     for x in ['name', 'cache', 'id',
                                               'x', 'y']]
        m.cache = int(cache)
        m.id = int(id)
        m.center.x = float(x)
        m.center.y = float(y)
        m.functions = [Action.getFunction(f) for
                       f in named_elements(element, 'function')]
        m.annotations = {}
        for a in named_elements(element, 'annotation'):
            akey = str(a.getAttribute('key'))
            avalue = str(a.getAttribute('value'))
            m.annotation[akey] = avalue
        return m

    @staticmethod
    def getConnection(connection):
        """ getConnection(connection) -> Connection
        Static method that creates a Connection object given a connection xml
        element. Vistrails version should be >= 0.3.0

        """
        c = Connection()
        sourceModule = connection.getAttribute('sourceModule')
        destinationModule = connection.getAttribute('destinationModule')
        sourcePort = connection.getAttribute('sourcePort')
        destinationPort = connection.getAttribute('destinationPort')
        # Leaving this to performing actions to get modules registry
        c.source = registry.portFromRepresentation(sourceModule,
                                                   sourcePort,
                                                   PortEndPoint.Source,
                                                   None, True)
        c.destination = registry.portFromRepresentation(destinationModule,
                                                        destinationPort,
                                                        PortEndPoint.Destination,
                                                        None, True)
        c.sourceInfo = (sourceModule, sourcePort)
        c.destinationInfo = (destinationModule, destinationPort)
        c.id = int(connection.getAttribute('id'))
        c.type = VistrailModuleType.Module
        c.sourceId = int(connection.getAttribute('sourceId'))
        c.destinationId = int(connection.getAttribute('destinationId'))
        return c
    
    @staticmethod
    def getConnection0_1_0(connection):
        """ getConnection0_1_0(connection) -> Connection
        Static method that creates a Connection object given a connection xml
        element of version 0.1.0

        """
        cId = int(connection.getAttribute('id'))
        for f in named_elements(connection, 'filterInput'):
	    c = Connection()
	    c.source = Port()
	    c.destination = Port()
	   	
	    c.source.endPoint = PortEndPoint.Source
	    c.destination.endPoint = PortEndPoint.Destination
	    
            (c.sourceId,
             c.destinationId,
             sourcePort,
             destinationPort) = [int(f.getAttribute(x))
                             for x in ['sourceId', 'destId',
                                       'sourcePort', 'destPort']]
	    c.source.moduleId = c.sourceId
	    c.source.name = "GetOutputPort" + str(sourcePort)

	    c.destination.moduleId = c.destinationId
	    c.destination.name = "SetInputConnection" + str(destinationPort)
	    
	    c.id = cId
            return c

        for o in named_elements(connection, 'objectInput'):
            c = Connection()
	    c.source = Port()
	    c.destination = Port()
	   	
	    c.source.endPoint = PortEndPoint.Source
	    c.destination.endPoint = PortEndPoint.Destination

            (moduleId,
             destId,
             name) = [str(o.getAttribute(x))
                                   for x in ['sourceId', 'destId',
                                             'name']]
	    
	    
	    c.source.moduleId = int(moduleId)
	    c.source.name = 'self'
	    c.destination.moduleId = int(destId)

	    c.destination.name = str(name) 
            c.id = cId
	    c.sourceId = int(moduleId)
            c.destinationId = int(destId)
            return c
        
	raise VistrailsInternalError("element is neither filter nor object")    

class AddModuleAction(Action):
    def __init__(self, timestep=0,parent=0,date=None,user=None,notes=None):
        Action.__init__(self,timestep,parent,date,user,notes)
        self.module = None
        self.type = 'AddModule'
        
    def serialize(self, dom, element):
        """ serialize(dom,element) -> None  
        Convert this object to an XML representation. 
        
        """
        element.setAttribute('what', 'addModule')
        self.module.serialize(dom, element)

    @staticmethod
    def parse(element, version=None):
        """ parse(element, version=None) -> AddModuleAction
        Static method that parses an xml element and creates an AddModuleAction.
        Keyword arguments:
          - element : xml.dom.minidom.Element
          - version : str

        """
        notes = None
        #backwards compatibility
        notes = str(element.getAttribute('notes'))
	
        for n in element.childNodes:
            if n.localName == "notes":
                notes = str(n.firstChild.nodeValue)
                break
            
        newAction = AddModuleAction(int(element.getAttribute('time')),
                                    int(element.getAttribute('parent')),
                                    str(element.getAttribute('date')),
                                    str(element.getAttribute('user')),
                                    notes)
        for o in named_elements(element, 'object'):
            newAction.module = Action.getModule(o)
            return newAction
        raise VistrailsInternalError("No objects in addModule action")
    
    def perform(self, pipeline):
        """ perform(pipeline:Pipeline) -> None 
        Apply this action to pipeline.
        
        """
        pipeline.addModule(copy.copy(self.module))

Action.createFromXMLDispatch['addModule'] = AddModuleAction.parse

class AddConnectionAction(Action):
    def __init__(self,timestep=0,parent=0,date=None,user=None,notes=None):
        Action.__init__(self, timestep, parent, date, user,notes)
        self.connection = None
        self.type = 'AddConnection'
        
    def serialize(self, dom, element):
        """ serialize(dom,element) -> None  
        Convert this object to an XML representation. 
        
        """
        element.setAttribute('what', 'addConnection')
        self.connection.serialize(dom, element)

    @staticmethod
    def parse(element, version=None):
        """ parse(element, version=None) -> AddConnectionAction
        Static method that parses an xml element according to its version and 
        creates an AddConnectionAction.
        Keyword arguments:
          - element : xml.dom.minidom.Element
          - version : str
          
        """
        notes = None
    	#backwards compatibility
        notes = str(element.getAttribute('notes'))
        
        for n in element.childNodes:
            if n.localName == "notes":
                notes = str(n.firstChild.nodeValue)
                break

        newAction = AddConnectionAction(int(element.getAttribute('time')),
                                        int(element.getAttribute('parent')),
                                        str(element.getAttribute('date')),
                                        str(element.getAttribute('user')),
                                        notes)
        for c in named_elements(element, 'connect'):
            if version == '0.1.0':
                newAction.connection = Action.getConnection0_1_0(c)
            else:
                newAction.connection = Action.getConnection(c)
            return newAction
        raise VistrailsInternalError("No connections in addConnection action")
     
    def perform(self, pipeline):
        """ perform(pipeline:Pipeline) -> None 
        Apply this action to pipeline.
        
        """
        if hasattr(self.connection, 'sourceInfo'):
            (si, di, cid) = (self.connection.sourceId,
                             self.connection.destinationId,
                             self.connection.id)
            (sourceModuleName, sourcePort) = self.connection.sourceInfo
            (destModuleName, destPort) = self.connection.destinationInfo
            sourceModule = pipeline.getModuleById(si)
            destModule = pipeline.getModuleById(di)
            portFromRep = registry.portFromRepresentation
            self.connection.source = portFromRep(sourceModuleName,
                                                 sourcePort,
                                                 PortEndPoint.Source,
                                                 sourceModule.registry,
                                                 False)
            self.connection.destination = portFromRep(destModuleName,
                                                      destPort,
                                                      PortEndPoint.Destination,
                                                      destModule.registry,
                                                      False)
            (self.connection.sourceId,
             self.connection.destinationId,
             self.connection.id) = (si, di, cid)
        pipeline.addConnection(copy.copy(self.connection))

Action.createFromXMLDispatch['addConnection'] = AddConnectionAction.parse

class ChangeParameterAction(Action):
    attributes = ['moduleId', 'functionId', 'function', 'parameterId',
                  'parameter', 'value', 'type', 'alias']
    conversions = [int, int, str, int, str, str, str, str]
    
    #for version "0.1.0"
    attributes0_1_0 = ['moduleId', 'functionId', 'function', 
                       'parameterId','parameter', 'value', 'type']
    conversions0_1_0 = [int, int, str, int, str, str, str]

    def __init__(self, timestep=0,parent=0,date=None,user=None,notes=None):
        Action.__init__(self, timestep,parent,date,user,notes)
        self.parameters = []
        self.type = 'ChangeParameter'

    def addParameter(self, moduleId, functionId, paramId,
                     function, param, value, type_, alias):
        """ addParameter(moduleId, functionId, paramID, function, 
                         param, value, type, alias) -> None
        Add a new parameter to the action.
        Keyword arguments: 
          - moduleId : 'int'
          - functionId : 'int'
          - paramId: 'int'
          - function: 'str'
          - param : 'str'
          - value : 'str'
          - type : 'str'
          - alias : 'str'
        
        """
        assert type(moduleId) == int
        assert type(functionId) == int
        assert type(paramId) == int
        assert type(function) == str
        assert type(param) == str
        assert type(value) == str
        assert type(type_) == str
        assert type(alias) == str
        p = [moduleId, functionId,function, paramId, param, value, type_, alias]
        self.parameters.append(p)
    
    def serialize(self, dom, element):
        """ serialize(dom,element) -> None  
        Convert this object to an XML representation. 
        
        """
        element.setAttribute('what', 'changeParameter')
        for parameter in self.parameters:
            child = dom.createElement('set')
            for a, v in zip(ChangeParameterAction.attributes, parameter):
                child.setAttribute(a,str(v))
            element.appendChild(child)

    @staticmethod
    def parse(element, version=None):
        """ parse(element, version=None) -> ChangeParameterAction
        Static method that parses an xml element and creates a 
        ChangeParameterAction.
        Keyword arguments:
          - element : xml.dom.minidom.Element
          - version : str

        """
	notes = None
	#backwards compatibility
	notes = str(element.getAttribute('notes'))

	for n in element.childNodes:
	    if n.localName == "notes":
		notes = str(n.firstChild.nodeValue)
		break

	newAction = ChangeParameterAction(int(element.getAttribute('time')),
                                          int(element.getAttribute('parent')),
					  str(element.getAttribute('date')),
					  str(element.getAttribute('user')),
                                          notes)
	if version == '0.1.0':
	    p = [[conv(set.getAttribute(key))
                  for conv,key in zip(ChangeParameterAction.conversions0_1_0,
                                      ChangeParameterAction.attributes0_1_0)]
                 for set in named_elements(element, 'set')]
	    
	    for par in p:
		if par[6] in ['double','float']:
		    par[6] = 'Float'
		elif par[6] == 'int':
		    par[6] = 'Integer'
		elif par[6] in ['const char *', 'const char*', 'string']:
		    par[6] = 'String'
		par.append("") #alias
	else:
	    p = [[conv(set.getAttribute(key))
		  for conv,key in zip(ChangeParameterAction.conversions,
				      ChangeParameterAction.attributes)]
		 for set in named_elements(element, 'set')]
        
	newAction.parameters = p
        return newAction
      
    def perform(self, pipeline):
        """ perform(pipeline:Pipeline) -> None 
        Apply this action to pipeline.
        
        """
        for p in self.parameters:
            m = pipeline.getModuleById(p[0])
            if p[1] >= len(m.functions):
                f = ModuleFunction()
                f.name = p[2]
                m.functions.append(f)
                if len(m.functions)-1 != p[1]:
                    msg = "Pipeline function id is inconsistent"
                    raise VistrailsInternalError(msg)
            f = m.functions[p[1]]
            if f.name != p[2]:
                msg = "Pipeline function name is inconsistent"
                raise VistrailsInternalError()
            if p[3] == -1:
                continue
            if p[3] >= len(f.params):
                param = ModuleParam()
                param.name = p[4]
                f.params.append(param)
                if len(f.params)-1 != p[3]:
                    msg = "Pipeline parameter id is inconsistent"
                    raise VistrailsInternalError()
            param = f.params[p[3]]
            param.name = p[4]
#            if param.name != p[4]:
#                msg = "Pipeline parameter name is inconsistent"
#                raise VistrailsInternalError(msg)
            param.strValue = p[5]
            param.type = p[6]
            if param.type.find('char')>-1 or param.type=='str':
                param.type = 'string'
            param.alias = p[7]
            if not pipeline.hasAlias(param.alias):
                pipeline.changeAlias(param.alias, 
                                     param.type, 
                                     p[0], #module id  
                                     p[1], #function id
                                     p[3]) #parameter id
                    
Action.createFromXMLDispatch['changeParameter'] = ChangeParameterAction.parse

class DeleteModuleAction(Action):
    def __init__(self, timestep=0,parent=0,date=None,user=None,notes=None):
        Action.__init__(self, timestep,parent,date,user,notes)
        self.ids = []
        self.type = 'DeleteModule'

    def addId(self, id):
        """ addId(id:int) -> None  
        Adds a module id to the list of modules to be deleted.
       
        """
        self.ids.append(id)
       
    def serialize(self, dom, element):
        """ serialize(dom,element) -> None  
        Convert this object to an XML representation. 
        
        """
        element.setAttribute('what','deleteModule')
        for id in self.ids:
            child = dom.createElement('module')
            child.setAttribute('moduleId', str(id))
            element.appendChild(child)

    @staticmethod
    def parse(element, version=None):
        """ parse(element, version=None) -> DeleteModuleAction
        Static method that parses an xml element and creates a 
        DeleteModuleAction.
        Keyword arguments:
          - element : xml.dom.minidom.Element
          - version : str

        """
	notes = None
	#backwards compatibility
	notes = str(element.getAttribute('notes'))
	for n in element.childNodes:
	    if n.localName == "notes":
		notes = str(n.firstChild.nodeValue)
		break

        newAction = DeleteModuleAction(int(element.getAttribute('time')),
                                       int(element.getAttribute('parent')),
				       str(element.getAttribute('date')),
				       str(element.getAttribute('user')),
                                       notes)
        newAction.ids = [int(m.getAttribute('moduleId'))
                    for m in named_elements(element, 'module')]
        return newAction
      
    def perform(self, pipeline):
        """ perform(pipeline:Pipeline) -> None 
        Apply this action to pipeline.
        
        """
        for id in self.ids:
            pipeline.deleteModule(id)

Action.createFromXMLDispatch['deleteModule'] = DeleteModuleAction.parse

class DeleteConnectionAction(Action):
    def __init__(self, timestep=0,parent=0,date=None,user=None,notes=None):
        Action.__init__(self, timestep,parent,date,user,notes)
        self.ids = []
        self.type = 'DeleteConnection'
        
    def addId(self, id):
        """ addId(id:int) -> None  
        Adds a connection id to the list of connections to be deleted
       
        """
        self.ids.append(id)

    def serialize(self, dom, element):
        """ serialize(dom,element) -> None  
        Convert this object to an XML representation. 
        
        """
        element.setAttribute('what','deleteConnection')
        for id in self.ids:
            child = dom.createElement('connection')
            child.setAttribute('connectionId', str(id))
            element.appendChild(child)

    @staticmethod
    def parse(element, version=None):
        """ parse(element, version=None) -> DeleteConnectionAction
        Static method that parses an xml element and creates a 
        DeleteConnectionAction.
        Keyword arguments:
          - element : xml.dom.minidom.Element
          - version : str

        """
	notes = None
	#backwards compatibility
	notes = str(element.getAttribute('notes'))
	for n in element.childNodes:
	    if n.localName == "notes":
		notes = str(n.firstChild.nodeValue)
		break
	
        newAction = DeleteConnectionAction(int(element.getAttribute('time')),
                                           int(element.getAttribute('parent')),
					   str(element.getAttribute('date')),
					   str(element.getAttribute('user')),
                                           notes)
        newAction.ids = [int(m.getAttribute('connectionId'))
                         for m in named_elements(element, 'connection')]
        return newAction
       
    def perform(self, pipeline):
        """ perform(pipeline:Pipeline) -> None 
        Apply this action to pipeline.
        
        """
        for id in self.ids:
            pipeline.deleteConnection(id)

Action.createFromXMLDispatch['deleteConnection'] = DeleteConnectionAction.parse

class MoveModuleAction(Action):
    def __init__(self, timestep=0,parent=0,date=None,user=None,notes=None):
        Action.__init__(self, timestep,parent,date,user,notes)
        self.moves = []
        self.type = 'MoveModule'

    @staticmethod
    def parse(element, version=None):
        """ parse(element, version=None) -> MoveModuleAction
        Static method that parses an xml element and creates a MoveModuleAction.
        Keyword arguments:
          - element : xml.dom.minidom.Element
          - version : str

        """
	notes = None
	#backwards compatibility
	notes = str(element.getAttribute('notes'))

	for n in element.childNodes:
	    if n.localName == "notes":
		notes = str(n.firstChild.nodeValue)
		break

        newAction = MoveModuleAction(int(element.getAttribute('time')),
                                     int(element.getAttribute('parent')),
				     str(element.getAttribute('date')),
				     str(element.getAttribute('user')),
                                     notes)
        newAction.moves = [(int(m.getAttribute('id')),
                            float(m.getAttribute('dx')),
                            float(m.getAttribute('dy')))
                           for m in named_elements(element, 'move')]
        return newAction
  
    def addMove(self, id, dx, dy):
        """addMove(id:int, dx:float, dy:float) -> None 
        Adds an item to the moves
         
        """
        self.moves.append((id, dx, dy))
        
    def perform(self, pipeline):
        """ perform(pipeline:Pipeline) -> None 
        Apply this action to pipeline.
        
        """
        for move in self.moves:
            m = pipeline.getModuleById(move[0])
            m.center.x = m.center.x + move[1]
            m.center.y = m.center.y + move[2]

    def serialize(self, dom, element):
        """ serialize(dom,element) -> None  
        Convert this object to an XML representation. 
        
        """
        element.setAttribute('what', 'moveModule')
        for move in self.moves:
            child = dom.createElement('move')
            child.setAttribute('id', str(move[0]))
            child.setAttribute('dx', str(move[1]))
            child.setAttribute('dy', str(move[2]))
            element.appendChild(child)

Action.createFromXMLDispatch['moveModule'] = MoveModuleAction.parse

class DeleteFunctionAction(Action):
    def __init__(self, timestep=0,parent=0,date=None,user=None,notes=None):
        Action.__init__(self,timestep,parent,date,user,notes)
        self.functionId = -1
        self.moduleId = -1
        self.type = 'DeleteFunction'
        
    def perform(self, pipeline):
        """ perform(pipeline:Pipeline) -> None 
        Apply this action to pipeline.
        
        """
        pipeline.getModuleById(self.moduleId).deleteFunction(self.functionId)
        pipeline.removeAliases(mId=self.moduleId,fId=self.functionId)

    def serialize(self, dom, element):
        """ serialize(dom,element) -> None  
        Convert this object to an XML representation. 
        
        """
        element.setAttribute('what', 'deleteFunction')
        child = dom.createElement('function')
        child.setAttribute('functionId', str(self.functionId))
        child.setAttribute('moduleId',   str(self.moduleId))
        element.appendChild(child)

    @staticmethod
    def parse(element, version=None):
        """ parse(element, version=None) -> AddModuleAction
        Static method that parses an xml element and creates an AddModuleAction.
        Keyword arguments:
          - element : xml.dom.minidom.Element
          - version : str

        """
	notes = None
	#backwards compatibility
	notes = str(element.getAttribute('notes'))
	
	for n in element.childNodes:
	    if n.localName == "notes":
		notes = str(n.firstChild.nodeValue)
		break

	newAction = DeleteFunctionAction(int(element.getAttribute('time')),
                                         int(element.getAttribute('parent')),
					 str(element.getAttribute('date')),
					 str(element.getAttribute('user')),
                                         notes)
        for el in named_elements(element, 'function'):
            newAction.moduleId = int(el.getAttribute('moduleId'))
            newAction.functionId = int(el.getAttribute('functionId'))
            return newAction
 
Action.createFromXMLDispatch['deleteFunction'] = DeleteFunctionAction.parse

class ChangeAnnotationAction(Action):
    attributes = ['moduleId', 'key', 'value']
    conversions = [int, str, str]

    def __init__(self, timestep=0,parent=0,date=None,user=None,notes=None):
        Action.__init__(self, timestep,parent,date,user,notes)
        self.moduleId = -1
        self.type = 'ChangeAnnotation'

    def addAnnotation(self, moduleId, key, value):
        """addAnnotation(moduleId:int, key:str, value:str) -> None 
        Add a new annotation to the action

        """
        self.moduleId = moduleId
        self.key = key
        self.value = value

    def serialize(self, dom, element):
        """ serialize(dom,element) -> None  
        Convert this object to an XML representation. 
        
        """
        element.setAttribute('what', 'changeAnnotation')
        child = dom.createElement('set')
        for a, v in zip(ChangeAnnotationAction.attributes, 
                        [self.moduleId, self.key, self.value]):
            child.setAttribute(a,str(v))
        element.appendChild(child)

    @staticmethod
    def parse(element, version=None):
        """ parse(element, version=None) -> AddModuleAction
        Static method that parses an xml element and creates an AddModuleAction.
        Keyword arguments:
          - element : xml.dom.minidom.Element
          - version : str

        """
	notes = None
	#backwards compatibility
	notes = str(element.getAttribute('notes'))

	for n in element.childNodes:
	    if n.localName == "notes":
		notes = str(n.firstChild.nodeValue)
		break

	newAction = ChangeAnnotationAction(int(element.getAttribute('time')),
                                          int(element.getAttribute('parent')),
					  str(element.getAttribute('date')),
					  str(element.getAttribute('user')),
                                          notes)
        p = [[conv(set.getAttribute(key))
              for conv,key in zip(ChangeAnnotationAction.conversions,
                                  ChangeAnnotationAction.attributes)]
             for set in named_elements(element, 'set')]
        [[newAction.moduleId, newAction.key, newAction.value]] = p
        return newAction
      
    def perform(self, pipeline):
        m = pipeline.getModuleById(self.moduleId)
        m.annotations[self.key] = self.value

Action.createFromXMLDispatch['changeAnnotation'] = ChangeAnnotationAction.parse

class DeleteAnnotationAction(Action):
    def __init__(self, timestep=0,parent=0,date=None,user=None,notes=None):
        Action.__init__(self,timestep,parent,date,user,notes)
        self.key = None
        self.moduleId = -1
        self.type = 'DeleteAnnotation'
        
    def perform(self, pipeline):
        """ perform(pipeline:Pipeline) -> None 
        Apply this action to pipeline.
        
        """
        pipeline.getModuleById(self.moduleId).deleteAnnotation(self.key)

    def serialize(self, dom, element):
        """ serialize(dom,element) -> None  
        Convert this object to an XML representation. 
        
        """
        element.setAttribute('what', 'deleteAnnotation')
        child = dom.createElement('annotation')
        child.setAttribute('key', self.key)
        child.setAttribute('moduleId',   str(self.moduleId))
        element.appendChild(child)

    @staticmethod
    def parse(element, version = None):
	""" parse(element, version=None) -> AddModuleAction
        Static method that parses an xml element and creates an AddModuleAction.
        Keyword arguments:
          - element : xml.dom.minidom.Element
          - version : str

        """
        notes = None
	#backwards compatibility
	notes = str(element.getAttribute('notes'))
	
	for n in element.childNodes:
	    if n.localName == "notes":
		notes = str(n.firstChild.nodeValue)
		break

	newAction = DeleteAnnotationAction(int(element.getAttribute('time')),
                                         int(element.getAttribute('parent')),
					 str(element.getAttribute('date')),
					 str(element.getAttribute('user')),
                                         notes)
        for el in named_elements(element, 'annotation'):
            newAction.moduleId = int(el.getAttribute('moduleId'))
            newAction.key = str(el.getAttribute('key'))
            return newAction
 
Action.createFromXMLDispatch['deleteAnnotation'] = DeleteAnnotationAction.parse

class AddModulePortAction(Action):
    attributes = ['moduleId', 'portType', 'portName', 'portSpec']
    conversions = [int, str, str, str]

    def __init__(self, timestep=0,parent=0,date=None,user=None,notes=None):
        Action.__init__(self, timestep,parent,date,user,notes)
        self.moduleId = -1
        self.type = 'AddModulePort'

    def addModulePort(self, moduleId, portType, portName, portSpec):
        """addModulePort(moduleId:int, portType:str, 
                         portName:str, portSpec:str) -> None 
        Add a new port to the module
       
        """
        self.moduleId = moduleId
        self.portType = portType
        self.portName = portName
        self.portSpec = portSpec
  
    def serialize(self, dom, element):
        """ serialize(dom,element) -> None  
        Convert this object to an XML representation. 
        
        """
        element.setAttribute('what', 'addModulePort')
        child = dom.createElement('addPort')
        for a, v in zip(AddModulePortAction.attributes,
                        [self.moduleId, self.portType, self.portName, 
                         self.portSpec]):
            child.setAttribute(a,str(v))
        element.appendChild(child)

    @staticmethod
    def parse(element, version=None):
        """ parse(element, version=None) -> AddModuleAction
        Static method that parses an xml element and creates an AddModuleAction.
        Keyword arguments:
          - element : xml.dom.minidom.Element
          - version : str

        """
        notes = None
        #backwards compatibility
        notes = str(element.getAttribute('notes'))

        for n in element.childNodes:
            if n.localName == "notes":
                notes = str(n.firstChild.nodeValue)
                break

        newAction = AddModulePortAction(int(element.getAttribute('time')),
                                        int(element.getAttribute('parent')),
                                        str(element.getAttribute('date')),
                                        str(element.getAttribute('user')),
                                        notes)
        p = [[conv(set.getAttribute(key))
              for conv,key in zip(AddModulePortAction.conversions,
                                  AddModulePortAction.attributes)]
             for set in named_elements(element, 'addPort')]
        [[newAction.moduleId, newAction.portType, newAction.portName, 
          newAction.portSpec]] = p
        return newAction
      
    def perform(self, pipeline):
        """ perform(pipeline:Pipeline) -> None 
        Apply this action to pipeline.
        
        """
        m = pipeline.getModuleById(self.moduleId)
        moduleThing = registry.getDescriptorByName(m.name).module
        if m.registry==None:
            m.registry = ModuleRegistry()
            m.registry.addModule(moduleThing)
        
        portSpecs = self.portSpec[1:-1].split(',')
        if self.portType=='input':
            m.registry.addInputPort(moduleThing,
                                    self.portName,
                                    [registry.getDescriptorByName(spec).module
                                     for spec in portSpecs])
        else:
            m.registry.addOutputPort(moduleThing,
                                     self.portName,
                                     [registry.getDescriptorByName(spec).module
                                      for spec in portSpecs])

Action.createFromXMLDispatch['addModulePort'] = AddModulePortAction.parse

class DeleteModulePortAction(Action):
    def __init__(self,timestep=0,parent=0,date=None,user=None,notes=None):
        Action.__init__(self,timestep,parent,date,user,notes)
        self.moduleId = -1
        self.type = 'DeleteModulePort'
        
    def perform(self, pipeline):
        """ perform(pipeline:Pipeline) -> None 
        Apply this action to pipeline.
        
        """
        m = pipeline.getModuleById(self.moduleId)
        moduleThing = registry.getDescriptorByName(m.name).module
        if self.portType=='input':
            m.registry.deleteInputPort(moduleThing, self.portName)
        else:
            m.registry.deleteOutputPort(moduleThing, self.portName)

    def serialize(self, dom, element):
        """ serialize(dom,element) -> None  
        Convert this object to an XML representation. 
        
        """
        element.setAttribute('what', 'deleteModulePort')
        child = dom.createElement('deletePort')
        child.setAttribute('moduleId',   str(self.moduleId))
        child.setAttribute('portType', self.portType)
        child.setAttribute('portName', self.portName)
        element.appendChild(child)

    @staticmethod
    def parse(element, version=None):
        """ parse(element, version=None) -> AddModuleAction
        Static method that parses an xml element and creates an AddModuleAction.
        Keyword arguments:
          - element : xml.dom.minidom.Element
          - version : str

        """
        notes = None
        #backwards compatibility
        notes = str(element.getAttribute('notes'))
        
        for n in element.childNodes:
            if n.localName == "notes":
                notes = str(n.firstChild.nodeValue)
                break

        newAction = DeleteModulePortAction(int(element.getAttribute('time')),
                                           int(element.getAttribute('parent')),
                                           str(element.getAttribute('date')),
                                           str(element.getAttribute('user')),
                                           notes)
        for el in named_elements(element, 'deletePort'):
            newAction.moduleId = int(el.getAttribute('moduleId'))
            newAction.portType = str(el.getAttribute('portType'))
            newAction.portName = str(el.getAttribute('portName'))
            return newAction
 
Action.createFromXMLDispatch['deleteModulePort'] = DeleteModulePortAction.parse

################################################################################

import unittest

class TestAction(unittest.TestCase):
    
    def test1(self):
        """Exercises aliasing on modules"""
        import core.vistrail
        import core.xml_parser
        parser = core.xml_parser.XMLParser()
        parser.openVistrail(core.system.visTrailsRootDirectory() +
                            '/tests/resources/dummy.xml')
        v = parser.getVistrail()
        parser.closeVistrail()
        p1 = v.getPipeline('final')
        p2 = v.getPipeline('final')
        self.assertEquals(len(p1.modules), len(p2.modules))
        for k in p1.modules.keys():
            if p1.modules[k] is p2.modules[k]:
                self.fail("didn't expect aliases in two different pipelines")

    def test2(self):
        """Exercises aliasing on points"""
        import core.vistrail
        import core.xml_parser
        import core.system
        parser = core.xml_parser.XMLParser()
        parser.openVistrail(core.system.visTrailsRootDirectory() +
                            '/tests/resources/dummy.xml')
        v = parser.getVistrail()
        parser.closeVistrail()
        p1 = v.getPipeline('final')
        v.getPipeline('final')
        p2 = v.getPipeline('final')
        m1s = p1.modules.items()
        m2s = p2.modules.items()
        m1s.sort()
        m2s.sort()
        for ((i1,m1),(i2,m2)) in zip(m1s, m2s):
            self.assertEquals(m1.center.x, m2.center.x)
            self.assertEquals(m1.center.y, m2.center.y)

    def test3(self):
        """ Exercises aliases manipulation """
        import core.vistrail
        import core.xml_parser
        parser = core.xml_parser.XMLParser()
        parser.openVistrail(core.system.visTrailsRootDirectory() +
                            '/tests/resources/test_alias.xml')
        v = parser.getVistrail()
        parser.closeVistrail()
        p1 = v.getPipeline('alias')
        p2 = v.getPipeline('alias')
        #testing removing an alias
        action = ChangeParameterAction()
        action.addParameter(0, 0, 0 , "value", "&lt;no description&gt;",
                            "2.0", "Float", "")
        action.perform(p1)
        self.assertEquals(p1.hasAlias('v1'),False)
        v1 = p2.aliases['v1']
        action = ChangeParameterAction()
        action.addParameter(2, 0, 0 , "value", "&lt;no description&gt;",
                            "2.0", "Float", "v1")
        action.perform(p2)
        self.assertEquals(v1, p2.aliases['v1'])
            
if __name__ == '__main__':
    unittest.main()
