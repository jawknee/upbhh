#!/usr/bin/env python
"""
	Classes and functions to handle key signature as well as 
	accidentals
"""

class Key():
	"""
	Class to store and process key information.  Typically
	part of a song.  Adjust routines are called when a note
	is added to a song.
	"""
	def __init__(self):
		self.reset_accidentals()
		self.key_signature = 0
		self.set_key(0)
		# natural offset of each note... (0-6) -> (0-12)
		self.NOTE_OFFSET=[ 0, 2, 4, 5, 7, 9, 11 ] 

	def reset_accidentals(self):
		"""
		resets all of the accidentals, called at the end of each measure
		"""
		self.accidentals = [ 'None' for n in range(128) ]
		#print "accidentals reset"
	
	def set_key(self, key):
		"""
		A little tricky:  key is in the range -7 to 7, with 0
		being C major / A minor - no sharps or flats.  Positive values
		are sharp keys, negative value are flat.  Flat keys are 
		reverse indexed from the end.  Setting the key table then
		consists of zeroing the 7 note entries, then putting the -1 or 
		+1 adjustment into the proper spots - indexing up or down until
		we get to C (0).

		Has the added feature that bizarre keys like 8 or 9 
		sharps or flats actually work
		"""
		key_master = [ 
			0,	# 0 C, no #/b   
			3,	# +1 G:  F -> F3  
			0,	# +2 D:  C -> C#  
			4,	# +3 A:  G -> G#  
			1,	# +4 E:  D -> D#  
			5,	# +5 B:  A -> A#  
			2,	# +6 F#: E -> E# (F)  
			6,	# +7 C#: B -> B# (C)  
  
			3,	# -7 Cb: F -> Fb (E)  
			0,	# -6 Gb: C -> Cb (B)  
			4,	# -5 Db: G -> Gb  
			1,	# -4 Ab: D -> Db  
			5,	# -3 Eb: A -> Ab  
			2,	# -2 Bb: E -> Eb  
			6,	# -1 F:  B -> Bb  
			]

		""" 
		Set the key via the table 
		"""
		self.key_table = [ 0 for n in range(7) ]

		if key < -9 or key > 9:		# odd, but they should work...
			print "Error: Key out of range (-7-7):", key
			return
		
		if key == 0:
			return

		sign = key / abs(key)	# +1 or -1

		for i in range(key, 0, -sign):
			self.key_table[key_master[i]] = sign

	
	def show_key_table(self):
		for i in range(6):
			print "Note/adj:", i, self.key_table[i]
	def show_acc(self):
		for i in range(128):
			print "key", i, self.accidentals[i] 
	def set_accidental(self, octave, note, key_value):
		""" convert note and octave to an index into the
		    accidentals table
		"""
		index = octave * 12 + note
		self.accidentals[index] = key_value
		#print "Accidental set:", index, key_value
	def adjust(self, note):
		"""
			take a note/noteoff object which has an octave and note
			(0-7) and convert it to a MIDI note number...
		"""

		if note.key != self.key_signature:
			self.key_signature = note.key
			self.set_key(note.key)
			#print "setting key to", note.key

		adj = self.key_table[note.note]

		key_num = note.note + note.octave * 12	# index into accidental table

		note_num = self.NOTE_OFFSET[note.note] + note.octave * 12

		accidental = self.accidentals[key_num]

		if accidental != 'None':
			adj = accidental	# override any key adjustment..

		note.note_num = note_num + adj
		#print "Adjust: note / Octave / num / adj", note.note, note.octave, note.note_num, adj


def main():
	key = Key()
	key.show_acc()
	key.accidentals[120] = 3
	key.show_acc()
	key.reset_accidentals()
	key.show_acc()

	for i in range(-7,8):
		#print "key:", i
		key.set_key(i)
		key.show_key_table()
	

if __name__ == "__main__":
	main()
