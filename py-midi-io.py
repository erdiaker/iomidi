
from collections import namedtuple
from pprint import pprint

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

NoteOffEvent = namedtuple('NoteOffEvent', \
  'delta channel key velocity')
NoteOnEvent = namedtuple('NoteOnEvent', \
  'delta channel key velocity')
PolyphonicKeyPressureEvent = namedtuple('PolyphonicKeyPressureEvent', \
  'delta channel key velocity')
ControlChangeEvent = namedtuple('ControlChangeEvent', \
  'delta channel controller value')
ProgramChangeEvent = namedtuple('ProgramChangeEvent', \
  'delta channel value')
ChannelPressureEvent = namedtuple('ChannelPressureEvent', \
  'delta, channel value')
PitchWheelChangeEvent = namedtuple('PitchWheelChangeEvent', \
  'delta channel least most')

#-----------------------------------------------
# Meta Events

EndOfTrackEvent = namedtuple('EndOfTrackEvent', 'delta')

#-----------------------------------------------
# System Exclusive Events

class SystemExclusiveEvent:
  pass

#-----------------------------------------------
# MIDI chunks

class MIDIHeader:
  def __init__(self, frmt, division, trackCount):
    self.frmt = frmt
    self.division = division
    self.trackCount = trackCount

class MIDITrack:
  def __init__(self):
    self.events = []

  def addEvent(self, event):
    self.events.append(event)

class MIDIFile:
  def __init__(self, header, tracks):
    self.header = header
    self.tracks = tracks
   
#-----------------------------------------------
# MIDI Reader

class MIDIReader:

  def readFromFile(self, fileName):
    with open(fileName, 'rb') as f:
      header = self._readHeader(f)
      tracks = []
      for i in range(header.trackCount):
        track = self._readTrack(f)
        tracks.append(track)
    return MIDIFile(header, tracks)

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
    f.read(length) #TODO: implement.
    return SystemExclusiveEvent(delta)
   
  def _readMetaEvent(self, delta, prefix, f):
    metaType = _readInt(f, 1)
    length = _readVarLen(f)
    f.read(length) #TODO: implement.
    if metaType == 0x2F:
      event = EndOfTrackEvent(delta)
    else:
      event = MetaEvent() #TODO: handle.
    return event

  def _readMIDIEvent(self, delta, prefix, f):
    status = prefix >> 4
    channel = prefix & 0xF
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
    retVal = retVal << 8
    byte = ord(f.read(1))
    retVal += byte & 0x7F
    # if the 8th bit of the last byte is 0, stop reading.
    if (byte >> 7) == 0:
      break
  return retVal

#-----------------------------------------------
# MIDI Writer

# TODO
class MIDIWriter:
  pass

def _writeInt(f, byteCount, n):
  for i in range(byteCount):
    f.write(chr((n >> (i*8) & 0xFF)))

def _writeVarLen(f, n):
  bits = n & 0x7F
  f.write(chr(bits))
  n = n >> 7

  while n > 0: 
    bits = (n & 0x7F) | 0x80
    f.write(chr(bits))
    n = n >> 7


#-----------------------------------------------
# Test

# TODO
def _test():
  mr = MIDIReader()
  mf = mr.readFromFile('example.mid')
  for track in mf.tracks:
    for event in track.events:
      pprint(event)

if __name__ == '__main__':
  _test()

  
