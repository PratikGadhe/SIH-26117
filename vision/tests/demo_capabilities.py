"""
Comprehensive demo of all Vision Service capabilities
Shows all 4 analysis types
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Add to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.vision_service import VisionService
import json


def create_sample_images():
    """Create sample images for different use cases"""
    
    sample_dir = Path(__file__).parent / "sample_images"
    sample_dir.mkdir(exist_ok=True)
    
    # 1. Create a P&ID-like drawing
    img = Image.new('RGB', (500, 400), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw a simple process flow diagram
    draw.rectangle([50, 50, 100, 100], outline='blue', width=2, fill='lightblue')
    draw.text((55, 70), 'PUMP', fill='black')
    
    draw.line([(100, 75), (150, 75)], fill='blue', width=2)
    
    draw.rectangle([150, 50, 200, 100], outline='green', width=2, fill='lightgreen')
    draw.text((155, 70), 'HEAT', fill='black')
    
    draw.line([(200, 75), (250, 75)], fill='blue', width=2)
    
    draw.rectangle([250, 50, 300, 100], outline='red', width=2, fill='lightcoral')
    draw.text((255, 70), 'VALVE', fill='black')
    
    # Add some labels
    draw.text((50, 150), 'P&ID Diagram', fill='black')
    draw.text((50, 180), 'Simplified Process Flow:', fill='blue')
    draw.text((50, 210), 'Pump -> Heat Exchanger -> Valve', fill='green')
    
    img.save(sample_dir / 'pid_diagram.png')
    print(f"✅ Created: pid_diagram.png")
    
    return sample_dir


def main():
    print("\n" + "="*70)
    print("🎯 VISION SERVICE - COMPREHENSIVE DEMO")
    print("="*70 + "\n")
    
    # Setup
    sample_dir = create_sample_images()
    
    try:
        service = VisionService()
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return False
    
    # Demo 1: Basic Image Analysis
    print("\n" + "-"*70)
    print("DEMO 1️⃣  BASIC IMAGE ANALYSIS")
    print("-"*70)
    
    demo1_path = str(sample_dir / "pid_diagram.png")
    demo1_prompt = "Describe what you see in this process diagram."
    
    print(f"\n📷 Image: pid_diagram.png")
    print(f"❓ Prompt: {demo1_prompt}\n")
    
    result1 = service.analyze_image(demo1_path, demo1_prompt)
    print(f"✅ Status: {result1['status']}")
    if result1['status'] == 'success':
        print(f"📊 Analysis:\n{result1['analysis']}")
    else:
        print(f"❌ Error: {result1.get('error', 'Unknown error')}")
    
    # Demo 2: Engineering Drawing Analysis
    print("\n" + "-"*70)
    print("DEMO 2️⃣  ENGINEERING DRAWING ANALYSIS")
    print("-"*70)
    
    print(f"\n📷 Image: pid_diagram.png")
    print("❓ Prompt: Analyze as engineering drawing\n")
    
    result2 = service.analyze_drawing(demo1_path)
    print(f"✅ Status: {result2['status']}")
    if result2['status'] == 'success':
        print(f"📊 Analysis:\n{result2['analysis']}")
    else:
        print(f"❌ Error: {result2.get('error', 'Unknown error')}")
    
    # Demo 3: Text Extraction
    print("\n" + "-"*70)
    print("DEMO 3️⃣  TEXT EXTRACTION (OCR)")
    print("-"*70)
    
    print(f"\n📷 Image: pid_diagram.png")
    print("❓ Task: Extract all text\n")
    
    try:
        text = service.extract_text_from_image(demo1_path)
        print(f"✅ Extracted Text:\n{text}")
    except Exception as e:
        print(f"⚠️  {e}")
    
    # Demo 4: Full JSON Response
    print("\n" + "-"*70)
    print("DEMO 4️⃣  FULL JSON RESPONSE STRUCTURE")
    print("-"*70)
    
    print(f"\n📋 Complete response structure:\n")
    print(json.dumps(result1, indent=2))
    
    # Summary
    print("\n" + "="*70)
    print("✅ DEMO COMPLETE")
    print("="*70)
    print("\nKey Capabilities Demonstrated:")
    print("  ✓ Basic image analysis")
    print("  ✓ Engineering drawing recognition")
    print("  ✓ Text extraction (OCR)")
    print("  ✓ Structured JSON responses")
    print("  ✓ No external API calls (100% local)")
    print("\n" + "="*70 + "\n")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n🛑 Demo interrupted")
        sys.exit(1)
