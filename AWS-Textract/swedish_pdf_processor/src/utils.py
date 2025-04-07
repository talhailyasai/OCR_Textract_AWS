"""
Utility functions for the Swedish PDF processor.
"""
import os
import logging
import json
import csv
import boto3
from pathlib import Path
import pandas as pd
from datetime import datetime

from config import OUTPUT_DIR

logger = logging.getLogger(__name__)

def setup_logging(log_level=logging.INFO):
    """
    Set up logging configuration.
    
    Args:
        log_level: Logging level
    """
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(OUTPUT_DIR / f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        ]
    )

def upload_to_s3(file_path, bucket, object_key=None):
    """
    Upload a file to S3.
    
    Args:
        file_path (str): Path to the file
        bucket (str): S3 bucket name
        object_key (str): S3 object key (optional)
        
    Returns:
        str: S3 object key
    """
    s3_client = boto3.client('s3')
    
    if object_key is None:
        object_key = os.path.basename(file_path)
    
    try:
        s3_client.upload_file(file_path, bucket, object_key)
        logger.info(f"Uploaded {file_path} to s3://{bucket}/{object_key}")
        return object_key
    except Exception as e:
        logger.error(f"Error uploading to S3: {str(e)}")
        raise

def download_from_s3(bucket, object_key, output_path):
    """
    Download a file from S3.
    
    Args:
        bucket (str): S3 bucket name
        object_key (str): S3 object key
        output_path (str): Local output path
        
    Returns:
        str: Local file path
    """
    s3_client = boto3.client('s3')
    
    try:
        s3_client.download_file(bucket, object_key, output_path)
        logger.info(f"Downloaded s3://{bucket}/{object_key} to {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error downloading from S3: {str(e)}")
        raise

def save_tables_to_excel(tables, output_path):
    """
    Save tables to Excel file, one sheet per table.
    
    Args:
        tables (list): List of 2D table data
        output_path (str): Output file path
    """
    if not tables:
        logger.warning("No tables to save to Excel")
        return
    
    output_path = Path(output_path)
    excel_path = output_path.with_suffix('.xlsx')
    
    try:
        with pd.ExcelWriter(excel_path) as writer:
            for i, table in enumerate(tables):
                df = pd.DataFrame(table)
                # Use first row as header if table has more than one row
                if len(table) > 1:
                    df = pd.DataFrame(table[1:], columns=table[0])
                df.to_excel(writer, sheet_name=f'Table_{i+1}', index=False)
        
        logger.info(f"Saved tables to Excel file: {excel_path}")
        return excel_path
    except Exception as e:
        logger.error(f"Error saving tables to Excel: {str(e)}")
        raise

def extract_maintenance_data(processed_content):
    """
    Extract structured maintenance data from processed content.
    
    Args:
        processed_content (dict): Processed content with text and tables
        
    Returns:
        dict: Structured maintenance data
    """
    # This is a placeholder for a more sophisticated extraction function
    # In a real implementation, you would use regex patterns and other methods
    # to extract specific maintenance information from the text and tables
    
    maintenance_data = {
        'years': [],
        'categories': [],
        'items': []
    }
    
    # Example logic to extract years (e.g., "2022", "2023", etc.)
    text = processed_content['text']
    year_pattern = r'\b(20\d{2})\b'
    years = set(re.findall(year_pattern, text))
    maintenance_data['years'] = sorted(list(years))
    
    # Example logic to extract maintenance categories
    # This should be customized based on your specific documents
    category_keywords = ['Fasader', 'Installationer', 'Ventilation', 'Tak', 'Mark']
    for category in category_keywords:
        if category in text:
            maintenance_data['categories'].append(category)
    
    # Process tables to extract maintenance items
    for table in processed_content['tables']:
        if len(table) > 1:  # Ensure table has content beyond header
            for row in table[1:]:  # Skip header row
                if len(row) >= 3:  # Ensure row has enough columns
                    item = {
                        'description': row[0] if row[0] else 'Unknown',
                        'year': extract_year(row),
                        'cost': extract_cost(row),
                        'category': extract_category(row, maintenance_data['categories'])
                    }
                    maintenance_data['items'].append(item)
    
    return maintenance_data

def extract_year(row):
    """Extract year from a table row."""
    # Look for year pattern in each cell
    for cell in row:
        year_match = re.search(r'\b(20\d{2})\b', cell)
        if year_match:
            return year_match.group(1)
    return 'Unknown'

def extract_cost(row):
    """Extract cost from a table row."""
    # Look for cost pattern in each cell
    for cell in row:
        # Match formats like "123 000 kr" or "123,000 kr"
        cost_match = re.search(r'(\d[\d\s,.]*)\s*kr', cell)
        if cost_match:
            # Clean and return the cost value
            cost_str = cost_match.group(1).replace(' ', '').replace(',', '.')
            try:
                return float(cost_str)
            except ValueError:
                pass
    return 0.0

def extract_category(row, known_categories):
    """Extract maintenance category from a table row."""
    for cell in row:
        for category in known_categories:
            if category.lower() in cell.lower():
                return category
    return 'Other'