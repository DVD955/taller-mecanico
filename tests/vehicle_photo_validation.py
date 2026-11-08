"""Validación real de fotografías: no requiere servicios ni modifica la BD."""
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from PIL import Image
from starlette.datastructures import Headers, UploadFile
from starlette.requests import Request
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app.vehicles import MAX_PHOTO_BYTES, VehicleEditInput, parse_upload, validate_photo


def photo_bytes(format='PNG'):
    output = io.BytesIO()
    Image.new('RGB', (4, 4), '#2F4F4F').save(output, format=format)
    return output.getvalue()


class VehiclePhotoTests(unittest.IsolatedAsyncioTestCase):
    async def validate(self, content, mime='image/png'):
        upload = UploadFile(io.BytesIO(content), filename='foto.png', headers=Headers({'content-type': mime}))
        try:
            return await validate_photo(upload)
        finally:
            await upload.close()

    async def test_real_formats(self):
        for format, mime in [('PNG', 'image/png'), ('JPEG', 'image/jpeg'), ('WEBP', 'image/webp')]:
            with self.subTest(format=format):
                self.assertEqual((await self.validate(photo_bytes(format), mime))['contentType'], mime)

    async def test_exactly_15_mb(self):
        content = photo_bytes()
        self.assertTrue((await self.validate(content + bytes(MAX_PHOTO_BYTES - len(content))))['content'])

    async def test_more_than_15_mb(self):
        with self.assertRaises(HTTPException) as error:
            await self.validate(bytes(MAX_PHOTO_BYTES + 1))
        self.assertEqual(error.exception.status_code, 413)

    async def test_invalid_and_disguised_images(self):
        for content, mime in [(b'', 'image/png'), (b'<svg></svg>', 'image/png'),
                              (photo_bytes(), 'image/jpeg'), (photo_bytes()[:30], 'image/png')]:
            with self.subTest(mime=mime, length=len(content)):
                with self.assertRaises(HTTPException) as error:
                    await self.validate(content, mime)
                self.assertEqual(error.exception.status_code, 422)

    async def test_stream_limit_without_content_length(self):
        async def receive():
            return {'type': 'http.request', 'body': b'0123456789', 'more_body': False}
        request = Request({'type': 'http', 'method': 'POST', 'path': '/', 'app': object(),
                           'headers': [(b'content-type', b'multipart/form-data; boundary=test')]}, receive=receive)
        with patch('app.vehicles.MAX_UPLOAD_BYTES', 8):
            with self.assertRaises(HTTPException) as error:
                await parse_upload(request)
            self.assertEqual(error.exception.status_code, 413)


class VehicleEditInputTests(unittest.TestCase):
    def setUp(self):
        self.valid = dict(vin='1HGCM82633A004352', plate='ABC-123-D', make='Honda', model='Accord',
                          year=2003, version='EX', color='Gris', mileage=0)

    def test_all_eight_fields_required(self):
        for field in self.valid:
            for invalid in ('', '   ', None):
                with self.subTest(field=field, invalid=invalid):
                    with self.assertRaises(ValidationError):
                        VehicleEditInput.model_validate({**self.valid, field: invalid})
            with self.subTest(field=field, omitted=True):
                with self.assertRaises(ValidationError):
                    VehicleEditInput.model_validate({key: value for key, value in self.valid.items() if key != field})

    def test_zero_mileage_and_existing_text(self):
        self.assertEqual(VehicleEditInput.model_validate(self.valid).mileage, 0)
        self.assertEqual(VehicleEditInput.model_validate({**self.valid, 'make': ' Honda '}).make, 'Honda')

    def test_numeric_types_and_limits(self):
        for invalid in (-1, 10000001, True, False, '0', 0.5):
            with self.subTest(mileage=invalid):
                with self.assertRaises(ValidationError):
                    VehicleEditInput.model_validate({**self.valid, 'mileage': invalid})


if __name__ == '__main__':
    unittest.main(verbosity=2)
