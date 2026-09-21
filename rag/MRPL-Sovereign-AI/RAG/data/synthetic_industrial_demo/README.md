# Synthetic Industrial Demonstration Knowledge Pack

## 1. Dataset Name
`synthetic_industrial_demo`

## 2. Purpose
This dataset provides a small, controlled, reproducible corpus of synthetic technical engineering documents to demonstrate and verify the local RAG (Retrieval-Augmented Generation) pipeline in Project VYASA (SIH-26117). It enables testing of document ingestion, semantic chunking, local sentence embeddings, vector retrieval, and model grounding without exposing or relying on confidential or proprietary refinery manuals.

## 3. Synthetic Status & Mandatory Disclaimer
> **SYNTHETIC DEMONSTRATION DATA — NOT FOR REAL INDUSTRIAL OPERATION**  
> All documents in this dataset are fictional test data created exclusively for the VYASA prototype. They do **not** represent actual refinery operating procedures, official engineering standards, regulatory requirements, equipment manufacturer specifications, or statutory safety instructions.  
> All numerical limits, operating parameters, and threshold values are **example synthetic demonstration values** only.

## 4. Documents Included

| File Name | Pages | Primary Domain & Coverage | Synthetic Disclaimer |
| :--- | :---: | :--- | :---: |
| `synthetic_flare_system_guideline.pdf` | 3 | Flare header concepts, purge gas terminology, example hydrogen flare purge velocity limits, alarm thresholds. | Present on Page 1 & Section 2 |
| `synthetic_pump_operating_sop.pdf` | 3 | Centrifugal pump operations, example pump P-102 vibration thresholds, bearing temperature observations, maintenance indicators. | Present on Page 1 |
| `synthetic_compressor_operating_sop.pdf` | 3 | Centrifugal compressor C-202 parameters, example vibration thresholds, operating temperatures, anti-surge observations. | Present on Page 1 |
| `synthetic_pid_equipment_reference.pdf` | 3 | P&ID equipment tagging conventions (P, C, V, FS), standard symbols for valves, pumps, compressors, and tag relationships. | Present on Page 1 |

## 5. Fictional Demonstration Values Notice
Every engineering number in this dataset is designated as an **Example / Synthetic Demonstration Value**:
- Flare Purge Velocity: Example synthetic demonstration minimum continuous purge velocity for hydrogen seal = 0.03 m/s; recommended continuous operating range = 0.03 to 0.15 m/s.
- Pump P-102 Vibration: Example synthetic demonstration warning threshold = > 5.0 mm/s; critical trip threshold = > 7.5 mm/s.
- Compressor C-202 Vibration: Example synthetic demonstration warning threshold = > 4.5 mm/s; critical trip threshold = > 7.0 mm/s.
- Valve Symbols: Opposing triangles meeting at a common apex (bowtie / hourglass symbol).

## 6. Intended Demonstration Queries
1. **Flare Purge Query:** *"Search the local knowledge base for hydrogen flare purge velocity limits."*  
   → Targets `synthetic_flare_system_guideline.pdf` Page 2.
2. **Pump Threshold Query:** *"What is the example synthetic vibration warning threshold for pump P-102?"*  
   → Targets `synthetic_pump_operating_sop.pdf` Page 2.
3. **Compressor Observations Query:** *"What example operating observations are documented for the compressor?"*  
   → Targets `synthetic_compressor_operating_sop.pdf` Pages 2–3.
4. **P&ID Valve Symbol Query:** *"What symbol represents a valve in the synthetic P&ID reference?"*  
   → Targets `synthetic_pid_equipment_reference.pdf` Page 2.
5. **Anti-Hallucination Negative Queries:**
   - *"According to the synthetic documents, what is the catalyst replacement interval for a hydrotreater?"* → Not in dataset; returns no relevant findings.
   - *"What is the exact statutory regulatory limit for flare purge velocity?"* → System must clarify that synthetic examples are not statutory limits.

