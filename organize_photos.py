import os
import hashlib
import shutil

def get_file_hash(filepath):
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

extracted_dir = r"C:\Users\mar1\Documents\testing\villaphotos\extracted"
unique_dir = r"C:\Users\mar1\Documents\testing\villaphotos\unique"

if not os.path.exists(unique_dir):
    os.makedirs(unique_dir)

unique_hashes = {}

for filename in os.listdir(extracted_dir):
    if not filename.lower().endswith('.jpg'):
        continue
    filepath = os.path.join(extracted_dir, filename)
    file_hash = get_file_hash(filepath)
    
    if file_hash not in unique_hashes:
        unique_hashes[file_hash] = []
    unique_hashes[file_hash].append(filename)

print(f"Found {len(unique_hashes)} unique photos.")

# Let's see the groups
for h, files in unique_hashes.items():
    print(f"Hash {h[:8]}: {files}")
