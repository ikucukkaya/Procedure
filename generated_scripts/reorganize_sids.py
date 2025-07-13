#!/usr/bin/env python3
"""
Script to reorganize SID configurations according to the specified mapping.
"""

import xml.etree.ElementTree as ET
from collections import defaultdict

def load_generated_sids(file_path):
    """Load SIDs from generated_sids.xml file"""
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    sids = {}
    
    # Find all SID elements
    for sid_elem in root.findall('.//SID'):
        sid_name = sid_elem.get('Name')
        if sid_name:
            sids[sid_name] = sid_elem
    
    return sids

def create_sid_configurations():
    """Define the SID configuration mapping"""
    
    # KUZEY Configuration (1C, 1D, 1E variants)
    kuzey_config = {
        'VADEN': ['1C', '1D', '1E'],
        'TUDBU': ['1C', '1D', '1E'],
        'IBLAX': ['1C', '1D', '1E'],
        'BARPE': ['1C', '1D', '1E'],
        'IVGUS': ['1C', '1D', '1E'],
        'MAKOL': ['1C', '1D', '1E'],
        'EKAWE': ['1C', '1D', '1E'],
        'VICEN': ['1C', '1D', '1E'],
        'RATVU': ['1C', '1D', '1E'],
    }
    
    # GÜNEY Configuration (1F, 1G, 1H variants)
    guney_config = {
        'VADEN': ['1F', '1G', '1H'],
        'TUDBU': ['1F', '1G', '1H'],
        'IBLAX': ['1F', '1G', '1H'],
        'BARPE': ['1F', '1G', '1H'],
        'IVGUS': ['1F', '1G', '1H'],
        'MAKOL': ['1F', '1G', '1H'],
        'EKAWE': ['1F', '1G', '1H'],
        'VICEN': ['1F', '1G', '1H'],
        'RATVU': ['1F', '1G', '1H'],
    }
    
    # TERS_KUZEY Configuration (mostly 1C, 1D, 1E, but VICEN has 1Q, 1R, 1S)
    ters_kuzey_config = {
        'VADEN': ['1C', '1D', '1E'],
        'TUDBU': ['1C', '1D', '1E'],
        'IBLAX': ['1C', '1D', '1E'],
        'BARPE': ['1C', '1D', '1E'],
        'IVGUS': ['1C', '1D', '1E'],
        'MAKOL': ['1C', '1D', '1E'],
        'EKAWE': ['1C', '1D', '1E'],
        'VICEN': ['1Q', '1R', '1S'],
        'RATVU': ['1C', '1D', '1E'],
    }
    
    # TERS_GÜNEY Configuration (mostly 1F, 1G, 1H, but some exceptions)
    ters_guney_config = {
        'VADEN': ['1F', '1G', '1H'],
        'TUDBU': ['1F', '1G', '1H'],
        'IBLAX': ['1F', '1G', '1H'],
        'BARPE': ['1F', '1G', '1V'],  # 1V instead of 1H
        'IVGUS': ['1F', '1G', '1V'],  # 1V instead of 1H
        'MAKOL': ['1F', '1G', '1H'],
        'EKAWE': ['1F', '1G', '1H'],
        'VICEN': ['1T', '1U', '1V'],  # Special variants
        'RATVU': ['1T', '1U', '1V'],  # Special variants
    }
    
    return {
        'KUZEY': kuzey_config,
        'GÜNEY': guney_config,
        'TERS_KUZEY': ters_kuzey_config,
        'TERS_GÜNEY': ters_guney_config
    }

def copy_element(elem):
    """Create a deep copy of an XML element"""
    new_elem = ET.Element(elem.tag, elem.attrib)
    new_elem.text = elem.text
    new_elem.tail = elem.tail
    for child in elem:
        new_elem.append(copy_element(child))
    return new_elem

def create_new_star_sid_xml(generated_sids_path, output_path):
    """Create new STAR_SID.xml with reorganized SID configurations"""
    
    # Load existing SIDs
    all_sids = load_generated_sids(generated_sids_path)
    print(f"Loaded {len(all_sids)} SIDs from {generated_sids_path}")
    
    # Get configuration mapping
    configurations = create_sid_configurations()
    
    # Create new XML structure
    root = ET.Element('Procedures')
    sids_elem = ET.SubElement(root, 'SIDs')
    
    # Process each configuration
    for config_name, sid_mapping in configurations.items():
        print(f"\nProcessing {config_name} configuration...")
        
        runway_elem = ET.SubElement(sids_elem, 'Runway')
        runway_elem.set('Name', config_name)
        
        # Add SIDs for this configuration
        for base_name, variants in sid_mapping.items():
            for variant in variants:
                sid_name = f"{base_name}{variant}"
                
                if sid_name in all_sids:
                    # Copy the SID element
                    sid_copy = copy_element(all_sids[sid_name])
                    runway_elem.append(sid_copy)
                    print(f"  Added {sid_name}")
                else:
                    print(f"  WARNING: {sid_name} not found in generated SIDs")
    
    # Read existing STARs from current STAR_SID.xml
    try:
        current_tree = ET.parse('/Users/ibrahimkucukkaya/Desktop/PROJELER/route_draw/v.calisma/data/Airspace_01.01.2025/STAR_SID.xml')
        current_root = current_tree.getroot()
        
        # Find STARs section
        stars_elem = current_root.find('STARs')
        if stars_elem is not None:
            # Copy STARs section
            stars_copy = copy_element(stars_elem)
            root.append(stars_copy)
            print("\nCopied existing STARs section")
        
    except Exception as e:
        print(f"Warning: Could not copy STARs section: {e}")
    
    # Create XML tree and write to file
    tree = ET.ElementTree(root)
    
    # Pretty print
    def indent(elem, level=0):
        i = "\n" + level*"  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for child in elem:
                indent(child, level+1)
            if not child.tail or not child.tail.strip():
                child.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i
    
    indent(root)
    
    # Write to file
    with open(output_path, 'wb') as f:
        f.write(b'<?xml version=\'1.0\' encoding=\'utf-8\'?>\n')
        tree.write(f, encoding='utf-8')
    
    print(f"\nNew STAR_SID.xml created at: {output_path}")

if __name__ == "__main__":
    generated_sids_path = "/Users/ibrahimkucukkaya/Desktop/PROJELER/route_draw/v.calisma/generated_sids.xml"
    output_path = "/Users/ibrahimkucukkaya/Desktop/PROJELER/route_draw/v.calisma/data/Airspace_01.01.2025/STAR_SID_new.xml"
    
    create_new_star_sid_xml(generated_sids_path, output_path)
