"""Tests for menu image handling."""
import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.menu.services import compress_image


def create_test_image(width, height, format="JPEG"):
    """Create a large dummy image in memory."""
    img = Image.new("RGB", (width, height), color="red")
    buf = io.BytesIO()
    img.save(buf, format=format)
    return SimpleUploadedFile("test.jpg", buf.getvalue(), content_type="image/jpeg")


@pytest.mark.django_db
def test_compress_image_downscales():
    """compress_image downscales an oversized image to max 1024."""
    large_image = create_test_image(2000, 1000)
    from apps.menu.models import Category, MenuItem
    cat = Category.objects.create(name="Cat")
    item = MenuItem(category=cat, name="Item")
    item.image = large_image
    
    # Compress in memory
    compress_image(item.image)
    
    item.image.seek(0)
    with Image.open(item.image) as img:
        assert max(img.width, img.height) == 1024
        assert img.width == 1024
        assert img.height == 512
