#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import xml.etree.ElementTree as ET
import re

def extract_waypoints_from_star_sid(file_path):
    """STAR_SID.xml dosyasından waypoint isimlerini çıkarır"""
    waypoints = set()
    
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Tüm Waypoint elementlerini bul
        for waypoint in root.findall(".//Waypoint"):
            name = waypoint.get("Name")
            if name:
                waypoints.add(name)
    
    except Exception as e:
        print(f"STAR_SID.xml dosyası okuma hatası: {e}")
    
    return waypoints

def extract_waypoints_from_waypoints_xml(file_path):
    """waypoints.xml dosyasından waypoint isimlerini çıkarır"""
    waypoints = set()
    
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Tüm Point elementlerini bul
        for point in root.findall(".//Point"):
            name = point.get("Name")
            if name:
                waypoints.add(name)
    
    except Exception as e:
        print(f"waypoints.xml dosyası okuma hatası: {e}")
    
    return waypoints

def get_waypoint_coordinates(file_path, waypoint_name):
    """Belirli bir waypoint'in koordinatlarını waypoints.xml'den alır"""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        for point in root.findall(".//Point"):
            name = point.get("Name")
            if name == waypoint_name:
                lat_elem = point.find("Latitude")
                lon_elem = point.find("Longitude")
                
                if lat_elem is not None and lon_elem is not None:
                    return {
                        'latitude': lat_elem.text.strip(),
                        'longitude': lon_elem.text.strip()
                    }
    except Exception as e:
        print(f"Koordinat okuma hatası: {e}")
    
    return None

def main():
    star_sid_file = "/Users/ibrahimkucukkaya/Desktop/PROJELER/route_draw/v.calisma/data/Airspace_01.01.2025/STAR_SID.xml"
    waypoints_file = "/Users/ibrahimkucukkaya/Desktop/PROJELER/route_draw/v.calisma/data/Airspace_01.01.2025/waypoints.xml"
    
    print("Dosyalar analiz ediliyor...")
    
    # Her iki dosyadan waypoint isimlerini çıkar
    star_sid_waypoints = extract_waypoints_from_star_sid(star_sid_file)
    waypoints_xml_waypoints = extract_waypoints_from_waypoints_xml(waypoints_file)
    
    print(f"STAR_SID.xml'de toplam {len(star_sid_waypoints)} waypoint bulundu")
    print(f"waypoints.xml'de toplam {len(waypoints_xml_waypoints)} waypoint bulundu")
    
    # STAR_SID.xml'de olup waypoints.xml'de olmayan waypoint'leri bul
    missing_waypoints = star_sid_waypoints - waypoints_xml_waypoints
    
    print(f"\nSTAR_SID.xml'de olup waypoints.xml'de olmayan {len(missing_waypoints)} waypoint:")
    print("=" * 60)
    
    if missing_waypoints:
        for waypoint in sorted(missing_waypoints):
            print(f"- {waypoint}")
    else:
        print("Tüm waypoint'ler her iki dosyada da mevcut.")
    
    # Ek olarak: Her iki dosyada da olan waypoint'leri göster
    common_waypoints = star_sid_waypoints & waypoints_xml_waypoints
    print(f"\nHer iki dosyada da mevcut olan {len(common_waypoints)} waypoint:")
    print("=" * 60)
    
    for waypoint in sorted(list(common_waypoints)[:10]):  # İlk 10'unu göster
        coords = get_waypoint_coordinates(waypoints_file, waypoint)
        if coords:
            print(f"- {waypoint}: {coords['latitude']}, {coords['longitude']}")
    
    if len(common_waypoints) > 10:
        print(f"... ve {len(common_waypoints) - 10} tane daha")

if __name__ == "__main__":
    main()
