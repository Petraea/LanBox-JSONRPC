import socket
import ConfigParser
from twisted.internet.protocol import Protocol, ReconnectingClientFactory
from twisted.protocols.basic import LineReceiver
from twisted.internet import reactor, defer

commandDict = {'CommonGetAppID':'00050000','Common16BitMode':'65','CommonReboot':'B5','CommonSaveData':'A9','ChannelSetData':'C9','ChannelReadData':'CD','ChannelReadStatus':'CE','ChannelSetOutputEnable':'CA','ChannelSetActive':'CC','ChannelSetSolo':'CB','CommonGetLayers':'B1','LayerGetStatus':'0A','LayerSetID':'45','LayerSetOutput':'48','LayerSetFading':'46','LayerSetSolo':'4A','LayerSetAutoOutput':'64','LayerSetMixMode':'47','LayerSetTransparencyDepth':'63','LayerSetLocked':'43','LayerConfigure':'44','LayerGo':'56','LayerClear':'57','LayerPause':'58','LayerResume':'59','LayerNextStep':'5A','LayerPreviousStep':'5B','LayerNextCue':'73','LayerPreviousCue':'74','LayerSetChaseMode':'4B','LayerSetChaseSpeed':'4C','LayerSetFadeType':'4D','LayerSetFadeTime':'4E','LayerSetEditRunMode':'49','LayerUsesCueList':'0C','CueListCreate':'5F','LayerInsertStep':'5C','LayerReplaceStep':'67','LayerSetCueStepType':'4F','LayerSetCueStepParameters1':'50','LayerSetCueStepParameters2':'51','LayerSetCueStepParameters3':'52','LayerSetCueStepParameters4':'53','LayerSetCueStepParameters5':'54','LayerSetCueStepParameters6':'55','LayerSetDeviceID':'5E','LayerSetSustain':'40','LayerIgnoreNoteOff':'41','CueListGetDirectory':'A7','CueListRemove':'60','CueListRead':'AB','CueSceneRead':'AD','CueListWrite':'AA','CueSceneWrite':'AC','CueListRemoveStep':'62','CommonSetMIDIMode':'68','CommonMIDIBeat':'6B','CommonGetPatcher':'80','CommonSetPatcher':'81','CommonGetGain':'82','CommonSetGain':'83','CommonGetCurveTable':'84','CommonSetCurveTable':'85','CommonGetCurve1':'8C','CommonSetCurve1':'8D','CommonGetCurve2':'8E','CommonSetCurve2':'8F','CommonGetCurve3':'90','CommonSetCurve3':'91','CommonGetCurve4':'92','CommonSetCurve4':'93','CommonGetCurve5':'94','CommonSetCurve5':'95','CommonGetCurve6':'96','CommonSetCurve6':'97','CommonGetCurve7':'98','CommonSetCurve7':'99','CommonGetSlope':'86','CommonSetSlope':'87','CommonGetGlobalData':'0B','CommonSetBaudRate':'0006','CommonSetDMXOffset':'6A','CommonSetNumDMXChannels':'69','CommonSetName':'AE','CommonSetPassword':'AF','CommonSetIpConfig':'B0','CommonSetDmxIn':'B2','CommonSetUdpIn':'B8','CommonSetUdpOut':'B9','CommonSetTime':'BA','CommonGet16BitTable':'A0','CommonSet16BitTable':'A1','CommonStore16BitTable':'A2','CommonGetMIDIMapping':'A3','CommonSetMIDIMapping':'A4','CommonStoreMIDIMapping':'A5','CommonGetDigOutPatcher':'B3','CommonSetDigOutPatcher':'B4','CommonResetNonVolatile':'A8','DebugGetTotalUsage':'DD','DebugGetFreeList':'DE','DebugGetCuelistUsage':'DF'}

c = ConfigParser.ConfigParser()
c.read('config.ini')
LIGHTSERVER = (c.get('LanBox','name'), c.getint('LanBox','port'))
PASSWORD=c.get('LanBox','password')

class lanbox(Protocol):
    '''Prototype async handler. Unfinished.'''
    def __init__(self, methods):
        self.methods = methods
        self.methods._lanbox = self.sendLine

    def connectionMade(self):
        self.transport.write(PASSWORD+'\n')

    @defer.inlineCallbacks
    def sendLine(self, string):
        self.transport.write(string+'\n')
        defer.returnValue (self.dataReceived())

    def dataReceived(self, data):
        data.strip('\n')
        data.strip()
        if data is '?': return None
        else: return data

class LanboxFactory(ReconnectingClientFactory):
    '''Prototype async handler. Unfinished.'''
    def __init__(self, methods):
        self.host, self.port = LIGHTSERVER
        self.methods = methods
    def buildProtocol(self,addr):
        return Lanbox(self.methods)

class LanboxMethods():
    '''Lanbox methods from the manual.'''
    def _connectToLB(self, s=None):
        '''Handler for connecting to the lanbox. Blocking.'''
        if s is None:
            s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        data = ''
        s.connect(LIGHTSERVER)
        data=s.recv(512)
        while data != 'connected':
            s.sendall(PASSWORD+'\n')
            data=s.recv(512)
        s.sendall('*6501#') #16 bit mode on
        data=s.recv(512)
        return s

    def _lanbox(self, command,s=None):
        '''Handler for connecting to the lanbox.'''
        closeafter = False
        if s is None: 
            closeafter = True
            s = self._connectToLB()
#        print('*'+command+'#')
        s.sendall('*'+command+'#')
        ret = s.recv(512)
#        print(ret)
        if ret != '?':
            ret = ret[1:-2]
        if closeafter:
            s.close()
        return ret

    def _chunk(self, seq, n ):
        '''Iterable handler function.'''
        while seq:
            yield seq[:n]
            seq = seq[n:]
    
    def _to_hex(self, n,length=2):
        '''Convert int to hex string of set length.'''
        if isinstance(n,basestring):
            try:
                n = int(n)
            except:
                if n.lower().startswith('y'):
                    n = True
                elif n.lower().startswith('n'):
                    n = False
                else: raise ValueError #Trying to encode hex?
        if isinstance(n,bool):
            if n: return 'F'*length
            else: return '0'*length
        return hex(n)[2:].zfill(length)
    
    def _from_hex(self, n):
        '''Convert hex string to int. Not designed to return bools.'''
        if not isinstance(n,basestring): raise ValueError #Probably a typo!
        return int(n,16)
    
    def _Table1(self, response='',model = ''): 
        '''What model am I from response, or, what response would give this model?'''
        T1 = {'LC+':'F8FB','LCX':'F8FD','LXM':'F8FF','LCE':'F901'}
        rT1 = {value: key for key, value in T1.items()}
        if response != '':
            m = 'unknown'
            for model in T1:
                if T1[model] == response:
                    m = model
            return m
        if model != '':
            r = ''
            for response in rT1:
                if rT1[response] == model:
                    r = response
            return r
        return T1.keys()

    def showModels(self):
        '''Show a list of LanBox model names.'''
        return self._Table1()

    def _Table2(self, model, device):
        '''Does this model LanBox have this device, and if so what's the channel?'''
        T2 = {'LCX':{'mixer':'FE','dmxout':'FF','dmxin':'FC','externalinputs':'FD'},
              'LCE':{'mixer':'FE','dmxout':'FF','dmxin':'FC','externalinputs':'FD'},
              'LCM':{'mixer':'FE','dmxout':'FF'},
              'LC+':{'mixer':'09','dmxout':'0A'}}
        ret = {}
        try:
            m_Table = T2[model]
            ret = m_Table[device]
        except:
            return None
        return ret
        
    def _Table3(self, response = '', status = []): 
        '''What is the status list of this channel, or, what would give this status from a list?'''
        T3 = {0:'mixstatus',1:'channeleditstatus',2:'solostatus',3:'fadestatus'}
        rT3 = {value: key for key, value in T3.items()}
        if response != '':
            ret = []
            bits = bin(int(response,16))[2:]
            try:
                for bit in T3:
                    if bits[-bit-1] == '1':
                        ret.append(T3[bit])
                return ret
            except:
                return
        if status != []:
            ret = '0000'
            for s in status:
                if s.lower() in rT3:
                   ret[3-rT3[s.lower()]]='1'
            return ret
        return rT3.keys()

    def showChannelStatusList(self):
        '''Show a list of valid channel status names.'''
        return self._Table3()

    def _Table4(self, response='', flags = []): 
        '''What is the attribute flags list for this layer, or, what would give this flag list?'''
        T4 = {0:'layeroutputenabled',1:'sequencemode',2:'fadestatus',3:'solostatus',4:'pausestatus',5:'auto',6:'sequencerwaiting',7:'locked'}
        rT4 = {value: key for key, value in T4.items()}
        if response != '':
            ret = []
            bits = bin(int(response,16))[2:]
            try:
                for bit in T4:
                    if bits[-bit-1] == '1':
                        ret.append(T4[bit])
                return ret
            except:
                return
        if flags != []:
            ret = '00000000'
            for f in flags:
                if f.lower() in rT4:
                   ret[7-rT4[f.lower()]]='1'
            return ret
        return rT4.keys()

    def showLayerAttributeList(self):
        '''Show a list of valid layer attribute names.'''
        return self._Table4()
    
    def _Table5(self, response = '', mode = ''): 
        '''What is the mix mode of this layer, or, what would I need to set to have this mix mode?'''
        T5 = {'0':'off','1':'copy','2':'htp','3':'ltp','4':'transparent','5':'add'}
        rT5 = {value: key for key, value in T5.items()}
        if response != '':
            response = str(response).lstrip('0')
            mode = 'unknown'
            if response in T5:
                mode = T5[response]
            return mode
        if mode != '':
            ret = ''
            if mode.lower() in rT5:
                ret = rT5[mode.lower()].zfill(2)
            return ret
        return rT5.keys()

    def showLayerMixModeList(self):
        '''Show a list of valid layer mix modes.'''
        return self._Table5()

    def _Table6(self, response = '', mode = ''): 
        '''What is the chase mode of this layer, or, what would I need to set to have this chase mode?'''
        T6={'0':'off','1':'chaseup','2':'loopup','3':'chasedown','4':'loopdown','5':'random',
        '6':'looprandom','7':'bounce','8':'loopbounce'}
        rT6 = {value: key for key, value in T6.items()}
        if response != '':
            response = str(response).lstrip('0')
            mode = 'unknown'
            if response in T6:
                mode = T6[response]
            return mode
        if mode != '':
            ret = ''
            if mode.lower() in rT6:
                ret = rT6[mode.lower()].zfill(2)
            return ret
        return rT6.keys()

    def showLayerChaseModeList(self):
        '''Show a list of valid layer chase modes.'''
        return self._Table6()

    def _Table7(self, response = '', mode = ''): 
        '''What is the fade mode of this layer, or, what would I need to set to have this fade mode?'''
        T7={'0':'off','1':'fadein','2':'fadeout','3':'crossfade','4':'off','5':'fadeincr',
        '6':'fadeoutcr','7':'crossfadecr'}
        rT7 = {value: key for key, value in T7.items()}
        if response != '':
            response = str(response).lstrip('0')
            mode = 'unknown'
            if response in T7:
                mode = T7[response]
            return mode
        if mode != '':
            ret = ''
            if mode.lower() in rT7:
                ret = rT7[mode.lower()].zfill(2)
            return ret
        return rT7.keys()

    def showLayerFadeModeList(self):
        '''Show a list of valid layer fade modes.'''
        return self._Table7()
    
    def _Table8(self, response = '', speed = ''): 
        '''What baud rate am I, or, what baud rate would give this?'''
        T8 = {'0':'38400','1':'19200','2':'9600','3':'31250','80':'31250','81':'31250','82':'31250','83':'31250'}
        rT8 = {value: key for key, value in T8.items()}
        if response != '':
            response = str(response).lstrip('0')
            speed = '38400'
            if response in T8:
                speed = T8[response]
            return int(speed)
        if speed != '':
            ret = ''
            if str(speed) in rT8:
                ret = rT8[speed].zfill(2)
            return ret
        return rT8.keys()

    def showBaudRateList(self):
        '''Show a list of valid LanBox baud rates.'''
        return self._Table8()

    def _Table9(self, response = '', output = []): 
        '''What UDP output am I, or, what would I do for this?'''
        T9 = {0:'broadcastdmxout',1:'broadcastmixerchannels',2:'broadcastexternalinputvalues',
        3:'broadcastdmxin',4:'broadcastlayerlist',5:'synchronizelayers'}
        rT9 = {value: key for key, value in T9.items()}
        if response != '':
            ret = []
            bits = bin(int(response,16))[2:]
            try:
                for bit in T9:
                    if bits[-bit-1] == '1':
                        ret.append(T9[bit])
                return ret
            except:
                return
        if output != []:
            ret = '00000000'
            for f in output:
                if f.lower() in rT9:
                   ret[7-rT9[f.lower()]]='1'
            return ret
        return rT9.keys()

    def showUDPOutputList(self):
        '''Show a list of valid LanBox UDP output modes.'''
        return self._Table9()
        
    def _Table10(self, secs='',offset=''): 
        '''Give me the right format to update the clock'''
        if secs !='':
            offset = int(secs) + 335361600
            return self._to_hex(offset,8)
        if offset !='':
            offset = self._from_hex(offset)
            secs = int(offset) - 335361600
            return secs   
        
    def _AppendixA(self, response = '', secs = ''): 
        '''Convert a fade duration to a time, or, convert a duration to the closest time available.'''
        ApA = [0,0.05,0.1,0.15,0.2,0.25,0.3,0.25,0.4,0.45,0.5,0.55,0.6,0.65,0.7,0.75,
        0.8,0.85,0.9,0.95,1,1.1,1.2,1.3,1.5,1.6,1.8,2.0,2.2,2.4,2.7,3,3.3,3.6,3.9,
        4.3,4.7,5.1,5.6,6.2,6.8,7.5,8.2,9.1,10,11,12,13,15,16,18,20,22,24,27,30,
        33,36,39,43,47,51,56,60,66,72,78,90,96,108,120,132,144,162,180,198,222,234,
        258,288,306,342,378,408,450,492,546,600,660,720,780,900,float('inf')]
        if response is not '':
            time = 0
            try:
                if int(response,16) in range(len(ApA)):
                    time = ApA[int(response)]
                return time
            except:
                return
        if secs is not '':
            dur = float(secs)
            if dur != float('inf'):
                distance = abs(dur - ApA[0])
                ret = 0
                for n, v in enumerate(ApA[1:]):
                    if abs(dur - v) < distance:
                        distance = abs(dur - v)
                        ret = n+1
                    else:
                        continue
            else: ret = 92 #Don't mess if you're infinite; closest won't work
            return self._to_hex(ret,2)
    
    def _commentTranslate(self, response = '', comment = ''): 
        '''Decode a comment line, or, encode one'''
        commentchars = [' ','A','B','C','D','E','F','G','H','I','J','K','L','M','N','O',
        'P','Q','R','S','T','U','V','W','X','Y','Z','a','b','c','d','e','f','g','h','i',
        'j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z','0','1','2',
        '3','4','5','6','7','8','9','-']
        if response is not '':
            try:
                commentbytes = bin(self._from_hex(response))[2:]
                out = ''
                for i in range(0,len(commentbytes)-5,6): #six bit per letter
                    out = out + commentchars[int(commentbytes[i:i+5],2)]
                return out
            except:
                return
        if comment is not '':
            comment = (str(comment)+'        ')[:7]
            response = ''
            for letter in comment:
                for n, c in enumerate(commentchars):
                    if c == letter:
                        response = response + bin(n)[2:].zfill(6) #ABCDEF ABCD...
            return hex(int(response,2))[2:]
    
    def _chaseSpeed(self, response = '', speed = ''): 
        '''Decode a chase speed response, or encode one.'''
        if response is not '':
            return 12800/(255-int(response,16))
        if speed is not '':
            s = int(speed)
            if s <= 50.1: s = 50.1
            if s > 1600: s = 1600
            return hex(255-int(12800/s))[2:].zfill(2)
    
    
    def _AppendixB(self, response = '', stepstocode = {}): 
        '''Decode a stepdata string, or, encode one.'''
        stepdata={1:{'name':'showScene',1:'fadeType',2:'fadeTime',3:'holdTime'},
        2:{'name':'showSceneOfCueList',1:'fadetype',2:'fadeTime',3:'holdTime',4:'cueList',6:'cueStep'}, 
        10:{'name':'goCueStepInLayer',1:'layerId',2:'cueList',4:'cueStep'},
        11:{'name':'clearLayer',1:'layerId'},
        12:{'name':'pauseLayer',1:'layerId'},
        13:{'name':'resumeLayer',1:'layerId'},
        14:{'name':'startLayer',1:'layerId'},
        15:{'name':'stopLayer',1:'layerId'},
        16:{'name':'configureLayer',1:'sourceLayerId',2:'destLayerId',3:'newLayerId',4:'cueList',5:'cueStep'},
        17:{'name':'stopLayer',1:'layerId'},
        18:{'name':'goTrigger',1:'layerId',2:'cueList',3:'triggerid',4:'channel'},
        20:{'name':'goCueStep',1:'cueStep'},
        21:{'name':'goNextInLayer',1:'layerId'},
        22:{'name':'goPreviousInLayer',1:'layerId'},
        23:{'name':'loopToCueStep',1:'cueStep',2:'numberOfLoops'},
        24:{'name':'hold',1:'holdTime'},
        25:{'name':'holdUntil',1:'day',2:'hours',3:'minutes',4:'seconds',5:'frames'},
        26:{'name':'goIfAnalogueChannel',1:'analogueData',6:'cueStep'},
        27:{'name':'goIfChannel',1:'layerId',2:'channel',3:'goValues',5:'cueStep'},
        30:{'name':'setLayerAttributes',1:'fadeEnable',2:'outputEnable',3:'soloEnable',4:'lock'},
        31:{'name':'setLayerMixMode',1:'layerId',2:'mixMode',3:'transparencyDepth1',4:'transparencyDepth2',5:'fadeTime'},
        32:{'name':'setLayerChaseMode',1:'layerId',2:'mixMode',3:'_chaseSpeed1',4:'_chaseSpeed2',5:'fadeTime'},
        40:{'name':'writeMidiStream',1:'midiData'},
        49:{'name':'writeSerialStream1',1:'serialData'},
        50:{'name':'writeSerialStream2',1:'serialData'},
        51:{'name':'writeSerialStream3',1:'serialData'},
        52:{'name':'writeSerialStream4',1:'serialData'},
        53:{'name':'writeSerialStream5',1:'serialData'},
        54:{'name':'writeSerialStream6',1:'serialData'},
        55:{'name':'writeSerialStream7',1:'serialData'},
        56:{'name':'writeSerialStream8',1:'serialData'},
        70:{'name':'comment',1:'comment'}}
        if response != '':
            ret = dict()
            type = int(response[0:2],16)
            if type in stepdata:
                steptype = stepdata[type]
                for value in steptype:
                    if value == 'name':
                        ret['name'] = steptype['name']
                    else:
                        datatype = steptype[value] #Where value = field number
                        if datatype == 'fadeEnable' or datatype == 'outputEnable' or datatype == 'soloEnable' or datatype == 'lock': #Booleans
                            if response[2*value+1:2*value+2] is '00': ret[datatype]=False
                            else: ret[datatype]=True
                        elif datatype == 'fadeTime' or datatype == 'holdTime' or datatype == 'fadeTime': #_Appendix A lookup
                            ret[datatype] = self._AppendixA(response[2*value+1:2*value+2])
                        elif datatype == 'channel' or datatype == 'goValues': #2-byte length
                            ret[datatype] = response[2*value+1:2*value+4]
                        elif datatype == 'midiData' or datatype =='analoguedata' or datatype == 'serialData': #6-byte length
                            ret[datatype] = response[2*value+1:2*value+12]
                        elif datatype == 'transparencyDepth1' or datatype == 'transparencyDepth2': #100% = 255
                            ret[datatype] = str(int(response[2*value+1:2*value+2],16)*100/255)
                        elif datatype == '_chaseSpeed1' or datatype =='_chaseSpeed2': #_chaseSpeeds
                            ret[datatype] = self._chaseSpeed(response[2*value+1:2*value+2])
                        elif datatype == 'fadeType':
                            ret[datatype] = self._Table7(response[2*value+1:2*value+2])
                        elif datatype == 'mixMode':
                            ret[datatype] = self._Table5(response[2*value+1:2*value+2])
                        elif datatype == 'comment':
                            ret[datatype] = self._commentTranslate(response[2*value+1:2*value+12])
                        elif datatype == 'day':
                            d = response[2*value+1:2*value+2]
                            if d == '00': ret[datatype]='Mon'
                            if d == '01': ret[datatype]='Tue'
                            if d == '02': ret[datatype]='Wed'
                            if d == '03': ret[datatype]='Thu'
                            if d == '04': ret[datatype]='Fri'
                            if d == '05': ret[datatype]='Sat'
                            if d == '06': ret[datatype]='Sun'
                            if d == '80': ret[datatype]='ALL'
                        else:
                            ret[datatype] = response[2*value+1:2*value+2]
            return ret
        if stepstocode != {}:
            returnlist = ['00','00','00','00','00','00','00']
            for steptype in stepdata:
                if stepstocode['name'].lower() == stepdata[steptype]['name'].lower():
                    returnlist[0]= hex(steptype)[2:].zfill(2)
                    del stepstocode['name']
                    for element in stepstocode:
                        for position in stepdata[steptype]:
                            if element.lower() == stepdata[steptype][position].lower():
                                payload = stepstocode[element]
                                if element.lower() == 'fadeenable' or element.lower() == 'outputenable' or element.lower() == 'soloenable' or element.lower() == 'lock': #Booleans
                                    if payload is True:
                                        returnlist[position] = 'FF'
                                    else: returnlist[position]='00'
                                elif element.lower() == 'fadetime' or element.lower() == 'holdtime': #_Appendix A lookup
                                    returnlist[position] = self._AppendixA('',payload)
                                elif element.lower() == 'channel' or element.lower() == 'govalues': #2-byte length
                                    returnlist[position] = payload[0:2]
                                    returnlist[position+1] = payload[2:4]
                                elif element.lower() == 'mididata' or element.lower() =='analoguedata' or element.lower() == 'serialdata': #6-byte length
                                    returnlist[position] = payload[0:2]
                                    returnlist[position+1] = payload[2:4]
                                    returnlist[position+2] = payload[4:6]
                                    returnlist[position+3] = payload[6:8]
                                    returnlist[position+4] = payload[8:10]
                                    returnlist[position+5] = payload[10:12]
                                elif element.lower() == 'transparencydepth1' or element.lower() == 'transparencydepth2': #100% = 255
                                    try:
                                        percent = int(payload)
                                        if percent >100: percent = 100
                                        if percent <0: percent = 0
                                    except:
                                        percent = 0
                                    returnlist[position] = hex(int(payload)*255/100)[2:].zfill(2)
                                elif element.lower() == '_chaseSpeed1' or element.lower() =='_chaseSpeed2': #_chaseSpeeds
                                    returnlist[position] = self._chaseSpeed('',payload)
                                elif element.lower() == 'fadetype':
                                    returnlist[position] = self._Table7('',payload)
                                elif element.lower() == 'mixmode':
                                    returnlist[position] = self._Table5('',payload)
                                elif element.lower() == 'comment':
                                    returnlist[position] = self._commentTranslate('',payload)
                                elif element.lower() == 'day':
                                    if payload.lower()[:3] == 'mon': returnlist[position] = '00'
                                    if payload.lower()[:3] == 'tue': returnlist[position] = '01'
                                    if payload.lower()[:3] == 'wed': returnlist[position] = '02'
                                    if payload.lower()[:3] == 'thu': returnlist[position] = '03'
                                    if payload.lower()[:3] == 'fri': returnlist[position] = '04'
                                    if payload.lower()[:3] == 'sat': returnlist[position] = '05'
                                    if payload.lower()[:3] == 'sun': returnlist[position] = '06'
                                    if payload.lower()[:3] == 'all': returnlist[position] = '80'
                                    if payload.lower()[:5] == 'every': returnlist[position] = '80'
                                else:
                                    retlist[position]= hex(element)[2:].zfill(2)
                    return ''.join(returnlist)
                else: pass
        ret = {}
        for type in stepdata:
            names = stepdata[type]
            n = names['name']
            del names['name']
            ret[n] = names.values()
        return ret

    def showStepDataList(self):
        '''Show a table of valid step data arguments for each type of step data.'''
        return self._AppendixB()

    def commonGetAppID (self):
        '''Return the device ID and version of this Lanbox.'''
        ret = {}
        response = self._lanbox(commandDict['CommonGetAppID'])
        ret['deviceId'] = self._Table1(response[0:4])
        ret['version'] = self._from_hex(response[4:8])
        return ret
    def _common16BitMode (self, sixteenBitMode):
        '''Toggle 16-Bit mode. Warning - this will not do anything!'''
        return self._lanbox(commandDict['Common16BitMode']+self._to_hex(sixteenBitMode,2))
    def commonReboot (self):
        '''Reboot the lanbox.'''
        return self._lanbox(commandDict['CommonReboot'])
    def commonSaveData (self):
        '''Save data to the internal flash.'''
        return self._lanbox(commandDict['CommonSaveData'])
    def channelSetData (self, layer=1,**channelData):
        '''Set each channel to a value on each layer. Expects a dict.'''
        cmd=commandDict['ChannelSetData']
        cmd = cmd + self._to_hex(layer,2)
        for d in channelData:
            channel = d
            value = channelData[d]
            cmd = cmd + self._to_hex(channel,4)+self._to_hex(value,2)
        return self._lanbox(cmd)        
    def channelReadData (self, startChannel, num=1, layer=1):
        '''Returns a list of values of channels on layer.'''
        response=self._lanbox(commandDict['ChannelReadData']+self._to_hex(layer,2)+self._to_hex(startChannel,4)+self._to_hex(num,2))
        ret = {}
        for n,c in enumerate(self._chunk(response,2)):
            ret[startChannel+n] = self._from_hex(c)
        return ret
    def channelReadStatus (self, startChannel, num=1,layer=1):
        '''Gives a dict of flags for channel in layer'''
        response=self._lanbox(commandDict['ChannelReadData']+self._to_hex(layer,2)+self._to_hex(startChannel,4)+self._to_hex(num,2))
        ret = {}
        for n,c in enumerate(self._chunk(response,2)):
            ret[startChannel+n] = self._Table3(c)
        return ret
    def channelSetOutputEnable (self, layer=1, **channelData):
        '''Sets the enable flag on channel. Expects a dict{channel:bool}'''
        cmd=commandDict['ChannelSetOutputEnable']
        cmd = cmd + self._to_hex(layer,2)
        for d in channelData:
            channel = d
            value = channelData[d]
            cmd = cmd + self._to_hex(channel,4)+self._to_hex(value,2)
        return self._lanbox(cmd)
    def channelSetActive (self, layer=1, **channelData):
        '''Sets the active flag on channel. Expects a dict{channel:bool}'''
        cmd=commandDict['ChannelSetActive']
        cmd = cmd + self._to_hex(layer,2)
        for d in channelData:
            channel = d
            value = channelData[d]
            cmd = cmd + self._to_hex(channel,4)+self._to_hex(value,2)
        return self._lanbox(cmd)
    def channelSetSolo (self, layer=1, **channelData):
        '''Sets the solo flag on channel. Expects a dict{channel:bool}'''
        cmd=commandDict['ChannelSetSolo']
        cmd = cmd + self._to_hex(layer,2)
        for d in channelData:
            channel = d
            value = channelData[d]
            cmd = cmd + self._to_hex(channel,4)+self._to_hex(value,2)
        return self._lanbox(cmd)
    def commonGetLayers (self):
        '''Returns a dict of all layers with nested layer attributes'''
        ret = {}
        response = self._lanbox(commandDict['CommonGetLayers'])
        for c in self._chunk(response,24):
            layer = self._from_hex(c[:2])
            ret[layer]={}
            ret[layer]['layerID']=self._from_hex(c[2:4])
            ret[layer]['layerAttr']=self._Table4(c[4:6])
            ret[layer]['cueList']=self._from_hex(c[6:10])
            ret[layer]['cueStep']=self._from_hex(c[10:12])
            ret[layer]['fadeTime']=self._AppendixA(c[12:14])
            ret[layer]['remainingFadeTime']=self._from_hex(c[14:18])*0.05
            ret[layer]['holdTime']=self._AppendixA(c[18:20])
            ret[layer]['remainingHoldTime']=self._from_hex(c[20:24])*0.05
        return ret
    def layerGetStatus (self, layer=1):
        '''Returns a dict of layer with extended layer attributes'''
        ret = {}
        response = self._lanbox(commandDict['LayerGetStatus']+self._to_hex(layer,2))
        ret['outputStatus'] = bool(self._from_hex(response[:2]))
        ret['sequenceStatus'] = bool(self._from_hex(response[2:4]))
        ret['fadeStatus'] = bool(self._from_hex(response[4:6]))
        ret['soloStatus'] = bool(self._from_hex(response[6:8]))
        ret['mixStatus'] = self._Table5(response[8:10])
        ret['holdTime'] = self._AppendixA(response[12:14])
        ret['remainingHoldTime'] = self._from_hex(response[14:18])*0.05
        ret['activeCueList'] = self._from_hex(response[18:22])
        ret['activeCueStep'] = self._from_hex(response[22:24])
        ret['chaseMode'] = self._Table6(response[22:24])
        ret['layerSpeed'] = self._chaseSpeed(response[24:26])
        ret['fadeType'] = self._Table7(response[26:28])
        ret['fadeTime'] = self._AppendixA(response[28:30])
        ret['cueStepFadeTime'] = self._AppendixA(response[30:32])
        ret['remainingFadeTime'] = self._from_hex(response[32:36])*0.05
        ret['layerTransparency'] = self._from_hex(response[36:38])/2.55
        ret['loadingIndication'] = self._from_hex(response[38:40])*0.05/255
        ret['pauseStatus'] = bool(self._from_hex(response[40:42]))
        ret['sysExDeviceId'] = self._from_hex(response[42:44])
        ret['autoStatus'] = bool(self._from_hex(response[42:44]))
        ret['currentCueStep'] = self._AppendixB(response[44:58])
        return ret
    def layerSetID (self, oldLayer, newLayer):
        '''Sets a layer ID'''
        return self._lanbox(commandDict['LayerSetID']+self._to_hex(oldLayer,2)+self._to_hex(newLayer,2))
    def layerSetOutput (self, layer, output):
        '''Sets a layer output flag'''
        return self._lanbox(commandDict['LayerSetOutput']+self._to_hex(layer,2)+self._to_hex(output,2))
    def layerSetFading (self, layer, fade):
        '''Sets a layer fade flag'''
        return self._lanbox(commandDict['LayerSetFading']+self._to_hex(layer,2)+self._to_hex(fade,2))
    def layerSetSolo (self, layer, solo):
        '''Sets a layer solo flag'''
        return self._lanbox(commandDict['LayerSetSolo']+self._to_hex(layer,2)+self._to_hex(solo,2))
    def layerSetAutoOutput (self, layer, auto):
        '''Sets a layer automatic output flag'''
        return self._lanbox(commandDict['LayerSetAutoOutput']+self._to_hex(layer,2)+self._to_hex(auto,2))
    def layerSetMixMode (self, layer, mixMode):
        '''Sets a layer mix mode flag from a dict of mixmodes supplied.'''
        return self._lanbox(commandDict['LayerSetMixMode']+self._to_hex(layer,2)+self._Table5('',mixMode))
    def layerSetTransparencyDepth (self, layer, transparencyDepth):
        '''Sets a layer transparency depth from 0 to 100%'''
        return self._lanbox(commandDict['LayerSetTransparencyDepth']+self._to_hex(layer,2)+self._to_hex(transparencyDepth*2.55,2))
    def layerSetLocked (self, layer, locked):
        '''Sets a layer automatic locked flag'''
        return self._lanbox(commandDict['LayerSetLocked']+self._to_hex(layer,2)+self._to_hex(locked,2))
    def layerConfigure (self, destLayer, sourceLayer, layerId=None, layerAttr=None, startCueList=None, startCueStep=None):
        '''Configures a layer based on another layer.'''
        cmd=commandDict['LayerConfigure']
        cmd = cmd + self._to_hex(destLayer,2)
        cmd = cmd + self._to_hex(sourceLayer,2)
        if layerId is not None:
            cmd = cmd+self._to_hex(layerId,2)
            if layerAttr is None:
                raise ValueError('need layerAttr')
            cmd = cmd+self._Table4('',layerAttr)
            if startCueList is None:
                raise ValueError('need startCueList')
            cmd = cmd+self._to_hex(startCueList,4)
            if startCueStep is None:
                raise ValueError
                raise ValueError('need startCueStep')
        return self._lanbox(cmd)
    def layerGo (self, layer=1, cueList=1, cueStep=None):
        '''Runs the cues set to a layer.'''
        cmd=commandDict['LayerGo']+self._to_hex(layer,2)+self._to_hex(cueList,4)
        if cueStep is not None:
            cmd = cmd + self._to_hex(cueStep,2)
        return self._lanbox(cmd)
    def layerClear (self, layer=1):
        '''Clears a layer.'''
        return self._lanbox(commandDict['LayerClear']+self._to_hex(layer,2))
    def layerPause (self, layer=1):
        '''Pauses a layers cues.'''
        return self._lanbox(commandDict['LayerPause']+self._to_hex(layer,2))
    def layerResume (self, layer=1):
        '''Resumes a layers cues.'''
        return self._lanbox(commandDict['LayerResume']+self._to_hex(layer,2))
    def layerNextStep (self, layer=1):
        '''Go to the next step of a layers cues.'''
        return self._lanbox(commandDict['LayerNextStep']+self._to_hex(layer,2))
    def layerPreviousStep (self, layer=1):
        '''Go to the previous step of a layers cues.'''
        return self._lanbox(commandDict['LayerPreviousStep']+self._to_hex(layer,2))
    def layerNextCue (self, layer=1):
        '''Go to the next cue of a layers cues.'''
        return self._lanbox(commandDict['LayerNextCue']+self._to_hex(layer,2))
    def layerPreviousCue (self, layer=1):
        '''Go to the previous cue of a layers cues.'''
        return self._lanbox(commandDict['LayerPreviousCue']+self._to_hex(layer,2))
    def layerSetChaseMode (self, layer,chaseMode):
        '''Sets the chase mode flag of a layer.'''
        return self._lanbox(commandDict['LayerSetChaseMode']+self._to_hex(layer,2)+self._Table6('',chaseMode))
    def layerSetChaseSpeed (self, layer, chaseSpeed):
        '''Sets the chase speed of a layer i.e. how quickly each cue gets executed.'''
        return self._lanbox(commandDict['LayerSetChaseSpeed']+self._to_hex(layer,2)+self._chaseSpeed('',chaseSpeed))
    def layerSetFadeType (self, layer, fadeType):
        '''Sets the fade type of a layer. Expects a string.'''
        return self._lanbox(commandDict['LayerSetFadeType']+self._to_hex(layer,2)+self._Table7('',fadeType))
    def layerSetFadeTime (self, layer, fadeTime):
        '''Sets the fade time of a layer.'''
        return self._lanbox(commandDict['LayerSetFadeTime']+self._to_hex(layer,2)+self._AppendixA('',fadeTime))
    def layerSetEditRunMode (self, layer, edit):
        '''Puts a layer in Edit Run mode.'''
        return self._lanbox(commandDict['LayerSetEditRunMode']+self._to_hex(layer,2)+self._to_hex(edit,2))
    def layerUsesCueList (self, layer, cueList):
        '''Assigns a cue list to a layer.'''
        return self._lanbox(commandDict['LayerUsesCueList']+self._to_hex(layer,2)+self._to_hex(cueList,4))
    def cueListCreate (self, cueList):
        '''creates a new cue list.'''
        return self._lanbox(commandDict['CueListCreate']+self._to_hex(cueList,4))
    def layerInsertStep (self, layer, cueStep=None):
        '''Adds a new step to a layer.'''
        cmd = commandDict['LayerInsertStep']+self._to_hex(layer,2)
        if cueStep is not None: cmd = cmd + self._to_hex(cueStep,2)
        return self._lanbox(cmd)
    def layerReplaceStep (self, layer, cueStep):
        '''Exchanges a step on a layer with another.'''
        return self._lanbox(commandDict['LayerReplaceStep']+self._to_hex(layer,2)+self._to_hex(cueStep,2))
    def layerSetCueStepParameters (self, layer, stepData):
        '''Sets a step Parameters.'''
        data = self._AppendixB('',stepData)
        self._lanbox(commandDict['LayerSetCueStepType']+self._to_hex(layer,2)+self._to_hex(data[:2],2))
        self._lanbox(commandDict['LayerSetCueStepParameters1']+self._to_hex(layer,2)+self._to_hex(data[2:4],2))
        self._lanbox(commandDict['LayerSetCueStepParameters2']+self._to_hex(layer,2)+self._to_hex(data[4:6],2))
        self._lanbox(commandDict['LayerSetCueStepParameters3']+self._to_hex(layer,2)+self._to_hex(data[6:8],2))
        self._lanbox(commandDict['LayerSetCueStepParameters4']+self._to_hex(layer,2)+self._to_hex(data[8:10],2))
        self._lanbox(commandDict['LayerSetCueStepParameters5']+self._to_hex(layer,2)+self._to_hex(data[10:12],2))
        self._lanbox(commandDict['LayerSetCueStepParameters6']+self._to_hex(layer,2)+self._to_hex(data[12:14],2))
        return None
    def layerSetDeviceID (self, layer, deviceId):
        '''Sets the MIDI Device ID for a layer.'''
        return self._lanbox(commandDict['LayerSetDeviceID']+self._to_hex(layer,2)+self._to_hex(deviceId,2))
    def layerSetSustain (self, layer, sustain):
        '''Sets the MIDI sustain flag on a layer. This affects how MIDI notes with velocity 0 interact with the layer.'''
        return self._lanbox(commandDict['LayerSetSustain']+self._to_hex(layer,2)+self._to_hex(sustain,2))
    def layerIgnoreNoteOff (self, layer, ignoreNote):
        '''Toggles the effect of MIDI Note-Off signals'''
        return self._lanbox(commandDict['LayerIgnoreNoteOff']+self._to_hex(layer,2)+self._to_hex(ignoreNote,2))
    def cueListGetDirectory (self, index=1):
        '''Lists 80 cue list lengths from index.'''
        ret = {}
        response = self._lanbox(commandDict['CueListGetDirectory']+self._to_hex(index,4))
        for c in self._chunk(response,6):
            ret[self._from_hex(c[:4])]=self._from_hex(c[4:6])
        return ret
    def cueListRemove (self, cueList):
        '''Delete a cue list.'''
        return self._lanbox(commandDict['CueListRemove']+self._to_hex(cueList,4))
    def cueListRead (self, cueList, start, num=0):
        '''Returns a cue list steps with flags.'''
        ret = {}
        response = self._lanbox(commandDict['CueListRead']+self._to_hex(cueList,4)+self._to_hex(start,2)+self._to_hex(num,2))
        for n,c in enumerate(self._chunk(response,14)):
            ret[start+n]=self._AppendixB(c)
        return ret
    def cueSceneRead (self, cueList, cueStep, start=1):
        '''Returns the scene (channel data) info for cueStep of cueList.Start may be needed if length of return over 250.'''
        ret = {}
        cmd = commandDict['CueSceneRead']+self._to_hex(cueList,4)+self._to_hex(cueStep,2)
        if start>1: cmd = cmd + self._to_hex(start,2)
        response = self._lanbox(cmd)
        ret['channelsInScene']=self._from_hex(response[2:6])
        for c in self._chunk(response[6:],6):
            ret[self._from_hex(c[:4])]=self._from_hex(c[4:6])
        return ret
    def cueListWrite (self, cueList, *stepData):
        '''Write in the cueList step data. Expects a dict of flags per step.'''
        cmd = commandDict['CueListWrite']+self._to_hex(cueList,4)
        for step in stepData:
            cmd = cmd + self._AppendixB('',step)
        return self._lanbox(cmd)
    def cueSceneWrite (self, cueList, cueStep, **channelData):
        '''Write in the cueList scene (channel values) data. Expects a dict of channels and values.'''
        cmd = commandDict['CueSceneWrite']+self._to_hex(cueList,4)+self._to_hex(cueStep,2)
        cmd = cmd + '00'+self._to_hex(len(channelData),4)
        for channel in channelData:
            cmd = cmd +self._to_hex(channel,4)+self._to_hex(channelData[channel],4)
        return self._lanbox(cmd)
    def cueListRemoveStep (self, cueList, stepNum):
        '''Deletes a step in the cueList.'''
        return self._lanbox(commandDict['CueListRemoveStep']+self._to_hex(cueList,4)+self._to_hex(stepNum,2))
    def commonSetMIDIMode (self, midiMode):
        '''Sets the MIDI mode of the lanbox.'''
        return self._lanbox(commandDict['CommonSetMIDIMode']+self._to_hex(midiMode,2))
    def commonMIDIBeat (self):
        '''Send a MIDI beat.'''
        return self._lanbox(commandDict['CommonSetMIDIBeat'])
    def commonGetPatcher (self, dmxChan=1, num=255):
        '''Return the DMX Patch table.'''
        response = self._lanbox(commandDict['CommonGetPatcher']+self._to_hex(dmxChan,4)+self._to_hex(num,2))
        for n,c in enumerate(self._chunk(response,4)):
            ret[dmxChan+n]=self._from_hex(c)
        return ret
    def commonSetPatcher (self, **dmxData):
        '''Set the DMX Patch table. Expects a dict.'''
        cmd = commandDict['CommonSetPatcher']
        for l in dmxData:
            cmd = cmd + self._to_hex(l,4)
            cmd = cmd + self._to_hex(dmxData[l],4)
        return self._lanbox(cmd)
    def commonGetGain (self, dmxChan=1, num=255):
        '''Returns the gain factor for each channel.'''
        ret = {}
        cmd = commandDict['CommonGetGain']+self._to_hex(dmxChan,4)+self._to_hex(num,2)
        response = self._lanbox(cmd)
        for n,c in enumerate(self._chunk(response,2)):
            ret[dmxChan+n]=self._from_hex(c)
        return ret
    def commonSetGain (self, **dmxData):
        '''Sets the gain factor for channels. Expects a dict.'''
        cmd = commandDict['CommonSetGain']
        for l in dmxData:
            cmd = cmd + self._to_hex(l,4)
            cmd = cmd + self._to_hex(dmxData[l],2)
        return self._lanbox(cmd)
    def commonGetCurveTable (self, dmxChan=1, num=255):
        '''Returns which curve tables are assigned to what DMX channels.'''
        ret = {}
        cmd = commandDict['CommonGetCurveTable']+self._to_hex(dmxChan,4)+self._to_hex(num,2)
        response = self._lanbox(cmd)
        for n,c in enumerate(self._chunk(response,2)):
            ret[dmxChan+n]=self._from_hex(c)
        return ret
    def commonSetCurveTable (self, **dmxData):
        '''Assigns a curve table to channels. Expects a dict, chan->table.'''
        cmd = commandDict['CommonSetCurveTable']
        for l in dmxData:
            cmd = cmd + self._to_hex(l,4)
            cmd = cmd + self._to_hex(dmxData[l],2)
        return self._lanbox(cmd)
    def commonGetCurve (self, curveNum, firstVal=0, num=255):
        '''Returns a curve table from memory as a dict.'''
        ret = {}
        if curveNum<1 or curveNum>8: raise ValueError
        cmd = commandDict['CommonGetCurve'+str(curveNum)]
        cmd = cmd+self._to_hex(firstVal,2)+self._to_hex(num,2)
        response = self._lanbox(cmd)
        for n,c in enumerate(self._chunk(response,2)):
            ret[firstVal+n]=self._from_hex(c)
        return ret
    def commonSetCurve (self, curveNum, **curveData):
        '''Sets a curve table. Expects a dict, input:output.'''
        if curveNum<1 or curveNum>8: raise ValueError
        cmd = commandDict['CommonSetCurve'+str(curveNum)]
        for l in curveData:
            cmd = cmd + self._to_hex(l,4)
            cmd = cmd + self._to_hex(curveData[l],2)
        return self._lanbox(cmd)
    def commonGetSlope (self, dmxChan=1, num=255):
        '''Returns the maximum rate of change (in frames) per channel.'''
        ret = {}
        cmd = commandDict['CommonGetSlope']+self._to_hex(dmxChan,4)+self._to_hex(num,2)
        response = self._lanbox(cmd)
        for n,c in enumerate(self._chunk(response,2)):
            ret[dmxChan+n]=self._from_hex(c)
        return ret
    def commonSetSlope (self, **dmxData):
        '''Sets the maximum rate of change per channel. Expects a dict, channel:rate.'''
        cmd = commandDict['CommonSetSlope']
        for l in dmxData:
            cmd = cmd + self._to_hex(l,4)
            cmd = cmd + self._to_hex(dmxData[l],2)
        return self._lanbox(cmd)
    def commonGetGlobalData (self):
        '''Returns a lot of global information, baudrate, name, dmx channel data etc.'''
        ret = {}
        response = self._lanbox(commandDict['CommonGetGlobalData'])
        ret['baudRate']=self._Table8(response[:2])
        ret['dmxOffset']=self._from_hex(response[2:6])
        ret['dmxChannels']=self._from_hex(response[6:10])
        namelength = self._from_hex(response[10:12])
        ret['name']=''
        namelist = list(self._chunk(response[12:38],2))[:namelength]
        for letter in namelist:
            ret['name']=ret['name']+chr(int(letter,16))
        ret['sysExDeviceId']=self._from_hex(response[38:40])
        ret['ipAddress']='.'.join([str(self._from_hex(x)) for x in list(self._chunk(response[40:48],2))])
        ret['ipSubnet']='.'.join([str(self._from_hex(x)) for x in list(self._chunk(response[48:56],2))])
        ret['ipGateway']='.'.join([str(self._from_hex(x)) for x in list(self._chunk(response[56:64],2))])
        ret['dmxInDestinationLayer']=self._from_hex(response[64:66])
        ret['dmxInDestinationOffset']=self._from_hex(response[66:70])
        ret['dmxInSourceOffset']=self._from_hex(response[70:74])
        ret['dmxInSize']=self._from_hex(response[74:78])
        ret['udpInDestinationLayer']=self._from_hex(response[78:80])
        ret['udpInSourceAddress']='.'.join([str(self._from_hex(x)) for x in list(self._chunk(response[80:88],2))])
        ret['udpInPort']=self._from_hex(response[88:90])
        ret['udpInDestinationStartChannel']=self._from_hex(response[90:94])
        ret['udpInChannelCount']=self._from_hex(response[94:98])
        ret['udpOutPort']=self._from_hex(response[98:102])
        ret['udpOutSourceStartChannel']=self._from_hex(response[102:106])
        ret['udpOutChannelCount']=self._from_hex(response[106:110])
        ret['udpOutFlags']=self._Table9(response[110:112])
        ret['clockToChannel']=self._from_hex(response[112:116])
        ret['mtcToChannel']=self._from_hex(response[116:120])
        ret['ntpServerAddress']='.'.join([str(self._from_hex(x)) for x in list(self._chunk(response[120:128],2))])
        ret['ntpTimeOffset']=self._Table10('',response[128:136])
        ret['clockFrequencyTuning']=self._from_hex(response[136:144])/4294967296
        return ret
    def commonSetBaudRate (self, baudRate):
        '''Set the baud rate of the LanBox.'''
        return self._lanbox(commandDict['CommonSetBaudRate']+self._Table8('',baudRate))
    def commonSetDMXOffset (self, offset):
        '''Set the DMX offset of the LanBox.'''
        return self._lanbox(commandDict['CommonSetDMXOffset']+self._to_hex(offset,4))
    def commonSetNumDMXChannels (self, num):
        '''Set the number of DMX channels the LanBox controls.'''
        return self._lanbox(commandDict['CommonSetNumDMXChannels']+self._to_hex(num,4))
    def commonSetName (self, name):
        '''Set the name of the LanBox.'''
        name = str(name).encode('ascii')
        if len(name)>13: raise ValueError
        cmd = commandDict['CommonSetName']
        for c in name:
            cmd = cmd + self._to_hex(ord(c),2)
        return self._lanbox(cmd)
    def _commonSetPassword (self, password):
        '''Set the numeric password of the LanBox.'''
        if not isinstance(password,int): raise ValueError
        if password > 65535 or password <0: raise ValueError
        return self._lanbox(commandDict['CommonSetPassword']+self._to_hex(password,4))
    def _commonSetIpConfig (self, ipAddress, ipSubnet, ipGateway):
        '''Set the network config of the LanBox.'''
        cmd=commandDict['CommonSetIpConfig']
        for a in ipAddress.split('.'):
            cmd = cmd + self._to_hex(a,2)
        for a in ipSubnet.split('.'):
            cmd = cmd + self._to_hex(a,2)
        for a in ipGateway.split('.'):
            cmd = cmd + self._to_hex(a,2)
        return self._lanbox(cmd)
    def commonSetDmxIn (self, destLayer, destStart, inputStart, inputSize):
        '''Adjusts the way the Lanbox handles DMX input signals.'''
        return self._lanbox(commandDict['CommonSetDmxIn']+self._to_hex(destLayer,2)+self._to_hex(destStart,4)+self._to_hex(inputStart,4)+self._to_hex(inputSize,4))
    def commonSetUDPIn (self, destLayer, udpAddress, udpPort, udpInDestStart, udpInSourceStart, udpSourceSize):
        '''Sets UDP signals to a layer or buffer.'''
        cmd = commandDict['CommonSetUdpIn']+self._to_hex(destLayer,2)
        for a in udpAddress.split('.'):
            cmd = cmd + self._to_hex(a,2)
        cmd = cmd+self._to_hex(udpInDestStart,4)+self._to_hex(udpInSourceStart,4)+self._to_hex(udpSourceSize,4)
        return self._lanbox(cmd)
    def commonSetUDPOut (self, udpOutPort, udpOutSourceStart, udpSourceSize, udpOutFlags):
        '''Broadcast UDP layer or buffer info. Expects a list of flags as strings.'''
        return self._lanbox(commandDict['CommonSetUdpOut']+self._to_hex(udpOutPort,4)+self._to_hex(udpOutSourceStart,4)+self._to_hex(udpSourceSize,4)+self._Table9(udpOutFlags))
    def _commonSetTime (self, clock, mtc,ntpServer=None,ntpOffset=None,frequencyTuning=None):
        '''Sets the NTP server information.'''
        cmd=commandDict['CommonSetTime']
        cmd = cmd + self._to_hex(clock,4)
        cmd = cmd + self._to_hex(mtc,4)
        if ntpServer is not None: 
            for a in ntpServer.split('.'):
                cmd = cmd + self._to_hex(a,2)
            if ntpOffset is None:
                raise ValueError
            cmd = cmd + self._Table10(ntpOffset)
            if frequencyTuning is None:
                raise ValueError
            cmd = cmd + self._to_hex(frequencyTuning*4294967296,8)
        return self._lanbox(cmd)
    def commonGet16BitTable (self):
        '''Returns the linked channel table.'''
        ret = {}
        response = self._lanbox(commandDict['CommonGet16BitTable'])
        for n,c in enumerate(self._chunk(response,8)):
            ret[n]['highChannel']= self._from_hex(c[:4])
            ret[n]['lowChannel']= self._from_hex(c[4:])
        return ret
    def commonSet16BitTable (self, *sixteenBitData):
        '''Configures the linked channel table. Expects a lists of lists, [mode, highchannel, lowchannel].'''
        cmd=commandDict['CommonSet16BitTable']
        for d in sixteenBitData:
            modePair = self._from_hex(d[0],2)
            highChannel = self._from_hex(d[1],4)
            lowChannel = self._from_hex(d[2],4)
            cmd = cmd + modePair+highChannel+lowChannel
        return self._lanbox(cmd)
    def commonStore16BitTable (self):
        '''Saves the 16 bit linked channel info'''
        return self._lanbox(commandDict['CommonStore16BitTable'])
    def commonGetMIDIMapping (self):
        '''Returns the MIDI mapping.'''
        ret = {}
        response = self._lanbox(commandDict['CommonGetMIDIMapping'])
        for n,c in enumerate(self._chunk(response,6)):
            ret[n]['layer']= self._from_hex(c[:2])
            ret[n]['offset']= self._from_hex(c[2:])
        return ret
    def commonSetMIDIMapping (self, midiChan, layer, offset=0):
        '''Maps MIDI channels to layers.'''
        return self._lanbox(commandDict['CommonSetMIDIMapping']+self._to_hex(midiChan,2)+self._to_hex(layer,2)+self._to_hex(offset,4))
    def commonStoreMIDIMapping (self):
        '''Saves the MIDI map.'''
        return self._lanbox(commandDict['CommonStoreMIDIMapping'])
    def commonGetDigOutPatcher (self, firstPort=1, num=8):
        '''Returns the digital output channel link table.'''
        ret = {}
        response = self._lanbox(commandDict['CommonGetDigOutPatcher']+self._to_hex(firstPort,2)+self._to_hex(num,2))
        for n,c in enumerate(self._chunk(response,4)):
            ret[firstPort+n]=self._from_hex(c)
        return ret    
    def commonSetDigOutPatcher (self, **portData):
        '''Assigns a channel to digital output. Expects a dict, port:channel'''
        cmd=commandDict['CommonSetDigOutPatcher']
        for d in portData:
            portNum = self._from_hex(d,2)
            channel = self._from_hex(portData[d],4)
            cmd = cmd + portNum+channel
        return self._lanbox(cmd)
    def _commonResetNonVolatile (self):
        '''Soft-erases all non-volatile data.'''
        return self._lanbox(commandDict['CommonResetNonVolatile'])
    def _debugGetTotalUsage (self):
        '''Returns memory usage information.'''
        ret = {}
        response = self._lanbox(commandDict['DebugGetTotalUsage'])
        ret['memUsed'] = self._from_hex(response[:8])
        ret['memTotal'] = self._from_hex(response[8:])
        return ret
    def _debugGetFreeList (self):
        '''Returns free memory sections.'''
        ret = {}
        response = self._lanbox(commandDict['DebugGetFreeList'])
        for c in self._chunk(response,16):
            ret[self._from_hex(c[:8])]=self._from_hex(c[8:])
        return ret
    def _debugGetCuelistUsage (self, cueList, stepNum):
        '''Returns memory information about cue lists.'''
        ret = {}
        response = self._lanbox(commandDict['DebugGetCuelistUsage'])
        ret['address'] = self._from_hex(response[:8])
        ret['bytesReserved'] = self._from_hex(response[8:12])
        ret['bytesUsed'] = self._from_hex(response[12:])
        return ret
    
