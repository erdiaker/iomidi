iomidi
==============

Python library for basic MIDI input and output. 

## Installation

You can install via [PyPI](https://pypi.python.org/pypi) by typing the
following in your terminal:
```sh
pip install iomidi
```

## Examples

### Creating a MIDI file

```python
import iomidi

# A MIDI file consists of one or more MIDI tracks.
# Create an empty track.
track = iomidi.MIDITrack()

# A MIDI track is a series of one or more events.
# Create some events.
pressC = iomidi.NoteOnEvent(
  delta=100,    # time to wait after the previous event in terms of ticks
  channel=0,    # midi channel
  key=60,       # midi note, 60 is middle C
  velocity=100) # pressure of the key press

releaseC = iomidi.NoteOffEvent(
  delta=1100,
  channel=0,
  key=60,
  velocity=0)

# Add these events to the track.
track.addEvent(pressC)
track.addEvent(releaseC)

# Add a meta event to denote the end of track
endOfTrack = iomidi.EndOfTrackEvent(delta=1)
track.addEvent(endOfTrack)

# Create a MIDI structure, put the track in it.
midi = iomidi.MIDI(tracks=[track])

# Write the midi structure into a file.
iomidi.write('simple.mid', midi)
```

### Loading a MIDI file

```python
import iomidi

midi = iomidi.read('simple.mid')

print(midi)
```

## License
MIT

