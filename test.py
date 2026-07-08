from pathlib import Path

# Define the path to your file (replace with your folder and file name)
file_path = Path("data/placement.csv")

try:
    # Open and print the contents
    with open(file_path, "r", encoding="utf-8") as file:
        print(file.read())
except FileNotFoundError:
    print(f"Error: The file at {file_path} was not found.")
