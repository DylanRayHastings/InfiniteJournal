import os

def count_lines_in_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return sum(1 for _ in f)
    except (UnicodeDecodeError, FileNotFoundError):
        return 0

def count_total_lines(directory):
    total_lines = 0
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                total_lines += count_lines_in_file(file_path)
    return total_lines

if __name__ == "__main__":
    folder_to_scan = os.getcwd()  # Use the current directory
    total = count_total_lines(folder_to_scan)
    print(f"Total lines of Python code in '{folder_to_scan}': {total}")
