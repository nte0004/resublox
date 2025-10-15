from fontTools.ttLib import TTFont
from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Dict, Any

# CONFIG

# Page Dimensions
PAGE_WIDTH_INCHES = 8.5
PAGE_HEIGHT_INCHES = 11

# [top, right, bottom, left]
MARGIN_INCHES = [1, 1, 1, 1]

LINE_HEIGHT = 1.15

MAX_PAGES = 1

# Font Sizes (Pts)
FONT_SIZE_NAME = 13
FONT_SIZE_TITLE = 12
FONT_SIZE_SUBTITLE = 11
FONT_SIZE_REGULAR = 10

# Gaps (Pts)
SPACING_GAP = 6
SPACING_GAP_SMALL = 3

MIN_POINTS_PER_SECTION = 3      # Minimum number of points per section
SKILLS_LINE_COUNT = 2           # Number of lines to reserve for skills
COURSES_LINE_COUNT = 1          # Number of lines to reserve for courses
KEYWORD_LINES_PER_SECTION = 1

# Model Paths
# - larger the model, the longer the runtime.
# - modelHelper.py can be used to get different models.
MODEL_SMALL = './models/all-MiniLM-L6-v2'
MODEL_MEDIUM = './models/all-MiniLM-L12-v2'
MODEL_LARGE = './models/all-mpnet-base-v2'

# CHANGE FONT BELOW

# END CONFIG

@dataclass
class FontInfo:
    name: str
    path: str
    unitsPerEm: int
    fontHeightUnits: int
    fontAvgWidthUnits: int

class Fonts:
    # Values found with fontHelper.py
    ARIAL = FontInfo(
        name = 'arial', # This should be the name of the font recognized by python-docx
        path = 'fonts/arial/arial.ttf',
        unitsPerEm = 2048,
        fontHeightUnits = 2355,
        fontAvgWidthUnits = 1079
    )

FONT = Fonts.ARIAL

# Precision of text measurements
SCALE_FACTOR = 1000

PAGE_WIDTH = int(PAGE_WIDTH_INCHES * SCALE_FACTOR)
PAGE_HEIGHT = int(PAGE_HEIGHT_INCHES * SCALE_FACTOR)
MARGIN = [int(m * SCALE_FACTOR) for m in MARGIN_INCHES]

@dataclass
class SizeInfo:
    size: float
    heightPt: float = field(init=False)
    heightInch: float = field(init=False)
    height: int = field(init=False)

    def __post_init__(self):
        self.heightPt = (FONT.fontHeightUnits * self.size * LINE_HEIGHT) / FONT.unitsPerEm
        self.heightInch = (self.heightPt / 72)
        self.height = int(self.heightInch * SCALE_FACTOR)


class FontSize:
    NAME = SizeInfo(FONT_SIZE_NAME)
    REGULAR = SizeInfo(FONT_SIZE_REGULAR)
    TITLE = SizeInfo(FONT_SIZE_TITLE)
    SUBTITLE = SizeInfo(FONT_SIZE_SUBTITLE)

class Spacing:
    GAP = SizeInfo(SPACING_GAP)
    GAP_SMALL = SizeInfo(SPACING_GAP_SMALL)

class Models:
    SMALL = MODEL_SMALL
    MEDIUM = MODEL_MEDIUM
    LARGE = MODEL_LARGE



class FontMetrics:
    def __init__(self):
        self.font = TTFont(FONT.path)
        self.cmap = self.font.getBestCmap()
        self.hmtx = self.font['hmtx']
        self.maxWidthInches = PAGE_WIDTH_INCHES - MARGIN_INCHES[1] - MARGIN_INCHES[3]
        self.maxWidth = PAGE_WIDTH - MARGIN[1] - MARGIN[3]
        
    def getWidth(self, text: str, size: SizeInfo) -> int:
        """ Returns the width a string will consume.
            Does not account for line-wrapping.
        """
        totalWidth = 0
        for char in text:
            glyph_name = self.cmap.get(ord(char))
            if glyph_name:
                width, _ = self.hmtx[glyph_name]
                totalWidth += width
            else:
                totalWidth += FONT.fontAvgWidthUnits
        
        widthPts = (totalWidth * size.size) / FONT.unitsPerEm
        widthInches = widthPts / 72
        width = int(widthInches * SCALE_FACTOR)

        return width

    def getHeight(self, text: str, size: SizeInfo) -> int:
        """ Returns the height a string will consume. """
        if not text.strip():
            return int((size.size / 72) * SCALE_FACTOR)
            
        width = self.getWidth(text, size)
        lineCount = math.ceil(width / self.maxWidth)
        
        height = size.height * lineCount
        
        return height

class ItemType(Enum):
    SKILL = 0
    POINT = 1
    KEYWORD = 2
    COURSE = 3
    JOB_POSTING = 4

@dataclass
class ProcessedItem:
    text: str
    index: int
    lineHeight: int
    lineWidth: int
    itemType: ItemType
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SpaceInformation:
    jobOverhead: int = field(init = False)
    sectionOverhead: int = field(init = False)
    skillReserve: int = field(init = False)
    keywordReserve: int = field(init = False)
    maxHeight: int = field(init = False)
    keywordLinesPerSection: int = KEYWORD_LINES_PER_SECTION
    skillsLineCount: int = SKILLS_LINE_COUNT
    coursesLineCount: int = COURSES_LINE_COUNT
    minPointsPerSection: int = MIN_POINTS_PER_SECTION

    def __init__(self):
        # TODO: Have these be defined relative to some kind of YAML schema
        self.jobOverhead = (4 * FontSize.REGULAR.height) + Spacing.GAP_SMALL.height + Spacing.GAP.height
        self.sectionOverhead = FontSize.SUBTITLE.height + Spacing.GAP_SMALL.height
        self.skillReserve = self.skillsLineCount * FontSize.REGULAR.height
        self.keywordReserve = self.keywordLinesPerSection * FontSize.REGULAR.height
        self.courseReserve = self.coursesLineCount * FontSize.REGULAR.height
        self.maxHeight = (PAGE_HEIGHT - MARGIN[0] - MARGIN[2]) * MAX_PAGES

