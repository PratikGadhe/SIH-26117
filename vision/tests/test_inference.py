"""
Test inference with actual Qwen3-VL model
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import directly from modules
from vision.src.vision_service import VisionService
import json


def main():
    print("\n" + "="*60)
    print("🧪 VISION SERVICE INFERENCE TEST")
    print("="*60 + "\n")
    
    # Initialize
    print("1️⃣  Initializing Vision Service...")
    try:
        service = VisionService()
        print("   ✅ Service initialized\n")
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
        return False
    
    # Test image path
    test_image = Path(__file__).parent / "sample_images" / "test_diagram.png"
    
    if not test_image.exists():
        print(f"   ❌ Test image not found: {test_image}\n")
        return False
    
    # Test inference
    print("2️⃣  Testing inference with test image...")
    print(f"   Image: {test_image.name}")
    print("   Prompt: What do you see in this diagram?\n")
    
    try:
        result = service.analyze_image(
            str(test_image),
            "What do you see in this diagram? List all components, shapes, and text labels."
        )
        
        print(f"   Status: {result['status']}")
        print(f"   Confidence: {result.get('confidence', 0):.2f}")
        print(f"\n   Analysis:")
        print(f"   {result['analysis']}")
        print(f"\n   ✅ Inference successful!")
        
        # Pretty print full result
        print(f"\n3️⃣  Full Response (JSON):")
        print(json.dumps(result, indent=2))
        
        return True
    
    except Exception as e:
        print(f"   ❌ Inference failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
