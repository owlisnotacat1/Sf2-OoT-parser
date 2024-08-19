#!/usr/bin/env bash

# Check if the input directory is provided
if [[ -z $1 ]]; then
    echo 'Usage: <wav directory>'
    exit 1
fi

input_dir=$1

# Check if the input directory exists
if [[ ! -d "${input_dir}" ]]; then
    echo "Error: Input directory ${input_dir} does not exist."
    exit 1
fi

# Enable nullglob to handle the case where no .wav files are found
shopt -s nullglob

# Iterate through all .wav files in the input directory
for wav_file in "${input_dir}"/*.wav; do
    # Generate the corresponding .aifc file name
    aifc_file="${wav_file%.wav}.aifc"

    # Call the conversion script with the wav file and aifc file as arguments
    echo "Converting ${wav_file} to ${aifc_file}"
    ./convert_to_aifc.sh "${wav_file}" "${aifc_file}"
done

# Call the Python script with the input directory as both arguments
echo "Running rip_zsound.py with directory ${input_dir}"
python3 tools/rip_zsound.py "${input_dir}" "${input_dir}"
