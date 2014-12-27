
from collections import namedtuple
from abc import ABCMeta
from io import BytesIO

#-----------------------------------------------
# Constants 

_CHUNK_TYPE_HEADER=r'MThd'
_CHUNK_TYPE_TRACK=r'MTrk'

_PREFIX_SYSEX = 0xF0
_PREFIX_SYSEX_NOXMIT = 0xF7
_PREFIX_META = 0xFF

_STATUS_NOTE_OFF = 0b1000
_STATUS_NOTE_ON = 0b1001
_STATUS_POLY_KEY_PRESS = 0b1010
_STATUS_CONTROL_CHANGE = 0b1011
_STATUS_PROGRAM_CHANGE = 0b1100
_STATUS_CHANNEL_PRESS = 0b1101
_STATUS_PITCH_WHEEL_CHANGE = 0b1110

_META_END_OF_TRACK = 0x2F

#-----------------------------------------------
# Error classes

class MIDIIOError(IOError):
  pass

#-----------------------------------------------
# MIDI Events
class MIDIEvent(object):
  __metaclass__ = ABCMeta

NoteOffEvent = namedtuple('NoteOffEvent', 
  'delta channel key velocity')
MIDIEvent.register(NoteOffEvent)

NoteOnEvent = namedtuple('NoteOnEvent', 
  'delta channel key velocity')
MIDIEvent.register(NoteOnEvent)

PolyphonicKeyPressureEvent = namedtuple('PolyphonicKeyPressureEvent', 
  'delta channel key velocity')
MIDIEvent.register(PolyphonicKeyPressureEvent)

ControlChangeEvent = namedtuple('ControlChangeEvent', 
  'delta channel controller value')
MIDIEvent.register(ControlChangeEvent)

ProgramChangeEvent = namedtuple('ProgramChangeEvent', 
  'delta channel value')
MIDIEvent.register(ProgramChangeEvent)

ChannelPressureEvent = namedtuple('ChannelPressureEvent', 
  'delta, channel value')
MIDIEvent.register(ChannelPressureEvent)

PitchWheelChangeEvent = namedtuple('PitchWheelChangeEvent', 
  'delta channel least most')
MIDIEvent.register(PitchWheelChangeEvent)

#-----------------------------------------------
# Meta Events

class MetaEvent(object):
  def __init__(self, delta, metaType, data, **kwargs):
    self.delta = delta
    self.metaType = metaType
    self.data = data

  def __repr__(self):
    return "%s(%r)" % (self.__class__.__name__, self.__dict__)

class EndOfTrackEvent(MetaEvent):
  def __init__(self, delta, **kwargs):
    super(EndOfTrackEvent, self).__init__(delta, _META_END_OF_TRACK, [])

#-----------------------------------------------
# System Exclusive Events

class SystemExclusiveEvent(object):
  def __init__(self, delta, sysExType, data, **kwargs):
    self.delta = delta
    self.sysExType = sysExType
    self.data = data

  def __repr__(self):
    return "%s(%r)" % (self.__class__.__name__, self.__dict__)

#-----------------------------------------------
# MIDI chunks

class MIDIHeader:
  def __init__(self, frmt=1, division=220, trackCount=0):
    self.frmt = frmt
    self.division = division
    self.trackCount = trackCount

class MIDITrack:
  def __init__(self):
    self.events = []

  def addEvent(self, event):
    self.events.append(event)

class MIDI:
  def __init__(self, header=None, tracks=None):
    self.header = header if header else MIDIHeader()
    self.header.trackCount = len(tracks) if tracks else 0
    self.tracks = tracks
   
#-----------------------------------------------
# MIDI Reader

class MIDIReader:
  def __init__(self):
    self._runningStatus = None

  def read(self, fileName):
    with open(fileName, 'rb') as f:
      header = self._readHeader(f)
      tracks = []
      for i in range(header.trackCount):
        track = self._readTrack(f)
        tracks.append(track)
    return MIDI(header=header, tracks=tracks)

  def _readHeader(self, f):
    buff = f.read(4)
    if buff != _CHUNK_TYPE_HEADER:
      raise MIDIIOError('Invalid MIDI header identifier.')

    length = _readInt(f, 4)
    frmt = _readInt(f, 2)
    trackCount = _readInt(f, 2)
    division = _readInt(f, 2)
    # consume remainder (for non-standard headers)
    f.read(length - 6)

    return MIDIHeader(frmt, division, trackCount)

  def _readTrack(self, f):
    buff = f.read(4)
    if buff != _CHUNK_TYPE_TRACK:
      raise MIDIIOError('Invalid MIDI track identifier.')

    length = _readInt(f, 4)
    track = MIDITrack()

    while True:
      event = self._readEvent(f)
      track.addEvent(event)
      if isinstance(event, EndOfTrackEvent):
        break
    return track

  def _readEvent(self, f):
    delta = _readVarLen(f)
    prefix = _readInt(f, 1)

    if prefix == _PREFIX_SYSEX or prefix == _PREFIX_SYSEX_NOXMIT:
      event = self._readSystemExclusiveEvent(delta, prefix, f)
    elif prefix == _PREFIX_META:
      event = self._readMetaEvent(delta, prefix, f)
    else:
      event = self._readMIDIEvent(delta, prefix, f)
    return event

  def _readSystemExclusiveEvent(self, delta, prefix, f):
    length = _readVarLen(f)
    data = f.read(length)
    return SystemExclusiveEvent(delta, prefix, data)
   
  def _readMetaEvent(self, delta, prefix, f):
    metaType = _readInt(f, 1)
    length = _readVarLen(f)
    data = f.read(length)
    if metaType == _META_END_OF_TRACK:
      event = EndOfTrackEvent(delta)
    else:
      event = MetaEvent(delta, metaType, length, data)
    return event

  def _readMIDIEvent(self, delta, prefix, f):
    status = prefix >> 4
    channel = prefix & 0xF
    
    # use the status of the last event,
    # if the current status is not set.
    if status != 0:
      self._runningStatus = status
    else:
      status = self._runningStatus

    if status == _STATUS_NOTE_OFF:
      key = _readInt(f, 1) 
      vel = _readInt(f, 1)
      event = NoteOffEvent(delta, channel, key, vel)
    elif status == _STATUS_NOTE_ON:
      key = _readInt(f, 1) 
      vel = _readInt(f, 1)
      event = NoteOnEvent(delta, channel, key, vel)
    elif status == _STATUS_POLY_KEY_PRESS:
      key = _readInt(f, 1) 
      val = _readInt(f, 1)
      event = PolyphonicKeyPressureEvent(delta, channel, key, val)
    elif status == _STATUS_CONTROL_CHANGE:
      controller = _readInt(f, 1)
      val = _readInt(f, 1)
      event = ControlChangeEvent(delta, channel, controller, val)
    elif status == _STATUS_PROGRAM_CHANGE:
      val = _readInt(f, 1)
      event = ProgramChangeEvent(delta, channel, val)
    elif status == _STATUS_CHANNEL_PRESS:
      val = _readInt(f, 1)
      event = ChannelPressureEvent(delta, channel, val)
    elif status == _STATUS_PITCH_WHEEL_CHANGE:
      least = _readInt(f, 1)
      most = _read(f, 1)
      event = PitchWheelChangeEvent(delta, channel, least, most)
    else:
      event = MIDIEvent() #TODO: handle it.

    return event

def _readInt(f, byteCount):
  buff = f.read(byteCount)
  retVal = 0
  for byte in buff:
    retVal = retVal << 8
    retVal += ord(byte)
  return retVal

def _readVarLen(f):
  retVal = 0
  while True:
    retVal = retVal << 7
    byte = ord(f.read(1))
    retVal += byte & 0x7F
    # if the 8th bit of the last byte is 0, stop reading.
    if (byte >> 7) == 0:
      break
  return retVal

#-----------------------------------------------
# MIDI Writer

class MIDIWriter:
  def write(self, fileName, midi):
    with open(fileName, 'wb') as f:
      self._writeHeader(f, midi.header)
      for track in midi.tracks:
        self._writeTrack(f, track)

  def _writeHeader(self, f, header):
    f.write(_CHUNK_TYPE_HEADER)
    _writeInt(f, 4, 6)
    _writeInt(f, 2, header.frmt) 
    _writeInt(f, 2, header.trackCount) 
    _writeInt(f, 2, header.division) 

  def _writeTrack(self, f, track):
    f.write(_CHUNK_TYPE_TRACK)

    buff = BytesIO()
    for event in track.events:
      self._writeEvent(buff, event)

    _writeInt(f, 4, len(buff.getvalue()))
    f.write(buff.getvalue())

  def _writeEvent(self, f, event):
    _writeVarLen(f, event.delta)
    if isinstance(event, SystemExclusiveEvent):
      self._writeSystemExclusiveEvent(f, event)
    elif isinstance(event, MetaEvent):
      self._writeMetaEvent(f, event)
    else:
      self._writeMIDIEvent(f, event)

  def _writeMIDIEvent(self, f, event):
    if isinstance(event, NoteOffEvent):
      prefix = _concatPrefix(_STATUS_NOTE_OFF, event.channel)
      _writeInt(f, 1, prefix)
      _writeInt(f, 1, event.key)
      _writeInt(f, 1, event.velocity)
    elif isinstance(event, NoteOnEvent):
      prefix = _concatPrefix(_STATUS_NOTE_ON, event.channel)
      _writeInt(f, 1, prefix)
      _writeInt(f, 1, event.key)
      _writeInt(f, 1, event.velocity)
    elif isinstance(event, PolyphonicKeyPressureEvent):
      prefix = _concatPrefix(_STATUS_POLY_KEY_PRESS , event.channel)
      _writeInt(f, 1, prefix)
      _writeInt(f, 1, event.key)
      _writeInt(f, 1, event.velocity)
    elif isinstance(event, ControlChangeEvent):
      prefix = _concatPrefix(_STATUS_CONTROL_CHANGE, event.channel)
      _writeInt(f, 1, prefix)
      _writeInt(f, 1, event.controller)
      _writeInt(f, 1, event.value)
    elif isinstance(event, ProgramChangeEvent):
      prefix = _concatPrefix(_STATUS_PROGRAM_CHANGE, event.channel)
      _writeInt(f, 1, prefix)
      _writeInt(f, 1, event.value)
    elif isinstance(event, ChannelPressureEvent):
      prefix = _concatPrefix(_STATUS_CHANNEL_PRESS, event.channel)
      _writeInt(f, 1, prefix)
      _writeInt(f, 1, event.value)
    elif isinstance(event, PitchWheelChangeEvent):
      prefix = _concatPrefix(_STATUS_PITCH_WHEEL_CHANGE, event.channel)
      _writeInt(f, 1, prefix)
      _writeInt(f, 1, event.least)
      _writeInt(f, 1, event.most)

  def _writeMetaEvent(self, f, event):
    _writeInt(f, 1, _PREFIX_META)
    _writeInt(f, 1, event.metaType)
    _writeInt(f, 1, len(event.data))
    if event.data:
      f.write(event.data)

  def _writeSystemExclusiveEvent(self, f, event):
    _writeInt(f, 1, event.sysExType)
    _writeInt(f, 1, len(event.data))
    if event.data:
      f.write(event.data)
      
def _concatPrefix(status, channel):
  return (status << 4) + channel

def _writeInt(f, byteCount, n):
  for i in range(byteCount-1,-1,-1):
    f.write(chr((n >> (i*8) & 0xFF)))

def _writeVarLen(f, n):
  buff = []
  while True:
    byte = n & 0x7F
    buff.append(byte)
    n = n >> 7
    if n == 0:
      break

  buff = [buff[0]] + [byte | 0x80 for byte in buff[1:]]
  for byte in reversed(buff):
    f.write(chr(byte))
  
