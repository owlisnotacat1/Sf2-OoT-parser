import struct
import sys
import os
import xml.etree.ElementTree as ET

def extract_data_from_o_file(o_file):
    with open(o_file, "rb") as f:
        # Seek to offset 0x9A to read the size of the data
        f.seek(0x98)
        data_size = struct.unpack(">I", f.read(4))[0]  # Read 32-bit integer (big endian)

        # Reset the file pointer to the beginning
        f.seek(0)
        file_content = f.read()  # Read the entire file content

        # Look for the byte string "73 79 6D 74 61 62 00" (symtab)
        marker = b"symtab\x00"
        marker_offset = file_content.find(marker)

        if marker_offset == -1:
            print("Marker not found in the .o file.")
            return

        # Calculate the start of the data
        data_start = marker_offset + len(marker)

        # Ensure we don't read past the size specified at offset 0x9A
        data_end = data_start + data_size

        # Extract the data within the bounds
        data = file_content[data_start:data_end]

        # Define the output file path
        output_file_path = os.path.join(os.getcwd(), "extracted_data.bin")

        # Write the extracted data to a binary file
        with open(output_file_path, "wb") as out_file:
            out_file.write(data)

        print(f"Data extracted to '{output_file_path}', size: {len(data)} bytes.")

    return output_file_path

def generate_meta_file(xmlpath):
    # Load the XML file
    tree = ET.parse(xmlpath)
    root = tree.getroot()

    # Initialize variables to find the highest index
    max_instrument_index = -1
    max_drum_index = -1

    # Iterate through instruments to find the highest index
    for instrument in root.findall(".//Instrument"):
        index = int(instrument.get("Index", -1))
        if index > max_instrument_index:
            max_instrument_index = index

    # Iterate through drums to find the highest index
    for drum in root.findall(".//Drum"):
        index = int(drum.get("Index", -1))
        if index > max_drum_index:
            max_drum_index = index

    # Write the .meta file with the appropriate header and sizes
    meta_header = bytes([0x02, 0x02, 0x01, 0xFF])
    meta_data = struct.pack("BB", max_instrument_index + 1, max_drum_index + 1) + b'\x00\x00'

    meta_file_path = os.path.join(os.getcwd(), "output.meta")
    with open(meta_file_path, "wb") as meta_file:
        meta_file.write(meta_header + meta_data)

    print(f"Meta file generated at '{meta_file_path}'.")

# Example usage
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py <input.o> <input.xml>")
        sys.exit(1)

    o_file_path = sys.argv[1]
    xml_file_path = sys.argv[2]

    extract_data_from_o_file(o_file_path)
    generate_meta_file(xml_file_path)
