"""
Link Handler Module
Provides a structured way to handle links with aliases throughout the resume system.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Tuple
import re

@dataclass
class Link:
    """
    Represents a link with optional alias and formatting information.
    
    This class handles:
    - Parsing different link formats (markdown, pipe-separated, plain)
    - Calculating display text for height measurements
    - Rendering final formatted text for document generation
    """
    descriptor: str  # e.g., "GitHub", "Demo", "Documentation"
    url: str  # The actual URL
    alias: Optional[str] = None  # The text to display (if different from URL)
    
    def __post_init__(self):
        if self.alias is None:
            if self.url.startswith('mailto:'):
                self.alias = self.url[len('mailto:')::]
            elif self.url.startswith('tel:'):
                self.alias = self.url[len('tel:')::]
            else:
                self.alias = self.url

        self.set_formatted_url()
    
    def get_display_text(self) -> str:
        """Get the text that will be displayed (for height calculation)"""
        return f"{self.descriptor}: {self.alias}"
    
    def set_formatted_url(self):
        """Get the URL with proper protocol"""
        if not self.url.startswith(('https://', 'mailto:', 'tel:')):
            if '@' in self.url and not self.url.startswith('mailto:'):
                self.url = f'mailto:{self.url}'
            elif re.fullmatch(r"^(\+\d{1,2}\s?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}$", self.url):
                digits = re.sub(r'\D', '', self.url)
                if len(digits) == 11 and digits.startswith('1'):
                    digits = digits[1:]
                
                self.url = f'tel:{digits}'
            else:
                self.url = f'https://{self.url}'
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Link':
        """Create Link from dictionary (YAML format)"""
        return cls(
            descriptor=data['descriptor'],
            url=data['url'],
            alias=data.get('alias', None)
        )

@dataclass
class LinkCollection:
    """
    Manages a collection of links for a section or project.
    Handles formatting multiple links with separators.
    """
    links: List[Link] = field(default_factory=list)
    separator: str = " | "
    
    def add_link(self, descriptor: str, url: str, alias: Optional[str] = None) -> 'LinkCollection':
        """Add a link to the collection"""
        link = Link(descriptor=descriptor, url=url, alias=alias)
        self.links.append(link)
        return self
    
    def get_display_text(self) -> str:
        """Get the combined display text for all links (for height calculation)"""
        if not self.links:
            return ""
        
        link_texts = [link.get_display_text() for link in self.links]
        return self.separator.join(link_texts)
    
    @classmethod
    def from_list(cls, data: List[dict], separator: str = " | ") -> 'LinkCollection':
        """Create LinkCollection from list of dictionaries (YAML format)"""
        collection = cls(separator=separator)
        for item in data:
            collection.links.append(Link.from_dict(item))
        return collection
    
    def __bool__(self) -> bool:
        """Check if collection has any links"""
        return len(self.links) > 0
    
    def __len__(self) -> int:
        """Get number of links in collection"""
        return len(self.links)
    
    def __iter__(self):
        """Make collection iterable"""
        return iter(self.links)

class LinkFormatter:
    """
    Utility class for formatting links in different contexts.
    This can be used by the format.py module to properly render links.
    """
    
    @staticmethod
    def format_for_docx(link: Link) -> Tuple[str, str, str]:
        """
        Format a link for DOCX output.
        Returns: (prefix_text, display_text, url)
        """
        prefix = f"{link.descriptor}: "
        display = link.alias or ""
        url = link.url
        return prefix, display, url
    
    @staticmethod
    def format_collection_for_docx(collection: LinkCollection) -> List[Tuple[str, str, str]]:
        """
        Format a LinkCollection for DOCX output.
        Returns list of (prefix_text, display_text, url) tuples with separators.
        """
        result = []
        for i, link in enumerate(collection):
            if i > 0:
                # Add separator as plain text
                result.append((collection.separator, None, None))
            prefix, display, url = LinkFormatter.format_for_docx(link)
            result.append((prefix, display, url))
        return result
