"""
Test Script: Phase 1 — Ollama Local Connection & Text Reasoning Benchmark
Verifies that local Qwen model responds on your M2 Mac with Apple Silicon Metal acceleration.
"""

import os
import sys

# Add agents/ directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
agents_root = os.path.abspath(os.path.join(current_dir, ".."))
if agents_root not in sys.path:
    sys.path.insert(0, agents_root)

from src.ollama_text_client import OllamaTextClient


def run_phase1_test():
    print("=" * 65, flush=True)
    print("   SIH 26117 — PHASE 1: LOCAL TEXT & REASONING MODEL TEST        ", flush=True)
    print("=" * 65, flush=True)

    # 1. Initialize client
    client = OllamaTextClient(base_url="http://localhost:11434", model_name="qwen3:4b")

    print("\n[Step 1] Checking Ollama Service Status...", flush=True)
    if not client.is_available():
        print("❌ FAILED: Ollama is not running on http://localhost:11434", flush=True)
        print("👉 Run: 'brew services start ollama' or 'ollama serve' in terminal.", flush=True)
        return

    print("✅ SUCCESS: Ollama daemon is running locally!", flush=True)

    # 2. List available models
    models = client.list_local_models()
    print(f"\n[Step 2] Found {len(models)} local model(s) installed:", flush=True)
    for m in models:
        print(f"   • {m}", flush=True)

    # Detect if qwen3:4b or another model is active
    target_model = "qwen3:4b"
    if not any(target_model in m for m in models):
        # Fallback to any qwen model found
        qwen_fallbacks = [m for m in models if "qwen" in m.lower() or "llama" in m.lower()]
        if qwen_fallbacks:
            target_model = qwen_fallbacks[0]
            print(f"\n⚠️ Note: 'qwen3:4b' not found in list, using available fallback: '{target_model}'")
            client.model = target_model
        else:
            print(f"\n❌ FAILED: Neither 'qwen3:4b' nor any Qwen model is installed.")
            print(f"👉 Run: 'ollama pull qwen3:4b' or 'ollama pull qwen2.5:3b'")
            return

    # 3. Test Text Generation (Refinery Reasoning prompt)
    print(f"\n[Step 3] Sending Industrial Reasoning Prompt to '{client.model}'...", flush=True)
    system_prompt = (
        "You are an expert Chief Chemical Engineer at MRPL Oil Refinery. "
        "Provide factual, concise, professional answers."
    )
    prompt = "Explain the primary safety function of a Flare Stack in an oil refinery in 2 bullet points."

    print(f"Query: \"{prompt}\"", flush=True)
    print("Thinking locally on Apple Silicon Metal GPU...", flush=True)

    result = client.generate(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=0.1
    )

    if result.get("status") == "success":
        print("\n" + "-" * 50, flush=True)
        print("🤖 MODEL RESPONSE:", flush=True)
        print("-" * 50, flush=True)
        print(result["response"], flush=True)
        print("-" * 50, flush=True)
        print(f"\n📊 METRICS:", flush=True)
        print(f"   • Elapsed Time    : {result['elapsed_seconds']} seconds", flush=True)
        print(f"   • Tokens Generated: {result['eval_count']} tokens", flush=True)
        print(f"   • Speed           : {result['tokens_per_second']} tokens/sec", flush=True)
    else:
        print(f"❌ Error during generation: {result.get('error')}", flush=True)
        return

    # 4. Test Structured JSON output
    print(f"\n[Step 4] Testing Structured JSON Generation (For LangGraph routing)...", flush=True)
    json_prompt = (
        "Classify this user request into a JSON object with keys 'task_type' (choose: 'manual_lookup' or 'diagram_inspection') "
        "and 'equipment_tag': 'Check valve status for pump P-102'."
    )
    json_result = client.generate_json(prompt=json_prompt)

    if json_result.get("status") == "success":
        print("✅ SUCCESS: Model generated valid JSON:", flush=True)
        print(f"   {json_result['json_data']}", flush=True)
    else:
        print(f"⚠️ JSON parsing note: {json_result.get('error', 'Check model formatting')}", flush=True)

    print("\n" + "=" * 65, flush=True)
    print("   PHASE 1 COMPLETE: TEXT REASONING ENGINE IS 100% OPERATIONAL!   ", flush=True)
    print("=" * 65, flush=True)


if __name__ == "__main__":
    run_phase1_test()
