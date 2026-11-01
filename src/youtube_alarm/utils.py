import re


def sanitize_name(name, max_length=100):

    sanitized = re.sub(r"[^\w\s-]", "_", name)

    sanitized = re.sub(r"[\s_]+", "_", sanitized).strip("_")

    return sanitized[:max_length]


def extract_id_from_url(url):

    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    return match.group(1) if match else None


def extract_id_from_filename(filename):

    return filename[:11]
