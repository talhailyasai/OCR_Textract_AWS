"""
Configuration settings for the Swedish PDF processor.
"""
import os
from pathlib import Path

# AWS settings
AWS_REGION = 'eu-west-1'  # Stockholm region (best for Swedish documents)
AWS_PROFILE = os.environ.get('AWS_PROFILE', 'default')

# Project paths
PROJECT_ROOT = Path(__file__).parent
OUTPUT_DIR = PROJECT_ROOT / 'output'
TEMP_DIR = PROJECT_ROOT / 'temp'

# Create directories if they don't exist
OUTPUT_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

# PDF processing settings
PDF_DPI = 300  # Higher DPI for better OCR quality
IMAGE_FORMAT = 'PNG'
CONTRAST_FACTOR = 1.5  # Increase contrast by 50%

# Textract settings
TEXTRACT_FEATURES = ['TABLES', 'FORMS']  # Enable table and form recognition

# Swedish language settings
SWEDISH_CHARS = ['å', 'ä', 'ö', 'Å', 'Ä', 'Ö']