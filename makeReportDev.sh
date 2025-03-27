#!/bin/bash

source /etc/profile 
#$ -q all.q
#$ -cwd
#$ -N elgato
#$ -l h_vmem=5G

module load miniconda3
conda activate eg1.21.1

# Function to list files of a certain type, excluding specific directories
list_files_of_type() {
  local parent_dir="$1"
  local file_extension="$2"
  # Use find to exclude directories and get file paths
  local file_paths=$(find "$parent_dir"  -type f -name "*$file_extension" -print)
  if [ -z "$file_paths" ]; then
    echo "No files found."
    return 1
  fi
  echo "$file_paths"
}
 
## Usage
parent_directory="/scicomp/home-pure/ptx4/mySandbox/el_gato"
extension=".json"
 
# Get the file paths
file_list=$(list_files_of_type "$parent_directory" "$extension")
 
# If no files were found, exit the script
if [ $? -ne 0 ]; then
  exit 1
fi
 
## Convert the newline-separated file list into an array
IFS=$'\n' read -r -d '' -a file_array <<< "$file_list"
 
## Check if the array is empty before proceeding
if [ ${#file_array[@]} -eq 0 ]; then
  echo "No valid files to process."
  exit 1
fi
 
## Get the current date and time in the desired format
date_str=$(date +'%Y-%m-%d_%H-%M-%S')
 
## Set the output path to the current working directory with the current date and time
output_path="./elgatoBatchReport_${date_str}.pdf"
 
## Execute the Python script with the file list as an argument
~/el_gato/elgato_report.py -i "${file_array[@]}" -o "$output_path" -d --header_file elgatoHeader.txt 
 
