#!/usr/bin/env python3
# remove_grid_feature.py - Grid özelliğini ve bağlantılarını kaldırmak için script

import os
import re

PROJECT_PATH = '/Users/ibrahimkucukkaya/Desktop/PROJELER/route_draw/v.calisma'

def update_snap_manager_py():
    """snap_manager.py dosyasından grid'le ilgili kodları kaldır"""
    filepath = os.path.join(PROJECT_PATH, 'snap_manager.py')
    
    with open(filepath, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # SNAP_GRID sabitini kaldır ve SNAP_ALL değerini güncelle
    content = re.sub(r'SNAP_GRID = 8\n', '', content)
    content = re.sub(r'SNAP_ALL = 31.*# Tüm modlar aktif \(31 = 1\+2\+4\+8\+16\)', 
                    'SNAP_ALL = 23  # Tüm modlar aktif (23 = 1+2+4+16)', content)
    
    # Grid aralığı değişkenini kaldır
    content = re.sub(r'self\.snap_grid_spacing = 5\.0.*# NM cinsinden ızgara aralığı\n', '', content)
    
    # Grid aralığını ayarlama metodunu kaldır
    content = re.sub(r'def set_snap_grid_spacing\(self, spacing\):.*?# 0\.1-50 NM aralığında sınırla\n', '', 
                    content, flags=re.DOTALL)
    
    # Grid snap bulma kısmını kaldır
    content = re.sub(r'# Izgara için snap noktaları bul.*?self\._find_grid_snap_points\(mouse_pos\)\n', '', 
                    content, flags=re.DOTALL)
    
    # _find_grid_snap_points metodunu tamamen kaldır
    content = re.sub(r'def _find_grid_snap_points\(self, mouse_pos\):.*?self\.snap_points\.append\(SnapPoint\(grid_screen, \(lat_grid, lon_grid\), desc, "grid"\)\)\n', 
                    '', content, flags=re.DOTALL)
    
    with open(filepath, 'w', encoding='utf-8') as file:
        file.write(content)
    
    print(f"✅ {filepath} güncellendi")

def update_left_sidebar_py():
    """left_sidebar.py dosyasından grid ile ilgili elemanları kaldır"""
    filepath = os.path.join(PROJECT_PATH, 'left_sidebar.py')
    
    with open(filepath, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Grid snap checkbox'ını kaldır
    content = re.sub(r'# Izgaraya snap.*?snap_modes_layout.addWidget\(self\.cb_snap_grid\)\n', '', 
                     content, flags=re.DOTALL)
    
    # Grid spacing alanını kaldır
    content = re.sub(r'# Izgara aralığı ayarı.*?snap_layout\.addLayout\(snap_grid_layout\)\n', '', 
                     content, flags=re.DOTALL)
    
    # Grid spacing sinyalini kaldır
    content = re.sub(r'snapGridSpacingChanged = pyqtSignal\(float\)', '', content)
    
    # Grid spacing changed metodunu kaldır
    content = re.sub(r'def on_snap_grid_spacing_changed\(self, value\):.*?self\.snapGridSpacingChanged\.emit\(value\)', 
                     '', content, flags=re.DOTALL)
    
    # mode_value hesaplamasında grid bitleri kaldır
    content = re.sub(r'if self\.cb_snap_grid\.isChecked\(\):\n.*?mode_value \|= 8.*# SNAP_GRID = 8\n', 
                     '', content, flags=re.DOTALL)
                    
    # all_checked ve none_checked kontrollerinde grid referanslarını kaldır
    content = content.replace('self.cb_snap_grid.isChecked(),', '')
    
    # set_snap_mode_checkboxes metodunda grid değişkenlerini ve referanslarını kaldır
    content = re.sub(r'grid_checked = bool\(mode & 8\).*# SNAP_GRID = 8\n', '', content)
    content = content.replace('self.cb_snap_grid.setChecked(grid_checked)', '')
    content = content.replace('grid_checked,', '')
    
    # cb_snap_all.blockSignals fonksiyonlarında grid referanslarını kaldır
    content = content.replace('self.cb_snap_grid.blockSignals(True)', '')
    content = content.replace('self.cb_snap_grid.blockSignals(False)', '')
    content = content.replace('self.cb_snap_grid.setChecked(checked)', '')
    
    with open(filepath, 'w', encoding='utf-8') as file:
        file.write(content)
    
    print(f"✅ {filepath} güncellendi")

def update_airspace_visualizer_py():
    """airspace_visualizer.py dosyasından grid ilgili metodları kaldır"""
    filepath = os.path.join(PROJECT_PATH, 'airspace_visualizer.py')
    
    with open(filepath, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Sinyal bağlantısını kaldır
    content = content.replace('self.left_sidebar.snapGridSpacingChanged.connect(self.on_snap_grid_spacing_changed)', '')
    
    # on_snap_grid_spacing_changed metodunu kaldır
    content = re.sub(r'def on_snap_grid_spacing_changed\(self, value\):.*?self\.map_widget\.update_status_message\(f"Snap ızgara aralığı: \{value\} NM"\)', 
                     '', content, flags=re.DOTALL)
    
    # Grid referanslarını içeren mode_names dizisini güncelle
    content = re.sub(r'8: "Grid",', '', content)
    
    with open(filepath, 'w', encoding='utf-8') as file:
        file.write(content)
    
    print(f"✅ {filepath} güncellendi")

def main():
    print("Grid özelliğinin kaldırılması başlatılıyor...\n")
    
    update_snap_manager_py()
    update_left_sidebar_py()
    update_airspace_visualizer_py()
    
    print("\nTüm dosyalardaki grid özellikleri ve bağlantıları kaldırıldı.")

if __name__ == "__main__":
    main()
