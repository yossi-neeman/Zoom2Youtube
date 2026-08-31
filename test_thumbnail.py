#!/usr/bin/env python3
"""
Test thumbnail generation with custom template
"""
import sys
sys.path.insert(0, '/Users/yossin/workspace/Zoom2Youtube')

from zoom_to_youtube import create_thumbnail
from datetime import datetime

# Test with Hebrew text like in the example
test_text = "חולין קיט"

print("Creating test thumbnail...")

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_filename = f'test_thumbnail_{timestamp}.jpg'

thumbnail_path = create_thumbnail(
    test_text,
    output_filename,
    'graphics_template.jpg'
)

print(f"\n✓ Thumbnail created successfully!")
print(f"Output: {thumbnail_path}")
print(f"Timestamp: {timestamp}")
print("\nYou can view it to check if it matches your example.")
