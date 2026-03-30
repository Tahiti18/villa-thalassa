import os
import shutil

extracted_dir = r"C:\Users\mar1\Documents\testing\villaphotos\extracted"
final_dir = r"C:\Users\mar1\Documents\testing\villaphotos\final"

if not os.path.exists(final_dir):
    os.makedirs(final_dir)

mapping = {
    # Living Room
    "living_room_1.jpg": "living_room_1.jpg",
    "living_room_2.jpg": "living_room_2.jpg",
    
    # Kitchen
    "kitchen_1.jpg": "kitchen_1.jpg",
    "IMG_7238.jpg": "kitchen_2.jpg",
    
    # Dining
    "IMG_7239.jpg": "dining_1.jpg",
    "dining_area_1.jpg": "dining_2.jpg",
    "dining_area_2.jpg": "dining_3.jpg",
    "IMG_7241.jpg": "dining_4.jpg",
    
    # Bedrooms
    "IMG_7242.jpg": "bedroom_1_1.jpg",  # Canopy Double
    "IMG_7243.jpg": "bedroom_1_2.jpg",  # Canopy Double
    "IMG_7248.jpg": "bedroom_2_1.jpg",  # Blue vase double
    "IMG_7246.jpg": "bedroom_3_1.jpg",  # Twin beds
    "IMG_7247.jpg": "bedroom_4_1.jpg",  # Dark wood double
    "IMG_7250.jpg": "bedroom_4_2.jpg",  # Double baby crib
    "IMG_7245.jpg": "bedroom_generic_1.jpg", # Folded sheets
    
    # Bathrooms
    "IMG_7251.jpg": "bathroom_1.jpg",
    "IMG_7252.jpg": "bathroom_2.jpg",
    
    # Patio & Exterior
    "IMG_7253.jpg": "patio_bbq.jpg",
    "IMG_7254.jpg": "patio_driveway.jpg",
    "IMG_7255.jpg": "patio_table.jpg",
    "IMG_7256.jpg": "patio_bar_1.jpg",
    "IMG_7257.jpg": "patio_bar_2.jpg",
    "IMG_7258.jpg": "patio_pergola_1.jpg",
    "IMG_7259.jpg": "patio_pergola_2.jpg",
    "IMG_7260.jpg": "exterior_house_1.jpg",
    "IMG_7261.jpg": "exterior_view_1.jpg",
    "IMG_7263.jpg": "exterior_street.jpg",
    "IMG_7264.jpg": "exterior_view_2.jpg"
}

for src_name, dst_name in mapping.items():
    src_path = os.path.join(extracted_dir, src_name)
    dst_path = os.path.join(final_dir, dst_name)
    
    if os.path.exists(src_path):
        shutil.copy2(src_path, dst_path)
        print(f"Copied {src_name} -> {dst_name}")
    else:
        print(f"Warning: {src_name} not found!")

print("Reorganization complete.")
