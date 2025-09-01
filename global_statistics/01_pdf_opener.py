import fitz
import json
import re
import pandas

def page_classifier(pdf_path):
    """
    input = path to a faction pack pdf
    output = 3 lists containing each classified page (units, faction_traits, delete)
    """
    
    doc = fitz.open(pdf_path)

    units = []
    delete_pages = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()

        unit_pattern = r'\d+\+\s*\d+\s*\d+\s*\d+"'
        
        if re.search(unit_pattern, text):
            units.append(page_num)            
        else:
            delete_pages.append(page_num)

    doc.close()

    return units

def unit_reader(pdf_path, pages):
    """
    input = path to a faction pack pdf, list of unit pages
    output = dict containing all relevant information for that unit
    """

    doc = fitz.open(pdf_path)

    text = doc[0].get_text()
    faction_pattern = r'([A-Z][A-Z\s\-]+)\s*FACTION PACK'
    faction_match = re.search(faction_pattern, text)
    
    units = pandas.DataFrame(columns=['Faction', 'Unit', 'Health', 'Move', 'Save', 'Control'])

    if faction_match:
        faction_name = faction_match.group(1).strip()
        faction_name = re.sub(r'\s+', ' ', faction_name)
    else:
        faction_name = "Unknown"

    for page_num in pages:
        page = doc[page_num]
        text = page.get_text()

        unit_pattern = r'•\s*.*?WARSCROLL\s*•\s*([A-Z\s\-]+)'
        unit_match = re.search(unit_pattern, text)
        unit_name = unit_match.group(1).strip() if unit_match else "Unknown"
        unit_name = re.sub(r'\s+', ' ', unit_name)
        
        # Extract unit stats
        stats_pattern = r'(\d+)\+\s*(\d+)\s*(\d+)\s*(\d+)"'
        stats_match = re.search(stats_pattern, text)
        
        #print(f"Looking for stats pattern in page {page_num}")
        #print("Raw text sample:")
        #print(repr(text[:2500]))

        if stats_match:
            save = int(stats_match.group(1))
            control = int(stats_match.group(2))
            health = int(stats_match.group(3))
            move = int(stats_match.group(4))
        else:
            move = save = control = health = None
        
        # Create new row for this unit
        new_row = {'Faction': faction_name, 'Unit': unit_name, 'Health': health, 'Move': move, 'Save': save, 'Control': control}
        units = pandas.concat([units, pandas.DataFrame([new_row])], ignore_index=True)

    doc.close()  # Close the document after processing all pages

    return(units)

def explore_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    
    print(f"Document has {len(doc)} pages")
    
    # Look at first page
    page = doc[7]
    
    # Basic text extraction
    print("\n=== RAW TEXT ===")
    text = page.get_text()
    print(text[:1500])  # First 500 chars
    
    # Text with positions (more useful for parsing)
    print("\n=== TEXT WITH POSITIONS ===")
    text_dict = page.get_text("dict")
    
    # Print first few text blocks
    for i, block in enumerate(text_dict["blocks"][:3]):
        if "lines" in block:
            print(f"Block {i}:")
            for line in block["lines"][:2]:  # First 2 lines per block
                for span in line["spans"]:
                    print(f"  '{span['text']}' at {span['bbox']}")

# Test it
#explore_pdf("index_pdfs/lumineth.pdf")
unit_pages = page_classifier("index_pdfs/sylvaneth.pdf")
sample_pandas = unit_reader("index_pdfs/sylvaneth.pdf", unit_pages)
print(sample_pandas)