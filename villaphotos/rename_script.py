import os
import shutil

mapping = {
    "IMG_7233.jpg": "living_room_1.jpg",
    "IMG_7234.jpg": "living_room_2.jpg",
    "IMG_7235.jpg": "dining_area_1.jpg",
    "IMG_7236.jpg": "dining_area_2.jpg",
    "IMG_7237.jpg": "kitchen_1.jpg",
    "IMG_7238.jpg": "kitchen_2.jpg",
    "IMG_7239.jpg": "bedroom_1_1.jpg",
    "IMG_7241.jpg": "bedroom_1_2.jpg",
    "IMG_7242.jpg": "bedroom_2_1.jpg",
    "IMG_7243.jpg": "bedroom_2_2.jpg",
    "IMG_7245.jpg": "bedroom_3_1.jpg",
    "IMG_7246.jpg": "bedroom_3_2.jpg",
    "IMG_7247.jpg": "bedroom_4_1.jpg",
    "IMG_7248.jpg": "bedroom_4_2.jpg",
    "IMG_7250.jpg": "bedroom_4_3.jpg",
    "IMG_7251.jpg": "bathroom_1.jpg",
    "IMG_7252.jpg": "bathroom_1_detail.jpg",
    "IMG_7253.jpg": "outdoor_bbq.jpg",
    "IMG_7254.jpg": "exterior_driveway.jpg",
    "IMG_7255.jpg": "outdoor_patio_1.jpg",
    "IMG_7256.jpg": "outdoor_bar_1.jpg",
    "IMG_7257.jpg": "outdoor_bar_2.jpg",
    "IMG_7258.jpg": "outdoor_patio_2.jpg",
    "IMG_7259.jpg": "outdoor_patio_3.jpg",
    "IMG_7260.jpg": "exterior_1.jpg",
    "IMG_7261.jpg": "view_sea_1.jpg",
    "IMG_7263.jpg": "exterior_street_1.jpg",
    "IMG_7264.jpg": "view_sea_2.jpg"
}

target_dir = r"C:\Users\mar1\Documents\testing\villaphotos\extracted"

for old_name, new_name in mapping.items():
    old_path = os.path.join(target_dir, old_name)
    new_path = os.path.join(target_dir, new_name)
    if os.path.exists(old_path):
        try:
            shutil.copy(old_path, new_path)
            print(f"Copied {old_name} to {new_name}")
        except Exception as e:
            print(f"Failed to copy {old_name}: {e}")
    elif os.path.exists(new_path):
        print(f"File {new_name} already exists.")
    else:
        print(f"Source file {old_name} not found.")
