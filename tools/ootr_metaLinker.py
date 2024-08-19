import xml.etree.ElementTree as ET
import sys

def sanitize_sample_name(sample_name):
    if sample_name:
        return sample_name.split('.')[0]  # Removes file extension
    return ""

def parse_xml_to_meta(xml_file, meta_file, track_name, bgm_fanfare):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    with open(meta_file, 'w') as meta:
        # Write the provided track name and bgm/fanfare
        meta.write(f'{track_name}\n')
        meta.write('-\n')
        meta.write(f'{bgm_fanfare}\n')
        meta.write('-\n')

        for child in root:
            if child.tag == 'Instruments':
                Instruments = child
                for Instrument in Instruments:
                    Index = Instrument.get('Index')
                    for key_tag, key_name in zip(['LowKey', 'MediumKey', 'HighKey'], ['LOW', 'NORM', 'HIGH']):
                        KeyElement = Instrument.find(key_tag)
                        if KeyElement is not None:
                            SampleString = KeyElement.get('Sample')
                            if SampleString is not None:
                                sanitized_name = sanitize_sample_name(SampleString)
                                line = f'ZSOUND:INST:{Index}:{key_name}:{sanitized_name}.zsound'
                                meta.write(line + '\n')

            if child.tag == "Drums":
                Drums = child
                for Drum in Drums:
                    Index = Drum.get('Index')
                    SampleString = Drum.get('Sample')
                    if SampleString is not None:
                        sanitized_name = sanitize_sample_name(SampleString)
                        line = f'ZSOUND:DRUM:{Index}::{sanitized_name}.zsound'
                        meta.write(line + '\n')

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python script.py <input_xml_file> <output_meta_file> <track_name> <bgm_fanfare>")
        sys.exit(1)
    
    input_xml = sys.argv[1]
    output_meta = sys.argv[2]
    track_name = sys.argv[3]
    bgm_fanfare = sys.argv[4]
    
    parse_xml_to_meta(input_xml, output_meta, track_name, bgm_fanfare)
