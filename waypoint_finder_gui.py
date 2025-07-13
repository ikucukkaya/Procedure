#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import xml.etree.ElementTree as ET
import os
import re
import threading
from pathlib import Path

try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    try:
        import fitz  # PyMuPDF
        PDF_AVAILABLE = True
    except ImportError:
        PDF_AVAILABLE = False

class WaypointFinderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Waypoint Koordinat Bulucu")
        self.root.geometry("800x600")
        
        # Ana frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Dosya seçim bölümü
        file_frame = ttk.LabelFrame(main_frame, text="Dosya Seçimleri", padding="5")
        file_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # STAR_SID.xml seçimi
        ttk.Label(file_frame, text="STAR_SID.xml dosyası:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.star_sid_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.star_sid_var, width=60).grid(row=0, column=1, padx=(5, 5))
        ttk.Button(file_frame, text="Seç", command=self.select_star_sid_file).grid(row=0, column=2)
        
        # waypoints.xml seçimi
        ttk.Label(file_frame, text="waypoints.xml dosyası:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.waypoints_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.waypoints_var, width=60).grid(row=1, column=1, padx=(5, 5))
        ttk.Button(file_frame, text="Seç", command=self.select_waypoints_file).grid(row=1, column=2)
        
        # PDF klasörü seçimi
        ttk.Label(file_frame, text="PDF klasörü:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.pdf_folder_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.pdf_folder_var, width=60).grid(row=2, column=1, padx=(5, 5))
        ttk.Button(file_frame, text="Seç", command=self.select_pdf_folder).grid(row=2, column=2)
        
        # Butonlar
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="Eksik Waypoint'leri Bul", command=self.find_missing_waypoints).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="PDF'lerde Ara", command=self.search_in_pdfs).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="Test PDF Parse", command=self.test_pdf_parsing).grid(row=0, column=2, padx=5)
        
        # İkinci satır butonlar
        button_frame2 = ttk.Frame(main_frame)
        button_frame2.grid(row=2, column=0, columnspan=2, pady=5)
        
        ttk.Button(button_frame2, text="Waypoints.xml'e Ekle", command=self.add_to_waypoints_xml).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame2, text="Sonuçları Temizle", command=self.clear_results).grid(row=0, column=1, padx=5)
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Sonuçlar
        results_frame = ttk.LabelFrame(main_frame, text="Sonuçlar", padding="5")
        results_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # Text widget with scrollbar
        self.results_text = scrolledtext.ScrolledText(results_frame, width=80, height=25, wrap=tk.WORD)
        self.results_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Grid weights
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        file_frame.columnconfigure(1, weight=1)
        
        # Değişkenler
        self.missing_waypoints = set()
        self.found_coordinates = {}
        
        # PDF kütüphanesi kontrolü
        if not PDF_AVAILABLE:
            self.show_pdf_warning()
    
    def show_pdf_warning(self):
        """PDF kütüphanesi uyarısı göster"""
        warning = """
PDF okuma kütüphanesi bulunamadı!

PDF dosyalarını okuyabilmek için aşağıdaki komutlardan birini çalıştırın:

pip install PyPDF2
veya
pip install PyMuPDF

Bu kütüphaneler kurulmadan PDF arama özelliği çalışmaz.
        """
        messagebox.showwarning("Kütüphane Eksik", warning)
    
    def select_star_sid_file(self):
        """STAR_SID.xml dosyası seç"""
        filename = filedialog.askopenfilename(
            title="STAR_SID.xml dosyasını seçin",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )
        if filename:
            self.star_sid_var.set(filename)
    
    def select_waypoints_file(self):
        """waypoints.xml dosyası seç"""
        filename = filedialog.askopenfilename(
            title="waypoints.xml dosyasını seçin",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )
        if filename:
            self.waypoints_var.set(filename)
    
    def select_pdf_folder(self):
        """PDF klasörü seç"""
        folder = filedialog.askdirectory(title="PDF dosyalarının bulunduğu klasörü seçin")
        if folder:
            self.pdf_folder_var.set(folder)
    
    def extract_waypoints_from_star_sid(self, file_path):
        """STAR_SID.xml'den waypoint'leri çıkar"""
        waypoints = set()
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            for waypoint in root.findall(".//Waypoint"):
                name = waypoint.get("Name")
                if name:
                    waypoints.add(name)
        except Exception as e:
            self.log_message(f"STAR_SID.xml okuma hatası: {e}")
        
        return waypoints
    
    def extract_waypoints_from_waypoints_xml(self, file_path):
        """waypoints.xml'den waypoint'leri çıkar"""
        waypoints = set()
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            for point in root.findall(".//Point"):
                name = point.get("Name")
                if name:
                    waypoints.add(name)
        except Exception as e:
            self.log_message(f"waypoints.xml okuma hatası: {e}")
        
        return waypoints
    
    def find_missing_waypoints(self):
        """Eksik waypoint'leri bul"""
        if not self.star_sid_var.get() or not self.waypoints_var.get():
            messagebox.showerror("Hata", "Lütfen her iki XML dosyasını da seçin!")
            return
        
        self.log_message("Eksik waypoint'ler aranıyor...\n")
        
        try:
            star_sid_waypoints = self.extract_waypoints_from_star_sid(self.star_sid_var.get())
            waypoints_xml_waypoints = self.extract_waypoints_from_waypoints_xml(self.waypoints_var.get())
            
            self.missing_waypoints = star_sid_waypoints - waypoints_xml_waypoints
            
            self.log_message(f"STAR_SID.xml'de {len(star_sid_waypoints)} waypoint bulundu")
            self.log_message(f"waypoints.xml'de {len(waypoints_xml_waypoints)} waypoint bulundu")
            self.log_message(f"Eksik waypoint sayısı: {len(self.missing_waypoints)}\n")
            
            if self.missing_waypoints:
                self.log_message("Eksik waypoint'ler:")
                self.log_message("-" * 30)
                for waypoint in sorted(self.missing_waypoints):
                    self.log_message(f"• {waypoint}")
                self.log_message("\n")
            else:
                self.log_message("Tüm waypoint'ler mevcut!")
                
        except Exception as e:
            messagebox.showerror("Hata", f"Analiz sırasında hata: {e}")
    
    def search_in_pdfs(self):
        """PDF'lerde eksik waypoint'leri ara"""
        if not self.missing_waypoints:
            messagebox.showwarning("Uyarı", "Önce eksik waypoint'leri bulun!")
            return
        
        if not self.pdf_folder_var.get():
            messagebox.showerror("Hata", "PDF klasörünü seçin!")
            return
        
        if not PDF_AVAILABLE:
            messagebox.showerror("Hata", "PDF okuma kütüphanesi yüklü değil!")
            return
        
        # Threading ile arama yap
        thread = threading.Thread(target=self._search_pdfs_thread)
        thread.daemon = True
        thread.start()
    
    def _search_pdfs_thread(self):
        """PDF arama thread fonksiyonu"""
        try:
            self.root.after(0, lambda: self.progress.start())
            self.root.after(0, lambda: self.log_message("PDF dosyalarında arama başlıyor...\n"))
            
            pdf_folder = Path(self.pdf_folder_var.get())
            pdf_files = list(pdf_folder.glob("**/*.pdf"))
            
            self.root.after(0, lambda: self.log_message(f"{len(pdf_files)} PDF dosyası bulundu\n"))
            
            found_count = 0
            
            for pdf_file in pdf_files:
                self.root.after(0, lambda f=pdf_file: self.log_message(f"Aranıyor: {f.name}"))
                
                try:
                    coordinates = self.search_waypoints_in_pdf(pdf_file)
                    if coordinates:
                        found_count += len(coordinates)
                        self.found_coordinates.update(coordinates)
                        
                        for waypoint, coords in coordinates.items():
                            self.root.after(0, lambda w=waypoint, c=coords, f=pdf_file: 
                                          self.log_message(f"  ✓ {w}: {c} ({f.name})"))
                except Exception as e:
                    self.root.after(0, lambda e=e, f=pdf_file: 
                                  self.log_message(f"  ✗ Hata: {e} ({f.name})"))
            
            self.root.after(0, lambda: self.progress.stop())
            self.root.after(0, lambda: self.log_message(f"\nArama tamamlandı. {found_count} koordinat bulundu."))
            
            if self.found_coordinates:
                self.root.after(0, self.show_found_coordinates)
            
        except Exception as e:
            self.root.after(0, lambda: self.progress.stop())
            self.root.after(0, lambda: messagebox.showerror("Hata", f"PDF arama hatası: {e}"))
    
    def search_waypoints_in_pdf(self, pdf_path):
        """Tek PDF dosyasında waypoint'leri ara"""
        found_coordinates = {}
        
        try:
            # PyMuPDF kullanmayı dene
            if 'fitz' in globals():
                doc = fitz.open(str(pdf_path))
                text = ""
                for page in doc:
                    text += page.get_text()
                doc.close()
            else:
                # PyPDF2 kullan
                with open(pdf_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text()
            
            # Önce tablo formatını dene
            table_coords = self.parse_table_format(text)
            for waypoint in self.missing_waypoints:
                if waypoint in table_coords:
                    found_coordinates[waypoint] = table_coords[waypoint]
            
            # Sonra diğer formatları ara
            for waypoint in self.missing_waypoints:
                if waypoint not in found_coordinates:
                    coords = self.find_coordinates_in_text(text, waypoint)
                    if coords:
                        found_coordinates[waypoint] = coords
                    
        except Exception as e:
            self.log_message(f"PDF okuma hatası: {e}")
        
        return found_coordinates
    
    def parse_table_format(self, text):
        """Tablo formatındaki koordinatları parse et"""
        coordinates = {}
        
        # Satırları böl
        lines = text.split('\n')
        
        for line in lines:
            # Tablo satırı formatını ara: FlyBy WAYPOINT LAT LON
            match = re.search(r'FlyBy\s+(\w+)\s+(\d{2,3}:\d{2}:\d{2}\.\d{2}[NS])\s+(\d{3}:\d{2}:\d{2}\.\d{2}[EW])', line)
            if match:
                waypoint, lat, lon = match.groups()
                coordinates[waypoint] = f"{lat}, {lon}"
                
        return coordinates
    
    def find_coordinates_in_text(self, text, waypoint):
        """Metinde waypoint koordinatlarını ara"""
        # Farklı koordinat formatları için regex pattern'ler
        patterns = [
            # PDF'deki format: 41:02:23.66N 026:53:50.73E
            rf"{re.escape(waypoint)}\s+(\d{{2,3}}:\d{{2}}:\d{{2}}\.\d{{2}}[NS])\s+(\d{{3}}:\d{{2}}:\d{{2}}\.\d{{2}}[EW])",
            
            # Tablo formatında: waypoint name'den sonra latitude ve longitude kolonları
            rf"{re.escape(waypoint)}\s+(\d{{2,3}}:\d{{2}}:\d{{2}}\.\d{{2}}[NS])\s+(\d{{3}}:\d{{2}}:\d{{2}}\.\d{{2}}[EW])",
            
            # 41 02 04.00 N, 26 36 40.00 E formatı
            rf"{re.escape(waypoint)}\s*[:\-]?\s*(\d{{1,2}}\s+\d{{1,2}}\s+\d{{1,2}}\.?\d*\s*[NS])\s*[,\s]+(\d{{1,3}}\s+\d{{1,2}}\s+\d{{1,2}}\.?\d*\s*[EW])",
            
            # 41°02'04"N 26°36'40"E formatı
            rf"{re.escape(waypoint)}\s*[:\-]?\s*(\d{{1,2}}°\d{{1,2}}'\d{{1,2}}\"?[NS])\s*[,\s]*(\d{{1,3}}°\d{{1,2}}'\d{{1,2}}\"?[EW])",
            
            # 41.0344 N, 26.6111 E formatı (decimal degrees)
            rf"{re.escape(waypoint)}\s*[:\-]?\s*(\d{{1,2}}\.\d+\s*[NS])\s*[,\s]*(\d{{1,3}}\.\d+\s*[EW])",
            
            # Reverse order: koordinat waypoint formatı
            rf"(\d{{1,2}}\s+\d{{1,2}}\s+\d{{1,2}}\.?\d*\s*[NS])\s*[,\s]+(\d{{1,3}}\s+\d{{1,2}}\s+\d{{1,2}}\.?\d*\s*[EW])\s*[:\-]?\s*{re.escape(waypoint)}",
            
            # Tablo satırı formatı: FlyBy WAYPOINT 41:02:23.66N 026:53:50.73E
            rf"FlyBy\s+{re.escape(waypoint)}\s+(\d{{2,3}}:\d{{2}}:\d{{2}}\.\d{{2}}[NS])\s+(\d{{3}}:\d{{2}}:\d{{2}}\.\d{{2}}[EW])",
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                lat, lon = match.groups()
                return f"{lat.strip()}, {lon.strip()}"
        
        return None
    
    def show_found_coordinates(self):
        """Bulunan koordinatları göster"""
        self.log_message("\n" + "="*50)
        self.log_message("BULUNAN KOORDİNATLAR:")
        self.log_message("="*50)
        
        for waypoint in sorted(self.found_coordinates.keys()):
            coords = self.found_coordinates[waypoint]
            self.log_message(f"{waypoint}: {coords}")
        
        # Hala eksik olanları göster
        still_missing = self.missing_waypoints - set(self.found_coordinates.keys())
        if still_missing:
            self.log_message(f"\nHala bulunamayan {len(still_missing)} waypoint:")
            self.log_message("-" * 30)
            for waypoint in sorted(still_missing):
                self.log_message(f"• {waypoint}")
    
    def log_message(self, message):
        """Sonuç alanına mesaj ekle"""
        self.results_text.insert(tk.END, message + "\n")
        self.results_text.see(tk.END)
        self.root.update_idletasks()
    
    def clear_results(self):
        """Sonuçları temizle"""
        self.results_text.delete(1.0, tk.END)
        self.missing_waypoints.clear()
        self.found_coordinates.clear()
    
    def test_pdf_parsing(self):
        """PDF parsing'i test et"""
        if not self.missing_waypoints:
            messagebox.showwarning("Uyarı", "Önce eksik waypoint'leri bulun!")
            return
            
        # Örnek PDF metni
        sample_text = """
AD 2 LTFM STAR-3A                                                AIP
17 APR 25                                                     TÜRKİYE

                    ISTANBUL AIRPORT RNAV (GNSS) STAR RWY 16R/17L/18

Type    Fix identifier    Latitude        Longitude        Type    Fix identifier    Latitude        Longitude
        (Waypoint                                                  (Waypoint
        name)                                                      name)

FlyBy   AGBET           41:02:23.66N    026:53:50.73E     FlyBy   FM407           41:35:49.29N    029:06:17.85E
FlyBy   DRAMO           41:02:04.00N    026:36:40.00E     FlyBy   FM751           41:03:28.55N    027:06:59.43E
FlyBy   ENLEC           41:28:29.32N    029:05:27.20E     FlyBy   FM752           41:10:32.56N    027:14:26.61E
FlyBy   ENRAW           41:08:57.15N    028:22:54.60E     FlyBy   FM753           41:17:36.08N    027:21:55.41E
FlyBy   FM375           41:08:51.65N    028:16:17.46E     FlyBy   FM754           41:12:31.45N    027:30:18.44E
FlyBy   FM395           41:09:11.36N    028:42:45.89E     FlyBy   FM755           41:07:26.21N    027:38:40.18E
FlyBy   FM400           41:10:41.52N    029:10:33.84E     FlyBy   FM756           41:05:37.10N    027:47:36.96E
FlyBy   FM401           41:18:20.48N    029:14:28.11E     FlyBy   FM757           41:05:31.98N    027:55:33.20E
FlyBy   FM402           41:22:16.85N    029:19:31.91E     FlyBy   FM758           41:07:06.22N    028:05:56.02E
FlyBy   FM403           41:27:04.29N    029:23:04.73E     FlyBy   GUBUL           40:44:18.84N    027:18:46.36E
FlyBy   FM404           41:32:23.34N    029:24:51.88E     FlyBy   INBET           40:11:11.00N    027:16:30.00E
FlyBy   FM405           41:37:52.36N    029:24:45.60E     FlyBy   LEKMI           40:28:37.07N    027:17:41.56E
FlyBy   FM406           41:36:51.20N    029:15:31.60E     FlyBy   GAZGE           41:34:46.63N    028:57:04.36E
FlyBy   KANQO           41:25:44.00N    030:43:29.00E     FlyBy   NEWPE           41:17:56.00N    029:59:58.00E
FlyBy   ULQAL           40:54:41.43N    029:00:34.36E     FlyBy   FM100           41:04:04.35N    028:17:31.43E
FlyBy   FM101           41:09:36.01N    028:11:49.95E     FlyBy   FM120           40:51:57.78N    029:38:38.02E
FlyBy   FM122           40:53:02.85N    029:28:10.77E     FlyBy   FM123           40:58:31.52N    029:27:49.08E
FlyBy   FM124           41:03:44.71N    029:25:35.70E     FlyBy   FM125           41:08:21.00N    029:21:39.35E
FlyBy   FM127           41:12:01.38N    029:16:15.91E     FlyBy   FM440           41:19:21.61N    029:03:11.33E
FlyBy   FM441           41:21:32.09N    029:17:46.43E     FlyBy   FM442           41:26:22.44N    029:22:29.45E
FlyBy   FM443           41:30:19.38N    029:36:08.84E     FlyBy   FM444           41:38:35.75N    029:40:58.68E
        """
        
        self.log_message("PDF parsing testi başlıyor...\n")
        
        # Test tablo parsing
        coordinates = self.parse_table_format(sample_text)
        found_count = 0
        
        self.log_message("Test sonuçları:")
        self.log_message("-" * 30)
        
        for waypoint in sorted(self.missing_waypoints):
            if waypoint in coordinates:
                found_count += 1
                self.log_message(f"✓ {waypoint}: {coordinates[waypoint]}")
        
        self.log_message(f"\nTest başarılı! {found_count} koordinat bulundu.")
        self.log_message("Şimdi gerçek PDF dosyalarında arama yapabilirsiniz.\n")
    
    def convert_coordinate_format(self, coord_string):
        """PDF formatındaki koordinatı waypoints.xml formatına dönüştür"""
        # 41:02:23.66N, 026:53:50.73E -> 41 02 23.66 N, 26 53 50.73 E
        try:
            # Koordinatları ayır
            parts = coord_string.split(', ')
            if len(parts) != 2:
                return None
            
            lat_part = parts[0].strip()
            lon_part = parts[1].strip()
            
            # Latitude dönüştür: 41:02:23.66N -> 41 02 23.66 N
            lat_match = re.match(r'(\d{2,3}):(\d{2}):(\d{2}\.\d{2})([NS])', lat_part)
            if lat_match:
                lat_deg, lat_min, lat_sec, lat_dir = lat_match.groups()
                formatted_lat = f"{int(lat_deg):02d} {lat_min} {lat_sec} {lat_dir}"
            else:
                return None
            
            # Longitude dönüştür: 026:53:50.73E -> 26 53 50.73 E
            lon_match = re.match(r'(\d{3}):(\d{2}):(\d{2}\.\d{2})([EW])', lon_part)
            if lon_match:
                lon_deg, lon_min, lon_sec, lon_dir = lon_match.groups()
                formatted_lon = f"{int(lon_deg):02d} {lon_min} {lon_sec} {lon_dir}"
            else:
                return None
            
            return formatted_lat, formatted_lon
            
        except Exception as e:
            self.log_message(f"Koordinat dönüştürme hatası: {e}")
            return None
    
    def add_to_waypoints_xml(self):
        """Bulunan koordinatları waypoints.xml dosyasına ekle"""
        if not self.found_coordinates:
            messagebox.showwarning("Uyarı", "Eklenecek koordinat bulunamadı! Önce PDF'lerde arama yapın.")
            return
        
        if not self.waypoints_var.get():
            messagebox.showerror("Hata", "waypoints.xml dosyası seçilmemiş!")
            return
        
        # Kullanıcıdan onay al
        result = messagebox.askyesno(
            "Onay", 
            f"{len(self.found_coordinates)} koordinat waypoints.xml dosyasına eklenecek.\n\n"
            "Bu işlem geri alınamaz. Devam etmek istiyor musunuz?"
        )
        
        if not result:
            return
        
        try:
            self.log_message("waypoints.xml dosyasına koordinatlar ekleniyor...\n")
            
            # XML dosyasını yükle
            tree = ET.parse(self.waypoints_var.get())
            root = tree.getroot()
            
            added_count = 0
            skipped_count = 0
            
            for waypoint_name, coord_string in self.found_coordinates.items():
                # Koordinatı dönüştür
                converted_coords = self.convert_coordinate_format(coord_string)
                if not converted_coords:
                    self.log_message(f"✗ {waypoint_name}: Koordinat dönüştürme hatası")
                    skipped_count += 1
                    continue
                
                formatted_lat, formatted_lon = converted_coords
                
                # Waypoint zaten var mı kontrol et
                existing = False
                for point in root.findall(".//Point"):
                    if point.get("Name") == waypoint_name:
                        existing = True
                        break
                
                if existing:
                    self.log_message(f"⚠ {waypoint_name}: Zaten mevcut, atlandı")
                    skipped_count += 1
                    continue
                
                # Yeni Point elementi oluştur
                new_point = ET.Element("Point", Name=waypoint_name, Type="Fix")
                
                # Latitude ve Longitude elementleri ekle
                lat_elem = ET.SubElement(new_point, "Latitude")
                lat_elem.text = formatted_lat
                
                lon_elem = ET.SubElement(new_point, "Longitude")
                lon_elem.text = formatted_lon
                
                # Root'a ekle
                root.append(new_point)
                
                self.log_message(f"✓ {waypoint_name}: {formatted_lat}, {formatted_lon}")
                added_count += 1
            
            # Dosyayı kaydet (düzgün formatlama ile)
            self.save_xml_with_formatting(tree, self.waypoints_var.get())
            
            self.log_message(f"\nİşlem tamamlandı!")
            self.log_message(f"Eklenen: {added_count}")
            self.log_message(f"Atlanan: {skipped_count}")
            
            messagebox.showinfo(
                "Başarılı", 
                f"İşlem tamamlandı!\n\n"
                f"Eklenen koordinat: {added_count}\n"
                f"Atlanan koordinat: {skipped_count}"
            )
            
        except Exception as e:
            error_msg = f"waypoints.xml güncelleme hatası: {e}"
            self.log_message(f"✗ {error_msg}")
            messagebox.showerror("Hata", error_msg)
    
    def save_xml_with_formatting(self, tree, filename):
        """XML dosyasını düzgün formatlama ile kaydet"""
        try:
            # Önce backup oluştur
            import shutil
            backup_file = filename + ".backup"
            shutil.copy2(filename, backup_file)
            self.log_message(f"Backup oluşturuldu: {backup_file}")
            
            # XML'i string olarak al
            root = tree.getroot()
            xml_string = ET.tostring(root, encoding='unicode')
            
            # Yeni Point elementlerini düzgün formatla
            formatted_xml = self.format_xml_string(xml_string)
            
            # Dosyaya yaz
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('<?xml version=\'1.0\' encoding=\'utf-8\'?>\n')
                f.write(formatted_xml)
                
        except Exception as e:
            raise Exception(f"XML kaydetme hatası: {e}")
    
    def format_xml_string(self, xml_string):
        """XML string'ini waypoints.xml formatına uygun hale getir"""
        # Yeni eklenen Point elementlerini düzgün formatla
        # Mevcut format: <Point Name="..." Type="Fix"><Latitude>...</Latitude><Longitude>...</Longitude></Point>
        # İstenen format: <Point Name="..." Type="Fix">\n    <Latitude>...</Latitude>\n    <Longitude>...</Longitude>\n  </Point>
        
        formatted = xml_string.replace('><Latitude>', '>\n    <Latitude>')
        formatted = formatted.replace('</Latitude><Longitude>', '</Latitude>\n    <Longitude>')
        formatted = formatted.replace('</Longitude></Point>', '</Longitude>\n  </Point>')
        
        return formatted

def main():
    root = tk.Tk()
    app = WaypointFinderGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
