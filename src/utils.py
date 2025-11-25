import re

def sanitize_name(name, max_length=100):
    """
    Sanitizes a file or playlist name by removing or replacing invalid characters.

    Args:
        name (str): The original name to sanitize.
        max_length (int): Maximum length for the sanitized name. Default is 50.

    Returns:
        str: The sanitized name.
    """
    # Replace problematic characters with underscores
    sanitized = re.sub(r'[^\w\s-]', '_', name)
    # Replace multiple spaces or underscores with a single underscore
    sanitized = re.sub(r'[\s_]+', '_', sanitized).strip('_')
    # Limit the length if it exceeds max_length
    return sanitized[:max_length]

def extract_id_from_url(url):
    """Extract the YouTube ID from a YouTube URL."""
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    return match.group(1) if match else None

def extract_id_from_filename(filename):
    """Extract the YouTube ID from the filename (first 11 characters)."""
    return filename[:11]
