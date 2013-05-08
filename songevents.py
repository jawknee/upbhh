#!/usr/bin/env python
"""
	Song related classes.
	A song is a list of events, and some related functions related
	to creating MIDI File Format data.  Part of the Unplayed by Human Hands
	project of Prentiss Knowlton.
"""
import MFF
import key

def poskey(self):
	return (self.pos)	# lets us sort events based on the position

class Song:
	""" 
	Basically aA list of events (note, comment, etc.) and sorted list function.
	"""
	def __init__(self):
		self.events = []	# a list of events that defines the song
		self.key = key.Key()	# create key object: stores, processes key info
		self.track_count = 0	# number of tracks in this song 
		self.track_list = []	# where the tracks live..

	def append(self, event):
		"""
		Take an event, process as needed (notes) and append
		to the event list
		"""
		if event.type == "NOTE" or event.type == "NOTEOFF":
			self.key.adjust(event)	# take care of key / accidental adjustments
		self.events += [ event ]

	def clear_ties(self):
		for i in range(self.track_count):
			track = self.track_list[i]
			if track.tied:
				print "Warning: unresolved tie."
				track.tied = False
			
	def create_MFF(self, outfile, txt_file):
		""" 
		Create a MIDI File Format file - based on the events
	    	in the song object - output to previously opened file
		"""
	
		# We emit a header chunk and then one or more track chunks.
	
		# create head object, initialize, post to file...
		head = MFF.Header_Chunk()
		# initialze the hearder chunk values...
		head.Init(fformat=self.format, tracks=self.track_count, ppq=self.PPQ)

		#head.dump()	# debug output
		head.post(outfile)	# output the header
		
		# 
		# initialize a table of positions for each track,
		# at the same time - create an event for each track 
		# that sets the name
		
		track_pos = []
		for i in range(self.track_count):
			track_pos.append(0)		# where we are in each tack...
			name_ev = Meta_Event()	# "generic"
			name_ev.type = "TRACK NAME"
			name_ev.event_type = 0x03	# sequence/track name
			name_ev.data = self.track_list[i].name
			name_ev.track_num = i
			name_ev.pos = 0
			self.append(name_ev)

		self.events.sort(key=poskey)	# put the events in time order...

		track_index = 0

		for event in self.events:
			track_index = event.track_num
			diff = event.pos - track_pos[track_index]
			if diff < 0:
				print "Event / pos", event.pos, track_pos[track_index]
			track = self.track_list[track_index]
			track.append(MFF.vlq(diff))	# add the delta-time
			event.emit(track)		# add the event...
			track_pos[track_index]= event.pos
		
		print "Track count:", self.track_count
		for track_num in range(self.track_count):
			#print "Ending track", track_num
			self.track_list[track_num].end()
			#print "Posting track", track_num
			#self.track_list[track_num].dump()
			self.track_list[track_num].post(outfile)


	def list(self,mask=[ 'All' ]):
		""" list the events in time order
		"""
		self.events.sort(key=poskey)
		#print "mask", mask
		for e in self.events:
			if "All" in mask:
				return(e)
			elif e.type in mask:
				return(e)
class Event:
	"""
	Base class for events.  At a minimum, a type, a position, and a track number
	"""
	def __init__(self):
		self.type = "uninit"
		self.pos = 0
		self.track_num = 0
		
	def Info(self):	
		print "Event: type, pos, track#", self.type, self.pos, self.track_num


class Note(Event):
	"""
	Defines a note, and a method for emitting it to the file...
	"""
	def __init__(self):
		self.type = 'NOTE'
		self.dur = 0
		self.note = 0
		self.velocity = 96

	# put the note as bytes (3, or 2 with running status) 
	# into the passed track
	def emit(self, track):
		# note on is 0x90 
		channel = track.track_num & 0x0f	# simulate MIDI channel, round-robin
		cmd = 0x90 | channel
		track.append(chr(cmd))
		track.append(chr(self.note_num))
		track.append(chr(self.velocity))

class NoteOff(Event):
	"""
	Much like Note  but with a different command 
	"""
	def __init__(self):
		self.type = 'NOTEOFF'
		self.note = 0
		self.velocity = 96

	def emit(self, track):
		# note off is 0x80 or'd with MIDI channel
		channel = track.track_num & 0x0f	# simulate MIDI channel, round-robin
		cmd = 0x80 | channel
		track.append(chr(cmd))
		track.append(chr(self.note_num))
		track.append(chr(self.velocity))

class Volume(Event):
	"""
	A specific control change (7) for setting volume.
	"""
	def __init__(self):
		self.type = "VOLUME"
		self.volume = 96
		
	def emit(self, track):
		# MIDI Volume event - control change 7
		channel = track.track_num & 0x0f	# simulate MIDI channel, round-robin
		cmd = 0xB0 | channel		# control change
		track.append(chr(cmd))
		track.append(chr(7))	# '7' is the volume control change
		track.append(chr(self.volume))
		#print "Emitting Volume Event", self.volume, self.track_num, self.pos
	
class Meta_Event(Event):
	"""
	Generic meta event
	"""
	def __init__(self):
		self.type = "Generic Meta Event"
		self.event_type = 1	# default to a comment
		self.data = "None"
		self.track_num = 0
		
	def emit(self, track):
		""" 
		Can be called by most child methods 
		by filling in self.data as a string, setting self.type, 
		then calling: Meta_Event.emit(self, track)
		"""
		track.append(chr(0xff))		# all meta start with 0xff
		track.append(chr(self.event_type))
		track.append(MFF.vlq(len(self.data)))
		track.append(self.data)
		
class Comment(Meta_Event):
	def __init__(self):
		self.type = 'COMMENT'
		self.event_type = 1		# default: generic text type
		self.data = "Blank"
		
	def Info(self):
		print "Comment from", self.pos, self.comment


class Tempo(Meta_Event):
	"""
	Tempo - send out the data as noted - already computed
	"""
	
	def __init__(self):
		self.type = 'TEMPO'
		self.event_type = 0x51	# Tempo event
		self.t_val = 0			# a time value: microseconds per quarter note

	def emit(self, track):
		#print "Emitting Tempo Event", self.t_val, self.track_num, self.pos
		# 
		self.data = MFF.int2chars(self.t_val, 3) 	 # three byte value...
		# call the parent class...
		Meta_Event.emit(self, track)

class Time_Signature(Meta_Event):
	def __init__(self):
		self.type = "TIME SIGNATURE"
		self.event_type = 0x58
		self.track_num = 0
		self.numerator = 4
		self.denomintor = 4

	def emit(self, track):
		# Build up the fun bits of a tempo event...
		self.data = chr(self.numerator) 	# start off easy...
		self.ppq = 192
		#
		# the next value is the log-base2 of the number
		log = 0	# proposed value
		n = 1	# starting value
		d = self.denominator
		valid = False
		while n <= d:
			if n == d:	# we've found it...
				valid = True
				break	# "N" is the answer
			log += 1	# next power of 2
			n *= 2	# double it to the next power
		if not valid:
			print "Error: illegal denominator in time signature:", d, n, valid 
			return
		self.data += chr(log)
		
		# think that was tricky?  Now need to figure out how many pulses per "beat".
		# if the numerator is evenly divisible by 3, and the denominator is 8 or better (not 
		# sure I've ever seen 16) then divide by 2 (can't used dotted-quarter  3/2 of 192 is 
		# greater than 256)
		if self.numerator % 3 == 0 and d >= 8:
			ppb = self.ppq / 2	# pulses per beat: eighth note
		else:
			ppb = self.ppq
		
		self.data += chr(ppb)	# pulses per beat
		self.data += chr(8)		# notated 32nd notes per quarter
		
		#print "Time signature emit:", self.numerator, d, ppb 
		Meta_Event.emit(self, track)
			
class Key_Event(Meta_Event):	
		def __init__(self):
			self.type = "KEY"
			self.event_type = 0x59
			self.key = 0
			self.mode = 0	# default to Major mode, short of analyzing the notes, this is reasonable
			self.track_num = 0
			
		def emit(self, track):
			#print "Emitting key event", self.key, self.mode
			self.data = chr(self.key & 0xff)	# range -7 - +7,  mask to 8 bits
			self.data += chr(self.mode)
			
			Meta_Event.emit(self, track)
"""
Debug code...
"""
def main():
	print "Song test..."

	song = Song()

	etype = 'COMMENT'
	poslist = [ 9, 8, 7, 6, 5 ]
	for pos in poslist:
		for n in 'C', 'D', 'E', 'C':
			note = Event()
			note.Info()
			note.type = etype
			note.note = n
			note.pos = pos
			note.Info()
	
			song.events += [ note ]
	
			pos += 1

		if etype == 'COMMENT':
			etype='NOTE'
		elif etype == 'NOTE':
			etype='TEMPO'
		elif etype == 'TEMPO':
			etype = 'MISC'
	
	print "can we list them??"

	print "can we list them, sorted????"
	song.list()
	print "just notes?"
	mask = [ 'NOTE' ]
	song.list(mask)
	print "Comments??"
	mask =[ 'COMMENT' ] 
	song.list(mask)
	print "c & n "
	mask =[ 'COMMENT', 'NOTE' ] 
	song.list(mask)

if __name__ == "__main__":
	main()
