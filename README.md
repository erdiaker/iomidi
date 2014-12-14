iomidi
==============

This is a Python library for basic MIDI input and output.

## Installation

Clone this repository in a directory of your choice:

```sh
git clone https://github.com/erdiaker/iomidi.git
```

It should create a directory named `iomidi`. Enter the directory, and install the package by typing the following:

```sh
cd iomidi
python setup.py install
```

This should install `iomidi` in your `site-packages` directory. 

## Examples

### Creating a MIDI track

```python
from iomidi import *

# A MIDI file consists of one or more MIDI tracks.
# Create an empty track.
track = MIDITrack()

# A MIDI track is a series of one or more events.
# Create some events.
pressC = NoteOnEvent(
  delta=100,    # time to wait after the previous event in milliseconds
  channel=0,    # midi channel
  key=60,       # midi note, 60 is middle C
  velocity=100) # pressure of the key press

releaseC = NoteOffEvent(
  delta=1100,
  channel=0,
  key=60,
  velocity=0)

# Add these events to the track.
track.addEvent(pressC)
track.addEvent(releaseC)

# Add a meta event to the denote the end of track
endOfTrack = EndOfTrackEvent(delta=1)
track.addEvent(endOfTrack)

# Create a MIDI structure with the track.
midi = MIDI(tracks=[track])

# Write the midi structure into a file.
writer = MIDIWriter()
writer.write('simple.mid', midi)
```

### Loading a MIDI file

```python
from iomidi import *

reader = MIDIReader()
midi = reader.read('simple.mid')

print midi.tracks[0].events
```

## License
MIT

