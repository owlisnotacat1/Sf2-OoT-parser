import os
import sys
import struct

def extract_ssnd_chunk(aifc_file, output_file):
    with open(aifc_file, 'rb') as f:
        data = f.read()

        # Check for RIFF header
        if data[0:4] != b'FORM':
            print(f"{aifc_file} is not a valid RIFF file.")
            return False

        # Locate the SSND chunk
        offset = 12  # Skip FORM header and first 8 bytes
        while offset < len(data):
            chunk_id = data[offset:offset + 4]
            chunk_size = struct.unpack('>I', data[offset + 4:offset + 8])[0]
            
            if chunk_id == b'SSND':
                # The SSND chunk starts 8 bytes after the chunk size
                ssnd_chunk_start = offset + 8 + 8
                ssnd_chunk = data[ssnd_chunk_start:ssnd_chunk_start + chunk_size - 8]
                with open(output_file, 'wb') as out_f:
                    out_f.write(ssnd_chunk)
                print(f"Extracted SSND chunk to {output_file}")
                return True
            
            offset += 8 + chunk_size
        
        print(f"No SSND chunk found in {aifc_file}.")
        return False

def process_directory(input_dir, output_dir):
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith('.aifc'):
                aifc_file = os.path.join(root, file)
                output_file = os.path.join(output_dir, os.path.splitext(file)[0] + '.zsound')
                extract_ssnd_chunk(aifc_file, output_file)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python extract_ssnd.py <input_directory> <output_directory>")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_dir = sys.argv[2]

    if not os.path.isdir(input_dir):
        print(f"Error: Input directory {input_dir} does not exist.")
        sys.exit(1)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    process_directory(input_dir, output_dir)