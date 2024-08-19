#!/bin/bash

# Check if the correct number of arguments is provided
if [ "$#" -ne 4 ]; then
    echo "Usage: $0 <input.sf2> <input.seq> <track_name> <bgm_fanfare>"
    exit 1
fi

# Assign input arguments to variables
input_file="$1"
seq_file="$2"
track_name="$3"
bgm_fanfare="$4"

# Generate the output XML file path based on the input SF2 file name
output_file="output/$(basename "${input_file%.sf2}.xml")"

# Path to the parse_soundfont.py script
script_path="tools/parse_soundfont.py"

# Check if the input file exists
if [ ! -f "$input_file" ]; then
    echo "Error: Input file '$input_file' does not exist."
    exit 1
fi

# Check if the parse_soundfont.py script exists
if [ ! -f "$script_path" ]; then
    echo "Error: Script '$script_path' does not exist."
    exit 1
fi

# Check if the .seq file exists
if [ ! -f "$seq_file" ]; then
    echo "Error: Input .seq file '$seq_file' does not exist."
    exit 1
fi

# Run the parse_soundfont.py script with the provided input and output files
python3 "$script_path" "$input_file" "$output_file"

# Check if the script ran successfully
if [ $? -eq 0 ]; then
    echo "Script ran successfully. Output written to '$output_file'."
else
    echo "Error: Script failed to run."
    exit 1
fi

# Define the Samples directory based on the input file's directory
samples_dir="$(dirname "$input_file")/Samples"

# Check if the Samples directory exists
if [ ! -d "$samples_dir" ]; then
    echo "Error: Samples directory '$samples_dir' does not exist."
    exit 1
fi

# Call the script to convert all WAV files in the Samples directory to AIFC
./convert_folder_to_aifc.sh "$samples_dir"

# Move all files from Samples to Samples/0 Sound Effects
mkdir -p "$samples_dir/0 Sound Effects"
mv "$samples_dir"/*.wav "$samples_dir/0 Sound Effects/"
mv "$samples_dir"/*.aifc "$samples_dir/0 Sound Effects/"
mv "$samples_dir"/*.zsound "$samples_dir/0 Sound Effects/"

# Create a new folder named 'ootrs' in the input file's directory
ootrs_dir="$(dirname "$input_file")/ootrs"
mkdir -p "$ootrs_dir"

# Copy all .zsound files into the 'ootrs' directory
find "$samples_dir" -name "*.zsound" -exec cp {} "$ootrs_dir" \;

# Generate the .meta file path based on the XML output file name
meta_file="${output_file%.xml}.meta"

# Run the oot_metaLinker.py script with the provided XML file, meta file, track name, and bgm/fanfare
python3 tools/ootr_metaLinker.py "$output_file" "$ootrs_dir/$(basename "$meta_file")" "$track_name" "$bgm_fanfare"

# Define the root directory where this script is located
script_root="$(dirname "$(realpath "$0")")"

# Define paths for output, build, include, and samples directories
output_dir="$script_root/output"
build_dir="$script_root/build/assets"
include_dir="$script_root/include"
samples_dir="$script_root/Samples"

# Ensure the directories exist
mkdir -p "$output_dir"
mkdir -p "$build_dir"
mkdir -p "$include_dir"

# Process the XML into binaries with tools/assemble_sound.py
python3 tools/assemble_sound.py "$output_dir" "$build_dir" "$include_dir" "$samples_dir" --build-bank

# Check if the binaries were built successfully
if [ $? -eq 0 ]; then
    echo "Binaries built successfully."
else
    echo "Error: Failed to build binaries."
    exit 1
fi

# Call to extract_bankbinaries.py on a file in build/assets/soundfonts
soundfont_file="$(find "$build_dir/soundfonts" -type f -name "*.o" | head -n 1)"
if [ -f "$soundfont_file" ];then
    python3 tools/extract_bankbinaries.py "$soundfont_file" "$output_file"
else
    echo "Error: No .o files found in $build_dir/soundfonts"
    exit 1
fi

# Move and rename extracted_data.bin to "output_file.zbank" in the ootrs directory
zbank_file="$ootrs_dir/$(basename "${output_file%.xml}.zbank")"
mv "$(dirname "$0")/extracted_data.bin" "$zbank_file"
echo "Renamed and moved extracted_data.bin to $zbank_file"

# Move and rename output.meta to "output_file.bankmeta" in the ootrs directory
bankmeta_file="$ootrs_dir/$(basename "${output_file%.xml}.bankmeta")"
mv "$(dirname "$0")/output.meta" "$bankmeta_file"
echo "Renamed and moved output.meta to $bankmeta_file"

# Rename the .seq file to match the naming convention and move it to ootrs
seq_file_renamed="$ootrs_dir/$(basename "${output_file%.xml}.seq")"
cp "$seq_file" "$seq_file_renamed"
echo "Renamed and copied .seq file to $seq_file_renamed"

# Delete all .zsound, .wav, and .aifc files from Samples and Samples/0 Sound Effects
find "$samples_dir" -name "*.zsound" -delete
find "$samples_dir" -name "*.wav" -delete
find "$samples_dir" -name "*.aifc" -delete
find "$samples_dir/0 Sound Effects" -name "*.zsound" -delete
find "$samples_dir/0 Sound Effects" -name "*.wav" -delete
find "$samples_dir/0 Sound Effects" -name "*.aifc" -delete

# Delete every file within the build, output, and include directories, but keep the folders
find "$build_dir" -type f -delete
find "$output_dir" -type f -delete
find "$include_dir" -type f -delete

echo "Clean-up completed: .zsound, .wav, .aifc files deleted, and build, output, and include directories cleaned."

# Archive the ootrs directory using ootrs_zip.py
python3 tools/ootrs_zip.py "$ootrs_dir" "$seq_file"

# Remove the .zip extension from the archived file in the output directory
for file in "$output_dir"/*.zip; do
    mv "$file" "${file%.zip}"
done

# Clean up the ootrs directory
rm -r "$ootrs_dir"
