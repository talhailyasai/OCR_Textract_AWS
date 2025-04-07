"""
Post-processing module for correcting Swedish characters in OCR output.
"""
import logging
import re
import json
from pathlib import Path

logger = logging.getLogger(__name__)

# Swedish character correction dictionary
SWEDISH_CHAR_FIXES = {
    # Character-level fixes
    "a ̊": "å", "a˚": "å", "aa": "å", "a°": "å", "aº": "å",
    "a ̈": "ä", "ae": "ä", "a¨": "ä",
    "o ̈": "ö", "oe": "ö", "o¨": "ö",
    # UTF-8 encoding issues
    "Ã¥": "å", "Ã¤": "ä", "Ã¶": "ö",
    # Capital letter variants
    "A ̊": "Å", "A˚": "Å", "A°": "Å", "Aº": "Å",
    "A ̈": "Ä", "AE": "Ä", "A¨": "Ä",
    "O ̈": "Ö", "OE": "Ö", "O¨": "Ö",
}

# Common Swedish maintenance terms with character issues
SWEDISH_TERM_FIXES = {
    # Common maintenance terms
    "underha ̊llsplan": "underhållsplan",
    "ma ̈ssen": "mässen",
    "o ̈versikt": "översikt",
    "a ̊tga ̈rd": "åtgärd",
    "la ̈ge": "läge",
    "na ̈sta a ̊r": "nästa år",
    "a ̊r": "år",
    # Month names
    "ma ̈rs": "mars",
    "fo ̈rstudie": "förstudie",
    "ino ̈m": "inom",
    "fo ̈rening": "förening",
    "ma ̊lning": "målning",
    "sta ̈dning": "städning",
    "do ̈rrar": "dörrar",
    "fo ̈nster": "fönster",
    "ma ̊nad": "månad",
    "va ̈rme": "värme",
    "va ̈gg": "vägg",
    "go ̈ra": "göra",
    "a ̈r": "är",
    "sa ̈kerhet": "säkerhet",
    "fo ̈rvaltning": "förvaltning",
}

def fix_swedish_characters(text):
    """
    Apply Swedish character fixes to the extracted text.
    
    Args:
        text (str): OCR text with potential Swedish character issues
        
    Returns:
        str: Text with corrected Swedish characters
    """
    if not text:
        return text
        
    logger.info("Applying Swedish character fixes")
    
    # First fix individual characters
    for bad, good in SWEDISH_CHAR_FIXES.items():
        text = text.replace(bad, good)
    
    # Then fix common terms
    for bad, good in SWEDISH_TERM_FIXES.items():
        # Use word boundary to avoid partial word replacements
        text = re.sub(r'\b' + re.escape(bad) + r'\b', good, text, flags=re.IGNORECASE)
    
    return text

def extract_text_from_blocks(blocks):
    """
    Extract text from Textract blocks.
    
    Args:
        blocks (list): List of Textract blocks
        
    Returns:
        str: Extracted text
    """
    text = ""
    for block in blocks:
        if block['BlockType'] == 'LINE':
            text += block['Text'] + "\n"
    return text

def process_textract_response(response):
    """
    Process and correct text from Textract response.
    
    Args:
        response (dict): Textract API response
        
    Returns:
        dict: Processed response with corrected text
    """
    logger.info("Processing Textract response")
    
    # Extract all blocks
    blocks = response['Blocks']
    
    # Extract text from LINE blocks
    raw_text = extract_text_from_blocks(blocks)
    
    # Apply Swedish character fixes
    corrected_text = fix_swedish_characters(raw_text)
    
    # Process table data if present
    tables = []
    for block in blocks:
        if block['BlockType'] == 'TABLE':
            table_data = extract_table_data(block, blocks)
            # Apply Swedish character fixes to each cell
            for row in table_data:
                for i, cell in enumerate(row):
                    row[i] = fix_swedish_characters(cell)
            tables.append(table_data)
    
    return {
        'text': corrected_text,
        'tables': tables
    }

def extract_table_data(table_block, all_blocks):
    """
    Extract data from a table block.
    
    Args:
        table_block (dict): Textract table block
        all_blocks (list): All Textract blocks
        
    Returns:
        list: 2D array of table data
    """
    # Get table cells (child blocks with CELL type)
    cell_ids = table_block.get('Relationships', [{}])[0].get('Ids', [])
    cells = [b for b in all_blocks if b['Id'] in cell_ids and b['BlockType'] == 'CELL']
    
    # Get table dimensions
    rows = max(cell['RowIndex'] for cell in cells)
    cols = max(cell['ColumnIndex'] for cell in cells)
    
    # Initialize empty table
    table = [[''] * cols for _ in range(rows)]
    
    # Fill table with cell content
    for cell in cells:
        row_idx = cell['RowIndex'] - 1
        col_idx = cell['ColumnIndex'] - 1
        
        # Get cell content (child blocks with WORD type)
        if 'Relationships' in cell and len(cell['Relationships']) > 0:
            word_ids = cell['Relationships'][0].get('Ids', [])
            cell_words = [b['Text'] for b in all_blocks if b['Id'] in word_ids and b['BlockType'] == 'WORD']
            cell_text = ' '.join(cell_words)
        else:
            cell_text = ''
        
        # Set cell content
        table[row_idx][col_idx] = cell_text
    
    return table

def save_processed_content(processed_content, output_path):
    """
    Save processed content to output file.
    
    Args:
        processed_content (dict): Processed content
        output_path (str): Output file path
    """
    output_path = Path(output_path)
    
    # Save plain text
    with open(output_path.with_suffix('.txt'), 'w', encoding='utf-8') as f:
        f.write(processed_content['text'])
    
    # Save tables as CSV if present
    if processed_content['tables']:
        import csv
        for i, table in enumerate(processed_content['tables']):
            table_path = output_path.with_name(f"{output_path.stem}_table_{i+1}.csv")
            with open(table_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(table)
    
    # Save full content as JSON
    with open(output_path.with_suffix('.json'), 'w', encoding='utf-8') as f:
        json.dump(processed_content, f, ensure_ascii=False, indent=2)