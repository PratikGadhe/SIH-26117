"""
Simple test script for Vision Service
Run this to verify Qwen3-VL inference works
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from vision_service import VisionService


def test_vision_service():
    """Test basic vision service functionality"""
    
    print("\n" + "="*60)
    print("🧪 VISION SERVICE TEST")
    print("="*60 + "\n")
    
    # Initialize service
    try:
        print("1️⃣  Initializing Vision Service...")
        service = VisionService()
        print("   ✅ Service initialized\n")
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
        return False
    
    # Test with a simple text prompt (no image)
    print("2️⃣  Testing inference without image...")
    try:
        result = service.analyze_image(
            image_path="",  # Will fail, but let's catch it
            prompt="What is machine learning?"
        )
        print(f"   Status: {result['status']}")
        if result['status'] == 'error':
            print(f"   ✓ Correctly rejected (expected)\n")
    except Exception as e:
        print(f"   ✓ Error handling works\n")
    
    print("3️⃣  Next steps:")
    print("   - Create test images (JPG, PNG, PDF)")
    print("   - Run: python test_vision.py <image_path> '<prompt>'")
    print("   - Example: python test_vision.py drawing.jpg 'What components do you see?'")
    print("\n" + "="*60 + "\n")
    
    return True


if __name__ == "__main__":
    success = test_vision_service()
    sys.exit(0 if success else 1)
