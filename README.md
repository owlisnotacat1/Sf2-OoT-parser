# Sf2-OoT-parser
Series of scripts that process a soundfont 2 file and a sequence file into the Ocarina of Time Randomizer music format

## Requirements
- Python 3.10 or higher
- Windows Subsystem for Linux (Known as WSL; requires Windows 10 Build 19041 and higher or Windows 11)
- A Linux distro from WSL (WSL should install Ubuntu by default)

### How to Use

To use the scripts follow the steps below:
1. Open the directory containing the `generate_ootrs.sh` script.
2. `Shift + Right-Click` to open the Windows extended context menu, then select "Open Linux shell here".
3. In the Linux terminal that opens, run the following command:
```
./generate_ootrs.sh [path_to_sf2] [path_to_seq] [meta_seq_name] [meta_seq_type]
```

The command arguments are as follows:
| CLI Argument | Description |
| :-: | --- |
| `[path_to_sf2]` | Path to the `.sf2` file. It's easiest to place the file in the root directory and just input the filename.<br>- Example: `"SOUNDFONT_FILE.sf2"` |
| `[path_to_seq]` | Path to the sequence file to be packed into the `.ootrs` file. It's easiest to place this file in the root directory and just input the filename.<br>- Example: `"OOT_SEQUENCE.aseq"` |
| `[meta_seq_name]` | The name for the sequence to be used in the `.meta` file contained within the packed `.ootrs` file. |
| `[meta_seq_type]` | Whether the sequence is background music or a fanfare/musical effect. For background music use `"bgm"`, and for fanfares use `"fanfare"`. |

※ *CLI arguments with text containing spaces must be contained within quotation marks.*

### Example Usage  
BGM
```
./generate_ootrs.sh "Super Mario 64.sf2" "Bob-omb Battlefield.seq" "Super Mario 64 — Bob-omb Battlefield" "bgm"
```
Fanfare
```
./generate_ootrs.sh "Super Mario 64.sf2" "Got a Star.seq" "Super Mario 64 — Got a Star!" "fanfare"
```

