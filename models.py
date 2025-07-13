from collections import defaultdict
import json
import os
import xml.etree.ElementTree as ET # Import XML parser
import re # Import regex for route parsing
import csv # Import csv module

# Import the specific DMS parser function needed
from utils import parse_dms as utils_parse_dms

class Procedure:
    """Represents a flight procedure (SID or STAR)"""
    def __init__(self, airport, runway, name, proc_type):
        self.airport = airport
        self.runway = runway
        self.name = name
        self.type = proc_type  # "SID" or "STAR"
        self.waypoints = []
    
    def add_waypoint(self, waypoint):
        self.waypoints.append(waypoint)
    
    def sort_waypoints(self):
        """Sort waypoints by sequence number if available"""
        if all('sequence' in w for w in self.waypoints):
            self.waypoints.sort(key=lambda w: w['sequence'])

class Runway:
    """Represents an airport runway"""
    def __init__(self, airport_id, runway_id, alt_id, start_lat, start_lon, end_lat, end_lon):
        self.airport_id = airport_id
        self.id = runway_id
        self.alt_id = alt_id
        self.start_lat = start_lat
        self.start_lon = start_lon
        self.end_lat = end_lat
        self.end_lon = end_lon
        self.show_centerline = False
        self.centerline_length = 15.0
        self.show_north = True
        self.show_south = True
        # UI widgets reference (will be set by the UI)
        self.widgets = {}

class RouteExtension:
    """Represents a route extension drawn on the map"""
    def __init__(self, name, points, color=None):
        self.name = name
        self.points = points  # List of (lat, lon) tuples
        self.color = color

class DataManager:
    """Manages loading and saving of application data"""
    def __init__(self):
        self.procedures = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))
        self.runways = []
        self.drawn_elements = {
            'routes': []
        }
        self.data_dir = "data"
        self.waypoint_coords = {} # To store coordinates loaded from waypoints.xml
        self.show_waypoints = True # Control visibility of waypoints on map - Checkbox ile uyumlu olmak için True yapıldı
        self.waypoint_display = {  # Display settings for waypoints
            'size': 3,           # Size in pixels
            'color': '#ff0000',  # Default color (blue)
            'border_color': '#000000',  # Border color (black)
            'border_width': 1,   # Border width
            'show_labels': True,  # Whether to show waypoint names
            'label_font_size': 8  # Label font size
        }
        # TMA sınırları için yeni özellikler
        self.tma_boundary_points = []  # TMA sınır noktalarını depolama
        self.show_tma_boundary = True  # TMA sınırlarının görünürlük kontrolü
        self.tma_display = {  # TMA sınırlarının görünüm ayarları
            'color': '#ff4400',    # Turuncu renk
            'line_width': 1.5,     # Çizgi kalınlığı
            'line_style': 'dash',  # Çizgi stili (dash = kesikli)
        }
        
        # LTD_P_R sahaları için yeni özellikler
        self.restricted_areas = []  # Yasaklı/kısıtlı sahaların listesi [{'name': '...', 'points': [(lat, lon), ...]}]
        self.show_restricted_areas = True  # Yasaklı sahaların görünürlük kontrolü
        self.restricted_areas_display = {  # Yasaklı sahaların görünüm ayarları
            'border_color': '#ff0000',   # Kırmızı sınır
            'line_width': 1.0,           # Çizgi kalınlığı
            'fill_color': '#ff000033',   # Yarı saydam kırmızı dolgu rengi
            'grid_enabled': True,        # Grid desenini etkinleştir
            'grid_spacing': 8,           # Grid çizgileri arası piksel mesafe
            'grid_color': '#ff0000',     # Grid çizgilerinin rengi
            'grid_line_width': 0.5       # Grid çizgi kalınlığı
        }
        
    # Çizimleri JSON dosyasına kaydetmek için yeni fonksiyon
    def save_drawings_to_json(self, filepath):
        """Save all drawn routes (trombone, point-merge, user routes) to a JSON file."""
        try:
            drawings_data = {
                'routes': self.drawn_elements['routes']
            }
            
            from json_utils import json_dumps
            with open(filepath, 'w', encoding='utf-8') as f:
                json_data = json_dumps(drawings_data, indent=4)
                f.write(json_data)
            
            return True, f"Çizimler başarıyla kaydedildi: {filepath}"
        except Exception as e:
            return False, f"Çizimleri kaydetme hatası: {str(e)}"
    
    # Çizimleri JSON dosyasından yüklemek için yeni fonksiyon
    def load_drawings_from_json(self, filepath):
        """Load drawn routes (trombone, point-merge, user routes) from a JSON file."""
        try:
            from json_utils import json_loads
            with open(filepath, 'r', encoding='utf-8') as f:
                json_data = f.read()
                drawings_data = json_loads(json_data)
            
            if 'routes' in drawings_data:
                loaded_routes = drawings_data['routes']
                # Mevcut rotalara ekle
                self.drawn_elements['routes'].extend(loaded_routes)
                return True, f"{len(loaded_routes)} çizim yüklendi"
            else:
                return False, "JSON dosyasında çizim bulunamadı"
        except Exception as e:
            return False, f"Çizimleri yükleme hatası: {str(e)}"
        
    def find_airspace_folders(self):
        """Scan the data directory for folders starting with 'Airspace' (case-insensitive)"""
        airspace_folders = []
        if not os.path.isdir(self.data_dir):
            print(f"Error: Data directory '{self.data_dir}' not found.")
            return []
            
        try:
            for item in os.listdir(self.data_dir):
                item_path = os.path.join(self.data_dir, item)
                # Use lower() for case-insensitive check
                if os.path.isdir(item_path) and item.lower().startswith("airspace"):
                    airspace_folders.append(item)
        except Exception as e:
            print(f"Error scanning data directory '{self.data_dir}': {e}")
            
        return airspace_folders

    def _load_waypoints_xml(self, waypoints_xml_path):
        """Parse waypoints.xml (<Fixes><Point><Latitude/Longitude>) to get coordinates."""
        self.waypoint_coords = {}
        waypoints_loaded = 0
        waypoints_skipped = 0
        try:
            tree = ET.parse(waypoints_xml_path)
            root = tree.getroot()
            if root.tag != 'Fixes':
                print(f"Warning: Expected root tag 'Fixes' but found '{root.tag}' in {waypoints_xml_path}")
                # Attempt to find Point elements anyway

            for point_elem in root.findall('.//Point'): # Find Point anywhere under root
                name = point_elem.get('Name')
                lat_elem = point_elem.find('Latitude')
                lon_elem = point_elem.find('Longitude')
                
                if name and lat_elem is not None and lon_elem is not None and lat_elem.text and lon_elem.text:
                    lat_str = lat_elem.text.strip()
                    lon_str = lon_elem.text.strip()
                    try:
                        # Use the imported DMS parser
                        lat_decimal = utils_parse_dms(lat_str)
                        lon_decimal = utils_parse_dms(lon_str)
                        
                        if lat_decimal is not None and lon_decimal is not None:
                            self.waypoint_coords[name] = (lat_decimal, lon_decimal)
                            waypoints_loaded += 1
                        else:
                            print(f"Warning: Could not parse DMS coordinates for waypoint '{name}' ('{lat_str}', '{lon_str}') in {waypoints_xml_path}")
                            waypoints_skipped += 1
                    except Exception as e:
                        print(f"Warning: Error parsing coordinates for waypoint '{name}' ('{lat_str}', '{lon_str}') in {waypoints_xml_path}: {e}")
                        waypoints_skipped += 1
                else:
                    # Try to get name from attribute if elements are missing
                    if not name:
                        name = point_elem.get('name', '{Unknown}') 
                    print(f"Warning: Missing data (Name/Lat/Lon element or text) for waypoint '{name}' in {waypoints_xml_path}")
                    waypoints_skipped += 1
                   
            print(f"Loaded {waypoints_loaded} waypoints from {waypoints_xml_path}. Skipped {waypoints_skipped}.")
            if not self.waypoint_coords:
                print(f"Warning: No valid waypoints loaded from {waypoints_xml_path}. Check file format and content.")
                
        except ET.ParseError as e:
            print(f"Error parsing {waypoints_xml_path}: {e}")
            raise ValueError(f"Invalid XML format in {waypoints_xml_path}")
        except FileNotFoundError:
            print(f"Error: {waypoints_xml_path} not found.")
            raise
        except Exception as e:
            print(f"Error loading {waypoints_xml_path}: {e}")
            raise
            
    def _parse_route_string(self, route_string):
        """Extract waypoint names from the complex route string."""
        waypoints = []
        # Regex to find potential waypoint names (alphanumeric, possibly with numbers)
        # It looks for sequences of letters/numbers separated by hyphens,
        # ignoring constraints within brackets [].
        # Example: FM047, VADEN, ORIAC, FM084[L], ASGAX[R]
        pattern = r"(?:\]-|\A)([A-Z0-9]+)(?:\[|\-|\Z)"
        
        # Simplified approach: Split by '-' and clean up bracketed info
        parts = route_string.split('-')
        for part in parts:
            # Remove bracketed constraints like [HDGM174;A900+;R] or [A2100+;K240-;R]
            cleaned_part = re.sub(r'\[.*?\]', '', part).strip()
            if cleaned_part: # Ensure it's not empty after stripping constraints
                # Handle cases like FM084[L] -> FM084
                final_wp = re.match(r"^([A-Z0-9]+)", cleaned_part)
                if final_wp:
                    waypoints.append(final_wp.group(1))
                elif cleaned_part.isalnum(): # If it's just alphanumeric (e.g., VADEN)
                    waypoints.append(cleaned_part)
                   
        # Remove duplicates while preserving order (if needed, but likely not)
        # seen = set()
        # waypoints = [x for x in waypoints if not (x in seen or seen.add(x))]
        return waypoints

    def _load_airspace_xml(self, airspace_xml_path):
        """Parse STAR_SID.xml to load procedures (SIDs/STARs) using waypoint coordinates.
        Handles XML structure like <Procedures><SIDs><Runway Name="...""><SID Name="..."><Route><Waypoint Name="...">...</Route></SID></Runway></Procedures>
        """
        self.procedures.clear()
        procedures_loaded = 0
        procedures_skipped = 0
        missing_waypoints_count = 0

        if not self.waypoint_coords:
            print("Error: Cannot load procedures because waypoint coordinates were not loaded successfully.")
            return # Cannot proceed without waypoint coordinates

        try:
            tree = ET.parse(airspace_xml_path)
            root = tree.getroot()

            if root.tag != 'Procedures':
                print(f"Warning: Expected root tag 'Procedures' but found '{root.tag}' in {airspace_xml_path}")
                # Attempt to find SIDs/STARs anyway

            # Process SIDs
            for runway_elem in root.findall('./SIDs/Runway'):
                runway_name = runway_elem.get('Name')
                if not runway_name:
                    print(f"Warning: Skipping Runway element under SIDs without a Name in {airspace_xml_path}")
                    continue
                
                for sid_elem in runway_elem.findall('./SID'):
                    proc_type = "SID"
                    airport = sid_elem.get('Airport')
                    proc_name = sid_elem.get('Name')
                    route_elem = sid_elem.find('Route')

                    if not (airport and proc_name and route_elem is not None):
                        print(f"Warning: Incomplete data for a {proc_type} under Runway '{runway_name}' (Airport/Name/Route missing) in {airspace_xml_path}")
                        procedures_skipped += 1
                        continue

                    waypoints_data_list = []
                    valid_procedure = True
                    sequence = 1
                    for wp_elem in route_elem.findall('Waypoint'):
                        wp_name = wp_elem.get('Name')
                        if not wp_name:
                            print(f"Warning: Skipping Waypoint without a Name in {proc_type} '{proc_name}' (Runway {runway_name}) in {airspace_xml_path}")
                            continue # Skip this specific waypoint
                            
                        if wp_name in self.waypoint_coords:
                            lat, lon = self.waypoint_coords[wp_name]
                            waypoints_data_list.append({
                                "lat": lat,
                                "lon": lon,
                                "name": wp_name,
                                "sequence": sequence,
                                "altitude": wp_elem.get('Altitude', ''), # Get altitude if available
                                "speed": wp_elem.get('Speed', ''),      # Get speed if available
                                "turn": wp_elem.get('Turn', ''),        # Get turn direction if available
                                "type": proc_type
                            })
                            sequence += 1
                        else:
                            print(f"Warning: Waypoint '{wp_name}' (from {proc_type} '{proc_name}', Runway {runway_name}) not found in loaded waypoints. Skipping procedure.")
                            valid_procedure = False
                            missing_waypoints_count += 1
                            break # Skip this whole procedure

                    if valid_procedure and waypoints_data_list:
                        self.procedures[proc_type][airport][runway_name][proc_name] = waypoints_data_list
                        procedures_loaded += 1
                    elif not valid_procedure:
                        procedures_skipped += 1 # Already counted missing waypoint
                    else: # Not valid and no waypoints (e.g., all waypoints skipped)
                        print(f"Warning: No valid waypoints could be processed for {proc_type} '{proc_name}' (Runway {runway_name}) in {airspace_xml_path}")
                        procedures_skipped += 1

            # Process STARs (similar logic)
            for runway_elem in root.findall('./STARs/Runway'):
                runway_name = runway_elem.get('Name')
                if not runway_name:
                    print(f"Warning: Skipping Runway element under STARs without a Name in {airspace_xml_path}")
                    continue
                
                for star_elem in runway_elem.findall('./STAR'):
                    proc_type = "STAR"
                    airport = star_elem.get('Airport')
                    proc_name = star_elem.get('Name')
                    route_elem = star_elem.find('Route')

                    if not (airport and proc_name and route_elem is not None):
                        print(f"Warning: Incomplete data for a {proc_type} under Runway '{runway_name}' (Airport/Name/Route missing) in {airspace_xml_path}")
                        procedures_skipped += 1
                        continue

                    waypoints_data_list = []
                    valid_procedure = True
                    sequence = 1
                    for wp_elem in route_elem.findall('Waypoint'):
                        wp_name = wp_elem.get('Name')
                        if not wp_name:
                            print(f"Warning: Skipping Waypoint without a Name in {proc_type} '{proc_name}' (Runway {runway_name}) in {airspace_xml_path}")
                            continue
                            
                        if wp_name in self.waypoint_coords:
                            lat, lon = self.waypoint_coords[wp_name]
                            waypoints_data_list.append({
                                "lat": lat,
                                "lon": lon,
                                "name": wp_name,
                                "sequence": sequence,
                                "altitude": wp_elem.get('Altitude', ''),
                                "speed": wp_elem.get('Speed', ''),
                                "turn": wp_elem.get('Turn', ''),
                                "type": proc_type
                            })
                            sequence += 1
                        else:
                            print(f"Warning: Waypoint '{wp_name}' (from {proc_type} '{proc_name}', Runway {runway_name}) not found in loaded waypoints. Skipping procedure.")
                            valid_procedure = False
                            missing_waypoints_count += 1
                            break

                    if valid_procedure and waypoints_data_list:
                        self.procedures[proc_type][airport][runway_name][proc_name] = waypoints_data_list
                        procedures_loaded += 1
                    elif not valid_procedure:
                        procedures_skipped += 1
                    else:
                        print(f"Warning: No valid waypoints could be processed for {proc_type} '{proc_name}' (Runway {runway_name}) in {airspace_xml_path}")
                        procedures_skipped += 1

            print(f"Loaded {procedures_loaded} procedures from {airspace_xml_path}. Skipped {procedures_skipped} procedures.")
            if missing_waypoints_count > 0:
                print(f"Warning: Skipped {procedures_skipped} procedures due to {missing_waypoints_count} missing waypoint definitions.")
            if procedures_loaded == 0 and procedures_skipped > 0:
                print(f"Warning: No procedures were successfully loaded from {airspace_xml_path}. Check XML structure, waypoint names, and ensure waypoints.xml is loaded correctly.")

        except ET.ParseError as e:
            print(f"Error parsing {airspace_xml_path}: {e}")
            raise ValueError(f"Invalid XML format in {airspace_xml_path}")
        except FileNotFoundError:
            print(f"Error: {airspace_xml_path} not found.")
            raise
        except Exception as e:
            print(f"Error loading {airspace_xml_path}: {e}")
            import traceback
            traceback.print_exc()
            raise
            
    def _parse_position_string(self, position_str):
        """Extract latitude and longitude DMS strings from the Position attribute."""
        lat_match = re.search(r"<Latitude>(.*?)</Latitude>", position_str)
        lon_match = re.search(r"<Longitude>(.*?)</Longitude>", position_str)
        
        lat_dms_str = lat_match.group(1).strip() if lat_match else None
        lon_dms_str = lon_match.group(1).strip() if lon_match else None
        
        return lat_dms_str, lon_dms_str

    def _load_tma_boundary_xml(self, tma_xml_path):
        """Istanbul_TMA.xml dosyasından TMA sınır noktalarını yükle."""
        try:
            # TMA noktalarını sıfırla
            self.tma_boundary_points = []
            
            # XML dosyasını aç ve ayrıştır
            tree = ET.parse(tma_xml_path)
            root = tree.getroot()
            
            for point in root.findall("Point[@Type='Boundary']"):
                name = point.get('Name')
                lat_elem = point.find('Latitude')
                lon_elem = point.find('Longitude')
                
                if lat_elem is not None and lon_elem is not None:
                    # DMS formatındaki koordinatları ondalık dereceye dönüştür
                    lat = utils_parse_dms(lat_elem.text)
                    lon = utils_parse_dms(lon_elem.text)
                    
                    # Sınır noktasını listeye ekle
                    self.tma_boundary_points.append((lat, lon))
            
            # Sınırı kapatmak için ilk noktayı sonuna ekleyelim (eğer zaten kapalı değilse)
            if len(self.tma_boundary_points) > 1 and self.tma_boundary_points[0] != self.tma_boundary_points[-1]:
                self.tma_boundary_points.append(self.tma_boundary_points[0])
            
            print(f"TMA sınır noktaları başarıyla yüklendi. Toplam {len(self.tma_boundary_points)} nokta.")
            return True
        except Exception as e:
            print(f"TMA sınırlarını yükleme hatası: {e}")
            return False

    def _load_ltd_pr_xml(self, ltd_pr_xml_path):
        """LTD_P_R.xml dosyasından yasaklı/kısıtlı sahaları yükle."""
        try:
            # Mevcut sahaları sıfırla
            self.restricted_areas = []
            
            # XML dosyasını aç ve ayrıştır
            tree = ET.parse(ltd_pr_xml_path)
            root = tree.getroot()
            
            # İsim prefixlerine göre sahaları gruplandır
            area_points = {}
            
            for point in root.findall("Point[@Type='Boundary']"):
                name = point.get('Name')
                lat_elem = point.find('Latitude')
                lon_elem = point.find('Longitude')
                
                if name and lat_elem is not None and lon_elem is not None:
                    # İsmin ilk kısmını (örn. "LTP2CanakkaleII") al, numarayı çıkar
                    area_prefix = ''.join([c for c in name if not c.isdigit()]).rstrip('0123456789')
                    
                    # DMS formatındaki koordinatları ondalık dereceye dönüştür
                    lat = utils_parse_dms(lat_elem.text)
                    lon = utils_parse_dms(lon_elem.text)
                    
                    # Yeni bir saha başlatılıyorsa noktaları ekleyeceğimiz liste oluştur
                    if area_prefix not in area_points:
                        area_points[area_prefix] = []
                    
                    # Noktayı ilgili saha listesine ekle
                    area_points[area_prefix].append((lat, lon, name))
            
            # Her bir saha için noktaları işle ve kapalı alanlar oluştur
            for area_name, points in area_points.items():
                # Noktaları isimdeki sayıya göre sırala (örn. LTP2CanakkaleII01, LTP2CanakkaleII02, ...)
                sorted_points = sorted(points, key=lambda p: p[2])
                
                # Sadece lat-lon koordinatları al
                coords = [(p[0], p[1]) for p in sorted_points]
                
                # Alanı kapatmak için ilk noktayı sona ekle (eğer zaten yoksa)
                if coords and coords[0] != coords[-1]:
                    coords.append(coords[0])
                
                if len(coords) >= 3:  # En az üç nokta olmalı (üçgen oluşturmak için)
                    self.restricted_areas.append({
                        'name': area_name,
                        'points': coords,
                        'original_names': [p[2] for p in sorted_points]
                    })
            
            print(f"Yasaklı/kısıtlı sahalar başarıyla yüklendi. Toplam {len(self.restricted_areas)} saha.")
            return True
        except Exception as e:
            print(f"Yasaklı/kısıtlı sahaları yükleme hatası: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _load_runways_xml(self, runways_xml_path):
        """Parse Runways.xml (<Airport><Runway><Threshold>) to load runways and their types."""
        self.runways = []
        runways_loaded = 0
        runways_skipped = 0
        # Store threshold data including type: {airport: {thr_name: (lat, lon, type)}} 
        thresholds_by_airport = defaultdict(dict) 

        try:
            tree = ET.parse(runways_xml_path)
            root = tree.getroot()

            if root.tag != 'Airports':
                print(f"Warning: Expected root tag 'Airports' but found '{root.tag}' in {runways_xml_path}")

            # --- Step 1: Collect all Thresholds with their Types --- 
            for airport_elem in root.findall('.//Airport'):
                airport_name = airport_elem.get('Name')
                if not airport_name:
                    print(f"Warning: Skipping Airport element without a Name in {runways_xml_path}")
                    continue
                
                for runway_elem in airport_elem.findall('.//Runway'):
                    # Get runway-level type, default to MIX if not specified
                    runway_level_type = runway_elem.get('Type', 'MIX').upper()
                    
                    for threshold_elem in runway_elem.findall('.//Threshold'):
                        thr_name = threshold_elem.get('Name')
                        # Use threshold type if present, otherwise fallback to runway level type
                        thr_type = threshold_elem.get('Type', runway_level_type).upper()
                        lat_elem = threshold_elem.find('Latitude')
                        lon_elem = threshold_elem.find('Longitude')
                        
                        if thr_name and lat_elem is not None and lon_elem is not None and lat_elem.text and lon_elem.text:
                            lat_str = lat_elem.text.strip()
                            lon_str = lon_elem.text.strip()
                            try:
                                lat_decimal = utils_parse_dms(lat_str)
                                lon_decimal = utils_parse_dms(lon_str)
                                if lat_decimal is not None and lon_decimal is not None:
                                    if thr_name in thresholds_by_airport[airport_name]:
                                        print(f"Warning: Duplicate threshold name '{thr_name}' found for airport '{airport_name}'. Overwriting.")
                                    thresholds_by_airport[airport_name][thr_name] = (lat_decimal, lon_decimal, thr_type) # Store type
                                else:
                                    print(f"Warning: Could not parse DMS for threshold '{thr_name}' at airport '{airport_name}'.")
                                    runways_skipped += 1 
                            except Exception as e:
                                print(f"Warning: Error parsing coordinates for threshold '{thr_name}' at airport '{airport_name}': {e}")
                                runways_skipped += 1
                        else:
                            print(f"Warning: Missing data (Name/Lat/Lon) for a threshold at airport '{airport_name}'.")
                            runways_skipped += 1
                           
            # --- Step 2: Pair Thresholds and Determine Runway Type --- 
            for airport_name, thresholds in thresholds_by_airport.items():
                processed_thresholds = set()
                for thr1_name, data1 in thresholds.items():
                    if thr1_name in processed_thresholds:
                        continue
                        
                    coords1 = (data1[0], data1[1])
                    type1 = data1[2]
                    
                    # Try to find the opposing runway threshold
                    try:
                        rwy_num = int(re.match(r'(\d+)', thr1_name).group(1))
                        opposing_num = (rwy_num + 18) % 36
                        if opposing_num == 0: opposing_num = 36
                        opposing_names = []
                        base_opp_name = f"{( (rwy_num + 18) % 36 ) or 36 :02d}"
                        if 'L' in thr1_name: opposing_names.append(base_opp_name + "R")
                        elif 'R' in thr1_name: opposing_names.append(base_opp_name + "L")
                        elif 'C' in thr1_name: opposing_names.append(base_opp_name + "C")
                        else: opposing_names.append(base_opp_name)
                        # Sometimes parallel runways might exist without L/R, check basic opposite
                        if base_opp_name + "L" in thresholds: opposing_names.append(base_opp_name + "L")
                        if base_opp_name + "R" in thresholds: opposing_names.append(base_opp_name + "R")
                        if base_opp_name + "C" in thresholds: opposing_names.append(base_opp_name + "C")
                        
                        thr2_name = None
                        coords2 = None
                        type2 = 'MIX' # Default type for opposing end if not found explicitly
                        for potential_opp_name in opposing_names:
                            if potential_opp_name in thresholds and potential_opp_name not in processed_thresholds:
                                thr2_name = potential_opp_name
                                data2 = thresholds[thr2_name]
                                coords2 = (data2[0], data2[1])
                                type2 = data2[2] # Get type of opposing end
                                break
                                
                        if thr2_name and coords2:
                            runway_id = f"{airport_name} {thr1_name}/{thr2_name}"
                            alt_id = f"{airport_name} {thr2_name}/{thr1_name}"
                            
                            # Determine overall runway type (prioritize ARR/MIX)
                            runway_type = 'DEP' # Assume DEP initially
                            if type1 == 'ARR' or type2 == 'ARR' or type1 == 'MIX' or type2 == 'MIX':
                                runway_type = 'MIX' # Treat ARR or MIX as MIX for drawing thickness
                                
                            self.runways.append({
                                'id': runway_id, 
                                'alt_id': alt_id,
                                'start_lat': coords1[0],
                                'start_lon': coords1[1],
                                'end_lat': coords2[0],
                                'end_lon': coords2[1],
                                'runway_type': runway_type, # Store the determined type
                                # Store individual end types if needed later
                                f'type_{thr1_name}': type1,
                                f'type_{thr2_name}': type2
                            })
                            runways_loaded += 1
                            processed_thresholds.add(thr1_name)
                            processed_thresholds.add(thr2_name) # Mark both as processed
                        else:
                            pass # Could not find a pair
                            
                    except (ValueError, AttributeError, IndexError) as e: # Handle errors in number parsing
                        print(f"Warning: Could not determine opposing runway for '{thr1_name}' at '{airport_name}': {e}")
                        runways_skipped += 1
                        processed_thresholds.add(thr1_name) # Mark as processed to avoid re-checking
                       
            print(f"Processed thresholds and formed {runways_loaded} runways. Issues encountered with {runways_skipped} thresholds/pairs.")
            if runways_loaded == 0:
                print(f"Warning: No valid runway pairs could be formed. Check threshold names and coordinates in {runways_xml_path}.")
                    
        except FileNotFoundError:
            print(f"Error: {runways_xml_path} not found.")
            raise # Re-raise critical error
        except Exception as e:
            print(f"Error loading/processing {runways_xml_path}: {e}")
            import traceback
            traceback.print_exc()
            raise # Re-raise critical error
            
    def load_airspace_data(self, selected_folder):
        """Load all airspace data (waypoints, procedures, runways) from selected folder."""
        print(f"Loading airspace data using folder: {selected_folder}")
        waypoints_file = os.path.join(selected_folder, "waypoints.xml")
        airspace_file = os.path.join(selected_folder, "STAR_SID.xml")
        runways_file = os.path.join(selected_folder, "Runways.xml") # Path to Runways.xml
        tma_file = os.path.join(selected_folder, "Istanbul_TMA.xml") # TMA sınırları dosyası
        ltd_pr_file = os.path.join(selected_folder, "LTD_P_R.xml") # LTD_P_R dosyası
        
        # Clear all previous data
        self.procedures.clear()
        self.runways = []
        self.waypoint_coords = {}
        self.tma_boundary_points = []
        self.restricted_areas = []
        
        success = True
        # --- Load Waypoints (Critical) ---
        try:
            self._load_waypoints_xml(waypoints_file)
            if not self.waypoint_coords: # Check if any waypoints were actually loaded
                print("CRITICAL: No valid waypoints loaded. Procedures cannot be loaded.")
                success = False
        except Exception as e:
            print(f"CRITICAL: Failed to load waypoints from {waypoints_file}. Procedures cannot be loaded. Error: {e}")
            success = False
            
        # --- Load Procedures (Requires Waypoints) ---
        if success: # Only proceed if waypoints loaded
            try:
                self._load_airspace_xml(airspace_file)
            except Exception as e:
                print(f"ERROR: Failed to load procedures from {airspace_file}. Error: {e}")
                # Decide if procedures are critical
                # success = False
        else:
            print("Skipping procedure loading due to waypoint loading failure.")
            
        # --- Load Runways (Independent but potentially Critical) ---
        try:
            self._load_runways_xml(runways_file) # Call the new XML runway loader
            if not self.runways: # Check if any runways were loaded
                print("Warning: No valid runways were loaded from XML.")
                # Decide if this is critical
                # success = False
        except Exception as e:
            print(f"ERROR: Failed to load runways from {runways_file}. Error: {e}")
            success = False # Assume runways are critical
            
        # --- Load TMA Boundaries (Independent, non-critical) ---
        try:
            self._load_tma_boundary_xml(tma_file)
            if not self.tma_boundary_points:
                print("Warning: No valid TMA boundary points were loaded.")
                # TMA sınır noktaları kritik değil, bu yüzden success değerini etkilemez
        except Exception as e:
            print(f"ERROR: Failed to load TMA boundaries from {tma_file}. Error: {e}")
            # TMA sınır noktaları kritik değil, bu yüzden success değerini etkilemez

        # --- Load LTD_P_R Areas (Independent, non-critical) ---
        try:
            self._load_ltd_pr_xml(ltd_pr_file)
            if not self.restricted_areas:
                print("Warning: No valid restricted areas were loaded.")
                # LTD_P_R sahaları kritik değil, bu yüzden success değerini etkilemez
        except Exception as e:
            print(f"ERROR: Failed to load restricted areas from {ltd_pr_file}. Error: {e}")
            # LTD_P_R sahaları kritik değil, bu yüzden success değerini etkilemez

        if success:
            print("Airspace data loading process completed.")
        else:
            print("Airspace data loading process completed with errors.")
            self.procedures.clear()
            self.runways = []
            self.waypoint_coords = {}
            
        return success

    # Remove original runway loader
    # def load_runway_data(self): ... 

    # Keep load_geo_data if map.geojson is independent of airspace folders
    def load_geo_data(self, geojson_path):
        """Load GeoJSON data for map from the specified path."""
        try:
            with open(geojson_path, 'r', encoding='utf-8') as f:
                geo_data = json.load(f)
            print(f"GeoJSON data loaded successfully from {geojson_path}.")
            return geo_data
        except FileNotFoundError:
            print(f"Error: GeoJSON file not found at {geojson_path}")
            return None # Return None on error
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in {geojson_path}")
            return None # Return None on error
        except Exception as e:
            print(f"Error loading {geojson_path}: {str(e)}")
            return None # Return None on error

    def find_geojson_files(self):
        """Scan the data directory for files ending with .geojson."""
        geojson_files = []
        if not os.path.isdir(self.data_dir):
            print(f"Error: Data directory '{self.data_dir}' not found.")
            return []
            
        try:
            for item in os.listdir(self.data_dir):
                item_path = os.path.join(self.data_dir, item)
                # Check if it's a file and ends with .geojson (case-insensitive)
                if os.path.isfile(item_path) and item.lower().endswith(".geojson"):
                    geojson_files.append(item)
        except Exception as e:
            print(f"Error scanning data directory '{self.data_dir}' for GeoJSON files: {e}")
            
        return geojson_files 

    def parse_csv_trajectory(self, filepath):
        """Parse a CSV file for trajectory data.

        Assumes format: Timestamp,UTC,Callsign,Position,Altitude,Speed,Direction
        where Position is "lat,lon".

        Returns trajectory_id (filename) and a list of (lat, lon) tuples.
        """
        points = []
        trajectory_id = os.path.splitext(os.path.basename(filepath))[0]
        callsign = None
        
        try:
            with open(filepath, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                # Check header implicitly by trying to access fields
                if not all(h in reader.fieldnames for h in ['Position', 'Callsign']):
                    print(f"Warning: Missing required columns ('Position', 'Callsign') in {filepath}")
                    return trajectory_id, None
                    
                for i, row in enumerate(reader):
                    if i == 0: # Get callsign from first row
                        callsign = row.get('Callsign', trajectory_id)
                        trajectory_id = callsign # Use callsign as ID if available

                    position_str = row.get('Position')
                    if position_str:
                        try:
                            lat_str, lon_str = position_str.split(',')
                            lat = float(lat_str.strip())
                            lon = float(lon_str.strip())
                            alt_str = row.get('Altitude', '0') # Get altitude, default to 0 if missing
                            try:
                                alt = float(alt_str) if alt_str else 0.0
                            except ValueError:
                                alt = 0.0 # Default altitude if conversion fails
                            points.append((lat, lon, alt)) # Store altitude
                        except ValueError:
                            print(f"Warning: Could not parse lat/lon from '{position_str}' in row {i+2} of {filepath}")
                            continue # Skip this row
            
            if not points:
                print(f"Warning: No valid trajectory points found in {filepath}")
                return trajectory_id, None
                
            return trajectory_id, points
        except FileNotFoundError:
            print(f"Error: CSV file not found: {filepath}")
            return trajectory_id, None
        except Exception as e:
            print(f"Error parsing CSV file {filepath}: {e}")
            import traceback
            traceback.print_exc()
            return trajectory_id, None

    def parse_kml_trajectory(self, filepath):
        """Parse a KML file for the first LineString coordinates.

        Returns trajectory_id (filename) and a list of (lat, lon) tuples.
        """
        points = []
        trajectory_id = os.path.splitext(os.path.basename(filepath))[0]
        
        try:
            # KML uses namespaces, we need to handle them
            # Common namespace (may need adjustment if file uses different prefix)
            namespaces = {'kml': 'http://www.opengis.net/kml/2.2'}
            
            tree = ET.parse(filepath)
            root = tree.getroot()
            
            # Find the Folder named 'Trail'
            trail_folder = None
            # Try with namespace first
            for folder in root.findall('.//kml:Folder', namespaces):
                name_elem = folder.find('kml:name', namespaces)
                if name_elem is not None and name_elem.text and 'trail' in name_elem.text.lower():
                    trail_folder = folder
                    break
            # If not found, try without namespace
            if trail_folder is None:
                for folder in root.findall('.//Folder'):
                    name_elem = folder.find('name')
                    if name_elem is not None and name_elem.text and 'trail' in name_elem.text.lower():
                        trail_folder = folder
                        break
            
            if trail_folder is None:
                print(f"Warning: Could not find a Folder named 'Trail' in {filepath}")
                return trajectory_id, None

            # Find ALL Placemarks within the Trail folder
            placemarks = trail_folder.findall('.//kml:Placemark', namespaces) 
            if not placemarks:
                placemarks = trail_folder.findall('.//Placemark') # Try without namespace
            
            if not placemarks:
                print(f"Warning: No Placemarks found within the 'Trail' folder in {filepath}")
                return trajectory_id, None

            # Iterate through each placemark and extract coordinates
            all_coords_text = ""
            for placemark in placemarks:
                # Look for coordinates within MultiGeometry/LineString or directly in LineString
                coord_paths = [
                    'kml:MultiGeometry/kml:LineString/kml:coordinates', 
                    'kml:LineString/kml:coordinates'
                ]
                coordinates_elem = None
                for path in coord_paths:
                    coordinates_elem = placemark.find(path, namespaces)
                    if coordinates_elem is not None and coordinates_elem.text:
                        break # Found coordinates with namespace
                
                # If not found with namespace, try without
                if coordinates_elem is None or not coordinates_elem.text:
                    coord_paths_no_ns = [
                        'MultiGeometry/LineString/coordinates',
                        'LineString/coordinates'
                    ]
                    for path in coord_paths_no_ns:
                        coordinates_elem = placemark.find(path)
                        if coordinates_elem is not None and coordinates_elem.text:
                            break # Found coordinates without namespace

                if coordinates_elem is not None and coordinates_elem.text:
                    # Append coordinates text, ensuring space separation
                    all_coords_text += coordinates_elem.text.strip() + " " 
                # else: # Optional: Warn if a placemark doesn't have coordinates?
                #     print(f"Warning: No coordinates found in a Placemark within {filepath}")
            
            # Process the concatenated coordinates string
            if not all_coords_text:
                print(f"Warning: No coordinate text found in any Placemark within the 'Trail' folder of {filepath}")
                return trajectory_id, None

            coord_tuples = all_coords_text.strip().split()
            
            last_point = None # To handle potential duplicates between segments
            for coord_str in coord_tuples:
                try:
                    lon_str, lat_str, *alt_parts = coord_str.split(',') # Capture optional altitude
                    lat = float(lat_str.strip())
                    lon = float(lon_str.strip())
                    alt = 0.0 # Default altitude
                    if alt_parts:
                        try:
                            alt = float(alt_parts[0].strip())
                        except ValueError:
                            pass # Keep default alt if conversion fails
                            
                    current_point = (lat, lon, alt) # Store altitude
                    # Avoid adding duplicate points that often connect segments
                    if current_point != last_point:
                        points.append(current_point)
                        last_point = current_point
                except ValueError:
                    print(f"Warning: Could not parse lon/lat from '{coord_str}' in {filepath}")
                    continue # Skip this tuple
            
            if not points:
                print(f"Warning: No valid trajectory points found in KML {filepath}")
                return trajectory_id, None

            return trajectory_id, points
        except FileNotFoundError:
            print(f"Error: KML file not found: {filepath}")
            return trajectory_id, None
        except ET.ParseError as e:
            print(f"Error parsing KML file {filepath}: {e}")
            return trajectory_id, None
        except Exception as e:
            print(f"Error processing KML file {filepath}: {e}")
            import traceback
            traceback.print_exc()
            return trajectory_id, None

    # CSV dosyasından çizilen rotaları yükleme fonksiyonu
    def load_route_from_csv(self, filepath):
        """Load a route from CSV file format.
        Supports standard user routes, trombone, and point merge route types.
        Returns (success, message, loaded_route)
        """
        try:
            route_name = os.path.splitext(os.path.basename(filepath))[0]
            points = []
            route_type = 'user_route'  # Varsayılan rota türü
            
            with open(filepath, 'r', newline='', encoding='utf-8') as csvfile:
                # İlk olarak dosyayı satır satır okuyarak başlık bilgilerini analiz edelim
                lines = csvfile.readlines()
                
                # Rota türünü ve yapılandırma bilgilerini tespit et 
                # Yapılandırma değerlerini depolamak için sözlükler
                pointmerge_config = {
                    'pattern_type': 'pointmerge'
                }
                trombone_config = {
                    'pattern_type': 'trombone'
                }
                
                for i, line in enumerate(lines):
                    if 'Route Type:' in line:
                        if 'trombone' in line.lower():
                            route_type = 'trombone'
                        elif 'pointmerge' in line.lower():
                            route_type = 'pointmerge'
                    
                    # Point Merge yapılandırma bilgilerini oku
                    elif 'First Point Distance (NM):' in line:
                        parts = line.split(',')
                        if len(parts) > 1:
                            try:
                                distance_value = float(parts[1].strip())
                                pointmerge_config['first_point_distance'] = distance_value  
                                pointmerge_config['distance'] = distance_value  # Her iki alanı da ayarla
                            except (ValueError, IndexError):
                                pass
                    
                    elif 'Track Angle (°):' in line or 'Track Angle (°):' in line:
                        parts = line.split(',')
                        if len(parts) > 1:
                            try:
                                angle_value = float(parts[1].strip())
                                pointmerge_config['track_angle'] = angle_value
                                pointmerge_config['angle'] = angle_value  # Her iki alanı da ayarla
                            except (ValueError, IndexError):
                                pass
                                
                    elif 'Number of Segments:' in line:
                        parts = line.split(',')
                        if len(parts) > 1:
                            try:
                                num_segments = int(parts[1].strip())
                                pointmerge_config['num_segments'] = num_segments
                            except (ValueError, IndexError):
                                pass
                    
                    # Trombone yapılandırma bilgilerini de oku
                    elif 'Trombone Configuration:' in line:
                        # Trombone yapılandırma bilgileri takip ediyor demektir
                        # Boş bir config nesnesini hazırla
                        trombone_config = {
                            'pattern_type': 'trombone',
                            'preserve_current_position': False  # CSV'den yüklenen rotalar için varsayılan
                        }
                    
                    # Rota taşınmış mı/döndürülmüş mü bilgisini oku - hem trombone hem point merge için
                    elif 'Moved or Rotated:' in line:
                        parts = line.split(',')
                        if len(parts) > 1:
                            moved_value = parts[1].strip().lower()
                            is_moved = moved_value in ['yes', 'true', '1']
                            # Rota tipine göre ilgili config'e ekle
                            if route_type == 'trombone':
                                trombone_config['moved_or_rotated'] = is_moved
                            elif route_type == 'pointmerge':
                                pointmerge_config['moved_or_rotated'] = is_moved
                
                # Waypoints bölümünü ve uygun sütunları bulmak için
                waypoints_start_idx = -1
                header_row = None
                lat_index, lon_index = -1, -1
                
                for i, line in enumerate(lines):
                    line = line.strip()
                    if line == 'Waypoints' or line.startswith('Waypoint') or line.startswith('WP'):
                        waypoints_start_idx = i
                        # Bir sonraki satır başlık satırı olmalı
                        if i + 1 < len(lines):
                            header_row = lines[i + 1].strip().split(',')
                            break
                
                if header_row:
                    # Özel formatlı CSV'lerin başlıklarını analiz et
                    for j, header in enumerate(header_row):
                        header_lower = header.lower()
                        # Desimal koordinat sütunlarını bul (öncelikli)
                        if header_lower in ['lat (dec)', 'latitude (dec)']:
                            lat_index = j
                        elif header_lower in ['lon (dec)', 'longitude (dec)', 'long (dec)']:
                            lon_index = j
                    
                    # Desimal koordinat sütunları bulunamadıysa DMS formatını kontrol et
                    if lat_index < 0 or lon_index < 0:
                        for j, header in enumerate(header_row):
                            header_lower = header.lower()
                            if header_lower in ['lat', 'latitude', 'lat (dms)']:
                                lat_index = j
                            elif header_lower in ['lon', 'long', 'longitude', 'lon (dms)']:
                                lon_index = j
                
                # Trombone yapılandırması için özel parametre değerlerini ara
                if route_type == 'trombone':
                    for i, line in enumerate(lines):
                        # Trombone threshold mesafesini ara
                        if 'Threshold Distance (NM):' in line:
                            parts = line.split(',')
                            if len(parts) > 1:
                                try:
                                    trombone_config['threshold_distance'] = float(parts[1].strip())
                                    print(f"CSV'den trombone threshold distance: {trombone_config['threshold_distance']}")
                                except (ValueError, IndexError):
                                    pass
                                    
                        # Trombone base açısını ara
                        elif 'Base Angle (°):' in line or 'Base Angle (deg):' in line:
                            parts = line.split(',')
                            if len(parts) > 1:
                                try:
                                    trombone_config['base_angle'] = float(parts[1].strip())
                                    print(f"CSV'den trombone base angle: {trombone_config['base_angle']}")
                                except (ValueError, IndexError):
                                    pass
                                    
                        # Trombone base mesafesini ara
                        elif 'Base Distance (NM):' in line:
                            parts = line.split(',')
                            if len(parts) > 1:
                                try:
                                    trombone_config['base_distance'] = float(parts[1].strip())
                                    print(f"CSV'den trombone base distance: {trombone_config['base_distance']}")
                                except (ValueError, IndexError):
                                    pass
                                    
                        # Trombone uzatma uzunluğunu ara
                        elif 'Extension Length (NM):' in line:
                            parts = line.split(',')
                            if len(parts) > 1:
                                try:
                                    trombone_config['extension_length'] = float(parts[1].strip())
                                    print(f"CSV'den trombone extension length: {trombone_config['extension_length']}")
                                except (ValueError, IndexError):
                                    pass

                # Eğer waypoints bölümü bulunduysa ve başlık satırı işlendiyse, verileri işle
                if waypoints_start_idx >= 0 and header_row and lat_index >= 0 and lon_index >= 0:
                    # Waypoint verilerini içeren satırları işle (başlık satırından sonra)
                    for i in range(waypoints_start_idx + 2, len(lines)):
                        line = lines[i].strip()
                        if not line:  # Boş satırı atla
                            continue
                            
                        row = line.split(',')
                        if len(row) > max(lat_index, lon_index):
                            try:
                                # Öncelikle koordinat değerlerini alıp kontrol edelim
                                lat_value = row[lat_index].strip()
                                lon_value = row[lon_index].strip()
                                
                                # Ondalık format mı DMS format mı kontrol et
                                try:
                                    lat = float(lat_value)
                                    lon = float(lon_value)
                                except ValueError:
                                    # DMS formatındaysa utils ile dönüştür
                                    from utils import parse_dms
                                    lat = parse_dms(lat_value)
                                    lon = parse_dms(lon_value)
                                    
                                if lat is not None and lon is not None:
                                    points.append((lat, lon))
                            except (ValueError, IndexError) as e:
                                print(f"Hata: Satır işlenirken hata oluştu: {row}, Detay: {str(e)}")
                                continue
                else:
                    # Standart formatları kontrol et (geleneksel CSV)
                    csvfile.seek(0)  # Dosyayı başa sar
                    reader = csv.reader(csvfile)
                    header_row = next(reader, None)
                    
                    if not header_row:
                        return False, "CSV dosyası boş.", None
                    
                    if header_row[0] == "Waypoint" or header_row[0] == "WP" or header_row[0].startswith("WP"):
                        # Standart rota CSV formatı
                        for row in reader:
                            if len(row) >= 3:  # En az 3 sütun: WPn, lat, lon
                                try:
                                    lat = float(row[1])
                                    lon = float(row[2])
                                    points.append((lat, lon))
                                except (ValueError, IndexError):
                                    print(f"Hata: Geçersiz satır: {row}")
                                    continue
                    else:
                        # Alternatif format kontrolü - başlıkları arayalım
                        lat_index, lon_index = -1, -1
                        for i, header in enumerate(header_row):
                            header_lower = header.lower()
                            if header_lower in ["lat", "latitude"]:
                                lat_index = i
                            elif header_lower in ["lon", "long", "longitude"]:
                                lon_index = i
                        
                        if lat_index >= 0 and lon_index >= 0:
                            for row in reader:
                                if len(row) > max(lat_index, lon_index):
                                    try:
                                        lat = float(row[lat_index])
                                        lon = float(row[lon_index])
                                        points.append((lat, lon))
                                    except (ValueError, IndexError):
                                        print(f"Hata: Geçersiz satır: {row}")
                                        continue
                        else:
                            return False, "CSV dosyasında geçerli Lat/Lon sütunları bulunamadı.", None
            
            if not points:
                return False, "CSV dosyasında geçerli nokta verisi bulunamadı.", None
            
            # Noktalardan bir rota oluştur
            import uuid
            route_id = str(uuid.uuid4())
            
            # Rota türüne göre renk seç
            route_color = '#FF0000'  # Standart kullanıcı rotası için varsayılan kırmızı
            if route_type == 'trombone':
                route_color = '#0000FF'  # Trombone için mavi
            elif route_type == 'pointmerge':
                route_color = '#00FF00'  # Point merge için yeşil
            
            new_route = {
                'id': route_id,
                'name': route_name,
                'type': route_type,
                'points': points,
                'color': route_color,
                'segment_distances': [],  # Daha sonra hesaplanabilir
                'track_angles': []  # Daha sonra hesaplanabilir
            }
            
            # Pattern türüne göre yapılandırma bilgilerini ekle
            if route_type == 'pointmerge':
                # Eğer merge point bilgileri bulunduysa, bunları ayarla
                if points and len(points) > 0:
                    # Son nokta merge point olmalıdır
                    merge_point = points[-1]
                    pointmerge_config['merge_lat'] = merge_point[0]
                    pointmerge_config['merge_lon'] = merge_point[1]
                
                # Segment bilgilerini oluştur
                if 'first_point_distance' in pointmerge_config and 'num_segments' in pointmerge_config:
                    first_point_distance = pointmerge_config['first_point_distance']
                    num_segments = pointmerge_config['num_segments']
                    
                    # Segment mesafelerini hesapla
                    total_arc_width = 60.0  # Varsayılan yay genişliği (derece)
                    import math
                    arc_length_nm = math.radians(total_arc_width) * first_point_distance
                    segment_distance = arc_length_nm / num_segments if num_segments > 0 else arc_length_nm
                    pointmerge_config['segments'] = [segment_distance] * num_segments
                
                # Config'i rotaya ekle
                new_route['config'] = pointmerge_config
            
            # Trombone yapılandırma bilgilerini ekle
            elif route_type == 'trombone':
                # Trombone için temel yapılandırma ekle
                if not 'moved_or_rotated' in trombone_config:
                    trombone_config['moved_or_rotated'] = False  # Başlangıçta hareket ettirilmemiş
                
                # pattern_type ekle
                trombone_config['pattern_type'] = 'trombone'
                
                # Pist bilgileri ve waypoint'ler: 
                # - A noktası (WP1) threshold mesafesindeki nokta
                # - B noktası (WP2) base leg dönüş noktası
                # - C noktası (WP3) uzatma noktası
                if points and len(points) >= 3:
                    # CSV'den yüklenen noktalarda doğru sıralama kullanılır:
                    # İlk nokta (WP1) threshold mesafesindeki A noktası
                    point_a = points[0]
                    
                    # İkinci nokta (WP2) base leg dönüş noktası B
                    point_b = points[1]
                    
                    # Üçüncü nokta (WP3) uzatma noktası C
                    point_c = points[2]
                    
                    # Doğru pist hesaplaması için A noktasından geriye doğru hesaplanacak
                    # bir "sanal" runway threshold noktası oluşturmamız gerekiyor
                    # Bu nokta tam olarak pist eşiği değilse de, eşik noktası gibi
                    # trombone deseninin doğru konumunu koruyacak bir hesaplamaya imkan verir
                    
                    import math
                    from utils import calculate_bearing, calculate_point_at_distance_and_bearing
                    
                    # Trombone dizilimini belirlemek için açıları ve uzunlukları analiz et
                    # A ve B noktaları arası, base leg
                    base_bearing = calculate_bearing(point_a[0], point_a[1], point_b[0], point_b[1])
                    
                    # B'den C'ye olan yön, uzatma kısmının yönü
                    extension_bearing = calculate_bearing(point_b[0], point_b[1], point_c[0], point_c[1])
                    
                    # Extension açısı aslında pist yönü ile aynıdır
                    runway_heading = extension_bearing
                    
                    # Approach açısı (piste yaklaşma yönü) pist yönünün 180 derece tersidir
                    approach_bearing = (runway_heading + 180) % 360
                    
                    # Runway threshold noktasını, A noktasından geriye doğru (approach yönünde) 
                    # threshold_distance mesafesinde hesaplayarak konumlandır
                    threshold_distance = trombone_config.get('threshold_distance', 3.0)
                    
                    # NOT: Bu ÇOK ÖNEMLİ - threshold_distance değişse bile, burada korunan gerçek pist eşiği konumudur
                    runway_lat, runway_lon = calculate_point_at_distance_and_bearing(
                        point_a[0], point_a[1], threshold_distance, approach_bearing
                    )
                    
                    # Tam bir runway yapılandırması oluştur
                    trombone_config['runway'] = {
                        'id': f'CSV_RWY_{route_id[:8]}',  # Benzersiz bir ID oluştur
                        'threshold_lat': runway_lat,  # Hesaplanan eşik noktası (sabit kalmalı)
                        'threshold_lon': runway_lon,  # 
                        'start_lat': runway_lat,  # Start = threshold
                        'start_lon': runway_lon,  # 
                        'end_lat': 2*point_c[0] - point_b[0],  # Pist yönünü korumak için daha uzakta bir nokta
                        'end_lon': 2*point_c[1] - point_b[1]    # B->C yönü extrapolasyonu
                    }
                    
                    print(f"CSV yükleme: Pist eşik koordinatları hesaplandı - {runway_lat:.6f}, {runway_lon:.6f}")
                    print(f"  Bu koordinatlar threshold_distance={threshold_distance} değiştiğinde SABIT kalacak")
                
                # Trombone parametrelerini varsayılan değerlerle ekle veya eksik olanları doldur
                # Bu parametreler, CSV dosyasındaki değerlerden elde edilmiş veya
                # CSV'de eksikse varsayılan değerlerle doldurulmuş olabilir
                
                # Eğer waypoint'ler varsa ve bu bir trombon dosyası ise,
                # trombon deseninin geometrisinden parametreleri hesaplayabiliriz
                if points and len(points) >= 3:
                    # Noktalar arasındaki mesafe ve açıları hesapla
                    from utils import calculate_distance, calculate_bearing
                    
                    # A, B ve C noktaları (sırayla)
                    point_a = points[0]
                    point_b = points[1]
                    point_c = points[2]
                    
                    # CSV dosya yüklemelerinde daha doğru parametre hesaplaması
                    # 1. Base distance: A ve B noktaları arasındaki mesafe
                    if 'base_distance' not in trombone_config:
                        base_distance = calculate_distance(point_a[0], point_a[1], point_b[0], point_b[1])
                        trombone_config['base_distance'] = round(base_distance, 1)
                        print(f"CSV yüklemesi: Hesaplanan base_distance = {trombone_config['base_distance']} NM")
                    
                    # 2. Extension length: B ve C noktaları arasındaki mesafe
                    if 'extension_length' not in trombone_config:
                        extension_length = calculate_distance(point_b[0], point_b[1], point_c[0], point_c[1])
                        trombone_config['extension_length'] = round(extension_length, 1)
                        print(f"CSV yüklemesi: Hesaplanan extension_length = {trombone_config['extension_length']} NM")
                
                # Hala eksik değerler varsa varsayılanları kullan
                if 'threshold_distance' not in trombone_config:
                    trombone_config['threshold_distance'] = 3.0
                    print("CSV yüklemesi: Varsayılan threshold_distance = 3.0 NM kullanılıyor")
                    
                if 'base_angle' not in trombone_config:
                    trombone_config['base_angle'] = 90.0
                    print("CSV yüklemesi: Varsayılan base_angle = 90.0° kullanılıyor")
                    
                if 'base_distance' not in trombone_config:
                    trombone_config['base_distance'] = 5.0
                    print("CSV yüklemesi: Varsayılan base_distance = 5.0 NM kullanılıyor")
                    
                if 'extension_length' not in trombone_config:
                    trombone_config['extension_length'] = 3.0
                    print("CSV yüklemesi: Varsayılan extension_length = 3.0 NM kullanılıyor")
                
                # Config'i rotaya ekle
                new_route['config'] = trombone_config
            
            # Segment mesafelerini ve açılarını hesapla
            from utils import calculate_distance, calculate_bearing
            segment_distances = []
            track_angles = []
            
            for i in range(1, len(points)):
                prev_lat, prev_lon = points[i-1]
                lat, lon = points[i]
                
                distance = calculate_distance(prev_lat, prev_lon, lat, lon)
                angle = calculate_bearing(prev_lat, prev_lon, lat, lon)
                
                segment_distances.append(distance)
                track_angles.append(angle)
            
            # Hesaplanan değerleri rotaya ekle
            new_route['segment_distances'] = segment_distances
            new_route['track_angles'] = track_angles
            
            return True, f"{route_type} tipi {len(points)} noktalı rota yüklendi", new_route
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"CSV rotası yüklenirken hata oluştu: {str(e)}", None