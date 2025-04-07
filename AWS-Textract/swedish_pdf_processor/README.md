# Swedish PDF Processor

A comprehensive solution for extracting and processing content from Swedish-language PDF documents, especially maintenance reports, using AWS Textract with enhanced handling of Swedish characters (å, ä, ö).

## Features

- High-quality PDF preprocessing for optimal OCR results
- Integration with AWS Textract for text and table extraction
- Specialized post-processing for Swedish character correction
- Table extraction and structured data conversion
- Maintenance report data extraction and analysis
- Output in multiple formats (TXT, JSON, Excel)

## Requirements

- Python 3.8+
- AWS account with Textract access
- AWS CLI configured with appropriate credentials
- Poppler (system dependency for PDF processing)

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/swedish-pdf-processor.git
   cd swedish-pdf-processor
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install Poppler (system dependency for pdf2image):
   - **Ubuntu/Debian**: `sudo apt-get install poppler-utils`
   - **macOS**: `brew install poppler`
   - **Windows**: Download from [poppler releases](https://github.com/oschwartz10612/poppler-windows/releases) and add to PATH

5. Configure AWS credentials:
   ```bash
   aws configure
   ```
   Enter your AWS Access Key ID, Secret Access Key, region (preferably eu-north-1 for Swedish content), and output format.

## Usage

### Basic Usage

Process a single PDF file:

```bash
python main.py path/to/your/swedish_document.pdf
```

### Advanced Options

```bash
python main.py path/to/your/swedish_document.pdf --output-dir /custom/output/path --dpi 400 --region eu-north-1 --debug
```

Options:
- `--output-dir`: Specify a custom output directory (default: `./output`)
- `--dpi`: Set DPI for image conversion (default: 300, higher values may improve OCR quality)
- `--region`: Set AWS region for Textract (default: eu-north-1)
- `--async`: Use asynchronous Textract API for large documents
- `--debug`: Enable debug logging

### Output Files

For an input file named `maintenance_report.pdf`, the script will generate:
- `maintenance_report_YYYYMMDD_HHMMSS.txt`: Extracted text with corrected Swedish characters
- `maintenance_report_YYYYMMDD_HHMMSS.json`: Complete extraction results in JSON format
- `maintenance_report_YYYYMMDD_HHMMSS.xlsx`: Extracted tables in Excel format
- `maintenance_report_YYYYMMDD_HHMMSS_maintenance.json`: Structured maintenance data

## Swedish Character Handling

This tool addresses AWS Textract's limitations with Swedish characters (å, ä, ö) using a specialized post-processing approach:

1. The PDF is converted to high-resolution images without removing Swedish characters
2. AWS Textract processes the images to extract text and tables
3. Post-processing applies corrections for commonly misrecognized Swedish patterns:
   - "a ̊" → "å", "a ̈" → "ä", "o ̈" → "ö"
   - "underha ̊llsplan" → "underhållsplan", etc.

The correction dictionary is fully customizable in `src/postprocess.py`.

## Maintenance Report Processing

For Swedish maintenance reports, the tool extracts structured data including:
- Yearly maintenance schedules
- Maintenance categories
- Actions and descriptions
- Cost information

This information is saved in a separate JSON file for further analysis or integration with other systems.

## Example

Processing a maintenance report:

```bash
python main.py samples/underhallsplan_2022.pdf
```

Example output:

```
INFO - Processing PDF: samples/underhallsplan_2022.pdf
INFO - Step 1: Preprocessing PDF
INFO - Created 148 preprocessed images
INFO - Step 2: Processing with AWS Textract
...
INFO - Saved text to: output/underhallsplan_2022_20250407_123456.txt
INFO - Saved JSON to: output/underhallsplan_2022_20250407_123456.json
INFO - Saved tables to Excel: output/underhallsplan_2022_20250407_123456.xlsx
INFO - Saved maintenance data to: output/underhallsplan_2022_20250407_123456_maintenance.json
INFO - Processing complete!
```

## Adding Custom Swedish Terms

To add additional Swedish terms to the correction dictionary, edit `src/postprocess.py`:

```python
SWEDISH_TERM_FIXES = {
    # Existing terms...
    "underha ̊llsplan": "underhållsplan",
    
    # Add your custom terms here
    "my_swedish_term": "corrected_term",
}
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.