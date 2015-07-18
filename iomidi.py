
import io
import json

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
# Mixins

class RepresentMixin(object):
  def __repr__(self):
    s = '{\'%s\': %r}' % (self.__class__.__name__, self.__dict__)
    s = s.replace('\'', '\"')
    return json.dumps(json.loads(s), indent=2)

#-----------------------------------------------
# MIDI Events

class MIDIEvent(RepresentMixin):
  def __init__(self, delta, channel):
    self.delta = delta
    self.channel = channel

class NoteOffEvent(MIDIEvent):
  def __init__(self, delta, channel, key, velocity): 
    super(NoteOffEvent, self).__init__(delta, channel)
    self.key = key
    self.velocity = velocity

class NoteOnEvent(MIDIEvent):
  def __init__(self, delta, channel, key, velocity): 
    super(NoteOnEvent, self).__init__(delta, channel)
    self.key = key
    self.velocity = velocity

class PolyphonicKeyPressureEvent(MIDIEvent):
  def __init__(self, delta, channel, key, velocity):
    super(PolyphonicKeyPressureEvent, self).__init__(delta, channel)
    self.key = key
    self.velocity = velocity

class ControlChangeEvent(MIDIEvent):
  def __init__(self, delta, channel, controller, value):
    super(ControlChangeEvent, self).__init__(delta, channel)
    self.controller = controller
    self.value = value

class ProgramChangeEvent(MIDIEvent):
  def __init__(self, delta, channel, value):
    super(ProgramChangeEvent, self).__init__(delta, channel)
    self.value = value

class ChannelPressureEvent(MIDIEvent):
  def __init__(self, delta, channel, value):
    super(ChannelPressureEvent, self).__init__(delta, channel)
    self.value = value

class PitchWheelChangeEvent(MIDIEvent): 
  def __init__(self, delta, channel, least, most):
    super(PitchWheelChangeEvent, self).__init__(delta, channel)
    self.least = least
    self.most = most

#-----------------------------------------------
# Meta Events

class MetaEvent(object):
  def __init__(self, delta, metaType, data, **kwargs):
    self.delta = delta
    self.metaType = metaType
    self.data = data

  def __repr__(self):
    # TODO: "data" may break repr(), since json.dumps() is used for formatting.
    # Escape it properly, then put back on repr().
    # Same for SystemExclusiveEvent.
    d = dict(self.__dict__) # copy
    del d['data']
    return '{\'%s\': %r}' % (self.__class__.__name__, d)

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
    #TODO: see MetaEvent.
    d = dict(self.__dict__)
    del d['data']
    return '{\'%s\': %r}' % (self.__class__.__name__, d)

#-----------------------------------------------
# MIDI chunks

class MIDIHeader(RepresentMixin):
  def __init__(self, frmt=1, division=220, trackCount=0):
    self.frmt = frmt
    self.division = division
    self.trackCount = trackCount

class MIDITrack(RepresentMixin):
  def __init__(self):
    self.events = []

  def addEvent(self, event):
    self.events.append(event)

class MIDI(RepresentMixin):
  def __init__(self, header=None, tracks=None):
    self.header = header if header else MIDIHeader()
    self.header.trackCount = len(tracks) if tracks else 0
    self.tracks = tracks
   
#-----------------------------------------------
# MIDI Reader

class MIDIReader(object):
  def __init__(self):
    self._runningStatus = 0
    self._byteCount = 0

  def read(self, fileName):
    with open(fileName, 'rb') as f:
      header = self._readHeader(f)
      tracks = []
      for i in range(header.trackCount):
        track = self._readTrack(f)
        tracks.append(track)
    return MIDI(header=header, tracks=tracks)

  def _readHeader(self, f):
    buff = self._readBlock(f, 4)
    if buff != _CHUNK_TYPE_HEADER:
      raise MIDIIOError('Invalid MIDI header identifier.')

    length = self._readInt(f, 4)
    frmt = self._readInt(f, 2)
    trackCount = self._readInt(f, 2)
    division = self._readInt(f, 2)
    # consume remainder (for non-standard headers)
    self._readBlock(f, length - 6)

    return MIDIHeader(frmt, division, trackCount)

  def _readTrack(self, f):
    buff = self._readBlock(f, 4)
    if buff != _CHUNK_TYPE_TRACK:
      raise MIDIIOError('Invalid MIDI track identifier.')

    length = self._readInt(f, 4)
    track = MIDITrack()

    while True:
      event = self._readEvent(f)
      track.addEvent(event)
      if isinstance(event, EndOfTrackEvent):
        break
    return track

  def _readEvent(self, f):
    delta = self._readVarLen(f)
    prefix = self._readInt(f, 1)

    if prefix == _PREFIX_SYSEX or prefix == _PREFIX_SYSEX_NOXMIT:
      event = self._readSystemExclusiveEvent(delta, prefix, f)
    elif prefix == _PREFIX_META:
      event = self._readMetaEvent(delta, prefix, f)
    else:
      event = self._readMIDIEvent(delta, prefix, f)
    return event

  def _readSystemExclusiveEvent(self, delta, prefix, f):
    length = self._readVarLen(f)
    data = self._readBlock(f, length)
    return SystemExclusiveEvent(delta, prefix, data)
   
  def _readMetaEvent(self, delta, prefix, f):
    metaType = self._readInt(f, 1)
    length = self._readVarLen(f)
    data = self._readBlock(f, length)
    if metaType == _META_END_OF_TRACK:
      event = EndOfTrackEvent(delta)
    else:
      event = MetaEvent(delta, metaType, data)
    return event

  def _readMIDIEvent(self, delta, prefix, f):
    # use the status of the last event,
    # if the current status is not set.
    if (prefix >> 7) & 1:
      self._runningStatus = prefix
    else:
      prefix = self._runningStatus
      f.seek(-1, io.SEEK_CUR)
      self._byteCount -= 1 # TODO: wrap it

    status = prefix >> 4
    channel = prefix & 0xF

    if status == _STATUS_NOTE_OFF:
      key = self._readInt(f, 1) 
      vel = self._readInt(f, 1)
      event = NoteOffEvent(delta, channel, key, vel)
    elif status == _STATUS_NOTE_ON:
      key = self._readInt(f, 1) 
      vel = self._readInt(f, 1)
      event = NoteOnEvent(delta, channel, key, vel)
    elif status == _STATUS_POLY_KEY_PRESS:
      key = self._readInt(f, 1) 
      val = self._readInt(f, 1)
      event = PolyphonicKeyPressureEvent(delta, channel, key, val)
    elif status == _STATUS_CONTROL_CHANGE:
      controller = self._readInt(f, 1)
      val = self._readInt(f, 1)
      event = ControlChangeEvent(delta, channel, controller, val)
    elif status == _STATUS_PROGRAM_CHANGE:
      val = self._readInt(f, 1)
      event = ProgramChangeEvent(delta, channel, val)
    elif status == _STATUS_CHANNEL_PRESS:
      val = self._readInt(f, 1)
      event = ChannelPressureEvent(delta, channel, val)
    elif status == _STATUS_PITCH_WHEEL_CHANGE:
      least = self._readInt(f, 1)
      most = self._readInt(f, 1)
      event = PitchWheelChangeEvent(delta, channel, least, most)

    return event

  def _readInt(self, f, byteCount):
    buff = f.read(byteCount)
    retVal = 0
    for byte in buff: #TODO: byte is '\0'
      retVal = retVal << 8
      retVal += ord(byte)
    self._byteCount += byteCount
    return retVal

  def _readVarLen(self, f):
    retVal = 0
    while True:
      retVal = retVal << 7
      byte = ord(f.read(1))
      retVal += byte & 0x7F
      self._byteCount += 1
      # if the 8th bit of the last byte is 0, stop reading.
      if (byte >> 7) == 0:
        break
    return retVal

  def _readBlock(self, f, byteCount):
    self._byteCount += byteCount
    return f.read(byteCount)

#-----------------------------------------------
# MIDI Writer

class MIDIWriter(object):
  def write(self, fileName, midi):
    with open(fileName, 'wb') as f:
      self._writeHeader(f, midi.header)
      for track in midi.tracks:
        self._writeTrack(f, track)

  def _writeHeader(self, f, header):
    self._writeBlock(f, _CHUNK_TYPE_HEADER)
    self._writeInt(f, 4, 6)
    self._writeInt(f, 2, header.frmt) 
    self._writeInt(f, 2, header.trackCount) 
    self._writeInt(f, 2, header.division) 

  def _writeTrack(self, f, track):
    self._writeBlock(f, _CHUNK_TYPE_TRACK)

    buff = io.BytesIO()
    for event in track.events:
      self._writeEvent(buff, event)

    self._writeInt(f, 4, len(buff.getvalue()))
    self._writeBlock(f, buff.getvalue())

  def _writeEvent(self, f, event):
    self._writeVarLen(f, event.delta)
    if isinstance(event, SystemExclusiveEvent):
      self._writeSystemExclusiveEvent(f, event)
    elif isinstance(event, MetaEvent):
      self._writeMetaEvent(f, event)
    else:
      self._writeMIDIEvent(f, event)

  def _writeMIDIEvent(self, f, event):
    if isinstance(event, NoteOffEvent):
      prefix = self._concatPrefix(_STATUS_NOTE_OFF, event.channel)
      self._writeInt(f, 1, prefix)
      self._writeInt(f, 1, event.key)
      self._writeInt(f, 1, event.velocity)
    elif isinstance(event, NoteOnEvent):
      prefix = self._concatPrefix(_STATUS_NOTE_ON, event.channel)
      self._writeInt(f, 1, prefix)
      self._writeInt(f, 1, event.key)
      self._writeInt(f, 1, event.velocity)
    elif isinstance(event, PolyphonicKeyPressureEvent):
      prefix = self._concatPrefix(_STATUS_POLY_KEY_PRESS , event.channel)
      self._writeInt(f, 1, prefix)
      self._writeInt(f, 1, event.key)
      self._writeInt(f, 1, event.velocity)
    elif isinstance(event, ControlChangeEvent):
      prefix = self._concatPrefix(_STATUS_CONTROL_CHANGE, event.channel)
      self._writeInt(f, 1, prefix)
      self._writeInt(f, 1, event.controller)
      self._writeInt(f, 1, event.value)
    elif isinstance(event, ProgramChangeEvent):
      prefix = self._concatPrefix(_STATUS_PROGRAM_CHANGE, event.channel)
      self._writeInt(f, 1, prefix)
      self._writeInt(f, 1, event.value)
    elif isinstance(event, ChannelPressureEvent):
      prefix = self._concatPrefix(_STATUS_CHANNEL_PRESS, event.channel)
      self._writeInt(f, 1, prefix)
      self._writeInt(f, 1, event.value)
    elif isinstance(event, PitchWheelChangeEvent):
      prefix = self._concatPrefix(_STATUS_PITCH_WHEEL_CHANGE, event.channel)
      self._writeInt(f, 1, prefix)
      self._writeInt(f, 1, event.least)
      self._writeInt(f, 1, event.most)

  def _writeMetaEvent(self, f, event):
    self._writeInt(f, 1, _PREFIX_META)
    self._writeInt(f, 1, event.metaType)
    self._writeInt(f, 1, len(event.data))
    if event.data:
      self._writeBlock(f, event.data)

  def _writeSystemExclusiveEvent(self, f, event):
    self._writeInt(f, 1, event.sysExType)
    self._writeInt(f, 1, len(event.data))
    if event.data:
      self._writeBlock(f, data)
      
  def _concatPrefix(self, status, channel):
    return (status << 4) + channel

  def _writeInt(self, f, byteCount, n):
    for i in range(byteCount-1,-1,-1):
      f.write(chr((n >> (i*8) & 0xFF)))

  def _writeVarLen(self, f, n):
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

  def _writeBlock(self, f, data):
    f.write(data)
  
#-----------------------------------------------
# Module functions

def read(fileName):
  reader = MIDIReader()
  return reader.read(fileName)

def write(fileName, midi):
  writer = MIDIWriter()
  writer.write(fileName, midi)

