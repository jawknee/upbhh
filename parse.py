#!/usr/bin/env python
"""
	Routines to convert the file format from Prentiss Knowlton's music
	format from his Unplayed by Human Hands project into MIDI FIle Format
	
	The parse function scans the file, character by character, building a song, 
	which is a list of events.  Events can be notes, tempo changes, comments or 
	whatever else maps to MFF events.  
"""


import songevents
import MFF

def getnum(string):
	""" 
	pull the next number off the current substring, 
	returns a tuple of the number and the offset into
	the string of the first non-digit.
	"""

	i=0
	nstr=''
	c=string[i]
	while c in '0123456789':
		nstr=nstr + c
		i+=1
		c=string[i]	# next char in string..
	try:
		n=int(nstr)
	except ValueError, info:
		raise ValueError(info)	# handled at higher level
	return (n,i)

uS_PER_MINUTE = 60 * 1000000	# microseconds per minute

def mk_tempo_event(song, tempo, pos, q_dur, n_dur):
	"""
	Create a tempo event in the song at the specified
	position.  Tempo is output as microseconds
	per quarter note.  The value entered is "current 
	note" durations per minute).  The calculation below
	makes that conversion.  (q_dur => quarter note duration,
	n_dur => current note duration)
	"""
			
	tempo_event = songevents.Tempo()	# new tempo event
	tempo_event.track_num = 0	# Always
	tempo_event.pos = pos
	# uS_PER_MINUTE = 60000000
	t_val = (uS_PER_MINUTE / tempo) * q_dur / n_dur
	tempo_event.t_val = int(t_val * song.time_factor)  # tempo correction for sync
	#print "Tempo event b/a/f:", t_val, tempo_event.t_val, song.time_factor
	# 
	#print "Tempo set to", tempo, "value:", tempo_event.t_val
	song.append(tempo_event)
		
def mk_volume_event(song, volume, pos, track_num):
	"""
	Create a volume event - simplifies the volume ramping...
	"""
	#print "mve:", volume, pos, track_num
	vol_event=songevents.Volume()		# new volume event...
	vol_event.pos = pos
	vol_event.track_num = track_num
	vol_event.volume = volume
				
	song.append(vol_event)
		
def parse_song(filename, song):
	"""
	We read the file into a string and them step through it
	dealing with the characters in a loop, processing them
	through a long if statement..

	At the end we have a song object that contains a long 
	list of events: notes, tempo changes, comments, etc.
	"""
	
	staccato = False
	fermata = False
	fermata_add = 0
	accidental = 'None'
	tuplet = False
	#tied... ties are kept on a per-track basis
	solo = False
	ended = False
	grouping = False
	tempo = 120
	uS_per_quarter = uS_PER_MINUTE / tempo 	# (500000 -> microseconds per quarter note)
	volume = 96		# default starting value...
	
	key = 0
	song.measure_num = 0
	last_measure = 0
	group_length = 0
	position = 0	# where are we in the "song" in pulses
	ramp_duration = 0
	current_track = 'None'
	track_list = ''

	# some constants
	# Note / pitch specific
	NOTES='CDEFGAB'		# 'C' is the first note of each octave
	OCTAVES='0123456789'	# octave specifier C4 = middle C	
	OCT_OFFSET = 1		# MIDI Octave adjust
	ACCIDENTALS = '!%#'	# flat, natural, sharp
	
	# Note duration...
	DURATIONS='WHQISTX'     # Whole, Half, Quarter, eIgth, Sixteenth, Thirty-second, siXty-fourth
	DUR_NAMES=[ 'Whole', 'Half', 'Quarter', 'Eighth', 'Sixteenth', 'Thirty-second', 'Sixty-fourth' ]

	# Divisions - these map to tracks in the MIDI file
	DIVISIONS='U*:JLMY@P\\'	# Characters to specify division (note: \\ a single backslash at end)
	DIV_NAMES=[ 'Great Division', 'Positiv Division', 'Pedal Division', 'Swell I Division',
		'Swell II Division', 'Unknown Division', 'Antiphonal Division', 'Trompeta Real', 
		'Chimes', 'PDP-8 Electronic Division' ]

	IGNORE=' \n'
	STOP='Z'

	#
	# First tricky bit...  create a dictionary of pulse values for each of the 
	# durations.  Start with a whole note (4 quarters) and divide by two for
	# each of the subsequent notes.  (Saves us doing an exponential each time)
	note_durations={}	
	pulses=song.PPQ * 4 	# length of a whole note...
	for c in DURATIONS:
		note_durations[c]=pulses
		pulses=pulses/2
	duration = song.PPQ 		# just to get rid of the warning - assigned on the fly...
	staccato_dur = duration / 2

	#for c in DURATIONS:
	#	print "Duration of note", c, "is", note_durations[c]

	measure_length = song.PPQ * 4	# initial for any "pre" measures...
	
	infile = open(filename)
	text = infile.read()	# the entire file
	for x in '\r', '\n':	# convert cr/lf to space
		text = text.replace(x,' ')	# convert to space

	# create the initial track (or for format 0, the only track)
	track_num = 0
	
	track = MFF.Track_Chunk()
	track.name = "Track 0 - Tempo, etc."
	song.track_list.append(track)
	song.track_count += 1
	
	i=0	# index into the text string, which is the enire file
	length=len(text)

	while i < length:
		# Now we step through the file, looking at each letter,
		# creating an event (note, tempo, etc.) as we go...
		# the expectation is that the 'Z' end character will show up before 
		# this loop ends.   
		#
		# we just check each letter, keep track of the data, and creating "events", 
		# which can be notes, comments, tempo changes, as needed.  Comments can be 
		# generated as they are encountered.   Tempo changes as well, and gradual 
		# accellerations / decellerations,volume changes can be emitted at once.
		# Notes are bit different, we have to peak ahead for a possible octave value.
		# When we create the note, we also created a note-off event.  When tied to 
		# another note, the note-off is moved forward in time.
		#
		c=text[i]	# next character...
		i+=1
		#
		# --------------------Note: pitch and timing
		#
		# Note  - start a new note...
		if c in NOTES:

			#  Create a new note... - set the note, position, key and duration 
			this_note = NOTES.find(c)

			# The note could be followed by an octave specifier....
			# peek ahead 
			o = text[i] # check for possible octave
			if o in OCTAVES:
				#print "Following octave found:", o
				octave = int(o) + OCT_OFFSET
				i += 1	# next char...
			else:	# octave set?
				try:
					o = octave	
				except NameError:
					#print "Error: octave not set before note"
					octave = 5
			# Is this a tied note?  If so, we do not generate a new note, we find the note-off
			# we already generated, and add the current note duration to its position
			if current_track.tied:
				tied_event = song.track_list[track_num].noteoff_list[octave*12+this_note]
				if  tied_event != 'None':
					tied_event.pos += duration
					current_track.tied = False
					#print "Tying note", track_num, tied_event.pos
				
			else:
					
				note_ev = songevents.Note()	# new note event...
				note_ev.note = this_note	# 0-6 - note value w/i octave
				note_ev.key = key
				note_ev.dur = duration
				note_ev.pos = position
				note_ev.track_num = track_num
	
				#print "New note Accidental:", accidental
	
				#
				note_ev.octave = octave
	
				#print 'emitting note: ', c, "#/octave", note_ev.note, note_ev.octave, "pos:", note_ev.pos, "duration:", duration, note_ev.dur, "track:", track_num
				if accidental != 'None':
					#print "Setting accidental:",  note_ev.octave, note_ev.note, accidental
					song.key.set_accidental(note_ev.octave, note_ev.note, accidental)
					accidental = 'None'
	
				song.append(note_ev)
	
				noteoff=songevents.NoteOff()	# new note-off
				if staccato:
					note_len = staccato_dur
				elif fermata:
					fermata_add = duration	# add to note, and to measure 
					note_len = duration + fermata_add
					
				else:
					note_len = note_ev.dur - 1	# to prevent collisions / stuck notes
				noteoff.pos = note_ev.pos + note_len
				noteoff.octave = note_ev.octave
				noteoff.note = note_ev.note
				noteoff.key = note_ev.key
				noteoff.track_num = track_num
	
				#print 'emitting note off: ', this_note, "#/octave", note_ev.note, note_ev.octave, "pos:", noteoff.pos
				# now... add the note off to this track's note-off list for possible ties
				song.track_list[track_num].noteoff_list[octave*12+this_note] = noteoff # this event
	
				song.append(noteoff)	# add the note off...


			# Update position...
			if grouping:
				#print "Grouping (note) - don't advance..."
				# The length of a group is the length of the shortest note...
				if group_length > duration:
					group_length = duration
					#print "group len", group_length
			else:
				position += duration
				#print "New, post note, position:", position
		
		#
		# Rest - a note with out all the work
		#   - just move the pointer forward...
		#
		elif c == 'R':
			#print "Rest"
			if grouping:
				# The length of a group is the length of the shortest note...
				#print "Grouping (rest) - don't advance..."
				if group_length > duration:
					group_length = duration
					#print "group len", group_length
			else:
				position += duration
				#print "New, post rest, position", position
		#
		#
		#  ------------------------Pitch:  octave, accidentals, key
		#
		# Octave 
		#
		elif c in OCTAVES:
			octave=int(c) + OCT_OFFSET	# we know it's a digit...
			#print 'octave: ', c, octave

		
		#
		# Accidentals...
		#
		elif c in ACCIDENTALS:
			#print "Accidental found:", c, "this note", this_note
			# ! => flat, # => sharp, % => natural
			# set the value for the current note to -1, 0, or 1
			accidental = ACCIDENTALS.find(c) - 1	# -1 => flat, 0 => natural +1 => flat
			#print "setting Accidental:", accidental
			# This will be processed at the next note...
		#
		#  Key...
		#
		elif c == 'K':		# new key...
			try:
				c=text[i]
				k=int(c)
			except ValueError, info:
				print "ERROR: Expected a digit for key, got:", c, "- Info:", info
			else:
				if k == 0:	
					key=0	# key of C (Am)
				else:	#only parse the flat/sharp if the key is not C (0)
					i+=1
					c = text[i]
					
					if c == '#':	# sharp key
						key=k
					elif c == '!':	# flat key - negative...
						key=-k
					else:
						print "ERROR: Expected # or ! for key, got:", c
						key=0	# kludge to prevent a blowup on the print...
				#print "Key set to", key
				key_event = songevents.Key_Event()	# new key event...
				key_event.key = key
				key_event.pos = position

				song.append(key_event)
			i+=1
		#
		#
		# -------   Timing: note duration, tuplets, staccato, fermata
		#
		# Note durations... whole, half, quarter, etc.
		#
		elif c in DURATIONS:
			duration=note_durations[c]
			if tuplet:
				duration = duration * 2 / tuplet
			half_dur=duration / 2	# for dotted notes...
			staccato_dur=half_dur	# about right most of the time.

			index=DURATIONS.find(c)	# index into the names list...
			#print 'Duration: ', c, '/', DUR_NAMES[index], ', duration:',  note_durations[c]
				
			if staccato:
				staccato = False
				#print "Staccato is:", staccato
			if fermata:
				fermata = False
				#print "Fermata is:", fermata
		#
		# Dot... (add half)
		elif c == ".":
			try:
				d=duration	# is it set yet?
			except:
				print "ERROR: Dot found before duration set - check file format"
			else:
				duration+=half_dur
				half_dur = half_dur / 2	# for a subsequent dot...
				#print "dot: duration is", duration

		elif c == "'":	# tuplets...
			if tuplet:
				tuplet = False
				#print "Tuplet ended."
			else:
				try:
					(tuplet, offset) = getnum(text[i:]) 
				except ValueError, info:
					print "Tuplet value not found...", info
				#else:
					#duration = duration * 2 / tuplet # only if no dur specified at start of tuplet
					#print "Tuplet started:", tuplet
				i += offset
		#
		# Duration modifiers...
		#
		# Staccato..
		elif c == '^':		
			staccato=True	# shorter note
			#print "Staccato is:", staccato
		# Fermata...
		elif c == '?':
			fermata=True	# longer note (and measure)
		#
		# Tie...
		# This one's a bit tricky as we've already created the event, but
		# here we just set the flag.  The Note code will deal with it
		elif c == '&':
			#print "TIE!"
			current_track.tied = True
		#
		#
		# ------------------   Timing: tempo, time signature
		#
		# Tempo 
		# 
		elif c == '=':
			try:
				(new_tempo, offset)=getnum(text[i:])
			except ValueError, info:
				#print "Expected to find a number for tempo,", info
				continue

			i+=offset	# point to the next char...
			
			# tempo is in "beats" per minute, where beats is the
			# current duration.  The value we store is microseconds per
			# quarter note.  So:
			# We take microseconds per minute, divide by tempo, then correct
			# with  a factor of a quarter note / current note...
			#
			# If ramp_duration is set - we issue a series of events going forward in 
			# time (they'll be sorted into the correct order later).   If ramp_duration
			# is zero, we make one.
			q_dur = note_durations['Q']	# duration of a quarter note
			n_dur = duration			# duration of current note 							]
			if ramp_duration == 0:
				mk_tempo_event(song, new_tempo, position, q_dur, n_dur)
			else:
				# calculate a reasonable increment for the position / tempo increment,
				# then create a series of events...
				t_diff = new_tempo - tempo
				if t_diff == 0:
					#print "Warning: tempo ramp specified with no change: dur/tempo", ramp_duration, tempo, new_tempo
					ramp_duration = 0
					continue	# no change
				t_size = abs(t_diff)
				t_sign = t_diff / t_size	# -1 or +1 
				
				# let's assume there will be many more pulses than tempo points 
				# so issue a tempo event for tempo point change
				pos = position
				dur_incr = ramp_duration / t_size
				for t in range(tempo, new_tempo, t_sign):
					mk_tempo_event(song, t, pos, q_dur, n_dur)
					pos += dur_incr 
				mk_tempo_event(song, new_tempo, position+ramp_duration, q_dur, n_dur)
			tempo = new_tempo
			ramp_duration = 0
	

		#
		# Time Signature (Meter) - generates an event...
		#
		elif c == '$':	# meter change...  (n)n-m   where nn is numerator, m denom

			try:
				(ts_num, offset) = getnum(text[i:])
			except ValueError, info:
				ts_num=4
				print "Expected time signature number, got:", str, info
				print "Assuming:", ts_num

			i += offset + 1 	# past the "-"
			try:
				(ts_denom, offset) = getnum(text[i:])
			except ValueError, info:
				ts_denom=4
				print "Expected a time signature denominotor, got:", c
				print "Assuming: 4"

			i += offset

			# set measure to the length of a whole note times the time signature
			measure_length = note_durations['W'] * ts_num / ts_denom
			#print "Setting time signature to %d/%d." % (ts_num, ts_denom)
			#print "Measure length is:", measure_length
			# now we get slightly tricky, the MFF wants us to emit
			# four values, numerator, dnomingtaro (as a negative power of two: 2 => Q)
			# MIDI clocks in a click
			ts_event = songevents.Time_Signature()
			ts_event.ppq = song.PPQ
			ts_event.numerator = ts_num
			ts_event.denominator = ts_denom
			ts_event.pos = position
			song.append(ts_event)		# add to the song

		#
		# New measure - move the position forward... 
		#
		elif c == '/':
				
			#print "new measure"
			newpos = last_measure + measure_length
			
			if newpos > position:
				print "Warning: position was short of new measure:", song.measure_num, position, newpos
				
			while newpos < position:
				print "Warning: current position:", position, "is greater than next measure/position:", song.measure_num, newpos
				newpos += measure_length + fermata_add	# keep adding to the measure pointer to catch up with position.
				fermata_add = 0	# allows a one-time addition to a bar for the longest held note
			
			position = newpos
			last_measure = position
			
			if solo:
				solo = False
				#print "Solo mode;", solo
			song.measure_num += 1
			#print "new measure:", song.measure_num
			# new measure resets all accidentals...
			song.key.reset_accidentals()
			song.clear_ties()
		#
		# restart measure - reset position, clear accidentals
		elif c == ';':
			barend = last_measure + measure_length
			if position > barend:
				print "Warning: restarted measure would be long: ",song.measure_num, position, barend
			position = last_measure
			#print "restart measure", position
			# new measure resets all accidentals...
			song.key.reset_accidentals()
			if solo:
				solo = False
				#print "Solo mode;", solo
		elif c == "@":
			solo = True
			#print "Solo mode:", solo
		elif c == '?':
			fermata = True
			#print "Fermata is:", fermata
			
		#
		#
		# --------------  Misc:  1	`, grouping, Divisions (tracks), orchestration 
		#
		elif c == 'V':	# volume
			try:
				(vol, offset) = getnum(text[i:])
			except ValueError, info:
				print "No volume value found", info
				continue
			
			new_volume = ( vol & 0x3f ) + 64 	# 0-63 maps to MIDI vol 64-127
			#print "Volume event:", volume, "->", new_volume, "ramp_duration:", ramp_duration
			if ramp_duration == 0:
				mk_volume_event(song,new_volume, position, track_num)
			else:
				# calculate a reasonable increment for the position / tempo increment,
				# then emit a series of events...
				v_diff = new_volume - volume
				v_size = abs(v_diff)
				v_sign = v_diff / v_size	# -1 or +1 
				
				# let's assume there will be many more pulses than tempo points 
				# so issue a tempo event for tempo point change
				pos = position
				dur_incr = ramp_duration / v_size
				for v in range(volume, new_volume, v_sign):
					pos += dur_incr 
					mk_volume_event(song, v, pos, track_num )
				mk_volume_event(song, new_volume, position+ramp_duration, track_num)
			volume = new_volume
			ramp_duration = 0

			i += offset
		
		# Acceleration, deacceleration, crescendo, decrescendo...
		elif c in '+-<>':	# handle some commonality (read the next value...)
			try:
				(num, offset) = getnum(text[i:])
			except ValueError, info:
				print "Expected value for modifier:", c, info
			else:
				# We can treat these all the same - just set the ramping value
				# to the current note duration.  When the next volume or tempo change
				# is hit, we process it then
				i += offset
				ramp_duration = duration * num
				# We could distinguish between volume / tempo or increase / decrease
				# but beyond generating a  warning - there's no real difference...	
		#
		# Grouping...  notes start at the same time...
		elif c == '(':
			grouping = True
			#print "Grouping:", grouping
			group_length = measure_length * 5 # (one bar *should* be the limit - this is plenty)
		elif c == ')':
			grouping = False
			position += group_length
			#print "Grouping:", grouping, ", new position:", position
		elif c == 'N':	# voicing information per track...
			(num, offset) = getnum(text[i:])
			i += offset
			#print "Voicing with value:", num
		
		#
		# Divisions...  corresponding to tracks...
		elif c in DIVISIONS:
			index=DIVISIONS.find(c)		# which one?
			if song.format == 1:	
				# have we seen this division/track yet?
				if c not in track_list:
					track_list += c
					# Track number is the position in the list + 1
					#print "New Division: ", DIV_NAMES[index], "track:", track_num, c
					track = MFF.Track_Chunk()
					track.name = DIV_NAMES[index]
					song.track_list.append(track)
					song.track_count += 1
					track.track_num = song.track_count	# assign a number 
					#print "Track count is:", song.track_count
				
				track_num = track_list.find(c) + 1
				current_track = song.track_list[track_num]
				#print "Track number set to:", track_num
		#
		# Orchestration...		
		elif c == 'O':		# "orchestration -> program change"
			try:
				(pc, offset) = getnum(text[i:])
			except ValueError, info:
				print "Orchestration not a number", info
			else:
				# generate a program change...
				#print "Orchestration / Program Change:", pc
				last_o = pc	# not sure what, if anything, to do with this.
			i += offset
		#
		#
		# ------- Meta:  Comments, etc...
		#
		# Comment - generates an event
		elif c == '"':
			end=text[i:].find('"') + i	# position of the next " n the full text
			comment_text=text[i:end]
			#print "Comment: ", comment_text
			i=end+1		# skip to the end of the comment
			comment=songevents.Comment()
			comment.pos = position
			comment.data = comment_text
			comment.track_num = 0	# comments always in track 0
			#song.events += [ comment ]
			song.append(comment)


		# other 
		elif c in IGNORE:
			continue

		elif c in STOP:
			ended=True
			#print "End Marker found."
			break
		else:
			print "Unrecognized: ", repr(c), "at:", position, '--------------------------------------------'
			print text[i-30:i+31]
			print "                 ----here----^"
	if not ended:
		print "Warning: file likely not properly terminated."

	

	print "Final position:", position
	print "Measures:", song.measure_num


def main():
	print "No debug at this time"


if __name__ == "__main__":
	main()
