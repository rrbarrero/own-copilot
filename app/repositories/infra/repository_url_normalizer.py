import re
from dataclasses import dataclass


@dataclass
class RepositoryUrlInfo:
    owner: str
    name: str
    normalized_url: str


class RepositoryUrlNormalizer:
    @staticmethod
    def normalize(url: str) -> RepositoryUrlInfo:
        """
        Normalizes a GitHub URL to a canonical form and extracts owner/name.
        Supported formats:
        - https://github.com/owner/repo
        - https://github.com/owner/repo/
        - https://github.com/owner/repo.git
        """
        url = url.strip()

        # Simple regex for github.com URLs
        pattern = r"https?://github\.com/([^/]+)/([^/.]+)(?:\.git|/)?$"
        match = re.match(pattern, url)

        if not match:
            raise ValueError(f"Invalid or unsupported GitHub URL: {url}")

        owner = match.group(1)
        name = match.group(2)

        normalized_url = f"https://github.com/{owner}/{name}.git"

        return RepositoryUrlInfo(owner=owner, name=name, normalized_url=normalized_url)
