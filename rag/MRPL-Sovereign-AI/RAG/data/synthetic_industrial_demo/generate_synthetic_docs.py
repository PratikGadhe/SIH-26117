"""
Generator script for synthetic industrial demonstration documents.
Produces 4 small, controlled synthetic PDFs for the VYASA RAG prototype.
All documents are strictly marked as synthetic demonstration data.
"""

import os
import pymupdf

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

DISCLAIMER_TEXT = (
    "SYNTHETIC DEMONSTRATION DATA\n"
    "This document is fictional test data created for the VYASA prototype.\n"
    "It is not an actual operating procedure, engineering standard,\n"
    "regulatory requirement, or safety instruction.\n"
    "All numerical values are example synthetic demonstration values only.\n"
)


def create_pdf(filename: str, pages_content: list[dict]):
    filepath = os.path.join(OUTPUT_DIR, filename)
    doc = pymupdf.open()

    for p_info in pages_content:
        page = doc.new_page(width=595, height=842)  # A4 standard
        rect = pymupdf.Rect(45, 45, 550, 795)

        # Build page text
        header = (
            f"{p_info['title']}\nPage {p_info['page_num']} of {len(pages_content)}\n"
        )
        separator = "=" * 60 + "\n\n"

        full_text = header + separator
        if p_info.get("include_disclaimer", False):
            full_text += f"[MANDATORY NOTICE]\n{DISCLAIMER_TEXT}\n" + "-" * 50 + "\n\n"

        full_text += p_info["body"]

        # Insert text box into page
        rc = page.insert_textbox(rect, full_text, fontsize=10, fontname="helv")
        if rc < 0:
            print(
                f"WARNING: Text overflow on {filename} page {p_info['page_num']} (rc={rc})"
            )

    doc.save(filepath)
    doc.close()
    print(f"Generated: {filename} ({len(pages_content)} pages)")


def generate_all_documents():
    # Document 1: Flare System Guideline
    flare_pages = [
        {
            "page_num": 1,
            "title": "SYNTHETIC DEMONSTRATION GUIDELINE: REFINERY FLARE SYSTEM OPERATIONS",
            "include_disclaimer": True,
            "body": (
                "SECTION 1: SCOPE, TERMINOLOGY & CONCEPTS\n\n"
                "1.1 Scope & Purpose\n"
                "This document establishes synthetic terminology and operational concepts for elevated "
                "refinery flare headers, knockout drums, and water seal drums in a fictional process plant.\n\n"
                "1.2 Flare Header Terminology\n"
                "- Flare Header: Main collecting pipe conveying emergency relief gases to the flare stack.\n"
                "- Knockout Drum (KOD): Dedicated separation vessel removing entrained liquid droplets prior to combustion.\n"
                "- Water Seal Drum: Liquid barrier preventing flame flashback from the stack into upstream headers.\n"
                "- Flare Tip Seal: Purge reduction seal positioned at the stack discharge.\n"
                "- Continuous Purge Gas: Continuous supply of non-condensable gas maintaining positive outflow.\n\n"
                "1.3 Purge Gas Concept\n"
                "Positive purge gas flow is continuously required through the flare header to maintain positive internal "
                "pressure, counteract wind-induced atmospheric air ingress, and eliminate the possibility of forming an "
                "explosive hydrocarbon-oxygen mixture inside the flare stack riser.\n"
            ),
        },
        {
            "page_num": 2,
            "title": "SYNTHETIC DEMONSTRATION GUIDELINE: FLARE PURGE VELOCITY LIMITS",
            "include_disclaimer": False,
            "body": (
                "SECTION 2: PURGE VELOCITY OPERATING LIMITS (SYNTHETIC DEMONSTRATION)\n\n"
                "2.1 Purge Gas Velocity Concepts & Example Operational Limits\n"
                "Purge gas flow rates must be measured continuously at the stack base and seal discharge.\n\n"
                "Example / Synthetic Demonstration Values:\n"
                "- Example synthetic demonstration minimum continuous purge velocity for fuel gas header: 0.04 m/s.\n"
                "- Example synthetic demonstration minimum continuous purge velocity for hydrogen flare seal: 0.03 m/s.\n"
                "- Example synthetic demonstration recommended continuous operating velocity range: 0.03 m/s to 0.15 m/s.\n"
                "- Example synthetic demonstration maximum design velocity limit during emergency relief depressurization: 12.0 m/s.\n\n"
                "2.2 Regulatory & Legal Notice Regarding Limits\n"
                "IMPORTANT: The figures stated above are example synthetic demonstration values created exclusively for "
                "software agent testing and verification within the VYASA prototype. They do NOT represent statutory "
                "regulatory limits, official API 521 standards, or MRPL operating specifications. No real-world regulatory "
                "compliance or operational validity may be inferred from this fictional demonstration document.\n"
            ),
        },
        {
            "page_num": 3,
            "title": "SYNTHETIC DEMONSTRATION GUIDELINE: ALARMS & HEADER OBSERVATIONS",
            "include_disclaimer": False,
            "body": (
                "SECTION 3: ALARM THRESHOLDS & FLARE HEADER OBSERVATIONS\n\n"
                "3.1 Example Alarm & Monitoring Thresholds\n"
                "- Example synthetic demonstration low purge flow alarm: triggered when purge velocity drops below 0.02 m/s.\n"
                "- Example synthetic demonstration pilot flame loss warning: thermocouple reading below 200.0 °C.\n"
                "- Example synthetic demonstration KOD high-high liquid level trip: > 65% liquid volume in knockout drum.\n\n"
                "3.2 Flare Header Observations & Field Safety Practices\n"
                "- Smokeless flaring steam ratio observations: steam injection flow should maintain clear plume without over-steaming.\n"
                "- Header pressure observation: maintain positive pressure above 5.0 mbarg to prevent negative draft.\n"
                "- Visual inspection: observe flare tip flame stability and absence of internal burning signs.\n"
            ),
        },
    ]

    # Document 2: Pump Operating SOP
    pump_pages = [
        {
            "page_num": 1,
            "title": "SYNTHETIC DEMONSTRATION SOP: CENTRIFUGAL PUMP OPERATIONS",
            "include_disclaimer": True,
            "body": (
                "SECTION 1: SCOPE, EQUIPMENT & OPERATING PARAMETERS\n\n"
                "1.1 Scope & Equipment Covered\n"
                "This synthetic procedure covers operational parameters and condition monitoring for centrifugal process "
                "pumps in boiler feed and hydrocarbon transfer service, specifically example equipment unit pump P-101 "
                "and pump P-102.\n\n"
                "1.2 Primary Operating Parameters\n"
                "- Rated volumetric flow capacity: 120 m3/h at rated RPM.\n"
                "- Example synthetic demonstration suction pressure: 2.5 bar gauge.\n"
                "- Example synthetic demonstration discharge pressure: 14.2 bar gauge.\n"
                "- Mechanical seal flush configuration: API Plan 11 with cooling jacket.\n"
            ),
        },
        {
            "page_num": 2,
            "title": "SYNTHETIC DEMONSTRATION SOP: PUMP P-102 MONITORING LIMITS",
            "include_disclaimer": False,
            "body": (
                "SECTION 2: PUMP P-102 VIBRATION & TEMPERATURE THRESHOLDS\n\n"
                "2.1 Vibration Monitoring Limits for Pump P-102\n"
                "Condition monitoring sensors measure overall velocity RMS on drive-end and non-drive-end bearings.\n\n"
                "Example / Synthetic Demonstration Values for Pump P-102:\n"
                "- Normal baseline vibration: < 2.8 mm/s RMS.\n"
                "- Example synthetic demonstration vibration warning threshold for pump P-102: vibration > 5.0 mm/s.\n"
                "- Example synthetic demonstration critical vibration trip threshold for pump P-102: vibration > 7.5 mm/s.\n\n"
                "2.2 Bearing Temperature Observations for Pump P-102\n"
                "- Normal operating bearing temperature: 60.0 °C to 75.0 °C.\n"
                "- Example synthetic demonstration bearing temperature warning threshold: > 80.0 °C.\n"
                "- Example synthetic demonstration bearing temperature critical trip threshold: > 95.0 °C.\n"
            ),
        },
        {
            "page_num": 3,
            "title": "SYNTHETIC DEMONSTRATION SOP: PUMP STARTUP, SHUTDOWN & MAINTENANCE",
            "include_disclaimer": False,
            "body": (
                "SECTION 3: STARTUP, SHUTDOWN OBSERVATIONS & MAINTENANCE INDICATORS\n\n"
                "3.1 Pre-Startup Verification Checklist\n"
                "- Confirm seal flush flow and vent casing to eliminate trapped air or vapor.\n"
                "- Check lubricating oil level in bearing housing sight glass (must be at mid-level 50%).\n"
                "- Rotate pump shaft manually to verify free rotation without binding.\n\n"
                "3.2 Abnormal Operating Observations & Maintenance Indicators\n"
                "- Cavitation noise: distinctive rattling or gravel-sound in casing indicates insufficient NPSH available.\n"
                "- Mechanical seal leakage: example synthetic observation limit of > 5 drops/minute indicates seal wear requiring scheduled overhaul.\n"
                "- Routine maintenance interval: example synthetic observation inspection every 2,000 running hours.\n"
            ),
        },
    ]

    # Document 3: Compressor Operating SOP
    compressor_pages = [
        {
            "page_num": 1,
            "title": "SYNTHETIC DEMONSTRATION SOP: CENTRIFUGAL COMPRESSOR OPERATIONS",
            "include_disclaimer": True,
            "body": (
                "SECTION 1: SCOPE, EQUIPMENT & OPERATING PARAMETERS\n\n"
                "1.1 Scope & Equipment Covered\n"
                "This synthetic procedure governs the condition monitoring, routine operation, and abnormal conditions "
                "for multistage centrifugal recycle gas compressors, specifically example equipment unit compressor C-201 "
                "and compressor C-202.\n\n"
                "1.2 Core Operating Parameters (Synthetic Demonstration Values)\n"
                "- Example synthetic observation suction pressure: 18.0 bar gauge.\n"
                "- Example synthetic observation discharge pressure: 45.0 bar gauge.\n"
                "- Nominal operating shaft speed: 9,800 RPM.\n"
            ),
        },
        {
            "page_num": 2,
            "title": "SYNTHETIC DEMONSTRATION SOP: COMPRESSOR C-202 LIMITS & OBSERVATIONS",
            "include_disclaimer": False,
            "body": (
                "SECTION 2: COMPRESSOR C-202 THRESHOLDS & OPERATING OBSERVATIONS\n\n"
                "2.1 Vibration Limits for Compressor C-202\n"
                "Example / Synthetic Demonstration Values for Compressor C-202:\n"
                "- Normal baseline vibration: < 3.0 mm/s RMS.\n"
                "- Example synthetic demonstration warning threshold for compressor C-202: vibration > 4.5 mm/s.\n"
                "- Example synthetic demonstration critical shutdown trip threshold for compressor C-202: vibration > 7.0 mm/s.\n\n"
                "2.2 Temperature & Pressure Operating Observations\n"
                "- Example synthetic demonstration discharge temperature warning limit: > 120.0 °C.\n"
                "- Example synthetic demonstration maximum discharge temperature trip: > 135.0 °C.\n"
                "- Lube oil header supply temperature: example synthetic observation range 40.0 °C to 50.0 °C.\n"
            ),
        },
        {
            "page_num": 3,
            "title": "SYNTHETIC DEMONSTRATION SOP: ABNORMAL CONDITIONS & SURGE OBSERVATIONS",
            "include_disclaimer": False,
            "body": (
                "SECTION 3: ABNORMAL-CONDITION INDICATORS & OPERATING OBSERVATIONS\n\n"
                "3.1 Documented Compressor Operating Observations\n"
                "- Surge Detection: Characterized by rapid flow reversals, violent pressure fluctuations, and acoustic rumbling.\n"
                "- Anti-Surge Controller: Modulates recycle valve to maintain operating point at minimum 10% above surge control line.\n"
                "- Lube Oil Differential Pressure: Example synthetic observation minimum differential pressure of 1.5 bar across filters.\n"
                "- Dry Gas Seal Leakage: Example synthetic observation threshold of > 15.0 Nm3/h primary vent flow requires seal examination.\n"
            ),
        },
    ]

    # Document 4: P&ID Equipment Reference
    pid_pages = [
        {
            "page_num": 1,
            "title": "SYNTHETIC DEMONSTRATION REFERENCE: P&ID SYMBOLS & EQUIPMENT TAGS",
            "include_disclaimer": True,
            "body": (
                "SECTION 1: EQUIPMENT TAGGING CONVENTIONS & CODING STANDARDS\n\n"
                "1.1 Tag Prefix Conventions (Synthetic Demonstration Reference)\n"
                "- P: Pump equipment identifier (e.g., P-101, P-102 in hydrocarbon service).\n"
                "- C: Compressor unit identifier (e.g., C-201, C-202 in recycle gas service).\n"
                "- V: Pressure vessel / drum identifier (e.g., V-301 suction drum, V-305 discharge separator).\n"
                "- FS: Flare stack identifier (e.g., FS-501 elevated emergency flare system).\n"
                "- MOV: Motor-operated valve.\n"
                "- PSV: Pressure safety valve.\n\n"
                "1.2 Drawing Numbering System\n"
                "Drawings in this reference follow the synthetic standard PID-MRPL-SYN-001 through PID-MRPL-SYN-004.\n"
            ),
        },
        {
            "page_num": 2,
            "title": "SYNTHETIC DEMONSTRATION REFERENCE: STANDARD P&ID SYMBOLS",
            "include_disclaimer": False,
            "body": (
                "SECTION 2: STANDARD EQUIPMENT & INSTRUMENT SYMBOLS\n\n"
                "2.1 Pump & Compressor Symbols\n"
                "- Centrifugal Pump Symbol: Represented in standard schematics by a circle with an inscribed tangential discharge triangle pointing towards the discharge line (or represented as a blue square in simplified schematic audits).\n"
                "- Centrifugal Compressor Symbol: Represented by a trapezoid showing flow entering the larger base and exiting the narrower top, indicating gas compression.\n\n"
                "2.2 Valve Symbols\n"
                "- Standard Gate/Globe Valve Symbol: A valve is represented by two opposing triangles meeting at a common apex or central point (commonly known as a bowtie or hourglass symbol, or represented as a red circle in simplified audit diagrams).\n"
                "- Check Valve: Opposing triangles with an internal directional check arrow.\n"
                "- Control Valve: Opposing triangles surmounted by an actuator dome or diaphragm.\n"
            ),
        },
        {
            "page_num": 3,
            "title": "SYNTHETIC DEMONSTRATION REFERENCE: TAG RELATIONSHIPS & FLARE SYMBOLS",
            "include_disclaimer": False,
            "body": (
                "SECTION 3: FLARE SYMBOLS & EQUIPMENT TAG RELATIONSHIPS\n\n"
                "3.1 Flare Stack Symbols\n"
                "- Flare Stack (FS-501): Represented by a vertical continuous line terminating with an open flare burner tip and flame icon.\n"
                "- Knockout Drum (V-308): Vertical cylindrical vessel with inlet deflector baffle and mist eliminator pad.\n\n"
                "3.2 Example Equipment Tag Relationships\n"
                "- Pump P-102 suction line connects directly from Feed Vessel V-301.\n"
                "- Compressor C-202 discharge header feeds directly into High-Pressure Separator V-305.\n"
                "- Emergency relief lines from V-301, V-305, and Compressor C-202 route into the main flare header terminating at Flare Stack FS-501.\n"
            ),
        },
    ]

    create_pdf("synthetic_flare_system_guideline.pdf", flare_pages)
    create_pdf("synthetic_pump_operating_sop.pdf", pump_pages)
    create_pdf("synthetic_compressor_operating_sop.pdf", compressor_pages)
    create_pdf("synthetic_pid_equipment_reference.pdf", pid_pages)


if __name__ == "__main__":
    generate_all_documents()
