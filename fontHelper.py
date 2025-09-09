#!/usr/bin/env python3
"""
Font Helper - English Characters
Calculates average width for common English document characters.
"""

from fontTools.ttLib import TTFont

FONT_PATH = 'fonts/arial/arial.ttf'

def get_document_characters():
    """Characters commonly used in English documents."""
    uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    lowercase = 'abcdefghijklmnopqrstuvwxyz'
    digits = '0123456789'
    punctuation = ' .,;:!?\'"-()[]{}/@#$%^&*+=<>|\\~`'
    return uppercase + lowercase + digits + punctuation

def analyze_font_metrics(font_path):
    """Extract font metrics and calculate English character averages."""
    print(f"Analyzing font: {font_path}")
    
    try:
        font = TTFont(font_path)
    except Exception as e:
        print(f"Failed to load font: {e}")
        return None
    
    # Basic font info
    head = font['head']
    hhea = font['hhea']
    units_per_em = head.unitsPerEm
    ascender = hhea.ascender
    descender = hhea.descender
    line_gap = hhea.lineGap
    font_height = ascender - descender + line_gap
    
    # Get font name
    font_name = "Unknown"
    name_table = font['name']
    for record in name_table.names:
        if record.platformID == 3 and record.langID == 1033 and record.nameID == 1:
            font_name = record.toUnicode()
            break
    
    # Get character mapping and metrics
    cmap = font.getBestCmap()
    hmtx = font['hmtx']
    
    if not cmap:
        print("No character map found")
        return None
    
    # Analyze English characters
    english_chars = get_document_characters()
    total_width = 0
    char_count = 0
    missing = []
    
    print("Processing English document characters...")
    
    for char in english_chars:
        unicode_point = ord(char)
        
        if unicode_point in cmap:
            glyph_identifier = cmap[unicode_point]
            
            # Handle both glyph names and IDs
            try:
                if isinstance(glyph_identifier, str):
                    glyph_name = glyph_identifier
                else:
                    # It's a glyph ID, convert to name
                    all_glyph_names = font.getGlyphNames()
                    glyph_name = all_glyph_names[glyph_identifier]
                
                # Get width from horizontal metrics
                width, left_bearing = hmtx[glyph_name]
                total_width += width
                char_count += 1
                
            except (KeyError, IndexError, TypeError):
                missing.append(char)
        else:
            missing.append(char)
    
    average_width = total_width / char_count if char_count > 0 else 0
    
    # Display results
    print("\n" + "=" * 50)
    print("FONT ANALYSIS COMPLETE")
    print("=" * 50)
    print(f"Font Name:                 {font_name}")
    print(f"Units Per Em:              {units_per_em}")
    print(f"Font Height:               {font_height}")
    print(f"Ascender:                  {ascender}")
    print(f"Descender:                 {descender}")
    print(f"Line Gap:                  {line_gap}")
    print()
    print("English Character Stats:")
    print(f"  Characters tested:       {len(english_chars)}")
    print(f"  Characters found:        {char_count}")
    print(f"  Average width:           {average_width:.1f} units")
    
    if missing:
        print(f"  Missing characters:      {''.join(missing[:20])}")
    
    # Sample widths
    print("\nSample Character Widths:")
    test_chars = ['A', 'a', 'M', 'i', 'W', 'l', ' ', '.']
    for char in test_chars:
        if ord(char) in cmap:
            glyph_id = cmap[ord(char)]
            try:
                if isinstance(glyph_id, str):
                    glyph_name = glyph_id
                else:
                    glyph_name = font.getGlyphNames()[glyph_id]
                width, _ = hmtx[glyph_name]
                print(f"  '{char}': {width} units")
            except:
                print(f"  '{char}': error getting width")
    
    return {
        'font_name': font_name,
        'units_per_em': units_per_em,
        'font_height': font_height,
        'ascender': ascender,
        'descender': descender,
        'line_gap': line_gap,
        'average_width': average_width,
        'chars_found': char_count
    }

def main():
    print("Font Helper - English Document Characters")
    print()
    
    result = analyze_font_metrics(FONT_PATH)
    
    if result:
        print("\n" + "=" * 50)
        print("CONSTANTS FOR YOUR CODE:")
        print("=" * 50)
        print(f"FONT_NAME = '{result['font_name']}'")
        print(f"UNITS_PER_EM = {result['units_per_em']}")
        print(f"FONT_HEIGHT = {result['font_height']}")
        print(f"AVERAGE_CHAR_WIDTH = {result['average_width']:.1f}")
        print(f"ASCENDER = {result['ascender']}")
        print(f"DESCENDER = {result['descender']}")
        print()
        print("# For text width estimation:")
        est_width = result['average_width']
        units = result['units_per_em']
        print(f"# width = text_length * {est_width:.0f} * font_size / {units}")
    else:
        print("Analysis failed!")

if __name__ == "__main__":
    main()
