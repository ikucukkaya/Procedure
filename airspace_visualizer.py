import sys
import os
import json
import csv
import webbrowser
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                          QToolBar, QAction, QSplitter, QMenuBar, QMenu, QDialog, QMessageBox, QLabel, 
                          QInputDialog, QFileDialog)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from map_widget import MapWidget
from left_sidebar import LeftSidebar
from path_extension import PathExtensionDialog
from models import DataManager
from runway_options_dialog import RunwayOptionsDialog
from startup_options_dialog import StartupOptionsDialog
from gradient_calculator_dialog import GradientCalculatorDialog

class AirspaceVisualizer(QMainWindow):
    """Main application window for Airspace Procedure Visualizer"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Airspace Procedure Visualizer")
        
        # Kullanıcının ekran boyutuna göre pencere boyutlandırma
        # Mevcut ekran boyutunun %80'i kadar bir alan kullanalım
        screen_geometry = self.screen().availableGeometry()
        window_width = int(screen_geometry.width() * 0.8)
        window_height = int(screen_geometry.height() * 0.8)
        self.resize(window_width, window_height)
        
        # Ekran merkezinde konumlandır
        self.center_on_screen()
        
        # Initialize data manager
        self.data_manager = DataManager()
        
        # --- Initialize Core UI Components Early --- 
        self.statusBar().showMessage("Loading...")
        self.coord_label = QLabel("00:00:00N 00:00:00E")
        self.coord_label.setStyleSheet("""
            font-family: monospace; 
            font-weight: bold;
            padding: 2px 5px;
            background-color: #ffffff;
            border: 1px solid #cccccc;
            border-radius: 2px;
        """)
        
        # Add coordinate display to the right side of status bar
        self.statusBar().addPermanentWidget(self.coord_label)
        
        # Set application-wide style
        self.setStyleSheet("""
            QMainWindow, QWidget, QToolBar, QMenuBar, QMenu, QStatusBar {
                background-color: #ffffff;
            }
            QMenuBar {
                border-bottom: 1px solid #cccccc;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 4px 10px;
            }
            QMenuBar::item:selected {
                background-color: #f5f5f5;
            }
            QMenuBar::item:pressed {
                background-color: #f0f0f0;
            }
            QMenu {
                border: 1px solid #cccccc;
            }
            QMenu::item {
                padding: 4px 20px;
            }
            QMenu::item:selected {
                background-color: #f5f5f5;
            }
            QToolBar {
                border-bottom: 1px solid #cccccc;
            }
            QStatusBar {
                border-top: 1px solid #cccccc;
            }
        """)
        
        # Create menu bar
        self.menubar = self.menuBar()
        
        # Create main widget with splitter
        self.main_widget = QWidget()
        self.main_layout = QHBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Create splitter for three panels
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #cccccc;
                width: 1px;
            }
            QSplitter::handle:hover {
                background-color: #999999;
            }
        """)
        
        # Create left sidebar container with adjustable width based on screen size
        self.left_sidebar_container = QWidget()
        screen_width = self.screen().availableGeometry().width()
        self.left_sidebar_container.setMinimumWidth(int(screen_width * 0.1))  # Ekran genişliğinin %10'u
        self.left_sidebar_container.setMaximumWidth(int(screen_width * 0.25)) # Ekran genişliğinin %25'i
        self.left_sidebar_container_layout = QHBoxLayout(self.left_sidebar_container)
        self.left_sidebar_container_layout.setContentsMargins(0, 0, 0, 0)
        self.left_sidebar_container_layout.setSpacing(0)
        
        # Create left sidebar
        self.left_sidebar = LeftSidebar()
        
        # Add left sidebar to container
        self.left_sidebar_container_layout.addWidget(self.left_sidebar)
        
        # Sol kenar çubuğunun post init işlemlerini çağır
        # (Waypoint görünürlüğü ile snap ayarlarını senkronize etmek için)
        
        # Create Map Widget BEFORE menus/toolbars that might reference it
        self.map_widget = MapWidget()
        
        # Create Menus and Toolbar AFTER map widget exists
        self.create_menu_actions()
        self.toolbar = QToolBar()
        self.addToolBar(self.toolbar)
        self.create_toolbar_actions()

        # --- Prompt for Options, Load Data, and Populate --- 
        data_loaded_successfully = self.prompt_and_load_data()

        if data_loaded_successfully:
            self.populate_ui_with_data()
            self.statusBar().showMessage("Ready")
        else:
             self.statusBar().showMessage("Data loading failed or cancelled.")
             # Consider closing or disabling features
             # QMessageBox.critical(self, "Error", "Failed to load required data. Exiting.")
             # sys.exit(1)

        # --- Finalize Layout --- 
        self.splitter.addWidget(self.left_sidebar_container)
        self.splitter.addWidget(self.map_widget)
        
        # Configure splitter behavior
        self.splitter.setCollapsible(0, False)  # Prevent left sidebar collapse
        self.splitter.setCollapsible(1, False)  # Prevent map collapse
        self.splitter.setStretchFactor(0, 0)    # Don't stretch left sidebar
        self.splitter.setStretchFactor(1, 1)    # Allow map to stretch
        self.splitter.setHandleWidth(1)         # Set slim handle
        
        # Set initial splitter sizes with error handling
        try:
             total_width = self.width() if self.width() > 0 else screen_geometry.width() * 0.8
             sidebar_width = int(total_width * 0.15)  # Sol panel genişliği ekranın %15'i kadar olsun
             self.splitter.setSizes([sidebar_width, total_width - sidebar_width])
        except Exception as e:
            print(f"Error setting initial splitter sizes: {e}. Using fallback.")
            # Fallback değerler için ekran genişliğinin %15'i ve %85'i
            screen_width = self.screen().availableGeometry().width()
            sidebar_width = int(screen_width * 0.15)
            self.splitter.setSizes([sidebar_width, screen_width - sidebar_width])
        
        # Add splitter to main layout
        self.main_layout.addWidget(self.splitter)
        
        self.setCentralWidget(self.main_widget)
        
        # Connect signals
        self.connect_signals()
        
        # UI ayarlarını başlat
        self.initialize_ui_settings()

    def prompt_and_load_data(self):
        """Show startup dialog, load selected data, return True on success."""
        airspace_folders = self.data_manager.find_airspace_folders()
        geojson_files = self.data_manager.find_geojson_files()

        if not airspace_folders:
            QMessageBox.critical(self, "Error", f"No airspace folders found in '{self.data_manager.data_dir}'. Required to run.")
            return False
        # GeoJSON might be optional, but we need at least one option if the list isn't empty
        # if not geojson_files: 
        #     QMessageBox.warning(self, "Warning", f"No GeoJSON files found in '{self.data_manager.data_dir}'. Map background will be empty.")

        dialog = StartupOptionsDialog(airspace_folders, geojson_files, self)
        if dialog.exec_() == QDialog.Accepted:
            folder_name, geojson_name = dialog.get_selected_paths()
            
            if not folder_name:
                QMessageBox.critical(self, "Error", "No airspace folder selected. Cannot continue.")
                return False
                
            # Load Airspace Data
            airspace_folder_path = os.path.join(self.data_manager.data_dir, folder_name)
            if not self.data_manager.load_airspace_data(airspace_folder_path):
                 QMessageBox.critical(self, "Error", f"Failed to load airspace data from \n{airspace_folder_path}")
                 return False
                 
            # Load GeoJSON Data (if selected)
            if geojson_name:
                geojson_path = os.path.join(self.data_manager.data_dir, geojson_name)
                if not self.map_widget.load_and_compute_geojson(geojson_path):
                     QMessageBox.warning(self, "Map Warning", f"Could not load selected GeoJSON map background from \n{geojson_path}")
                     # Continue anyway, map will be blank
            else:
                 print("No GeoJSON file selected or found.")
                 # Ensure map is empty if no file selected/loaded
                 self.map_widget.load_and_compute_geojson(None) 

            return True # Data loaded (even if GeoJSON failed non-critically)
        else:
            print("Startup options dialog cancelled.")
            return False # User cancelled
        
    def populate_ui_with_data(self):
        """Populate UI elements after data has been successfully loaded."""
        # Populate left sidebar
        self.left_sidebar.populate_procedures(self.data_manager.procedures)
        self.left_sidebar.populate_runways(self.data_manager.runways)
        
        # Set data manager ve runways on map widget
        self.map_widget.set_data_manager(self.data_manager)
        self.map_widget.set_runways(self.data_manager.runways)
        
        # Başlangıçta tüm runway ID'lerini seçili listeye ekle
        all_runway_ids = [runway.get('id') for runway in self.data_manager.runways if runway.get('id')]
        self.map_widget.set_selected_runways(all_runway_ids)
        
        # Haritayı güncelle
        self.map_widget.update()

    def create_menu_actions(self):
        """Create menu bar and its actions"""
        # File menu
        file_menu = self.menubar.addMenu("File")
        
        # Create file actions
        self.action_open = QAction("Open", self)
        self.action_open.setShortcut("Ctrl+O")
        file_menu.addAction(self.action_open)
        
        self.action_save = QAction("Save", self)
        self.action_save.setShortcut("Ctrl+S")
        file_menu.addAction(self.action_save)
        
        # Add Import Trajectory action (moved)
        self.action_import_trajectory = QAction("Import Trajectory...", self)
        file_menu.addAction(self.action_import_trajectory)
        
        file_menu.addSeparator()
        
        # Add Reset View action
        self.action_reset_view = QAction("Reset View", self)
        self.action_reset_view.setShortcut("Ctrl+R")
        file_menu.addAction(self.action_reset_view)
        
        # Add Clear Workspace action
        self.action_clear_workspace = QAction("Clear Workspace", self)
        self.action_clear_workspace.setShortcut("Ctrl+Shift+C")
        file_menu.addAction(self.action_clear_workspace)
        
        file_menu.addSeparator()
        
        self.action_exit = QAction("Exit", self)
        self.action_exit.setShortcut("Alt+F4")
        file_menu.addAction(self.action_exit)
        
        # Tools menu
        tools_menu = self.menubar.addMenu("Tools")
        
        # Add Gradient Calculator action with shortcut
        self.action_gradient_calculator = QAction("Gradient Calculator", self)
        self.action_gradient_calculator.setShortcut("Ctrl+G")
        self.action_gradient_calculator.setToolTip("İrtifa gradyan hesaplamalarını göster (Ctrl+G)")
        tools_menu.addAction(self.action_gradient_calculator)
        
        # Connect actions
        self.action_open.triggered.connect(self.on_open)
        self.action_save.triggered.connect(self.on_save)
        self.action_reset_view.triggered.connect(self.map_widget.on_reset_view)
        self.action_clear_workspace.triggered.connect(self.clear_workspace)
        self.action_exit.triggered.connect(self.close)
        self.action_gradient_calculator.triggered.connect(self.show_gradient_calculator)

    def create_toolbar_actions(self):
        """Create toolbar buttons and actions"""
        # Left sidebar toggle
        self.action_toggle_left_sidebar = QAction("≡", self)
        self.action_toggle_left_sidebar.setToolTip("Toggle Left Sidebar")
        self.action_toggle_left_sidebar.triggered.connect(self.toggle_left_sidebar)

        # Add path extension action
        self.action_path_extension = QAction("Path Extension", self)
        
        # Toolbar için gradient calculator butonu ekle
        self.action_gradient_calc_toolbar = QAction("Gradient", self)
        self.action_gradient_calc_toolbar.setToolTip("Gradient Calculator'ı aç (Ctrl+G)")
        self.action_gradient_calc_toolbar.triggered.connect(self.show_gradient_calculator)
        self.action_path_extension.setToolTip("Draw path extension")
        self.action_path_extension.triggered.connect(self.show_path_extension_dialog)
        
        # Add route drawing action
        self.action_draw_route = QAction("Draw Route", self)
        self.action_draw_route.setToolTip("Draw custom route")
        self.action_draw_route.setCheckable(True)
        self.action_draw_route.toggled.connect(self.toggle_route_drawing)
        
        # Çoklu seçim modu için aksiyon
        self.action_multi_select = QAction("Multi-Select", self)
        self.action_multi_select.setToolTip("Enable multi-select mode for routes")
        self.action_multi_select.setCheckable(True)
        self.action_multi_select.toggled.connect(self.toggle_multi_select_mode)
        
        # Birleştirme ve silme aksiyonları
        self.action_merge_routes = QAction("Merge Routes", self)
        self.action_merge_routes.setToolTip("Merge selected routes")
        self.action_merge_routes.setEnabled(False)  # Başlangıçta devre dışı
        self.action_merge_routes.triggered.connect(self.merge_selected_routes)
        
        self.action_delete_routes = QAction("Delete Routes", self)
        self.action_delete_routes.setToolTip("Delete selected routes")
        self.action_delete_routes.setEnabled(False)  # Başlangıçta devre dışı
        self.action_delete_routes.triggered.connect(self.delete_selected_routes)
        
        # Add actions to toolbar with separators
        self.toolbar.addAction(self.action_toggle_left_sidebar)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.action_path_extension)
        self.toolbar.addAction(self.action_draw_route)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.action_multi_select)
        self.toolbar.addAction(self.action_merge_routes)
        self.toolbar.addAction(self.action_delete_routes)

    def connect_signals(self):
        """Connect signals between widgets"""
        # Map widget signals
        self.map_widget.coordinatesChanged.connect(self.update_coordinates)
        self.map_widget.pathSelected.connect(self.on_path_selected)
        self.map_widget.routeDrawingStarted.connect(self.on_route_drawing_started)
        self.map_widget.routeDrawingFinished.connect(self.on_route_drawing_finished)
        self.map_widget.routePointAdded.connect(self.on_route_point_added)
        
        # Left sidebar signals
        self.left_sidebar.procedureToggled.connect(self.on_procedure_toggled)
        self.left_sidebar.runwayToggled.connect(self.on_runway_toggled)
        self.left_sidebar.resetViewRequested.connect(self.map_widget.on_reset_view)
        self.left_sidebar.runwayDisplayOptionsRequested.connect(self.show_runway_options_dialog)
        self.left_sidebar.showWaypointsToggled.connect(self.on_show_waypoints_toggled)
        self.left_sidebar.showTmaBoundaryToggled.connect(self.on_show_tma_boundary_toggled)
        
        # Harita görünürlük kontrolleri için sinyal bağlantıları
        # SID ve STAR görünürlük kontrolleri şu an için devre dışı
        # self.left_sidebar.showSidsToggled.connect(self.on_show_sids_toggled)
        # self.left_sidebar.showStarsToggled.connect(self.on_show_stars_toggled)
        self.left_sidebar.showWaypointsToggled.connect(self.on_show_waypoints_toggled)
        self.left_sidebar.showTmaBoundaryToggled.connect(self.on_show_tma_boundary_toggled)
        self.left_sidebar.showRestrictedAreasToggled.connect(self.on_show_restricted_areas_toggled)
        self.left_sidebar.showSegmentDistancesToggled.connect(self.on_show_segment_distances_toggled)
        
        # Eski çizgi kalınlığı ve renk ayarları sinyalleri kaldırıldı (artık route popup'ta yapılıyor)
        
        # Harita renkleri için sinyal bağlantıları
        self.left_sidebar.landColorChanged.connect(self.on_land_color_changed)
        self.left_sidebar.backgroundColorChanged.connect(self.on_background_color_changed)
        self.left_sidebar.restrictedAreaColorChanged.connect(self.on_restricted_area_color_changed)
        
        # Snap ayarları için sinyal bağlantıları
        self.left_sidebar.snapEnabledToggled.connect(self.on_snap_enabled_toggled)
        self.left_sidebar.snapModeChanged.connect(self.on_snap_mode_changed)
        self.left_sidebar.snapToleranceChanged.connect(self.on_snap_tolerance_changed)
        
        # Başlangıçta snap modunu sol paneldeki checkbox durumlarına göre ayarla
        # Sadece Uç Noktalar ve Orta Noktalar seçili olsun (3 = 1 + 2)
        initial_snap_mode = 3  # Uç Noktalar (1) + Orta Noktalar (2)
        self.on_snap_mode_changed(initial_snap_mode)

        # Import action
        self.action_import_trajectory.triggered.connect(self.on_import_trajectory)
        
        # Sol kenar çubuğunun post init işlemlerini çağır
        # (Waypoint görünürlüğü ile snap ayarlarını senkronize etmek için)
        self.left_sidebar.post_init()



    def initialize_ui_settings(self):
        """UI ayarlarını başlangıç değerlerine göre ayarla"""
        # Renk butonlarını güncelle - hata kontrolü ile
        try:
            if hasattr(self.left_sidebar, 'update_land_color_button'):
                self.left_sidebar.update_land_color_button(self.map_widget.land_color)
            if hasattr(self.left_sidebar, 'update_background_color_button'):
                self.left_sidebar.update_background_color_button(self.map_widget.background_color)
            if hasattr(self.left_sidebar, 'update_restricted_area_color_button'):
                self.left_sidebar.update_restricted_area_color_button(self.map_widget.restricted_area_border_color)
        except AttributeError as e:
            print(f"Warning: Could not initialize color buttons: {e}")
            # Devam et, bu kritik değil

    def on_procedure_toggled(self, checked, proc_type, airport, runway, procedure):
        """Handle procedure toggle"""
        if checked:
            waypoints = self.data_manager.procedures[proc_type][airport][runway][procedure]
            if waypoints:
                # Prosedürü eklediğimizde metadata'yı da ekleyelim (tipi, havaalanı, pist, prosedür adı)
                for waypoint in waypoints:
                    waypoint['proc_type'] = proc_type
                    waypoint['airport'] = airport
                    waypoint['runway'] = runway
                    waypoint['procedure'] = procedure
                self.map_widget.procedures.append(waypoints)
        else:
            # Prosedürü kaldırırken daha spesifik bir filtre kullanalım
            self.map_widget.procedures = [p for p in self.map_widget.procedures 
                if not (len(p) > 0 and 
                       p[0].get('proc_type') == proc_type and
                       p[0].get('airport') == airport and
                       p[0].get('runway') == runway and
                       p[0].get('procedure') == procedure)]
        self.map_widget.update()

    def on_runway_toggled(self, checked, runway_id):
        """Handle runway toggle"""
        if checked:
            # Runway'i seçili listeye ekle
            self.map_widget.selected_runways.add(runway_id)
        else:
            # Runway'i seçili listeden çıkar
            self.map_widget.selected_runways.discard(runway_id)
        
        # Haritayı güncelle
        self.map_widget.update()

    def toggle_left_sidebar(self):
        """Toggle the visibility of the left sidebar"""
        if self.left_sidebar_container.isVisible():
            self.left_sidebar_container.hide()
            # Update splitter sizes
            sizes = self.splitter.sizes()
            self.splitter.setSizes([0, sizes[0] + sizes[1]])
        else:
            self.left_sidebar_container.show()
            # Restore left sidebar width - ekran genişliğinin %15'i kadar
            sizes = self.splitter.sizes()
            screen_width = self.screen().availableGeometry().width()
            sidebar_width = int(screen_width * 0.15)
            self.splitter.setSizes([sidebar_width, sizes[1] - sidebar_width])

    def show_path_extension_dialog(self):
        """Show dialog to configure path extension"""
        # Create dialog but keep it non-modal
        self.path_extension_dialog = PathExtensionDialog(self.data_manager.runways, self)
        
        # Connect coordinate picking signals
        self.map_widget.coordinatePicked.connect(self.path_extension_dialog.set_coordinates)
        
        # Connect pattern change signal to update coordinate picking mode
        self.path_extension_dialog.patternChanged.connect(self.update_coordinate_picking_mode)
        
        # Connect dialog buttons to custom handlers
        self.path_extension_dialog.buttonBox.accepted.connect(self.on_path_extension_accepted)
        self.path_extension_dialog.buttonBox.rejected.connect(self.on_path_extension_rejected)
        
        # Set dialog properties to keep it on top but non-modal
        self.path_extension_dialog.setWindowFlags(
            Qt.Window | Qt.WindowStaysOnTopHint
        )
        
        # Show dialog with clear instructions about path extension functionality
        self.statusBar().showMessage("Path Extension: Önceden tanımlanmış desenler (Trombone/Point Merge) oluşturur - Noktaları ayrı ayrı taşıyamazsınız")
        self.path_extension_dialog.show()
        
        # Enable coordinate picking mode if point merge is selected
        self.update_coordinate_picking_mode(self.path_extension_dialog.pointmerge_radio.isChecked())
        
    def update_coordinate_picking_mode(self, is_point_merge):
        """Update coordinate picking mode based on pattern type"""
        if hasattr(self, 'path_extension_dialog'):
            # Only enable coordinate picking when point merge is selected
            self.map_widget.set_coordinate_picking_mode(is_point_merge)
            
            # Update status message
            if is_point_merge:
                self.statusBar().showMessage("Point Merge selected - Click to set coordinates, Ctrl+Click to specifically move merge point")
            else:
                self.statusBar().showMessage("Configure path extension")
            
    def on_path_extension_accepted(self):
        """Handle when the path extension dialog is accepted"""
        # Check if dialog still exists
        if not self.path_extension_dialog:
            self.statusBar().showMessage("Error: Dialog was closed unexpectedly", 3000)
            return
        
        try:
            # Dialog zaten accept() metodunda yapılandırmayı doğruladı ve kaydetti
            # Direkt olarak kaydedilen yapılandırmayı kullan
            if hasattr(self.path_extension_dialog, 'current_config') and self.path_extension_dialog.current_config:
                config = self.path_extension_dialog.current_config
                
                # Path extension'ı haritada çiz
                route_id = self.map_widget.draw_path_extension(config)
                
                # Path başarıyla çizildiğinde dialog'u kapat ve coordinate picking'i devre dışı bırak
                self.path_extension_dialog = None
                self.map_widget.set_coordinate_picking_mode(False)
                
                # Show helpful message about path movement shortcuts
                if config.get('pattern_type') == 'pointmerge':
                    self.statusBar().showMessage("Point Merge created - Use middle mouse button to pan the map - Double-click for options")
                else:
                    self.statusBar().showMessage("Trombone pattern created - Use middle mouse button to pan the map - Double-click for options")
            else:
                # Bu noktaya gelmemeli, çünkü dialog'un accept() metodu zaten valid config olmadan
                # super().accept() çağırmaz, ama yine de bir güvenlik kontrolü olarak burada da kontrol edelim
                self.statusBar().showMessage("Configuration could not be created. Please check all values and try again.", 5000)
                return
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.statusBar().showMessage(f"Error creating path: {str(e)}", 5000)
            # Keep dialog open in case of error
            return
        
    def on_path_extension_rejected(self):
        """Handle when the path extension dialog is canceled"""
        # Disable coordinate picking mode
        self.map_widget.set_coordinate_picking_mode(False)
        
        # Clean up
        self.path_extension_dialog = None
        self.statusBar().showMessage("Ready", 2000)

    def toggle_route_drawing(self, checked):
        """Toggle route drawing mode"""
        if checked:
            self.statusBar().showMessage("Route Drawing: Serbest rota çizimi - Sol tık: Nokta ekle, Sağ tık: Bitir, Orta düğme: Haritayı kaydır. Eklenen noktalar taşınabilir.")
            self.map_widget.start_route_drawing()
            
            # Path Extension butonunu devre dışı bırak
            self.action_path_extension.setEnabled(False)
            
            # Artık gradient calculator otomatik açılmıyor
        else:
            self.map_widget.cancel_route_drawing()
            self.statusBar().showMessage("Ready")
            
            # Draw Route modundan çıkıldığında Path Extension butonunu tekrar aktif hale getir
            self.action_path_extension.setEnabled(True)
        
    def on_route_drawing_started(self):
        """Handle when route drawing starts"""
        # Artık burada butonu devre dışı bırakmaya gerek yok, toggle_route_drawing'de yapılıyor
        pass
    
    def on_route_drawing_finished(self, route_id, points):
        """Handle when route drawing finishes"""
        self.action_draw_route.setChecked(False)
        self.action_path_extension.setEnabled(True)
        
        # Gradient Calculator otomatik açılmıyor, sadece açıksa güncelleniyor
        if hasattr(self, 'gradient_calculator') and self.gradient_calculator.isVisible():
            # Eğer zaten açıksa güncelle
            self.update_gradient_calculator()
            
        # Bildirim göster
        self.statusBar().showMessage("Rota tamamlandı! Gradient hesaplamak için Tools menüsünden Gradient Calculator'ı açabilirsiniz.", 5000)

    def toggle_multi_select_mode(self, checked):
        """Enable or disable multi-select mode for routes"""
        self.map_widget.set_multi_select_mode(checked)
        
        # Düğmeleri etkinleştir veya devre dışı bırak
        self.action_merge_routes.setEnabled(checked)
        self.action_delete_routes.setEnabled(checked)
        
        if checked:
            self.statusBar().showMessage("Çoklu seçim modu aktif. Rotaları seçmek için tıklayın.")
        else:
            self.statusBar().showMessage("Çoklu seçim modu kapatıldı.")
    
    def merge_selected_routes(self):
        """Merge selected routes"""
        if self.map_widget.merge_selected_routes():
            self.statusBar().showMessage("Seçilen rotalar birleştirildi.")
        else:
            self.statusBar().showMessage("Birleştirmek için en az iki rota seçin.", 3000)
    
    def delete_selected_routes(self):
        """Delete selected routes"""
        if self.map_widget.delete_selected_routes():
            self.statusBar().showMessage("Seçilen rotalar silindi.")
        else:
            self.statusBar().showMessage("Silmek için en az bir rota seçin.", 3000)

    def on_open(self):
        """Open a saved project"""
        print("on_open fonksiyonu çağrıldı")
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filePath, fileFilter = QFileDialog.getOpenFileName(
            self, "Çizimleri Yükle", "", 
            "Tüm Desteklenen Dosyalar (*.json *.csv);;JSON Dosyaları (*.json);;CSV Rotaları (*.csv);;Tüm Dosyalar (*)", 
            options=options
        )
        
        if not filePath:
            print("Dosya seçilmedi")
            return
            
        print(f"Seçilen dosya: {filePath}")
        
        # Dosya uzantısına göre işlem yap
        if filePath.lower().endswith('.json'):
            success, message = self.data_manager.load_drawings_from_json(filePath)
            print(f"JSON yükleme sonucu: başarı={success}, mesaj={message}")
        
            if success:
                # Çizimleri map_widget'a aktar (sadece routes anahtarını güncelle)
                # İlk olarak mevcut trajectories ve waypoints değerlerini kaydedelim
                trajectories = self.map_widget.drawn_elements.get('trajectories', [])
                waypoints = self.map_widget.drawn_elements.get('waypoints', [])
                
                # Şimdi routes listesini güncelleyelim
                self.map_widget.drawn_elements['routes'] = self.data_manager.drawn_elements['routes']
                
                # Diğer anahtarların değerlerini koruyalım
                self.map_widget.drawn_elements['trajectories'] = trajectories
                self.map_widget.drawn_elements['waypoints'] = waypoints
                
                self.map_widget.update()
                self.statusBar().showMessage(message, 5000)
                print("Çizimler başarıyla yüklendi ve map_widget güncellendi")
            else:
                QMessageBox.warning(self, "Yükleme Hatası", message)
                print(f"Yükleme hatası: {message}")
                
        elif filePath.lower().endswith('.csv'):
            # CSV dosyasından rota yükleme
            success, message, loaded_route = self.data_manager.load_route_from_csv(filePath)
            print(f"CSV yükleme sonucu: başarı={success}, mesaj={message}")
            
            if success and loaded_route:
                # İlk olarak mevcut trajectories ve waypoints değerlerini kaydedelim
                trajectories = self.map_widget.drawn_elements.get('trajectories', [])
                waypoints = self.map_widget.drawn_elements.get('waypoints', [])
                
                # Yüklenen rotayı drawn_elements listesine ekle
                if 'routes' not in self.map_widget.drawn_elements:
                    self.map_widget.drawn_elements['routes'] = []
                
                # Rotayı ekle
                self.map_widget.drawn_elements['routes'].append(loaded_route)
                
                # Diğer anahtarların değerlerini koruyalım
                self.map_widget.drawn_elements['trajectories'] = trajectories
                self.map_widget.drawn_elements['waypoints'] = waypoints
                
                # Haritayı güncelle
                self.map_widget.update()
                self.statusBar().showMessage(f"CSV Rotası Yüklendi: {message}", 5000)
                print(f"CSV rotası başarıyla yüklendi: {loaded_route['name']}")
            else:
                QMessageBox.warning(self, "CSV Yükleme Hatası", message)
                print(f"CSV yükleme hatası: {message}")
        else:
            QMessageBox.warning(self, "Yükleme Hatası", "Desteklenmeyen dosya formatı")
            print(f"Yükleme hatası: Desteklenmeyen dosya formatı")
        
    def on_save(self):
        """Save the current project"""
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        
        # Hem JSON hem CSV formatı seçeneği sun
        fileFormats = "JSON Dosyası (*.json);;CSV Dosyaları (*.csv);;Tüm Dosyalar (*)"
        filePath, selectedFilter = QFileDialog.getSaveFileName(
            self, "Çizimleri Kaydet", "", 
            fileFormats, 
            options=options
        )
        
        if not filePath:
            return
        
        # Map widget'taki veriyi önce DataManager'a aktar
        self.data_manager.drawn_elements = self.map_widget.drawn_elements
        
        # Seçilen formatı kontrol et
        if "JSON" in selectedFilter or filePath.lower().endswith('.json'):
            # JSON uzantısını kontrol et
            if not filePath.lower().endswith('.json'):
                filePath += '.json'
            
            # JSON formatında kaydet
            success, message = self.data_manager.save_drawings_to_json(filePath)
            
            if success:
                self.statusBar().showMessage(message, 5000)
            else:
                QMessageBox.warning(self, "Kaydetme Hatası", message)
                
        elif "CSV" in selectedFilter or filePath.lower().endswith('.csv'):
            # CSV uzantısını kontrol et
            if not filePath.lower().endswith('.csv'):
                filePath += '.csv'
            
            # Klasör yolu oluştur
            basePath = os.path.splitext(filePath)[0]
            
            # Tüm çizimleri CSV olarak kaydet
            routes = self.map_widget.drawn_elements.get('routes', [])
            
            if not routes:
                QMessageBox.warning(self, "Kaydetme Hatası", "Kaydedilecek çizim bulunamadı.")
                return
            
            # İlk rota dosyasını belirtilen yola kaydet, diğerlerini otomatik adlandır
            saved_count = 0
            for i, route in enumerate(routes):
                route_name = route.get('name', f"Route_{i+1}")
                route_id = route.get('id', '')
                
                # İlk rota için seçilen ismi kullan, diğerleri için otomatik isimlendirme yap
                if i == 0:
                    route_file = filePath
                else:
                    # Aynı klasördeki yeni bir dosya ismi oluştur
                    route_dir = os.path.dirname(filePath)
                    route_file = os.path.join(route_dir, f"{route_name}.csv")
                
                try:
                    # CSV dosyasını oluştur
                    with open(route_file, 'w', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        # Başlık satırı
                        writer.writerow(['Waypoint', 'Latitude', 'Longitude', 'Lat (DMS)', 'Lon (DMS)', 'Segment Distance (NM)', 'Track (°)'])
                        
                        # Nokta verilerini ve segment mesafelerini hesapla ve yaz
                        if 'points' in route:
                            for j, (lat, lon) in enumerate(route['points']):
                                wp_name = f"WP{j+1}"
                                lat_dms = self.map_widget.decimal_to_dms(lat, 'lat')
                                lon_dms = self.map_widget.decimal_to_dms(lon, 'lon')
                                
                                # Segment mesafesi ve açısını hesapla (ilk nokta hariç)
                                dist = ""
                                track = ""
                                if j > 0:
                                    prev_lat, prev_lon = route['points'][j-1]
                                    dist = f"{self.map_widget.calculate_distance(prev_lat, prev_lon, lat, lon):.1f}"
                                    track = f"{self.map_widget.calculate_bearing(prev_lat, prev_lon, lat, lon):.1f}"
                                
                                writer.writerow([wp_name, f"{lat:.6f}", f"{lon:.6f}", lat_dms, lon_dms, dist, track])
                    saved_count += 1
                
                except Exception as e:
                    QMessageBox.warning(self, "CSV Kaydetme Hatası", 
                                      f"{route_name} rotası kaydedilirken hata oluştu: {str(e)}")
            
            # Başarılı mesajı göster
            if saved_count > 0:
                self.statusBar().showMessage(f"{saved_count} rota CSV formatında kaydedildi.", 5000)
            else:
                QMessageBox.warning(self, "Kaydetme Hatası", "Hiçbir rota kaydedilemedi.")
    
    def on_load_drawings(self):
        """Çizimleri yükle fonksiyonu - sol kenar çubuğundaki butonla çağrılır"""
        print("on_load_drawings fonksiyonu çağrıldı")
        self.on_open()
        
    def on_path_selected(self, path_data):
        """Handle when a path is selected on the map"""
        # Update the right sidebar with path details
        # Show a status message with instructions for movement
        name = path_data.get('name', 'Path Extension')
        pattern_type = path_data.get('type', '')
        
        if pattern_type == 'user_route':
            self.statusBar().showMessage(f"Selected: {name} - Sol tık: Noktaları taşı, Sağ tık: Noktaları sil, Orta düğme: Haritayı kaydır, Çift tık: Rota seçenekleri", 5000)
        elif pattern_type == 'trombone' or pattern_type == 'pointmerge':
            self.statusBar().showMessage(f"Selected: {name} - Orta düğme: Haritayı kaydır, Çift tık: Desen seçenekleri", 5000)
        else:
            self.statusBar().showMessage(f"Selected: {name} - Orta düğme: Haritayı kaydır", 5000)

    def closeEvent(self, event):
        """Handle application close event"""
        # Cleanup temporary files
        if hasattr(self, 'temp_file') and os.path.exists(self.temp_file):
            os.remove(self.temp_file)
        event.accept()

    def update_coordinates(self, lat, lon):
        """Update coordinate display in status bar"""
        # Format coordinates with N/S and E/W indicators
        lat_direction = "N" if lat >= 0 else "S"
        lon_direction = "E" if lon >= 0 else "W"
        
        # Convert to absolute values
        lat_value = abs(lat)
        lon_value = abs(lon)
        
        # Convert decimal degrees to DD MM SS.SS format
        lat_deg = int(lat_value)
        lat_min_float = (lat_value - lat_deg) * 60
        lat_min = int(lat_min_float)
        lat_sec = (lat_min_float - lat_min) * 60
        
        lon_deg = int(lon_value)
        lon_min_float = (lon_value - lon_deg) * 60
        lon_min = int(lon_min_float)
        lon_sec = (lon_min_float - lon_min) * 60
        
        # Format text using DD MM SS.SS N   DD MM SS.SS E format
        # Note: Longitude degrees typically use 3 digits (000-180)
        text = f"{lat_deg:02d} {lat_min:02d} {lat_sec:05.2f} {lat_direction}   {lon_deg:03d} {lon_min:02d} {lon_sec:05.2f} {lon_direction}"
        self.coord_label.setText(text) 

    def show_runway_options_dialog(self):
        """Show the dialog to configure runway display options."""
        if not self.data_manager.runways:
            QMessageBox.information(self, "No Runways", "No runway data loaded to configure.")
            return
            
        dialog = RunwayOptionsDialog(self.data_manager.runways, self)
        if dialog.exec_() == QDialog.Accepted:
            updated_options = dialog.get_updated_runway_options()
            
            # Merkez hattı gösterimi için flag kontrol edilecek
            # Herhangi bir pist için merkez hattı etkinse genel flag de etkin olmalı
            show_any_centerline = False
            
            # Apply changes to the data manager
            for runway in self.data_manager.runways:
                runway_id = runway.get('id')
                if runway_id in updated_options:
                    options = updated_options[runway_id]
                    runway['centerline_length'] = options.get('centerline_length', 15.0)
                    runway['centerline_style'] = options.get('centerline_style', 'Dashed')
                    
                    # Herhangi bir pist için centerline etkinleştirilmiş mi kontrol et
                    if options.get('show_centerline', False):
                        show_any_centerline = True
                    
                    # Get the specific end names from the runway ID itself
                    try:
                        display_id_part = runway_id.split(' ', 1)[-1]
                        end1_name, end2_name = display_id_part.split('/')
                        key_end1 = f'show_{end1_name}'
                        key_end2 = f'show_{end2_name}'
                        runway[key_end1] = options.get(key_end1, False) # Use False default now
                        runway[key_end2] = options.get(key_end2, False) # Use False default now
                        
                        # Check if either end is set to show centerline
                        if runway[key_end1] or runway[key_end2]:
                            show_any_centerline = True
                    except Exception as e:
                        print(f"Warning: Could not parse end names for {runway_id} when applying options: {e}")
            
            # Set the global centerline visibility flag based on individual settings
            self.map_widget.show_centerlines = show_any_centerline
            
            # Update map display
            self.map_widget.update()
            print(f"Runway display options updated. Centerlines visible: {show_any_centerline}")
        else:
            print("Runway display options dialog cancelled.")

    def on_import_trajectory(self):
        """Handle the import trajectory action"""
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Trajectory", "",
                                                 "Trajectory Files (*.csv *.kml);;CSV Files (*.csv);;KML Files (*.kml);;All Files (*)", 
                                                 options=options)
        if file_path:
            self.statusBar().showMessage(f"Importing trajectory from {os.path.basename(file_path)}...")
            trajectory_id, trajectory_data = None, None
            try:
                if file_path.lower().endswith('.csv'):
                    trajectory_id, trajectory_data = self.data_manager.parse_csv_trajectory(file_path)
                elif file_path.lower().endswith('.kml'):
                    trajectory_id, trajectory_data = self.data_manager.parse_kml_trajectory(file_path)
                else:
                    QMessageBox.warning(self, "Unsupported File", f"Unsupported file type: {os.path.basename(file_path)}")
                    self.statusBar().showMessage("Import failed.", 2000)
                    return
                    
                if trajectory_data:
                    print(f"Successfully parsed {len(trajectory_data)} points for trajectory ID: {trajectory_id}")
                    self.map_widget.add_trajectory(trajectory_id, trajectory_data)
                    self.statusBar().showMessage(f"Trajectory '{trajectory_id}' imported successfully.", 5000)
                else:
                    QMessageBox.warning(self, "Import Failed", f"Could not parse trajectory data from {os.path.basename(file_path)}.")
                    self.statusBar().showMessage("Import failed.", 2000)
            except Exception as e:
                import traceback
                traceback.print_exc()
                QMessageBox.critical(self, "Import Error", f"An error occurred while importing {os.path.basename(file_path)}:\n{str(e)}")
                self.statusBar().showMessage("Import error.", 2000)

    def show_gradient_calculator(self):
        """Show the gradient calculator dialog"""
        # Rotaları bir sözlük olarak hazırla
        routes_dict = {}
        
        for route in self.map_widget.drawn_elements.get('routes', []):
            if 'points' in route and route['points']:
                route_id = route.get('id', f"route_{len(routes_dict)}")
                route_name = route.get('name', f"Route {len(routes_dict) + 1}")
                
                # Doğru formatta rota verisi oluştur
                routes_dict[route_id] = {
                    'name': route_name,
                    'points': [(p[0], p[1]) for p in route['points']],
                    'waypoint_names': route.get('waypoint_names', []),
                    'config': route.get('config', {})
                }
        
        # Create and show the gradient calculator dialog
        self.gradient_calculator = GradientCalculatorDialog(routes_dict, self)
        
        # Set dialog properties to keep it on top but non-modal
        self.gradient_calculator.setWindowFlags(
            Qt.Window | Qt.WindowStaysOnTopHint
        )
        
        # Connect route change signals
        self.map_widget.routeDrawingFinished.connect(self.update_gradient_calculator)
        self.map_widget.pathSelected.connect(self.update_gradient_calculator)
        
        # Connect signal for applying altitudes to waypoints
        self.gradient_calculator.altitudesCalculated.connect(self.apply_calculated_altitudes)
        
        # Show dialog (bu aşamada gösterilmeli ki boyutu belli olsun)
        self.gradient_calculator.show()
        
        # Ekranın sağ üst köşesinde konumlandır
        screen_geometry = self.screen().geometry()
        dialog_geometry = self.gradient_calculator.geometry()
        
        # Sağ üst köşeden hafif içeri konumlandır (10 piksel kenar payı bırak)
        x_position = screen_geometry.width() - dialog_geometry.width() - 10
        y_position = 10
        
        self.gradient_calculator.move(x_position, y_position)
        
        # Rota yoksa bilgilendirme mesajı göster
        if not routes_dict:
            self.statusBar().showMessage("Draw a route to calculate gradients", 3000)
        
    def update_gradient_calculator(self, *args):
        """Update gradient calculator with current routes"""
        if hasattr(self, 'gradient_calculator') and self.gradient_calculator.isVisible():
            # Rotaları bir sözlük olarak hazırla
            routes_dict = {}
            
            for route in self.map_widget.drawn_elements.get('routes', []):
                if 'points' in route and route['points']:
                    route_id = route.get('id', f"route_{len(routes_dict)}")
                    route_name = route.get('name', f"Route {len(routes_dict) + 1}")
                    
                    # Doğru formatta rota verisi oluştur
                    routes_dict[route_id] = {
                        'name': route_name,
                        'points': [(p[0], p[1]) for p in route['points']],
                        'waypoint_names': route.get('waypoint_names', []),
                        'config': route.get('config', {})
                    }
            
            # Update gradient calculator with new routes
            self.gradient_calculator.update_routes(routes_dict)

    def apply_calculated_altitudes(self, indices, altitudes):
        """Apply calculated altitudes from gradient calculator to route waypoints"""
        # Seçilen rota ID'sini al (eğer mevcutsa)
        selected_route_id = self.gradient_calculator.selected_route_id if hasattr(self.gradient_calculator, 'selected_route_id') else None
        
        # Check if we have a selected route
        selected_route = None
        selected_route_idx = -1
        
        # Eğer Gradient Calculator'dan bir rota ID'si mevcutsa, o rotayı bulmaya çalış
        if selected_route_id:
            for idx, route in enumerate(self.map_widget.drawn_elements['routes']):
                if route.get('id') == selected_route_id:
                    selected_route = route
                    selected_route_idx = idx
                    break
        
        # Eğer hala bir rota bulunamadıysa, seçili rotayı veya tek rotayı kullan
        if selected_route is None and hasattr(self.map_widget, 'selected_path_index') and self.map_widget.selected_path_index is not None:
            selected_route_idx = self.map_widget.selected_path_index
            if 0 <= selected_route_idx < len(self.map_widget.drawn_elements['routes']):
                selected_route = self.map_widget.drawn_elements['routes'][selected_route_idx]
        
        # If no route is selected but we have exactly one route, use it
        if selected_route is None and len(self.map_widget.drawn_elements['routes']) == 1:
            selected_route = self.map_widget.drawn_elements['routes'][0]
            selected_route_idx = 0
            
        if selected_route is None:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Rota Seçilmedi", "Lütfen önce irtifa uygulanacak rotayı seçin.")
            return
            
        # Ensure the route has altitude data structure
        if 'altitudes' not in selected_route:
            selected_route['altitudes'] = [None] * len(selected_route.get('points', []))
        
        # Apply the calculated altitudes to the route
        try:
            # Update altitudes for each waypoint in the selected range
            for i, wp_idx in enumerate(indices):
                if 0 <= wp_idx < len(selected_route['altitudes']):
                    selected_route['altitudes'][wp_idx] = altitudes[i]
            
            # Update altitude constraints if the route supports it
            if 'config' in selected_route:
                if 'altitude_constraints' not in selected_route['config']:
                    selected_route['config']['altitude_constraints'] = {}
                    
                for i, wp_idx in enumerate(indices):
                    wp_name = f"WP{wp_idx+1}"
                    if 'waypoint_names' in selected_route and 0 <= wp_idx < len(selected_route['waypoint_names']):
                        wp_name = selected_route['waypoint_names'][wp_idx]
                    
                    # Store as altitude constraint
                    selected_route['config']['altitude_constraints'][wp_name] = altitudes[i]
            
            # Redraw the route to reflect altitude changes if trajectory coloring is enabled
            if hasattr(self.map_widget, 'trajectory_altitude_coloring') and self.map_widget.trajectory_altitude_coloring:
                self.map_widget.update()
                
            # If this is a selected route, update the sidebar display
            if self.map_widget.selected_path_index == selected_route_idx:
                self.map_widget.pathSelected.emit(selected_route)
                
            self.statusBar().showMessage(f"{len(indices)} waypoint için irtifa değerleri güncellendi.", 5000)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "İrtifa Güncelleme Hatası", f"İrtifalar güncellenirken bir hata oluştu: {str(e)}")

    def on_route_point_added(self, route_points):
        """Her yeni waypoint eklendiğinde çağrılır"""
        # Gradient Calculator'ı güncelle veya göster
        if hasattr(self, 'gradient_calculator') and self.gradient_calculator.isVisible():
            # Güncel rotaları bir sözlük olarak hazırla
            routes_dict = {}
            
            # Yeni çizilen rotayı geçici olarak ekle
            if route_points:
                temp_route_id = "temp_drawing_route"
                routes_dict[temp_route_id] = {
                    'name': "Çizilen Rota",
                    'points': [(lat, lon) for lat, lon in route_points],
                    'waypoint_names': []  # Henüz isimlendirme yapılmamış
                }
            
            # Mevcut rotaları da ekle
            for route in self.map_widget.drawn_elements.get('routes', []):
                if 'points' in route and route['points']:
                    route_id = route.get('id', f"route_{len(routes_dict)}")
                    route_name = route.get('name', f"Route {len(routes_dict) + 1}")
                    
                    routes_dict[route_id] = {
                        'name': route_name,
                        'points': [(p[0], p[1]) for p in route['points']],
                        'waypoint_names': route.get('waypoint_names', [])
                    }
            
            # Gradient calculator'ı güncelle
            self.gradient_calculator.update_routes(routes_dict)

    # SID ve STAR görünürlük kontrolleri şu an için devre dışı bırakıldı
    # def on_show_sids_toggled(self, checked):
    #     """Handle SID visibility toggle"""
    #     self.map_widget.show_sids = checked
    #     self.map_widget.update() # Haritayı güncelle
    #     
    # def on_show_stars_toggled(self, checked):
    #     """Handle STAR visibility toggle"""
    #     self.map_widget.show_stars = checked
    #     self.map_widget.update() # Haritayı güncelle
        
    def on_show_waypoints_toggled(self, checked):
        """Handle waypoint visibility toggle"""
        # Waypoint görünürlüğünü hem map_widget hem de data_manager'da güncelle
        # Yeni set_show_waypoints metodunu kullan (bu otomatik olarak snap modunu da günceller)
        self.map_widget.set_show_waypoints(checked)
        if hasattr(self.data_manager, 'show_waypoints'):
            self.data_manager.show_waypoints = checked
        self.map_widget.update() # Haritayı güncelle
        self.statusBar().showMessage(f"Waypoint görünürlüğü: {'Açık' if checked else 'Kapalı'}", 2000)

    def on_show_tma_boundary_toggled(self, checked):
        """Handle TMA boundary visibility toggle"""
        # TMA sınır görünürlüğünü hem map_widget hem de data_manager'da güncelle
        self.map_widget.show_tma_boundary = checked
        if hasattr(self.data_manager, 'show_tma_boundary'):
            self.data_manager.show_tma_boundary = checked
        self.map_widget.update() # Haritayı güncelle
        self.statusBar().showMessage(f"TMA sınır görünürlüğü: {'Açık' if checked else 'Kapalı'}", 2000)

    def on_show_restricted_areas_toggled(self, checked):
        """Handle LTD_P_R restricted areas visibility toggle"""
        # Yasaklı/kısıtlı sahaların görünürlüğünü hem map_widget hem de data_manager'da güncelle
        self.map_widget.show_restricted_areas = checked
        if hasattr(self.data_manager, 'show_restricted_areas'):
            self.data_manager.show_restricted_areas = checked
        self.map_widget.update() # Haritayı güncelle
        self.statusBar().showMessage(f"Yasaklı saha görünürlüğü: {'Açık' if checked else 'Kapalı'}", 2000)
        
    def on_show_segment_distances_toggled(self, checked):
        """Handle segment distance labels visibility toggle"""
        self.map_widget.show_segment_distances = checked
        self.map_widget.update() # Haritayı güncelle
        self.statusBar().showMessage(f"Mesafe etiketleri: {'Açık' if checked else 'Kapalı'}", 2000)

    def on_snap_enabled_toggled(self, checked):
        """Snap özelliğini etkinleştir/devre dışı bırak"""
        if hasattr(self.map_widget, 'route_drawer') and hasattr(self.map_widget.route_drawer, 'snap_manager'):
            self.map_widget.route_drawer.snap_manager.set_snap_enabled(checked)
            self.map_widget.update()
            status = "etkin" if checked else "devre dışı"
            self.map_widget.update_status_message(f"Snap özelliği {status}")
            
    def on_snap_mode_changed(self, mode):
        """Snap modunu değiştir"""
        if hasattr(self.map_widget, 'route_drawer') and hasattr(self.map_widget.route_drawer, 'snap_manager'):
            self.map_widget.route_drawer.snap_manager.set_snap_mode(mode)
            self.map_widget.update()
            # Mod adını bul
            mode_names = {
                0: "None",
                1: "Endpoints",
                2: "Midpoints",
                3: "Endpoints and Midpoints",
                4: "Intersections", 
                15: "All"
            }
            mode_name = mode_names.get(mode, "Bilinmeyen mod")
            self.map_widget.update_status_message(f"Snap modu değiştirildi: {mode_name}")
            
    def on_snap_tolerance_changed(self, value):
        """Snap toleransını değiştir"""
        if hasattr(self.map_widget, 'route_drawer') and hasattr(self.map_widget.route_drawer, 'snap_manager'):
            self.map_widget.route_drawer.snap_manager.set_snap_tolerance(value)
            self.map_widget.update()
            self.map_widget.update_status_message(f"Snap toleransı: {value}px")
            
    # Eski route color ve width handler'ları kaldırıldı (artık popup'ta yapılıyor)
    
    # Route popup'tan gelen sinyalleri işle
    def on_route_color_changed(self, route_id, color):
        """Route rengi değiştiğinde haritayı güncelle"""
        print(f"DEBUG: Route {route_id} color changed to {color}")
        # Route'un haritadaki rengini güncelle
        for route in self.map_widget.drawn_elements.get('routes', []):
            if route.get('id') == route_id:
                route['color'] = color
                break
        self.map_widget.update()
        self.statusBar().showMessage(f"Route color updated: {color}", 2000)
        
    def on_route_line_width_changed(self, route_id, width):
        """Route line width değiştiğinde haritayı güncelle"""
        print(f"DEBUG: Route {route_id} line width changed to {width}")
        # Route'un haritadaki kalınlığını güncelle
        for route in self.map_widget.drawn_elements.get('routes', []):
            if route.get('id') == route_id:
                route['line_width'] = width
                break
        self.map_widget.update()
        self.statusBar().showMessage(f"Route line width updated: {width}px", 2000)
        
    def on_land_color_changed(self, color):
        """Land rengi değiştiğinde tetiklenen metot"""
        print(f"DEBUG: Land color changed to {color.name()}")
        if isinstance(color, QColor) and color.isValid():
            self.map_widget.land_color = color
            self.map_widget.country_color = color
            self.map_widget.colors['land'] = color
            self.map_widget.update()  # Haritayı güncelle
            self.statusBar().showMessage(f"Land rengi değiştirildi: {color.name()}", 2000)
    
    def on_background_color_changed(self, color):
        """Background rengi değiştiğinde tetiklenen metot"""
        print(f"DEBUG: Background color changed to {color.name()}")
        if isinstance(color, QColor) and color.isValid():
            self.map_widget.background_color = color
            self.map_widget.colors['background'] = color
            self.map_widget.update()  # Haritayı güncelle
            self.statusBar().showMessage(f"Background rengi değiştirildi: {color.name()}", 2000)
    
    def on_restricted_area_color_changed(self, color):
        """Yasaklı sahalar rengi değiştiğinde tetiklenen metot"""
        print(f"DEBUG: Restricted area color changed to {color.name()}")
        if isinstance(color, QColor) and color.isValid():
            self.map_widget.restricted_area_border_color = color
            self.map_widget.restricted_area_grid_color = QColor(color.red(), color.green(), color.blue(), 80)  # %31 saydamlık
            self.map_widget.restricted_area_fill_color = QColor(color.red(), color.green(), color.blue(), 40)  # %16 saydamlık
            self.map_widget.update()  # Haritayı güncelle
            self.statusBar().showMessage(f"Yasaklı sahalar rengi değiştirildi: {color.name()}", 2000)

    def center_on_screen(self):
        """Pencereyi ekranın merkezinde konumlandır"""
        screen_geometry = self.screen().geometry()
        window_geometry = self.geometry()
        
        x = (screen_geometry.width() - window_geometry.width()) / 2
        y = (screen_geometry.height() - window_geometry.height()) / 2
        
        self.move(int(x), int(y))

    def clear_workspace(self):
        """Clear all drawings from the map (routes, trajectories, and waypoints)"""
        # Kullanıcıdan onay al
        confirmation = QMessageBox.question(self, 
                                         "Çalışma Alanını Temizle", 
                                         "Tüm çizimleri (rotalar, trombone ve point merge desenleri) haritadan kaldırmak istediğinize emin misiniz?", 
                                         QMessageBox.Yes | QMessageBox.No)
        
        if confirmation == QMessageBox.Yes:
            # MapWidget'ın clear metodu tüm çizimleri temizleyecek
            self.map_widget.clear_all_drawings()
            self.statusBar().showMessage("Çalışma alanı temizlendi", 3000)
        else:
            self.statusBar().showMessage("İşlem iptal edildi", 2000)