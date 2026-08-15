#!/usr/bin/env python3
import os
from pypdf import PdfReader

PASSWORD = "MDEJ2812"
PDF_PATH = "/Users/ejazanwar/Documents/Gmail Automations/Flipkart Axis Statements/Flipkart_Axis_Statement_May_2026.pdf"

reader = PdfReader(PDF_PATH)
if reader.is_encrypted:
    reader.decrypt(PASSWORD)
    
text = "\n".join(page.extract_text() or "" for page in reader.pages)
output_path = "/Users/ejazanwar/Documents/Gmail Automations/Flipkart Axis Statements/May_2026_raw.txt"
with open(output_path, "w") as f:
    f.write(text)
print(f"Extracted {len(text)} characters to {output_path}")
