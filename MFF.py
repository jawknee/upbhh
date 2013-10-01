#!/usr/bin/env python
"""
	Routines to emit MFF chunks

	Two types:  
		Header chunks - simple, 3 16-bit values
		Track chunks - one or more, variable length, 
		    various MIDI events
		    
	Essentially a repository for the data of the chunk, and an inherited set of
	routines (append, post, dump) for loading and outputting the data (Chunk class)
"""

class Chunk():
	def __init__(self):
		self.type = 'XXxx'
		self.data = ''

	def append(self, string):
		self.data += string

	def post(self,outfile):
		""" 
		put the chunk to a file
		"""
		# simple: output the type, length and data...
		outfile.write(self.type)
		length=len(self.data)
		outfile.write(word(length))
		outfile.write(self.data)

	def dump(self):
		"""
		Debug output...
		"""
		print "Chunk type:", self.type
		
		length=len(self.data)
		print "Len:", length, "/",
		for c in word(length):
			print " %02x" % ord(c),

		print "\nData:"
		i=0
		for c in self.data:
			print " %02x" % ord(c),
			i += 1
			if i == 32:
				print
				i=0

class Header_Chunk(Chunk):
	""" 
	Very simple, the header and 3 values passed in via the
	Init() function:
		format: 0, 1, 2
		tracks: 1 or more
		ppq: pulses per quarter note (typical 192)
	"""
	def __init__(self):
		self.type = 'MThd'
		self.data = ''

	def Init(self, fformat, tracks, ppq):
		self.append(half(fformat))
		self.append(half(tracks))
		self.append(half(ppq))

class Track_Chunk(Chunk):
	"""
	deceptively simple.  each event types knows how to "emit" itself
	into the track data list (a binary string)
	"""
	def __init__(self):
		self.type = 'MTrk'
		self.name = "No Name"
		self.track_num = 0
		self.data = ''
		self.tied = False	# is there a tie pending?
		# create a table of note off events for each "note" (<128 86 should be enough..)
		# We use these for tied notes...
		self.noteoff_list = [ 'None' for i in range(128) ]	 

	def end(self):
		# add the track end..
		delay = 1536	# arbitrary length at the end (8 quarter notes)
		self.append(vlq(delay))
		
		for c in [ 0xff, 0x2f, 0x00 ]:	# end of track..
			self.append(chr(c))

def vlq(value, mask=0x00):
	"""  
	Variable Length Quantity
	Returns a binary string of 1 - 4 bytes
	in standard variable length quantity.
	Bytes have a 7 digit value, high-order bit 
	indicates more data to come. Final byte
	does not have high order bit set.

	Yes: this one is a bit tricky.   Does work though.
	"""
	# Uses recursion to output the higher order bytes first.

	string = ''	# what we'll eventually return, a binary string
	if value < 0x80:
		val = value | mask
		if val not in range(256):
			print "WHAT???", val
		return(chr(val))
	else:
		string += vlq(value >> 7, 0x80)	# downshift 7 bits, call recursively
		
		val = (value & 0x7f) 	# fall through: call again with lower 7 bits, pass mask
		string += vlq(val, mask)

	return(string)

def int2chars(val, count):
	"""
	Turn a value into a binary byte stream of length count
	"""
	shift = count * 3 	# how many bits to shift for mask
	mask = ( 8 << shift ) -1 
	mval = val & mask
	if mval != val:
		print "Error: value too big for", count, "byte field", val, "Masked to:", mval
		val = mval
	string = ''
	for i in range (count-1 , -1, -1):	
		shift = i * 8
		n = val >> shift
		n = n & 0xff
		string += chr(n)
	return(string)
		
def word(val):
	""" 
	return a 4 byte value - e.g., length
	"""
	return(int2chars(val, 4))

	
def half(val):
	""" 
	return two bytes of characters from val
	"""
	return(int2chars(val,2))

"""
Debug:
"""
def main():
	outfile = open('testout.mid','w')

	print "Header:"
	head_chunk = Header_Chunk()
	head_chunk.Init(format=0, tracks=1, ppq=192)
	head_chunk.dump()


	track_chunk = Track_Chunk()	

	# tempo...
	track_chunk.append(vlq(0))
	track_chunk.append(chr(0xff))
	track_chunk.append(chr(0x51))
	track_chunk.append(chr(3))
	# time 0 / 1 / 244 = 500 = 120bpm
	track_chunk.append(chr(0))
	track_chunk.append(chr(1))
	track_chunk.append(chr(244))

	track_chunk.append(vlq(20))
	track_chunk.append(chr(0x90))
	track_chunk.append(chr(48))
	track_chunk.append(chr(90))

	track_chunk.append(vlq(511))
	track_chunk.append(chr(0x80))
	track_chunk.append(chr(48))
	track_chunk.append(chr(64))

	track_chunk.append(vlq(31))
	track_chunk.append(chr(0xFF))
	track_chunk.append(chr(0x2F))
	track_chunk.append(chr(0x00))
	

	print "\nTrack:"	
	track_chunk.dump()
	print "\n----"

	head_chunk.post(outfile)
	track_chunk.post(outfile)

	outfile.close()


if __name__ == "__main__":
	main()
	
