"""
PDF preprocessing module for improving OCR quality.
"""
import os
import logging
from pathlib import Path
import uuid
from pdf2image import convert_from_path
from PIL import Image, ImageEnhance, ImageFilter
import tempfile

from config import PDF_DPI, IMAGE_FORMAT, CONTRAST_FACTOR, TEMP_DIR

logger = logging.getLogger(__name__)

def preprocess_pdf(pdf_path, output_dir=None, dpi=PDF_DPI):
    """
    Convert PDF to high-resolution images for better OCR results.
    
    Args:
        pdf_path (str): Path to the PDF file
        output_dir (str): Directory to save the images
        dpi (int): Resolution for the output images
        
    Returns:
        list: Paths to the generated images
        str: Unique document ID
    """
    logger.info(f"Preprocessing PDF: {pdf_path}")
    
    if output_dir is None:
        output_dir = TEMP_DIR
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
    
    # Generate a unique identifier for this document
    doc_id = str(uuid.uuid4())
    doc_dir = output_dir / doc_id
    doc_dir.mkdir(exist_ok=True)
    
    logger.info(f"Converting PDF to images at {dpi} DPI")
    
    try:
        # Convert PDF to images
        images = convert_from_path(pdf_path, dpi=dpi)
        image_paths = []
        
        for i, img in enumerate(images):
            # Apply image enhancements for better OCR
            enhanced_img = enhance_image(img)
            
            # Save the enhanced image
            img_path = os.path.join(doc_dir, f"page_{i+1}.{IMAGE_FORMAT.lower()}")
            enhanced_img.save(img_path, IMAGE_FORMAT)
            image_paths.append(img_path)
            
        logger.info(f"Successfully preprocessed {len(image_paths)} pages")
        return image_paths, doc_id
        
    except Exception as e:
        logger.error(f"Error preprocessing PDF: {str(e)}")
        raise

def enhance_image(image):
    """
    Apply image enhancements to improve OCR quality.
    
    Args:
        image (PIL.Image): Input image
        
    Returns:
        PIL.Image: Enhanced image
    """
    # Convert to grayscale for better OCR
    if image.mode != 'L':
        image = image.convert('L')
    
    # Enhance contrast
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(CONTRAST_FACTOR)
    
    # Apply slight sharpening
    image = image.filter(ImageFilter.SHARPEN)
    
    return image