import os
import wave
import sys

def remove_loop_points_if_start_zero(wav_file_path):
    with wave.open(wav_file_path, 'rb') as wav_file:
        params = wav_file.getparams()
        num_channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        num_frames = wav_file.getnframes()
        frames = wav_file.readframes(num_frames)

    # Open the file in binary mode to check for 'smpl' chunk where loop points are stored
    with open(wav_file_path, 'rb') as file:
        data = file.read()

    smpl_chunk_pos = data.find(b'smpl')
    if smpl_chunk_pos != -1:
        # 'smpl' chunk found, read the loop start position
        loop_start = int.from_bytes(data[smpl_chunk_pos + 28:smpl_chunk_pos + 32], byteorder='little')
        if loop_start == 0:
            # Removing the 'smpl' chunk which is 60 bytes long
            print(f"Removing loop points from: {wav_file_path}")
            data = data[:smpl_chunk_pos] + data[smpl_chunk_pos + 60:]

            # Write back the modified file
            with open(wav_file_path, 'wb') as file:
                file.write(data)
        else:
            print(f"No loop points with start 0 found in: {wav_file_path}")
    else:
        print(f"No 'smpl' chunk found in: {wav_file_path}")

def process_directory(directory):
    for root, _, files in os.walk(directory):
        for file_name in files:
            if file_name.endswith('.wav'):
                wav_file_path = os.path.join(root, file_name)
                remove_loop_points_if_start_zero(wav_file_path)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script_name.py <directory_path>")
        sys.exit(1)
    
    directory_path = sys.argv[1]
    
    if not os.path.isdir(directory_path):
        print(f"Error: {directory_path} is not a valid directory.")
        sys.exit(1)
    
    process_directory(directory_path)
