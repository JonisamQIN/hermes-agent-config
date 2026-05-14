#!/usr/bin/env python3
"""
WeChat Image OCR Service
Uses Tesseract OCR with Chinese and English support for WeChat image recognition.
"""

import argparse
import base64
import json
import logging
import sys
from pathlib import Path

from PIL import Image
import pytesseract

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def ocr_image(image_path: str, lang: str = 'eng+chi_sim') -> dict:
    """
    Perform OCR on an image file.
    
    Args:
        image_path: Path to the image file
        lang: Tesseract language codes (default: eng+chi_sim for English+Simplified Chinese)
    
    Returns:
        dict with 'success', 'text', 'confidence', and optionally 'error'
    """
    try:
        img = Image.open(image_path)
        
        # Get OCR data with confidence
        data = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)
        
        # Extract text with reasonable confidence
        words = []
        confidences = []
        for i, conf in enumerate(data['conf']):
            if conf > 0:  # Filter out low confidence
                word = data['text'][i].strip()
                if word:
                    words.append(word)
                    confidences.append(int(conf))
        
        full_text = ' '.join(words)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            'success': True,
            'text': full_text,
            'confidence': round(avg_confidence, 2),
            'word_count': len(words)
        }
        
    except FileNotFoundError:
        return {'success': False, 'error': f'Image file not found: {image_path}'}
    except Exception as e:
        logger.error(f"OCR error: {e}")
        return {'success': False, 'error': str(e)}

def ocr_base64(image_data: str, lang: str = 'eng+chi_sim') -> dict:
    """Process base64 encoded image data."""
    try:
        img_bytes = base64.b64decode(image_data)
        img = Image.open(io.BytesIO(img_bytes))
        
        text = pytesseract.image_to_string(img, lang=lang)
        
        return {
            'success': True,
            'text': text.strip(),
            'confidence': None
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

def main():
    parser = argparse.ArgumentParser(description='WeChat OCR Service')
    parser.add_argument('image', help='Path to image file')
    parser.add_argument('--lang', default='eng+chi_sim', help='Tesseract languages (default: eng+chi_sim)')
    parser.add_argument('--json', action='store_true', help='Output JSON format')
    
    args = parser.parse_args()
    
    result = ocr_image(args.image, args.lang)
    
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if result['success']:
            print(f"=== OCR Result (confidence: {result.get('confidence', 'N/A')}%) ===")
            print(result['text'])
        else:
            print(f"Error: {result.get('error')}", file=sys.stderr)
            sys.exit(1)

if __name__ == '__main__':
    main()
