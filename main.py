#!/usr/bin/python
from twisted.internet.protocol import Protocol, Factory
from twisted.protocols.basic import LineReceiver
from twisted.internet import reactor
import json
import inspect
import ConfigParser

import lanbox

c = ConfigParser.ConfigParser()
c.read('/opt/LanBox-JSONRPC/config.ini')
PORT = c.getint('JSONRPC','port')

class Methods():
    def __init__(self):
        self.methods = {}
        self.add(self.help)
        self.add(self.vars)
        self.add(self.list)
    def help(self,fname=''):
        '''Help function. Returns the comments on functions.'''
        if fname=='':
            ret = 'Help functions are help <cmd>, list, vars <cmd>'
            return ret
        if fname in self.methods:
            return inspect.getdoc(self.methods[fname]['function'])
        else:
            raise ValueError('%s not known.'%fname)
    def vars(self,fname=''):
        '''Returns the names and positions of arguments of functions.'''
        if fname=='':
            fname = 'vars'
        if fname in self.methods:
            i = inspect.getargspec(self.methods[fname]['function'])
            keys = self.methods[fname].keys()
            keys.remove('function')
            ret = {k:self.methods[fname][k] for k in keys}
            ret['name']=fname
            return ret
        else:
            raise ValueError('%s not known.'%fname)
    def list(self):
        '''Returns a list of all function names listed.'''
        return self.methods.keys()
    def add(self,function,name=None):
        '''Adds new methods to the listing.'''
        if name is None or name is '':
            name=function.__name__
        i = inspect.getargspec(function)
        args = list(i.args)
        args.remove('self')
        varargs=i.varargs
        kwargs=i.keywords
        if i.defaults is None:
            defaults={}
        else:
            l = len(i.args) - len(i.defaults)
            defaults = {i.args[l+q]:i.defaults[q] for q in range(len(i.defaults))}
        self.methods[name]={'args':args,'varargs':varargs,'kwargs':kwargs,'defaults':defaults,'function':function}

class JSONRPC(LineReceiver):
    delimiter='\n'
    def __init__(self,methods):
        self.methods=methods

    def lineReceived(self, data):
        data = data.lstrip('\r')
        result = self.read_rpc(data)
        if len(result) > self.MAX_LENGTH: #buffer overflow imminent!
            print ('buffer exceeding sensed. Directing to transport.')
            self.transport.write(result+'\n')
        else:
            self.sendLine(result)

    def lineLengthExceeded(self, line):
        print ('buffer exceeded')

    def read_rpc(self, jsonstr):
        '''Parses JSONRPC strings and performs the appropriate actions.'''
        try:
            j = json.loads(jsonstr)
        except:
            return json.dumps(self.json_error(-32700))

        if isinstance(j,dict): #We have a single RPC call
            response = self.parse_call(j)
            if response is not None:
                return json.dumps(response)

        ret = []
        for call in j:
            response = self.parse_call(call)
            if response is not None:
                ret.append(response)
        if len(ret)>0:
            return json.dumps(ret)

    def parse_call(self,call):
        try:
            id = call['id']
        except:
            return self.json_error(-32600)

        if not isinstance(call['method'],basestring):
            return self.json_error(-32600,id)
        meth = call['method']
        if 'params' in call:
            params = call['params']
        else:
            params = []
        return (self.get_request(meth,params,id))

    def json_error(self,num,id=None,msg=''):
        ret = {}
        err = {}
        errors = {-32700:'Parse error',-32600:'Invalid Request',-32601:'Method not found',-32602:'Invalid params',-32603:'Internal error'}
        ret['jsonrpc']='2.0'
        ret['id']=id
        err['code']=num
        if num in errors:
            err['message']=errors[num]
        else:
            err['message']=str(msg)
        ret['error']=err
        return ret

    def get_request(self,meth,params,id):
        ret = {}
        ret['jsonrpc']='2.0'
        ret['id']=id
        if meth not in self.methods.methods:
            return(self.json_error(-32601,id))
        methdata = self.methods.methods[meth]
        if isinstance(params,list): #by position reference
            if len(params)<len(methdata['args'])-len(methdata['defaults']):
                return(self.json_error(-32602,id))
            if len(params)>len(methdata['args']) and methdata['varargs'] is None:
                return(self.json_error(-32602,id))
            try:
                ret['result']=methdata['function'](*params)
                return ret
            except Exception as e:
                return(self.json_error(-32605,id,msg=e))
        if isinstance(params,dict): #by name reference
            for p in methdata['args'][:len(methdata['args'])-len(methdata['defaults'])]:
                if p not in params:
                    return(self.json_error(-32602,id))
            if len(params)>len(methdata['args']) and methdata['kwargs'] is None:
                return(self.json_error(-32602,id))
            try:
                ret['result']=methdata['function'](**params)
                return ret
            except Exception as e:
                return(self.json_error(-32605,id,msg=e))
        return(self.json_error(-32602,id))

class ExampleFunctions():
    '''Just some example functions.'''
    def add(self,a=0,*b):
        for x in b:
            a = a + x
        return a
    def subtract(self,a=0,*b):
        for x in b:
            a = a - x
        return a


class JSONRPCFactory(Factory):
    def __init__(self,methods):
        self.methods=methods

    def buildProtocol(self,addr):
        return JSONRPC(self.methods)

def populateMethods(methods):
    i = inspect.getmembers(lanbox.LanboxMethods(),inspect.ismethod)
    for function in i:
        if not function[0].startswith('_'):
            methods.add(function[1])

def main():
    methods = Methods()
    populateMethods(methods)
    f = JSONRPCFactory(methods)
    reactor.listenTCP(PORT, f)
    reactor.run()

if __name__ == '__main__':
    main()
