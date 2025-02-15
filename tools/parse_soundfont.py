import sys
import os
import xml.etree.ElementTree as XmlTree
import math
import struct
import ctypes
from xml.dom import minidom
import wave

updatesPerFrameScaled = 0.75
#initalize table
release_values = [0.0] * 256

def calculate_decay(arg):
    return (256.0 * 0.001302) / arg

def AudioHeap_InitAdsrDecayTable():
    release_values[0] = 100.0

    for i in range(1, 16):
        release_values[i] = 1.0 / calculate_decay(60 * (23 - i)) / 60# * 0.7
    for i in range(16, 128):
        release_values[i] = 1.0 / calculate_decay(4 * (143 - i)) / 60# * 0.7
    for i in range(128, 251):
        release_values[i] = 1.0 / calculate_decay(251 - i) / 60# * 0.7
    release_values[251] = 1.0 / calculate_decay(0.75) / 60# * 0.7
    release_values[252] = 1.0 / calculate_decay(0.66) / 60# * 0.7
    release_values[253] = 1.0 / calculate_decay(0.5) / 60# * 0.7
    release_values[254] = 1.0 / calculate_decay(0.33) / 60# * 0.7
    release_values[255] = 1.0 / calculate_decay(0.25) / 60# * 0.7

# Calculate tuning float for channel-based, or range-based, instruments (instruments).
# For channel-based instruments, a lower tuning float value results in a higher pitch.
def calc_chanbased_tuning(r, s, c, hR, sR):
    chanbased_tuning = 2 ** ((60 - (r - s - (0.01 * c))) / 12) / (hR / sR) # "Float * (sR / hR)" would also work, just preference.
    return chanbased_tuning

# Calculate tuning float for key-based instruments (drums and sound effects).
# For key-based instruments, a higher tuning float value results in a higher pitch.
#
# The tuning calculation already calculates as if the sample is assigned to 60. However, for SF2 parsing the distance from 60
# must also be calculated and added as a secondary coarse tune: "Key Range - Root Key = Distance from 60"
def calc_keybased_tuning(r, s, c, hR, sR):
    keybased_tuning = 2 ** ((r + s + (0.01 * c)) / 12) * (sR / hR)
    return keybased_tuning

def find_closest_index(value, value_list):
    return min(range(len(value_list)), key=lambda i: abs(value_list[i] - value))

def convert_pan_to_minus50_50_float(pan_value):
    # Clamp pan_value to the range -500 to 500
    if pan_value < -500:
        pan_value = -500
    elif pan_value > 500:
        pan_value = 500

    # Convert pan value from -500 to 500 range to -50.0 to 50.0 range
    pan_minus50_50 = pan_value / 10.0
    
    return pan_minus50_50

def unsigned_to_signed(unsigned_value):
    """Convert an unsigned 16-bit integer to a signed integer."""
    if unsigned_value >= 0x8000:
        return unsigned_value - 0x10000
    else:
        return unsigned_value

def timecents_to_seconds(timecents):
    """Convert a timecent value to seconds."""
    return 2 ** (timecents / 1200)

def convert_timecent_to_seconds(unsigned_value):
    """Convert an unsigned integer timecent value to seconds."""
    signed_timecent = unsigned_to_signed(unsigned_value)
    seconds = timecents_to_seconds(signed_timecent)
    return seconds

def fromRawValueToNoteName(raw_value):
    # First, convert the raw value back to a MIDI note by adding 0
    midi_note = raw_value + 12

    # Calculate the tone (note name) and octave
    tone = midi_note % 12
    octave = (midi_note // 12) - 1

    # Map tone values back to note names
    tone_str = {
        0: "C",
        1: "C♯",
        2: "D",
        3: "D♯",
        4: "E",
        5: "F",
        6: "F♯",
        7: "G",
        8: "G♯",
        9: "A",
        10: "A♯",
        11: "B"
    }[tone]

    # Return the musical notation
    return f"{tone_str}{octave}"

class phdr:
    def __init__(self):
        self.achPresetName = ''  # CHAR[20]
        self.wPreset = 0         # WORD
        self.wBank = 0           # WORD
        self.wPresetBagNdx = 0   # WORD  0x14 // 20 next pgen index 5
        self.dwLibrary = 0       # DWORD
        self.dwGenre = 0         # DWORD
        self.dwMorphology = 0    # DWORD



class pbag:
    def __init__(self):
        self.wGenNdx = 0 #index into generators for presets contains data that links the instrument to the preset(only need inst index)
        self.wModNdx = 0 #index into modulators for presets (Should be unused in this context as oot doesnt have an advanced enough soundfont struct)
        self.index = 0
# unused for oot
#class pmod:
#    def __init__(self):
#        self.

class pgen:
    def __init__(self):
        self.operator = ''
        self.amount = 0
        self.index = 0
class inst:
    def __init__(self):
        self.name = '' #probably dont need this
        self.wInstBagNdx = 0 #indexes into ibag to gather data like adsr, samples used, and tuning data etc
        self.index = 0
class ibag:
    def __init__(self):
        self.wInstGenNdx = 0 #indexes into igen to gather data like adsr, samples used, and tuning data etc
        self.wInstModNdx = 0 #indexes into imod to gather modulation data (unused)
        self.index = 0
# unused for oot
#class imod:
#    def __init__(self):
#        self.

class igen:
    def __init__(self):
        self.operator = ''
        self.amount = 0
        self.index = 0

    # 1  = loop data?
    # 2  = loop data?
    # 3  = loop data?
    # 4  = loop data?
    # 17 = pan
    # 33 = delay
    # 34 = attack
    # 35 = hold
    # 36 = decay
    # 37 = sustain
    # 38 = release
    # 41 = inst index(for pgen)
    # 43 = keyrange
    # 52 = fine tune
    # 53 = sample index
    # 54 = loop mode


#sample header stores sample meta data
class shdr:
    def __init__(self):
        self.name = ''
        self.start = 0
        self.end = 0
        self.startloop = 0  # Corrected attribute name
        self.endloop = 0    # Corrected attribute name
        self.samplerate = 0
        self.originalkey = 0  # Unused
        self.chCorrection = 0  # Pitch correction in cents
        self.samplelink = 0
        self.sampletype = 0
        self.index = None

class RiffChunk:
    def __init__(self, name='', size=0, offset=0):
        self.name = name
        self.size = size
        self.offset = offset
        self.type = ''
        self.subchunks = []

def db_to_linear(dB):
    return 10 ** (-dB / 20)

def clamp(value, min_value=1, max_value=32767):
    return max(min_value, min(value, max_value))

class Envelope:
    def __init__(self):
        self.name = ''
        self.envpoint = []

    def toxml(self, root):
        envelopeRoot = XmlTree.SubElement(root, "Envelope", {"Name": self.name})
        script = XmlTree.SubElement(envelopeRoot, "Script")
        for envpoint in self.envpoint:
            XmlTree.SubElement(script, "Point", {"Delay": str(envpoint.delay), "Value": str(envpoint.value)})

    def generate_envelope(self, sf2_attack, sf2_hold, sf2_decay, sf2_sustain):
        if sf2_sustain == 140:
            env_delay_1 = clamp(round((sf2_attack * (180)) / updatesPerFrameScaled))
            env_point_1 = 32767
            env_delay_2 = clamp(round((sf2_hold * (180)) / updatesPerFrameScaled))
            env_point_2 = 32767
            env_delay_3 = clamp(round((sf2_decay * (180)) / updatesPerFrameScaled))
            env_point_3 = 1
            env_delay_4 = "ADSR_HANG"
            env_point_4 = 0
        else:
            env_delay_1 = clamp(round((sf2_attack * (180)) / updatesPerFrameScaled))
            env_point_1 = 32767

            if sf2_sustain != 0:
                env_delay_2 = clamp(round((sf2_hold * (180)) / updatesPerFrameScaled))
                env_point_2 = 32767
                env_delay_3 = clamp(round((sf2_decay * (180)) / updatesPerFrameScaled))
                # Convert sustain dB value to linear and calculate the envelope point
                env_point_3 = round(math.sqrt(db_to_linear(sf2_sustain)) * 32767)
                env_delay_4 = "ADSR_HANG"
                env_point_4 = 0
            else:
                env_delay_2 = 32767
                env_point_2 = 32767
                env_delay_3 = "ADSR_HANG"
                env_point_3 = 0
                env_delay_4 = 0
                env_point_4 = 0

        # Assign calculated envelope points to the envpoint list
        self.envpoint = [
            EnvelopePoint(env_delay_1, env_point_1),
            EnvelopePoint(env_delay_2, env_point_2),
            EnvelopePoint(env_delay_3, env_point_3),
            EnvelopePoint(env_delay_4, env_point_4)
        ]

    def compare(self, other_envelope):
        if len(self.envpoint) != len(other_envelope.envpoint):
            return False
        for p1, p2 in zip(self.envpoint, other_envelope.envpoint):
            if p1.delay != p2.delay or p1.value != p2.value:
                return False
        return True

class EnvelopePoint:
    def __init__(self, delay=0, value=0):
        self.delay = delay
        self.value = value

class InstrumentKey:
    def __init__(self):
        self.sample = ''
        self.tuning = 0.0


class OotInstrument:
    def __init__(self):
        self.index = 0
        self.name = ''
        self.enum = ''
        self.lowkey = []
        self.maxNote = ''
        self.mediumkey = []
        self.highKey = []
        self.minNote = ''
        self.releaserate = 0
        self.envelope = ''

        self.lowkey = InstrumentKey()
        self.mediumkey = InstrumentKey()
        self.highKey = InstrumentKey()

    
    def display(self):
        print(f"Index: {self.index}")
        print(f"Name: {self.name}")
        print(f"Enum: {self.enum}")
        print(f"Low Key Sample: {self.lowkey.sample}")
        print(f"Low Key Tuning: {self.lowkey.tuning}")
        print(f"Max Note: {self.maxNote}")
        print(f"Medium Key Sample: {self.mediumkey.sample}")
        print(f"Medium Key Tuning: {self.mediumkey.tuning}")
        print(f"High Key Sample: {self.highKey.sample}")
        print(f"High Key Tuning: {self.highKey.tuning}")
        print(f"Min Note: {self.minNote}")
        print(f"Release Rate: {self.releaserate}")
        print(f"Envelope: {self.envelope}")
        print("------------------------------------------------------------------------------------------------")

    def toxml(self, root):
        element = XmlTree.SubElement(
            root,
            "Instrument",
            {
                "Name": self.name,
                "Index": str(self.index),
                "Enum": self.enum or "",
                "Decay": str(self.releaserate),
                "Envelope": self.envelope
            }
        )

        lowKeyElement = XmlTree.SubElement(element, "LowKey")
        medKeyElement = XmlTree.SubElement(element, "MediumKey")
        hiKeyElement = XmlTree.SubElement(element, "HighKey")

        if self.lowkey.sample != '':
            lowKeyElement.set("Sample", f"{self.lowkey.sample}")
            lowKeyElement.set("MaxNote", f"{self.maxNote}")
            lowKeyElement.set("Pitch", str(self.lowkey.tuning))

        if self.mediumkey.sample != '':
            medKeyElement.set("Sample", f"{self.mediumkey.sample}")
            medKeyElement.set("Pitch", str(self.mediumkey.tuning))

        if self.highKey.sample != '':
            hiKeyElement.set("Sample", f"{self.highKey.sample}")
            hiKeyElement.set("MinNote", f"{self.minNote}")
            hiKeyElement.set("Pitch", str(self.highKey.tuning))

        return element

class OotDrum:
    def __init__(self):
        self.samplename = ''
        self.release_index = 0
        self.envelope = ''
        self.tuningfloat = 0.0
        self.pan = 0
        self.index = 0
        self.name = ''
        self.enum = ''

    def display(self):
        print(f"Sample Name: {self.samplename}")
        print(f"Release Index: {self.release_index}")
        print(f"Envelope: {self.envelope}")
        print(f"Tuning Float: {self.tuningfloat}")
        print(f"Pan: {self.pan}")
        print(f"Index: {self.index}")
        print(f"Name: {self.name}")
        print(f"Enum: {self.enum}")
        print("------------------------------------------------------------------------------------------------")

    def toxml(self, root):
        drum_element = XmlTree.SubElement(root, "Drum")
        drum_element.set("Name", f"{self.name}")
        drum_element.set("Index", f"{self.index}")
        drum_element.set("Enum", f"{self.enum}")
        drum_element.set("Decay", f"{self.release_index}")
        drum_element.set("Pan", f"{self.pan}")
        drum_element.set("Sample", f"{self.samplename}")
        drum_element.set("Envelope", f"{self.envelope}")
        drum_element.set("Pitch", f"{self.tuningfloat}")

        return drum_element


class OotFont:
    def __init__(self):
        self.instruments = []
        self.drums = []
        self.sfx = []
        self.envelopes = []

class PseudoDrumSampleEntry:
    def __init__(self):
        self.samplename = ''
        self.attack = 0
        self.hold = 0
        self.decay = 0
        self.sustain = 0
        self.release = 0
        self.rootkey = 0
        self.tuning_semi = 0
        self.tuning_cents = 0
        self.loopType = 0
        self.samplerate = 0 
        self.lowrange = 0
        self.maxrange = 0
        self.envelope_enum = ''


class PseudoInstrumentSampleEntry:
    def __init__(self):
        self.lowrange = 0
        self.maxrange = 0
        self.samplename = ''
        self.keyrangelow = 0
        self.keyrangehigh = 127
        self.loopType = ''
        self.rootkey = 0
        self.tuning_semi = 0
        self.tuning_cents = 0
        self.samplerate = 0
        self.envelope_enum = ''

class PseudoInstrument:
    def __init__(self):
        self.index = 0
        self.attack = 0
        self.hold = 0
        self.decay = 0
        self.sustain = 0
        self.release = 0
        self.numsamples = 0
        self.sample_entrys = []
        self.envelope_enum = ""


#class Percussion:
#
#
#class SoundEffect:


class SF2File:
    def __init__(self, filepath):
        self.filepath = filepath
        self.list_chunks = []  # Initialize a list to hold RiffChunk objects
        self.presetheaders = []
        self.numphdr = 0
        self.pbags = []
        self.numpbag = 0
        self.pgens = []
        self.numpgen = 0
        self.pmods = []
        self.numpmod = 0
        self.insts = []
        self.numinst = 0
        self.ibags = []
        self.numibag = 0
        self.igens = []
        self.numigen = 0
        self.imods = []
        self.numimod = 0
        self.shdrs = []
        self.numshdr = 0
        self.drumindex = None

        self.processed_insts = []
        self.processed_percussions = []
        self.numdrums = 0
        self.ootfont = OotFont()
        self.smpl_offset = 0

        # Mapping for generator operator indices
        self.generator_mapping = {
            1: "loop start",
            2: "loop end",
            3: "sample modes",
            4: "sample modes",
            17: "pan",
            33: "delay",
            34: "attack",
            35: "hold",
            36: "decay",
            37: "sustain",
            38: "release",
            41: "instrument index",
            43: "keyrange",
            51: "coarse tune", #semitones
            52: "fine tune", #cents
            53: "sample index",
            54: "loop mode",
            58: "root key"
        }

    def riff_get_subchunk(self, chunk_offset):
        with open(self.filepath, 'rb') as rawfile:
            # Create a new RiffChunk object
            subchunk = RiffChunk()
            
            # Seek to the specified offset
            rawfile.seek(chunk_offset)
            
            # Read subchunk ID (4 bytes)
            subchunk.name = rawfile.read(4).decode('ascii')
            
            # Read subchunk size (4 bytes)
            subchunk.size = int.from_bytes(rawfile.read(4), 'little')

            # If the subchunk is a LIST chunk, read the type
            if subchunk.name == 'LIST':
                subchunk.type = rawfile.read(4).decode('ascii')
            
            subchunk.offset = chunk_offset
            
            return subchunk
        
    def deduplicate_envelopes(self):
        seen_envelopes = {}
        updated_references = {}

        print("Starting envelope deduplication...")
        for envelope in self.ootfont.envelopes:
            for seen_name, seen_envelope in seen_envelopes.items():
                if envelope.compare(seen_envelope):
                    print(f"Duplicate found: {envelope.name} is a duplicate of {seen_name}")
                    updated_references[envelope.name] = seen_name
                    break
            else:
                seen_envelopes[envelope.name] = envelope

        # Update references in processed_insts and processed_percussions
        for instrument in self.processed_insts:
            if instrument.envelope_enum in updated_references:
                print(f"Updating instrument {instrument.name} envelope_enum from {instrument.envelope_enum} to {updated_references[instrument.envelope_enum]}")
                instrument.envelope_enum = updated_references[instrument.envelope_enum]

        for drum in self.processed_percussions:
            if drum.envelope_enum in updated_references:
                print(f"envelope_enum from {drum.envelope_enum} to {updated_references[drum.envelope_enum]}")
                drum.envelope_enum = updated_references[drum.envelope_enum]

        # Remove duplicate envelopes
        original_count = len(self.ootfont.envelopes)
        self.ootfont.envelopes = [envelope for envelope in self.ootfont.envelopes if envelope.name not in updated_references]
        print(f"Deduplication completed. Removed {original_count - len(self.ootfont.envelopes)} duplicates.")

    def parse(self):
        # Open the file
        with open(self.filepath, 'rb') as file:
            file_size = os.path.getsize(self.filepath)
            offset = 0

            # Check for the RIFF header
            riff_header = file.read(4)
            if riff_header != b"RIFF":
                print("Not a valid RIFF file.")
                return

            # Skip the RIFF size (4 bytes) and read the form type (4 bytes)
            file.read(4)  # RIFF size
            form_type = file.read(4)
            if form_type != b"sfbk":
                print("Not a valid SoundFont2 file.")
                return
            
            offset = 12  # Skip RIFF header, size, and form type

            # Read level 0 chunks
            while offset < file_size:
                subchunk = self.riff_get_subchunk(offset)
                self.list_chunks.append(subchunk)  # Append the subchunk to the list
                
                # Update the offset to the next subchunk
                offset += subchunk.size + 8  # Add 8 bytes for ID and size fields

            # Process level 1 subchunks for each LIST chunk
            for subchunk in self.list_chunks:
                if subchunk.name == 'LIST':
                    current_offset = subchunk.offset + 12  # Move past LIST header (name, size, type)
                    end_offset = subchunk.offset + subchunk.size + 8

                    while current_offset < end_offset:
                        subchunk_lvl1 = self.riff_get_subchunk(current_offset)
                        subchunk.subchunks.append(subchunk_lvl1)
                        print(f"subchunk {subchunk_lvl1.name}, at {subchunk_lvl1.offset}")
                        
                        # Update offset to the next subchunk
                        current_offset += subchunk_lvl1.size + 8

            for subchunk in self.list_chunks:
                if subchunk.name == 'LIST': 
                    if subchunk.type == 'pdta':
                        for subchunk_lvl1 in subchunk.subchunks:
                            # Process data in phdr chunk
                            if subchunk_lvl1.name == 'phdr':
                                tmpoffset = subchunk_lvl1.offset + 8  # Move past 'phdr' ID and size
                                while tmpoffset < subchunk_lvl1.offset + subchunk_lvl1.size - 38: # - 38 is to ignore the dummy phdr segment which is the end of the list
                                    file.seek(tmpoffset)

                                    # Read 38 bytes for the phdr structure
                                    data = file.read(38)
                                    presetheader = phdr()

                                    # Unpack the data into the phdr structure
                                    (
                                        presetheader.achPresetName,
                                        presetheader.wPreset,
                                        presetheader.wBank,
                                        presetheader.wPresetBagNdx,
                                        presetheader.dwLibrary,
                                        presetheader.dwGenre,
                                        presetheader.dwMorphology
                                    ) = struct.unpack('<20sHHHIII', data)

                                    # Convert preset name to string and strip null bytes
                                    presetheader.achPresetName = presetheader.achPresetName.decode('ascii').rstrip('\x00')

                                    # Move to the next phdr entry
                                    tmpoffset += 38  # Size of phdr structure
                                    self.numphdr += 1
                                    self.presetheaders.append(presetheader)
                                    print(f"preset header name: {presetheader.achPresetName}")

                            elif subchunk_lvl1.name == 'pbag':
                                tmpoffset = subchunk_lvl1.offset + 8
                                i = 0
                                while tmpoffset < subchunk_lvl1.offset + subchunk_lvl1.size + 4:
                                    file.seek(tmpoffset)
                                    data = file.read(4)  # Read 4 bytes (2 for wGenNdx and 2 for wModNdx)
                                    pbag_entry = pbag()
                                    pbag_entry.index = i
                                    pbag_entry.wGenNdx, pbag_entry.wModNdx = struct.unpack('<HH', data)
                                    tmpoffset += 4
                                    i += 1
                                    self.numpbag += 1
                                    self.pbags.append(pbag_entry)

                            elif subchunk_lvl1.name == 'pgen':
                                tmpoffset = subchunk_lvl1.offset + 8
                                i = 0
                                while tmpoffset < subchunk_lvl1.offset + subchunk_lvl1.size + 4:
                                    file.seek(tmpoffset)
                                    data = file.read(4)
                                    pgen_entry = pgen()
                                    pgen_entry.index = i
                                    op_index, pgen_entry.amount = struct.unpack('<HH', data)
                                    pgen_entry.operator = self.generator_mapping.get(op_index, f"Unknown ({op_index})")
                                    tmpoffset += 4
                                    i += 1
                                    self.numpgen += 1
                                    self.pgens.append(pgen_entry)

                            elif subchunk_lvl1.name == 'inst':
                                tmpoffset = subchunk_lvl1.offset + 8
                                i = 0
                                while tmpoffset < subchunk_lvl1.offset + subchunk_lvl1.size:
                                    file.seek(tmpoffset)
                                    data = file.read(22)
                                    inst_entry = inst()
                                    inst_entry.index = i
                                    inst_entry.name, inst_entry.wInstBagNdx = struct.unpack('<20sH', data)
                                    inst_entry.name = inst_entry.name.decode('ascii').rstrip('\x00')
                                    #struct.unpack()
                                    #inst_entry.name = file.read(20).decode('ascii')
                                    #inst_entry.wInstBagNdx = int.from_bytes(file.read(2), 'little')
                                    tmpoffset += 22
                                    i += 1
                                    self.numinst += 1
                                    self.insts.append(inst_entry)
                                    print(f"inst name: {inst_entry.name}, Bag index: {inst_entry.wInstBagNdx}")

                            elif subchunk_lvl1.name == 'ibag':
                                tmpoffset = subchunk_lvl1.offset + 8
                                i = 0
                                while tmpoffset < subchunk_lvl1.offset + subchunk_lvl1.size + 4:
                                    file.seek(tmpoffset)
                                    data = file.read(4)
                                    ibag_entry = ibag()
                                    ibag_entry.index = i
                                    ibag_entry.wInstGenNdx, ibag_entry.wInstModNdx = struct.unpack('<HH', data)
                                    tmpoffset += 4
                                    i += 1
                                    self.numibag += 1
                                    self.ibags.append(ibag_entry)

                            elif subchunk_lvl1.name == 'igen':
                                tmpoffset = subchunk_lvl1.offset + 8
                                i = 0
                                #print(f"offset: {subchunk_lvl1.offset}, size: {subchunk_lvl1.size}")
                                while tmpoffset < subchunk_lvl1.offset + subchunk_lvl1.size + 4:
                                    file.seek(tmpoffset)
                                    data = file.read(4)

                                    # Check if the data read is actually 4 bytes
                                    if len(data) != 4:
                                        print(f"Warning: Expected 4 bytes, but got {len(data)} bytes. Stopping read.")
                                        break
                                    
                                    igen_entry = igen()
                                    igen_entry.index = i

                                    op_index, igen_entry.amount = struct.unpack('<HH', data)
                                    igen_entry.operator = self.generator_mapping.get(op_index, f"Unknown ({op_index})")

                                    # Debug: Print the generator data
                                    #print(f"Parsed Generator: Operator Index = {op_index}, Amount = {igen_entry.amount}, Operator = {igen_entry.operator}")

                                    tmpoffset += 4
                                    i += 1
                                    self.numigen += 1
                                    self.igens.append(igen_entry)
    
                                # Debug: Final list of igens
                                #print(f"Total number of igens parsed: {len(self.igens)}")

                            elif subchunk_lvl1.name == 'shdr':
                                tmpoffset = subchunk_lvl1.offset + 8
                                i = 0
                                while tmpoffset < subchunk_lvl1.offset + subchunk_lvl1.size - 46:
                                    file.seek(tmpoffset)
                                    shdr_entry = shdr()

                                    # Unpack the shdr structure
                                    data = file.read(46)
                                    (
                                        shdr_entry.name,
                                        shdr_entry.start,
                                        shdr_entry.end,
                                        shdr_entry.startloop,
                                        shdr_entry.endloop,
                                        shdr_entry.samplerate,
                                        shdr_entry.originalkey,
                                        shdr_entry.chCorrection,
                                        shdr_entry.samplelink,
                                        shdr_entry.sampletype
                                    ) = struct.unpack('<20sLLLLLBBHH', data)
                                    shdr_entry.index = i
                                    shdr_entry.name = shdr_entry.name.decode('ascii').rstrip('\x00')
                                    self.shdrs.append(shdr_entry)
                                    self.numshdr += 1

                                    # Move to the next shdr entry
                                    tmpoffset += 46
                                    i += 1
                        #for igen_entry in self.igens:
                        #    print(f"index: {igen_entry.index}, operator: {igen_entry.operator}")
                    elif subchunk.type == 'sdta':
                        print(f"found sdta")
                        # get offset in file of sdata smpl chunk
                        for subchunk_lvl1 in subchunk.subchunks:
                            if subchunk_lvl1.name == 'smpl':
                                print("found smpl")
                                self.smpl_offset = subchunk_lvl1.offset + 8
                            



    print("Parsing completed.")


    def process_instruments(self, name_mapping):
        # Iterate through each instrument
        instindex = 0
        for inst_entry in self.insts:
            # Check for invalid names and handle accordingly
            if not inst_entry.name.strip():
                print(f"Warning: Empty or invalid instrument name at index {instindex}")
                continue

            # Create an Instrument object
            instrument = PseudoInstrument()
            instrument.name = inst_entry.name.strip()  # Store the instrument name

            # Validate the instrument name
            if "pbag" in instrument.name.lower():
                print(f"Error: Detected invalid instrument name resembling 'pbag': {instrument.name}")
                continue

            # Gather all ibag entries associated with this instrument
            ibag_start_index = inst_entry.wInstBagNdx
            # Use the next instrument's bag index or total number of ibags
            ibag_end_index = self.numibag if inst_entry.index + 1 >= len(self.insts) else self.insts[inst_entry.index + 1].wInstBagNdx

            # Store global parameters
            global_params = {}

            for ibag_index in range(ibag_start_index, ibag_end_index):
                if ibag_index >= len(self.ibags):
                    continue

                ibag_entry = self.ibags[ibag_index]

                # Gather all igen entries associated with this ibag
                igen_start_index = ibag_entry.wInstGenNdx
                igen_end_index = self.numigen if ibag_index + 1 >= len(self.ibags) else self.ibags[ibag_index + 1].wInstGenNdx


                sample_entry = None
                is_global = False

                if ibag_index == ibag_start_index:
                    is_global = True
                    # Look ahead to check if any igen has a keyrange or sample index, which means it's not global
                    for igen_index in range(igen_start_index, igen_end_index):
                        if igen_index >= len(self.igens):
                            continue

                        igen_entry = self.igens[igen_index]
                        if igen_entry.operator in ['keyrange', 'sample index']:
                            is_global = False
                            break

                for igen_index in range(igen_start_index, igen_end_index):
                    if igen_index >= len(self.igens):
                        continue

                    igen_entry = self.igens[igen_index]

                    if is_global:
                        # Store global parameters
                        global_params[igen_entry.operator] = igen_entry.amount
                    else:
                        if sample_entry is None:
                            sample_entry = PseudoInstrumentSampleEntry()
                            # should only be called when global chunk is processedp

                        if igen_entry.operator == 'keyrange':
                            if sample_entry.keyrangehigh != 127:
                                print("Key range high is not 127. This might indicate an issue.")
                            sample_entry.keyrangelow = igen_entry.amount & 0xFF
                            sample_entry.keyrangehigh = (igen_entry.amount >> 8) & 0xFF
                        elif igen_entry.operator == 'attack':
                            instrument.attack = convert_timecent_to_seconds(igen_entry.amount)
                        elif igen_entry.operator == 'hold':
                            instrument.hold = convert_timecent_to_seconds(igen_entry.amount)
                        elif igen_entry.operator == 'decay':
                            instrument.decay = convert_timecent_to_seconds(igen_entry.amount)
                        elif igen_entry.operator == 'sustain':
                            instrument.sustain = igen_entry.amount / 10
                        elif igen_entry.operator == 'release':
                            instrument.release = convert_timecent_to_seconds(igen_entry.amount)
                        elif igen_entry.operator == 'root key':
                            sample_entry.rootkey = igen_entry.amount
                        elif igen_entry.operator == 'coarse tune':
                            sample_entry.tuning_semi = unsigned_to_signed(igen_entry.amount)
                        elif igen_entry.operator == 'fine tune':
                            sample_entry.tuning_cents = unsigned_to_signed(igen_entry.amount)
                        elif igen_entry.operator == 'loop mode':
                            sample_entry.loopType = igen_entry.amount
                        elif igen_entry.operator == 'sample index':
                            sample_index = igen_entry.amount
                            if 0 <= sample_index < len(self.shdrs):
                                sample_entry.samplename = name_mapping[sample_index]
                                sample_entry.samplerate = self.shdrs[sample_index].samplerate
                            instrument.numsamples += 1
                            instrument.sample_entrys.append(sample_entry)
                            sample_entry = PseudoInstrumentSampleEntry()

                # Apply global parameters if specific ones are missing
                if sample_entry:
                    if 'attack' not in globals() and 'attack' in global_params:
                        instrument.attack = convert_timecent_to_seconds(global_params['attack'])
                    if 'hold' not in globals() and 'hold' in global_params:
                        instrument.hold = convert_timecent_to_seconds(global_params['hold'])
                    if 'decay' not in globals() and 'decay' in global_params:
                        instrument.decay = convert_timecent_to_seconds(global_params['decay'])
                    if 'sustain' not in globals() and 'sustain' in global_params:
                        instrument.sustain = global_params['sustain'] / 10
                    if 'release' not in globals() and 'release' in global_params:
                        instrument.release = convert_timecent_to_seconds(global_params['release'])

            # Add the processed instrument to the list
            self.processed_insts.append(instrument)
            instindex += 1

    def process_drums(self, name_mapping):
        if self.drumindex is not None:
            for inst_entry in self.insts:
                if inst_entry.index == self.drumindex:
                    print(f"Processing drums for instrument index: {self.drumindex}")

                    ibag_start_index = inst_entry.wInstBagNdx
                    ibag_end_index = self.numibag if inst_entry.index + 1 >= len(self.insts) else self.insts[inst_entry.index + 1].wInstBagNdx

                    # Store global parameters
                    global_params = {}

                    for ibag_index in range(ibag_start_index, ibag_end_index):
                        if ibag_index >= len(self.ibags):
                            continue
                        
                        ibag_entry = self.ibags[ibag_index]
                        igen_start_index = ibag_entry.wInstGenNdx
                        igen_end_index = self.numigen if ibag_index + 1 >= len(self.ibags) else self.ibags[ibag_index + 1].wInstGenNdx
                        drum = None
                        is_global = (ibag_index == ibag_start_index)

                        for igen_index in range(igen_start_index, igen_end_index):
                            if igen_index >= len(self.igens):
                                continue

                            igen_entry = self.igens[igen_index]

                            if is_global:
                                global_params[igen_entry.operator] = igen_entry.amount
                            else:
                                if drum is None:
                                    drum = PseudoDrumSampleEntry()  # Initialize a new drum entry

                                if igen_entry.operator == 'keyrange':
                                    drum.lowrange = igen_entry.amount & 0xFF
                                    drum.maxrange = (igen_entry.amount >> 8) & 0xFF
                                elif igen_entry.operator == 'attack':
                                    drum.attack = convert_timecent_to_seconds(igen_entry.amount)
                                elif igen_entry.operator == 'hold':
                                    drum.hold = convert_timecent_to_seconds(igen_entry.amount)
                                elif igen_entry.operator == 'decay':
                                    drum.decay = convert_timecent_to_seconds(igen_entry.amount)
                                elif igen_entry.operator == 'sustain':
                                    drum.sustain = igen_entry.amount / 10
                                elif igen_entry.operator == 'release':
                                    drum.release = convert_timecent_to_seconds(igen_entry.amount)
                                elif igen_entry.operator == 'root key':
                                    drum.rootkey = igen_entry.amount
                                elif igen_entry.operator == 'coarse tune':
                                    drum.tuning_semi = unsigned_to_signed(igen_entry.amount)
                                elif igen_entry.operator == 'fine tune':
                                    drum.tuning_cents = unsigned_to_signed(igen_entry.amount)
                                elif igen_entry.operator == 'loop mode':
                                    drum.loopType = igen_entry.amount
                                elif igen_entry.operator == 'pan':
                                    drum.pan = convert_pan_to_minus50_50_float(unsigned_to_signed(igen_entry.amount))
                                elif igen_entry.operator == 'sample index':
                                    sample_index = igen_entry.amount
                                    if 0 <= sample_index < len(self.shdrs):
                                        drum.samplename = name_mapping[sample_index]
                                        drum.samplerate = self.shdrs[sample_index].samplerate

                        # If a drum entry was created and processed, append it to the list
                        if drum is not None:
                            self.processed_percussions.append(drum)
                            print(f"Drum processed: {drum.samplename} with range {drum.lowrange}-{drum.maxrange}")

                        # Apply global parameters if specific ones are missing
                        if drum:
                            if 'attack' not in globals() and 'attack' in global_params:
                                drum.attack = convert_timecent_to_seconds(global_params['attack'])
                            if 'hold' not in globals() and 'hold' in global_params:
                                drum.hold = convert_timecent_to_seconds(global_params['hold'])
                            if 'decay' not in globals() and 'decay' in global_params:
                                drum.decay = convert_timecent_to_seconds(global_params['decay'])
                            if 'sustain' not in globals() and 'sustain' in global_params:
                                drum.sustain = global_params['sustain'] / 10
                            if 'release' not in globals() and 'release' in global_params:
                                drum.release = convert_timecent_to_seconds(global_params['release'])

                        self.numdrums += 1



    def get_instrument_index_for_drum(self):
        # Find the preset with wPreset value 127 (typically drum kit)
        for presetheader in self.presetheaders:
            print(f"Checking preset: {presetheader.achPresetName} (Preset: {presetheader.wPreset})")
            if presetheader.wPreset == 127:
                print(f"Found percussion preset: {presetheader.achPresetName} (Preset: {presetheader.wPreset})")
                tmp_pbag_start = presetheader.wPresetBagNdx

                # Check if there is another preset after this one to determine the range
                next_preset_index = self.presetheaders.index(presetheader) + 1
                if next_preset_index < len(self.presetheaders):
                    tmp_pbag_end = self.presetheaders[next_preset_index].wPresetBagNdx
                else:
                    tmp_pbag_end = len(self.pbags)

                # Iterate through the pbag associated with this preset
                for pbag_index in range(tmp_pbag_start, tmp_pbag_end):
                    if pbag_index >= len(self.pbags):
                        continue

                    pbag_entry = self.pbags[pbag_index]
                    tmp_pgen_start = pbag_entry.wGenNdx
                    tmp_pgen_end = len(self.pgens)

                    if pbag_index + 1 < len(self.pbags):
                        tmp_pgen_end = self.pbags[pbag_index + 1].wGenNdx

                    # Iterate through all pgen entries within this pbag
                    for pgen_index in range(tmp_pgen_start, tmp_pgen_end):
                        if pgen_index >= len(self.pgens):
                            continue

                        pgen_entry = self.pgens[pgen_index]
                        print(f"Inspecting pgen entry: Operator = {pgen_entry.operator}, Amount = {pgen_entry.amount}")

                        # Check if the pgen entry has the operator "instrument index"
                        if pgen_entry.operator == 'instrument index':
                            print(f"Drum instrument index found: {pgen_entry.amount}")
                            self.drumindex = pgen_entry.amount
                            return pgen_entry.amount

        print("No 'instrument index' found for the drum preset.")
        self.drumindex = None
        return None





    def process_oot_envelopes(self):
        for instrument in self.processed_insts:
            if instrument.name == "EOI":
                continue
            envelope_entry = Envelope()
            envelope_entry.name = f"Env_{instrument.name.replace(' ', '_').replace('(', '_').replace(')', '_')}"
            envelope_entry.generate_envelope(instrument.attack, instrument.hold, instrument.decay, instrument.sustain)
            self.ootfont.envelopes.append(envelope_entry)
            instrument.envelope_enum = envelope_entry.name

        for drum in self.processed_percussions:
            envelope_entry = Envelope()
            envelope_entry.name = f"Env_Drum{drum.lowrange}_{drum.maxrange}"
            envelope_entry.generate_envelope(drum.attack, drum.hold, drum.decay, drum.sustain)
            self.ootfont.envelopes.append(envelope_entry)
            drum.envelope_enum = envelope_entry.name
        

    def process_oot_instruments(self):
        processed_indices = set()  # Keep track of processed instrument indices
    
        for presetheader in self.presetheaders:
            instIndex = None
            if presetheader.wPreset != 127:
                tmp_pbag_start = presetheader.wPresetBagNdx
    
                next_preset_index = self.presetheaders.index(presetheader) + 1
                if next_preset_index < len(self.presetheaders):
                    tmp_pbag_end = self.presetheaders[next_preset_index].wPresetBagNdx
                else:
                    tmp_pbag_end = len(self.pbags)
    
                for pbag_index in range(tmp_pbag_start, tmp_pbag_end):
                    if pbag_index >= len(self.pbags):
                        continue
                    
                    pbag_entry = self.pbags[pbag_index]
                    tmp_pgen_start = pbag_entry.wGenNdx
                    tmp_pgen_end = len(self.pgens)
    
                    if pbag_index + 1 < len(self.pbags):
                        tmp_pgen_end = self.pbags[pbag_index + 1].wGenNdx
    
                    if tmp_pgen_start >= tmp_pgen_end:
                        continue  # Skip if start index is not valid
                    
                    for pgen_index in range(tmp_pgen_start, tmp_pgen_end):
                        pgen_entry = self.pgens[pgen_index]
    
                        # Process the pgen entry based on its operator
                        if pgen_entry.operator == 'instrument index':
                            instIndex = pgen_entry.amount
                            break  # We found the instrument index, no need to continue in this pbag
                        
                if instIndex is not None:
                    if instIndex != self.drumindex and instIndex not in processed_indices:
                        processed_indices.add(instIndex)
                        oot_inst = OotInstrument()
                        curInst = self.processed_insts[instIndex]
                        oot_inst.index = presetheader.wPreset
                        oot_inst.name = f"{presetheader.achPresetName.replace(' ', '_').replace('(', '_').replace(')', '_')}"
                        oot_inst.enum = f"{presetheader.achPresetName.replace(' ', '_').replace('(', '_').replace(')', '_').upper()}"
                        oot_inst.envelope = curInst.envelope_enum
                        release = find_closest_index(curInst.release, release_values)
                        oot_inst.releaserate = ctypes.c_int8(release).value
    
                        # Process samples into OOT format with safety checks
                        if curInst.numsamples == 3:
                            # Sample 1
                            sample_name_1 = curInst.sample_entrys[0].samplename
                            if isinstance(sample_name_1, list):
                                sample_name_1 = sample_name_1[0]  # Use the first item if it's a list
                            oot_inst.lowkey.sample = sample_name_1.strip("[]").replace("'", "") + ".aifc"
                            oot_inst.lowkey.tuning = calc_chanbased_tuning(
                                curInst.sample_entrys[0].rootkey,
                                curInst.sample_entrys[0].tuning_semi,
                                curInst.sample_entrys[0].tuning_cents,
                                32000, curInst.sample_entrys[0].samplerate
                            )
    
                            # Sample 2
                            sample_name_2 = curInst.sample_entrys[1].samplename
                            if isinstance(sample_name_2, list):
                                sample_name_2 = sample_name_2[0]
                            oot_inst.mediumkey.sample = sample_name_2.strip("[]").replace("'", "") + ".aifc"
                            oot_inst.mediumkey.tuning = calc_chanbased_tuning(
                                curInst.sample_entrys[1].rootkey,
                                curInst.sample_entrys[1].tuning_semi,
                                curInst.sample_entrys[1].tuning_cents,
                                32000, curInst.sample_entrys[1].samplerate
                            )
    
                            # Sample 3
                            sample_name_3 = curInst.sample_entrys[2].samplename
                            if isinstance(sample_name_3, list):
                                sample_name_3 = sample_name_3[0]
                            oot_inst.highKey.sample = sample_name_3.strip("[]").replace("'", "") + ".aifc"
                            oot_inst.highKey.tuning = calc_chanbased_tuning(
                                curInst.sample_entrys[2].rootkey,
                                curInst.sample_entrys[2].tuning_semi,
                                curInst.sample_entrys[2].tuning_cents,
                                32000, curInst.sample_entrys[2].samplerate
                            )
    
                            oot_inst.minNote = fromRawValueToNoteName(curInst.sample_entrys[1].keyrangehigh)
                            oot_inst.maxNote = fromRawValueToNoteName(curInst.sample_entrys[1].keyrangelow)
    
                        elif curInst.numsamples == 2:
                            # Sample 1
                            sample_name_1 = curInst.sample_entrys[0].samplename
                            if isinstance(sample_name_1, list):
                                sample_name_1 = sample_name_1[0]
                            oot_inst.mediumkey.sample = sample_name_1.strip("[]").replace("'", "") + ".aifc"
                            oot_inst.mediumkey.tuning = calc_chanbased_tuning(
                                curInst.sample_entrys[0].rootkey,
                                curInst.sample_entrys[0].tuning_semi,
                                curInst.sample_entrys[0].tuning_cents,
                                32000, curInst.sample_entrys[0].samplerate
                            )
    
                            if len(curInst.sample_entrys) > 1:
                                # Sample 2
                                sample_name_2 = curInst.sample_entrys[1].samplename
                                if isinstance(sample_name_2, list):
                                    sample_name_2 = sample_name_2[0]
                                oot_inst.highKey.sample = sample_name_2.strip("[]").replace("'", "") + ".aifc"
                                oot_inst.highKey.tuning = calc_chanbased_tuning(
                                    curInst.sample_entrys[1].rootkey,
                                    curInst.sample_entrys[1].tuning_semi,
                                    curInst.sample_entrys[1].tuning_cents,
                                    32000, curInst.sample_entrys[1].samplerate
                                )
                                oot_inst.minNote = fromRawValueToNoteName(curInst.sample_entrys[0].keyrangehigh)
    
                        elif curInst.numsamples == 1:
                            # Sample 1
                            sample_name_1 = curInst.sample_entrys[0].samplename
                            if isinstance(sample_name_1, list):
                                sample_name_1 = sample_name_1[0]
                            oot_inst.mediumkey.sample = sample_name_1.strip("[]").replace("'", "") + ".aifc"
                            oot_inst.mediumkey.tuning = calc_chanbased_tuning(
                                curInst.sample_entrys[0].rootkey,
                                curInst.sample_entrys[0].tuning_semi,
                                curInst.sample_entrys[0].tuning_cents,
                                32000, curInst.sample_entrys[0].samplerate
                            )
    
                        self.ootfont.instruments.append(oot_inst)


    def process_percussion_set(self):
        for drum in self.processed_percussions:
            start = drum.lowrange
            end = drum.maxrange
            index = start
            #print(f"sample: {drum.samplename}")
            while index <= end:
                #process drums for current sample in inst
                oot_drum = OotDrum()
                sample_name = drum.samplename
                if isinstance(sample_name, list):
                    sample_name = sample_name[0]
                oot_drum.samplename = sample_name.strip("[]").replace("'", "") + ".aifc"
                #oot_drum.samplename = f"{drum.samplename}.aifc"
                oot_drum.envelope = drum.envelope_enum
                oot_drum.pan = max(0, min(64 + round(1.27 * drum.pan), 127))
                oot_drum.index = index - 21 # Convert index to Z64 here instead of during float calculation.
                oot_drum.release_index = ctypes.c_int8(find_closest_index(drum.release, release_values)).value
                oot_drum.name = f"drum_{index}"
                oot_drum.enum = f"DRUM_{index}"
                #tuning logic
                # The tuning calculation already calculates as if the sample is assigned to 60. However, for SF2 parsing
                # the distance from 60 must also be calculated and added as a secondary coarse tune.
                #
                # Calculate the distance from 60 below:
                pseudorootkey = index - drum.rootkey # If index is key range, then change to "Key Range - Root Key" for calculation.
                #print(f"root key: {pseudorootkey}")
                oot_drum.tuningfloat = calc_keybased_tuning(pseudorootkey,
                                        drum.tuning_semi,
                                        drum.tuning_cents, 
                                        32000, drum.samplerate)
                #print(f"tuning: {oot_drum.tuningfloat}")


                self.ootfont.drums.append(oot_drum)
                index += 1

    def process_oot_font(self):
        self.process_oot_envelopes()
        self.deduplicate_envelopes()
        self.process_oot_instruments()
        self.process_percussion_set()

        #for oot_inst in self.ootfont.instruments:
        #    oot_inst.display()
        #if self.drumindex is not None:
        #    for oot_drum in self.ootfont.drums:
        #        oot_drum.display()

    def generate_xml(self, output_file):
        root = XmlTree.Element("Soundfont", {
            "Medium": "Cartridge",
            "CachePolicy": "Temporary"
        })
        banks = XmlTree.SubElement(root, "SampleBanks")
        XmlTree.SubElement(banks, "Bank", { "Name": "1 Orchestra" })
        #for oot_inst in self.ootfont.instruments:
        instElements = XmlTree.SubElement(root, "Instruments")
        drumElements = XmlTree.SubElement(root, "Drums")
        effectElements = XmlTree.SubElement(root, "SoundEffects")
        envelopes = XmlTree.SubElement(root, "Envelopes")

        #realInst = [i for i in self.ootfont.instruments if type(i) is oot_inst]
        #realDrum = [d for d in self.ootfont.drums if type(d) is oot_drum]
        #realSfx = [x for x in self.ootfont. if type(x) is SoundEffect]
        for oot_inst in self.ootfont.instruments:
            oot_inst.toxml(instElements)

        for oot_drum in self.ootfont.drums:
            oot_drum.toxml(drumElements)

        for envelope_entry in self.ootfont.envelopes:
            envelope_entry.toxml(envelopes)
        





        with open(output_file, "w") as file:
            xmlstring = minidom.parseString(XmlTree.tostring(root, "unicode")).toprettyxml(indent="\t")
            file.write(xmlstring)
            print("xml generated")

    def get_loop_points(self, wav_path):
        """
        Extracts loop points from a WAV file if they exist.
        """
        try:
            with open(wav_path, 'rb') as wav_file:
                data = wav_file.read()

            # Search for 'smpl' chunk in the file
            smpl_index = data.find(b'smpl')
            if smpl_index != -1:
                # Read the loop start and end points from the 'smpl' chunk
                loop_start = struct.unpack('<I', data[smpl_index + 28:smpl_index + 32])[0]
                loop_end = struct.unpack('<I', data[smpl_index + 32:smpl_index + 36])[0]
                return loop_start, loop_end
            else:
                print(f"No 'smpl' chunk found in: {wav_path}, no loop to remove.")
                return None, None
        except Exception as e:
            print(f"Error reading {wav_path}: {e}")
            return None, None

    def extract_samples(self, output_dir):
        # Ensure the output directory exists
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
        sample_name_count = {}  # Dictionary to track sample name occurrences
        name_mapping = [[] for _ in range(self.numshdr + 1)]  # Map original names to unique names, initialized as lists
    
        # Open the SF2 file to read sample data
        with open(self.filepath, 'rb') as sf2_file:
            for shdr_entry in self.shdrs:
                if shdr_entry.name == "EOS":  # Skip the terminal "EOS" entry
                    continue
                
                # Generate a unique sample name
                base_name = shdr_entry.name
                if base_name in sample_name_count:
                    sample_name_count[base_name] += 1
                    unique_name = f"{base_name}_{sample_name_count[base_name]}"
                else:
                    sample_name_count[base_name] = 0
                    unique_name = base_name
    
                # Ensure name_mapping[shdr_entry.index] is a list (it is initialized as a list already)
                if isinstance(name_mapping[shdr_entry.index], list):
                    name_mapping[shdr_entry.index].append(unique_name)
                else:
                    name_mapping[shdr_entry.index] = [unique_name]
    
                print(f"Added {unique_name} to name_mapping[{shdr_entry.index}]")
    
                # Calculate the size of the sample
                sample_size = (shdr_entry.end - shdr_entry.start) * 2  # Since samples are 16-bit (2 bytes)
    
                # Seek to the start of the sample data
                sf2_file.seek((shdr_entry.start * 2) + self.smpl_offset)
    
                # Read the sample data
                sample_data = sf2_file.read(sample_size)
    
                # Calculate loop points
                loop_start = shdr_entry.startloop - shdr_entry.start
                loop_end = shdr_entry.endloop - shdr_entry.start
    
                # Validate loop points
                if loop_start <= 1 or loop_end < 0 or loop_start >= loop_end or loop_start == loop_end:
                    loop_start = None
                    loop_end = None
                elif loop_start == 0 and loop_end == shdr_entry.end - shdr_entry.start:
                    loop_start = None
                    loop_end = None
    
                # Convert the sample data into WAV format with loop points
                wav_file_path = os.path.join(output_dir, f"{unique_name}.wav")
                self.write_wav_file(wav_file_path, sample_data, shdr_entry.samplerate,
                                    loop_start, loop_end)
    
                print(f"Extracted: {wav_file_path}")
    
        return name_mapping  # Return the mapping to be used in instruments and drums


    def update_sample_names_in_instruments_and_drums(self, name_mapping):
        # Update sample names in instruments
        for instrument in self.processed_insts:
            for sample_entry in instrument.sample_entrys:
                original_name = sample_entry.samplename
                if original_name in name_mapping:
                    print(f"Updating instrument sample name from {original_name} to {name_mapping[original_name]}")
                    sample_entry.samplename = name_mapping[original_name]

        # Update sample names in drums
        for drum in self.processed_percussions:
            original_name = drum.samplename
            if original_name in name_mapping:
                print(f"Updating drum sample name from {original_name} to {name_mapping[original_name]}")
                drum.samplename = name_mapping[original_name]


    def write_wav_file(self, filepath, sample_data, sample_rate, loop_start=None, loop_end=None):
        # WAV file settings
        num_channels = 1  # Mono
        sample_width = 2  # 16-bit
        num_frames = len(sample_data) // sample_width
        wav_params = (num_channels, sample_width, sample_rate, num_frames, 'NONE', 'not compressed')

        # Clear the previous data by opening the file in write mode
        with wave.open(filepath, 'wb') as wav_file:
            wav_file.setparams(wav_params)
            wav_file.writeframes(sample_data)

        # Add loop points using the 'smpl' chunk if they are valid
        if loop_start is not None and loop_end is not None:
            self.add_smpl_chunk(filepath, loop_start, loop_end, sample_rate)

    def remove_smpl_chunk(self, wav_path):
        """
        Removes the 'smpl' chunk from a WAV file by rewriting the WAV file without it.
        """
        try:
            with open(wav_path, 'rb') as wav_file:
                data = wav_file.read()

            smpl_index = data.find(b'smpl')
            if smpl_index != -1:
                smpl_size = struct.unpack('<I', data[smpl_index + 4:smpl_index + 8])[0]
                smpl_chunk_size = smpl_size + 8  # 'smpl' ID (4 bytes) + Size (4 bytes)

                # Remove the 'smpl' chunk
                data_without_smpl = data[:smpl_index] + data[smpl_index + smpl_chunk_size:]

                # Overwrite the file without the 'smpl' chunk
                with open(wav_path, 'wb') as wav_file:
                    wav_file.write(data_without_smpl)
                print(f"Loop removed from: {wav_path}")

        except Exception as e:
            print(f"Error removing 'smpl' chunk from {wav_path}: {e}")

    def add_smpl_chunk(self, filepath, loop_start, loop_end, sample_rate):
        if loop_start is None or loop_end is None or loop_start >= loop_end:
            print(f"No valid loop for {filepath}, skipping SMPL chunk.")
            return  

        try:
            with open(filepath, 'r+b') as wav_file:
                # Read WAV header to find where to insert the 'smpl' chunk
                wav_file.seek(0)
                wav_data = wav_file.read()  

                # Verify existing chunks
                if b'smpl' in wav_data:
                    print(f"SMPL chunk already exists in {filepath}, skipping addition.")
                    return

                # Prepare the SMPL chunk
                sample_period = int(1e9 / sample_rate)
                midi_unity_note = 60  # Assuming the root note is C5
                num_loops = 1   

                smpl_chunk_data = struct.pack(
                    '<4sIIIIIIIIIIIIIIII',
                    b'smpl',                # Chunk ID
                    60,                     # Chunk size (total size of smpl chunk)
                    0,                      # Manufacturer
                    0,                      # Product
                    sample_period,          # Sample Period (ns)
                    midi_unity_note,        # MIDI Unity Note
                    0,                      # Pitch Fraction
                    0,                      # SMPTE Format
                    0,                      # SMPTE Offset
                    num_loops,              # Number of Sample Loops
                    0,                      # Sampler Data
                    0,                      # Cue Point ID
                    0,                      # Type (0 for forward loop)
                    loop_start,             # Start of loop
                    loop_end,               # End of loop
                    0,                      # Fraction
                    0                       # Play Count (0 for infinite loop)
                )   

                # Insert the SMPL chunk before the data chunk
                data_pos = wav_data.find(b'data')
                if data_pos == -1:
                    print(f"Failed to locate 'data' chunk in {filepath}.")
                    return  

                # Insert the SMPL chunk
                wav_file.seek(data_pos)
                wav_file.write(smpl_chunk_data)
                wav_file.write(wav_data[data_pos:])
                print(f"SMPL chunk added to {filepath} with Loop Start: {loop_start}, Loop End: {loop_end}")    

        except Exception as e:
            print(f"Failed to add SMPL chunk to {filepath}: {str(e)}")


    def delete_unassociated_samples(self, output_dir):
        # Gather all sample names associated with instruments and drums
        associated_samples = set()
    
        # Collect samples from instruments
        for instrument in self.processed_insts:
            for sample_entry in instrument.sample_entrys:
                if sample_entry.samplename:
                    if isinstance(sample_entry.samplename, list):
                        # If samplename is a list, add each name
                        associated_samples.update(sample_entry.samplename)
                    else:
                        # Otherwise, add the single name
                        associated_samples.add(sample_entry.samplename)
    
        # Collect samples from drums
        for drum in self.processed_percussions:
            if drum.samplename:
                if isinstance(drum.samplename, list):
                    # If samplename is a list, add each name
                    associated_samples.update(drum.samplename)
                else:
                    # Otherwise, add the single name
                    associated_samples.add(drum.samplename)
    
        print(f"Associated samples: {associated_samples}")
    
        # List all files in the output directory
        all_files = os.listdir(output_dir)
    
        # Delete files that are not associated with any instrument or drum
        for file_name in all_files:
            if file_name.endswith(".wav"):  # Check only .wav files
                sample_name = file_name.rsplit('.', 1)[0]  # Remove the file extension
                if sample_name not in associated_samples:
                    file_path = os.path.join(output_dir, file_name)
                    os.remove(file_path)
                    print(f"Deleted unassociated sample: {file_name}")

    def print_presets_and_instruments(sf2):
        print("Presets and their linked instruments:")
        for presetheader in sf2.presetheaders:
            print(f"\nPreset Name: {presetheader.achPresetName}")
            print(f"  Preset Index: {presetheader.wPreset}")
            print(f"  Bank: {presetheader.wBank}")
            print(f"  Preset Bag Index: {presetheader.wPresetBagNdx}")
            print("  Linked Instruments:")

            tmp_pbag_start = presetheader.wPresetBagNdx
            next_preset_index = sf2.presetheaders.index(presetheader) + 1
            if next_preset_index < len(sf2.presetheaders):
                tmp_pbag_end = sf2.presetheaders[next_preset_index].wPresetBagNdx
            else:
                tmp_pbag_end = len(sf2.pbags)

            for pbag_index in range(tmp_pbag_start, tmp_pbag_end):
                if pbag_index >= len(sf2.pbags):
                    continue

                pbag_entry = sf2.pbags[pbag_index]
                tmp_pgen_start = pbag_entry.wGenNdx
                tmp_pgen_end = len(sf2.pgens)

                if pbag_index + 1 < len(sf2.pbags):
                    tmp_pgen_end = sf2.pbags[pbag_index + 1].wGenNdx

                for pgen_index in range(tmp_pgen_start, tmp_pgen_end):
                    pgen_entry = sf2.pgens[pgen_index]

                    if pgen_entry.operator == 'instrument index':
                        instIndex = pgen_entry.amount
                        if instIndex < len(sf2.insts):
                            inst_entry = sf2.insts[instIndex]
                            print(f"    Instrument Name: {inst_entry.name}")
                            print(f"    Instrument Index: {inst_entry.index}")
                            print(f"    Instrument Bag Index: {inst_entry.wInstBagNdx}")
                            sf2.print_instrument_details(instIndex)
                        else:
                            print(f"    Instrument Index {instIndex} is out of range.")
                        break

    def print_instrument_details(self, instIndex):
        if instIndex >= len(self.processed_insts):
            print(f"    Error: Instrument Index {instIndex} out of range.")
            return

        instrument = self.processed_insts[instIndex]
        print(f"    Attack: {instrument.attack}")
        print(f"    Hold: {instrument.hold}")
        print(f"    Decay: {instrument.decay}")
        print(f"    Sustain: {instrument.sustain}")
        print(f"    Release: {instrument.release}")
        print(f"    Number of Samples: {instrument.numsamples}")
        print(f"    Sample Entries:")
        for sample_entry in instrument.sample_entrys:
            print(f"      Sample Name: {sample_entry.samplename}")
            print(f"      Key Range: {sample_entry.keyrangelow} - {sample_entry.keyrangehigh}")
            print(f"      Root Key: {sample_entry.rootkey}")
            print(f"      Tuning (Semi): {sample_entry.tuning_semi}")
            print(f"      Tuning (Cents): {sample_entry.tuning_cents}")
            print(f"      Sample Rate: {sample_entry.samplerate}")
            print(f"      Loop Type: {sample_entry.loopType}")

def create_xml_structure(output_file):
    # Create the root element
    root = XmlTree.Element("Soundfont")

    # Create sub-elements for initial XML structure
    sample_banks = XmlTree.SubElement(root, "SampleBanks")
    instruments = XmlTree.SubElement(root, "Instruments")

    # Create an ElementTree object
    tree = XmlTree.ElementTree(root)

    # Write the tree to the output XML file
    with open(output_file, 'wb') as f:
        tree.write(f, encoding='utf-8', xml_declaration=True)

def process_sf2_file(sf2_file, output_file):
    sf2 = SF2File(sf2_file)
    sf2.parse()

    # Extract samples and get the mapping of original to unique names
    output_dir = os.path.join(os.path.dirname(sf2_file), "Samples")
    name_mapping = sf2.extract_samples(output_dir)

    # Process instruments and drums
    sf2.process_instruments(name_mapping)
    drumInstId = sf2.get_instrument_index_for_drum()
    sf2.process_drums(name_mapping)

    # Update instruments and drums with unique sample names
    #sf2.update_sample_names_in_instruments_and_drums(name_mapping)
    
    # Process OOT font and generate XML
    sf2.process_oot_font()
    sf2.generate_xml(output_file)
    
    # Cleanup unassociated samples
    sf2.delete_unassociated_samples(output_dir)

def main():
    if len(sys.argv) != 3:
        print("Usage: python script.py <input.sf2> <output.xml>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    # Check if the input file exists
    if not os.path.exists(input_file):
        print(f"Error: The file {input_file} does not exist.")
        sys.exit(1)

    # Process the SF2 file
    AudioHeap_InitAdsrDecayTable()
    process_sf2_file(input_file, output_file)

if __name__ == "__main__":
    main()
