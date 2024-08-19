import shutil
import os
import sys

def archive_ootrs(ootrs_dir, seq_filename):
    # Define the archive name based on the .seq filename
    base_name = os.path.splitext(os.path.basename(seq_filename))[0]
    archive_name = f"{base_name}.ootrs"

    # Define the output path for the zip file
    output_path = os.path.join("output", archive_name)

    # Create a zip archive of the ootrs directory
    shutil.make_archive(output_path, 'zip', ootrs_dir)

    # Rename the .zip to .ootrs.zip
    final_output_path = f"{output_path}.zip"
    os.rename(f"{output_path}.zip", final_output_path)

    # Print the path where the archive was saved
    print(f"Archived ootrs directory to {final_output_path}")

    # Clean out the ootrs directory
    shutil.rmtree(ootrs_dir)
    os.makedirs(ootrs_dir)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py <ootrs_dir> <seq_filename>")
        sys.exit(1)

    ootrs_dir = sys.argv[1]
    seq_filename = sys.argv[2]

    archive_ootrs(ootrs_dir, seq_filename)
