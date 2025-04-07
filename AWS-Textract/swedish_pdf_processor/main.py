#!/usr/bin/env python3
"""
Main script for processing Swedish PDFs using AWS Textract.
"""
import os
import sys
import argparse
import logging
import json
import time
from pathlib import Path
from datetime import datetime
import pandas as pd

from config import OUTPUT_DIR
from src.preprocess import preprocess_pdf
from src.textract_client import TextractClient
from src.postprocess import process_textract_response, save_processed_content
from src.table_extractor import TableExtractor
from src.utils import setup_logging, save_tables_to_excel

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Process Swedish PDFs with AWS Textract')
    parser.add_argument('pdf_path', type=str, help='Path to the PDF file')
    parser.add_argument('--output-dir', type=str, default=str(OUTPUT_DIR),
                        help='Output directory for processed files')
    parser.add_argument('--dpi', type=int, default=300,
                        help='DPI for image conversion (default: 300)')
    parser.add_argument('--region', type=str, default='eu-north-1',
                        help='AWS region for Textract (default: eu-north-1)')
    parser.add_argument('--async', action='store_true',
                        help='Use asynchronous Textract API (for large documents)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')
    return parser.parse_args()

def process_pdf(pdf_path, output_dir, dpi=300, region='eu-north-1', use_async=False):
    """
    Process a PDF with Swedish content using AWS Textract.
    
    Args:
        pdf_path (str): Path to the PDF file
        output_dir (str): Output directory
        dpi (int): DPI for image conversion
        region (str): AWS region
        use_async (bool): Use asynchronous Textract API
        
    Returns:
        dict: Processed content
    """
    logger = logging.getLogger(__name__)
    
    # Create output directory if it doesn't exist
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Generate output file name base
    pdf_name = Path(pdf_path).stem
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_base = output_dir / f"{pdf_name}_{timestamp}"
    
    logger.info(f"Processing PDF: {pdf_path}")
    logger.info(f"Output will be saved to: {output_base}")
    
    # Step 1: Preprocess PDF to high-quality images
    logger.info("Step 1: Preprocessing PDF")
    image_paths, doc_id = preprocess_pdf(pdf_path, output_dir, dpi)
    logger.info(f"Created {len(image_paths)} preprocessed images")
    
    # Step 2: Process each page with Textract
    logger.info("Step 2: Processing with AWS Textract")
    textract_client = TextractClient(region_name=region)
    
    all_results = []
    for i, image_path in enumerate(image_paths):
        logger.info(f"Processing page {i+1}/{len(image_paths)}")
        try:
            response = textract_client.analyze_document(image_path)
            all_results.append(response)
        except Exception as e:
            logger.error(f"Error processing page {i+1}: {str(e)}")
            continue
    
    if not all_results:
        logger.error("No pages were successfully processed")
        return None
    
    # Step 3: Process and correct text with Swedish character fixes
    logger.info("Step 3: Post-processing text with Swedish character fixes")
    processed_pages = []
    
    for i, result in enumerate(all_results):
        logger.info(f"Post-processing page {i+1}/{len(all_results)}")
        processed_content = process_textract_response(result)
        processed_pages.append(processed_content)
    
    # Step 4: Extract tables
    logger.info("Step 4: Extracting tables")
    table_extractor = TableExtractor()
    all_tables = []
    
    for i, result in enumerate(all_results):
        logger.info(f"Extracting tables from page {i+1}/{len(all_results)}")
        tables = table_extractor.extract_tables(result['Blocks'])
        all_tables.extend(tables)
    
    # Step 5: Save results
    logger.info("Step 5: Saving results")
    
    # Combine all text from pages
    combined_text = "\n\n".join([page['text'] for page in processed_pages])
    
    # Create a combined result
    combined_result = {
        'text': combined_text,
        'tables': all_tables,
        'document_id': doc_id,
        'timestamp': timestamp,
        'source_file': pdf_path,
        'page_count': len(image_paths)
    }
    
    # Save as text, JSON, and Excel
    logger.info("Saving processed content")
    
    # Save plain text
    text_path = output_base.with_suffix('.txt')
    with open(text_path, 'w', encoding='utf-8') as f:
        f.write(combined_text)
    logger.info(f"Saved text to: {text_path}")
    
    # Save full content as JSON
    json_path = output_base.with_suffix('.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        # Create a serializable version of the result
        serializable_result = {
            'text': combined_result['text'],
            'tables': combined_result['tables'],
            'document_id': combined_result['document_id'],
            'timestamp': combined_result['timestamp'],
            'source_file': str(combined_result['source_file']),
            'page_count': combined_result['page_count']
        }
        json.dump(serializable_result, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved JSON to: {json_path}")
    
    # Save tables to Excel if there are any
    if all_tables:
        excel_path = save_tables_to_excel(all_tables, output_base)
        logger.info(f"Saved tables to Excel: {excel_path}")
    
    # Extract structured maintenance data
    try:
        logger.info("Extracting structured maintenance data")
        maintenance_data = table_extractor.extract_maintenance_data(all_tables)
        
        # Save maintenance data as JSON
        maintenance_path = output_base.with_name(f"{output_base.stem}_maintenance.json")
        with open(maintenance_path, 'w', encoding='utf-8') as f:
            json.dump(maintenance_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved maintenance data to: {maintenance_path}")
    except Exception as e:
        logger.error(f"Error extracting maintenance data: {str(e)}")
    
    logger.info("Processing complete!")
    return combined_result

def main():
    """Main entry point."""
    args = parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(log_level)
    
    logger = logging.getLogger(__name__)
    logger.info("Swedish PDF Processor")
    logger.info(f"Processing file: {args.pdf_path}")
    
    try:
        # Process the PDF
        start_time = time.time()
        process_pdf(
            args.pdf_path,
            args.output_dir,
            args.dpi,
            args.region,
            getattr(args, 'async', False)
        )
        end_time = time.time()
        logger.info(f"Total processing time: {end_time - start_time:.2f} seconds")
        
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}", exc_info=True)
        sys.exit(1)
    
    logger.info("Processing completed successfully")

if __name__ == '__main__':
    main()