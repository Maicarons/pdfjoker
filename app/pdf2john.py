from io import BytesIO
from typing import Optional, Union
from pyhanko.pdf_utils.misc import PdfReadError
from pyhanko.pdf_utils.reader import PdfFileReader


def get_pdf_hash(pdf_file: Union[str, bytes]) -> Optional[str]:
    """Generate John the Ripper compatible hash from a PDF file.

    Args:
        pdf_file: Either a file path (str) or PDF file bytes

    Returns:
        String containing the hash in John format, or None if not encrypted
    """
    try:
        if isinstance(pdf_file, str):
            with open(pdf_file, 'rb') as f:
                return _process_pdf(f)
        else:
            return _process_pdf(BytesIO(pdf_file))
    except (PdfReadError, RuntimeError) as e:
        print(f"Error processing PDF: {e}")
        return None


def _process_pdf(stream) -> Optional[str]:
    """Internal function to process PDF stream"""
    pdf = PdfFileReader(stream)
    if not pdf.encrypt_dict:
        return None

    encrypt_dict = pdf.encrypt_dict
    security_handler = pdf.security_handler

    # Get password data components
    max_len = {2: 32, 3: 32, 4: 32, 5: 48, 6: 48}.get(encrypt_dict['/R'], 48)
    passwords = []
    for key in ('udata', 'odata', 'oeseed', 'ueseed'):
        if data := getattr(security_handler, key, None):
            passwords.extend([str(len(data[:max_len])), data[:max_len].hex()])

    # Build hash string
    return "*".join([
        f"$pdf${encrypt_dict.get('/V')}",
        str(encrypt_dict['/R']),
        str(encrypt_dict.get('/Length', 40)),
        str(encrypt_dict['/P']),
        str(int(security_handler.encrypt_metadata)),
        str(len(pdf.document_id[0])),
        pdf.document_id[0].hex(),
        "*".join(passwords)
    ])