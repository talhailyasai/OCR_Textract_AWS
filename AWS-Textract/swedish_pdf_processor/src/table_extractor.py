"""
Specialized module for extracting and processing tables from Textract output.
"""
import logging
import pandas as pd
from collections import defaultdict

from src.postprocess import fix_swedish_characters

logger = logging.getLogger(__name__)

class TableExtractor:
    """Class for extracting and processing tables from Textract output."""
    
    def __init__(self):
        """Initialize the table extractor."""
        self.blocks_map = {}
    
    def extract_tables(self, blocks):
        """
        Extract tables from Textract blocks.
        
        Args:
            blocks (list): List of Textract blocks
            
        Returns:
            list: List of extracted tables
        """
        logger.info("Extracting tables from Textract blocks")
        
        # Reset blocks map
        self.blocks_map = {block['Id']: block for block in blocks}
        
        # Find table blocks
        table_blocks = [block for block in blocks if block['BlockType'] == 'TABLE']
        logger.info(f"Found {len(table_blocks)} tables")
        
        # Extract each table
        tables = []
        for i, table_block in enumerate(table_blocks):
            logger.info(f"Processing table {i+1}")
            table = self._process_table(table_block)
            if table:
                # Apply Swedish character fixes to each cell
                for r, row in enumerate(table):
                    for c, cell in enumerate(row):
                        if isinstance(cell, str):
                            table[r][c] = fix_swedish_characters(cell)
                tables.append(table)
        
        return tables
    
    def _process_table(self, table_block):
        """
        Process a single table block.
        
        Args:
            table_block (dict): Textract table block
            
        Returns:
            list: 2D array of table data
        """
        # Get relationships between table and cells
        if 'Relationships' not in table_block:
            logger.warning("Table block has no relationships")
            return []
        
        cell_ids = []
        for relationship in table_block['Relationships']:
            if relationship['Type'] == 'CHILD':
                cell_ids = relationship['Ids']
                break
        
        if not cell_ids:
            logger.warning("No cell IDs found in table relationships")
            return []
        
        # Get all cells
        cells = [self.blocks_map[cell_id] for cell_id in cell_ids 
                if cell_id in self.blocks_map and self.blocks_map[cell_id]['BlockType'] == 'CELL']
        
        # Determine table dimensions
        max_row = max(cell['RowIndex'] for cell in cells)
        max_col = max(cell['ColumnIndex'] for cell in cells)
        
        # Initialize table with empty strings
        table = [[''] * max_col for _ in range(max_row)]
        
        # Fill in cells
        for cell in cells:
            row_idx = cell['RowIndex'] - 1  # Convert to 0-based index
            col_idx = cell['ColumnIndex'] - 1  # Convert to 0-based index
            
            # Extract cell content
            cell_content = self._get_cell_content(cell)
            
            # Handle cells that span multiple rows or columns
            row_span = cell.get('RowSpan', 1)
            col_span = cell.get('ColumnSpan', 1)
            
            # Add content to the cell
            table[row_idx][col_idx] = cell_content
            
            # For merged cells, repeat the content (if needed)
            if row_span > 1 or col_span > 1:
                for r in range(row_idx, row_idx + row_span):
                    for c in range(col_idx, col_idx + col_span):
                        if r < max_row and c < max_col and (r != row_idx or c != col_idx):
                            table[r][c] = cell_content
        
        return table
    
    def _get_cell_content(self, cell):
        """
        Extract content from a cell.
        
        Args:
            cell (dict): Textract cell block
            
        Returns:
            str: Cell content
        """
        if 'Relationships' not in cell:
            return ''
        
        content = []
        for relationship in cell['Relationships']:
            if relationship['Type'] == 'CHILD':
                for id in relationship['Ids']:
                    if id in self.blocks_map:
                        block = self.blocks_map[id]
                        if block['BlockType'] == 'WORD':
                            content.append(block['Text'])
                        elif block['BlockType'] == 'LINE':
                            content.append(block['Text'])
        
        return ' '.join(content)
    
    def tables_to_dataframes(self, tables):
        """
        Convert tables to pandas DataFrames.
        
        Args:
            tables (list): List of 2D table data
            
        Returns:
            list: List of pandas DataFrames
        """
        dataframes = []
        
        for table in tables:
            if not table:
                continue
                
            # Use the first row as header if it seems to be a header
            # (simple heuristic: first row has different format or contains keyword like "År" or "Kategori")
            first_row_header = False
            if len(table) > 1:
                first_row = table[0]
                first_row_text = ' '.join(first_row).lower()
                if any(keyword in first_row_text for keyword in ['år', 'kategori', 'åtgärd', 'pris']):
                    first_row_header = True
                    
            if first_row_header:
                # Skip empty columns and ensure headers are not empty
                headers = [col if col else f'Column{i+1}' for i, col in enumerate(table[0])]
                df = pd.DataFrame(table[1:], columns=headers)
            else:
                df = pd.DataFrame(table)
            
            # Clean up DataFrame: remove empty rows and columns
            df = df.dropna(how='all').dropna(axis=1, how='all')
            
            dataframes.append(df)
        
        return dataframes
    
    def is_maintenance_table(self, df):
        """
        Check if a DataFrame appears to be a maintenance table.
        
        Args:
            df (pandas.DataFrame): Table as DataFrame
            
        Returns:
            bool: True if table appears to be a maintenance table
        """
        # Get column names as lowercase strings
        columns = [str(col).lower() for col in df.columns]
        
        # Check for common maintenance table columns
        maintenance_keywords = [
            'år', 'kategori', 'åtgärd', 'läge', 'intervall', 'status', 'pris', 'kostnad',
            'year', 'category', 'action', 'interval', 'price', 'cost'
        ]
        
        # Check if any maintenance keywords are in the columns
        if any(keyword in ' '.join(columns) for keyword in maintenance_keywords):
            return True
            
        # Check if date/year columns exist
        year_patterns = ['år', 'year', '20', '19']
        if any(any(pattern in str(col).lower() for pattern in year_patterns) for col in columns):
            # And if a cost/price column exists
            cost_patterns = ['pris', 'kostnad', 'cost', 'price', 'kr']
            if any(any(pattern in str(col).lower() for pattern in cost_patterns) for col in columns):
                return True
        
        return False
    
    def extract_maintenance_data(self, tables):
        """
        Extract structured maintenance data from tables.
        
        Args:
            tables (list): List of table data or DataFrames
            
        Returns:
            dict: Structured maintenance data
        """
        # Convert tables to DataFrames if they aren't already
        if tables and not isinstance(tables[0], pd.DataFrame):
            dfs = self.tables_to_dataframes(tables)
        else:
            dfs = tables
        
        # Filter to maintenance tables
        maintenance_tables = [df for df in dfs if self.is_maintenance_table(df)]
        
        # Initialize maintenance data structure
        maintenance_data = {
            "yearly_maintenance": defaultdict(list),
            "categories": set(),
            "total_cost": 0
        }
        
        # Process each maintenance table
        for df in maintenance_tables:
            # Attempt to identify column meanings
            year_col = self._find_column(df, ['år', 'year', '20', 'nästa'])
            category_col = self._find_column(df, ['kategori', 'category', 'typ', 'type'])
            action_col = self._find_column(df, ['åtgärd', 'action', 'beskrivning', 'description', 'aktivitet'])
            cost_col = self._find_column(df, ['pris', 'kostnad', 'cost', 'price', 'kr', 'inkl', 'moms'])
            
            # Process each row
            for _, row in df.iterrows():
                year = self._extract_year(row, year_col)
                if not year:
                    continue
                    
                # Extract data
                item = {
                    "category": self._get_value(row, category_col, "Okategoriserat"),
                    "action": self._get_value(row, action_col, ""),
                    "cost": self._extract_cost(row, cost_col)
                }
                
                # Add to maintenance data
                maintenance_data["yearly_maintenance"][year].append(item)
                maintenance_data["categories"].add(item["category"])
                maintenance_data["total_cost"] += item["cost"] or 0
        
        # Convert defaultdict to regular dict for JSON serialization
        maintenance_data["yearly_maintenance"] = dict(maintenance_data["yearly_maintenance"])
        maintenance_data["categories"] = list(maintenance_data["categories"])
        
        return maintenance_data
    
    def _find_column(self, df, keywords):
        """Find column that matches any of the keywords."""
        for col in df.columns:
            col_str = str(col).lower()
            if any(keyword.lower() in col_str for keyword in keywords):
                return col
        return None
    
    def _get_value(self, row, col, default=""):
        """Get value from row with fallback to default."""
        if col is not None and col in row:
            return row[col] or default
        return default
    
    def _extract_year(self, row, year_col):
        """Extract year from a row."""
        if year_col is not None:
            value = str(row[year_col])
            # Look for 4-digit year pattern
            import re
            match = re.search(r'20\d{2}', value)
            if match:
                return match.group(0)
        return None
    
    def _extract_cost(self, row, cost_col):
        """Extract cost from a row."""
        if cost_col is not None:
            value = str(row[cost_col])
            # Remove non-numeric characters (except decimal point)
            import re
            numbers = re.sub(r'[^\d.,]', '', value)
            # Replace comma with dot for decimal
            numbers = numbers.replace(',', '.')
            try:
                return float(numbers)
            except ValueError:
                pass
        return None