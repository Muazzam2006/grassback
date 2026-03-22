import os
from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile
import logging

logger = logging.getLogger(__name__)

def convert_image_to_webp(image_field, quality=85):
    """
    Converts an uploaded image to WebP format.
    If the image is already a WebP or empty, it skips conversion.
    Modifies the image_field in place before saving.
    """
    if not image_field:
        return

    filename = getattr(image_field, 'name', '')
    if not filename or filename.lower().endswith('.webp'):
        return

    try:
        # Check if the file has been modified or is a new upload
        # Usually checking file attribute works
        if not hasattr(image_field, 'file'):
            return
            
        image_field.file.seek(0)
        img = Image.open(image_field.file)

        if img.format == 'WEBP':
            return

        output = BytesIO()
        
        # WebP supports transparency, so we can save as is without enforcing RGB
        # But for JPEGs it's usually RGB.
        img.save(output, format='WEBP', quality=quality)
        output.seek(0)

        name, _ = os.path.splitext(os.path.basename(filename))
        new_filename = f"{name}.webp"

        image_field.save(new_filename, ContentFile(output.read()), save=False)
    except Exception as e:
        logger.warning(f"Failed to convert image {filename} to WebP: {e}")
