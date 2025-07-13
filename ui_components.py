from PyQt5.QtWidgets import (QFrame, QVBoxLayout, QToolButton, QWidget, 
                          QSizePolicy, QScrollArea, QHBoxLayout, QLabel)
from PyQt5.QtCore import Qt, QParallelAnimationGroup, QPropertyAnimation

class CollapsibleSection(QFrame):
    """A collapsible section widget with animated expansion/collapse"""
    def __init__(self, title, parent=None):
        super().__init__(parent)
        
        # Set frame styling
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setStyleSheet("""
            QFrame {
                border: 1px solid #cccccc;
                border-radius: 2px;
                background-color: #ffffff;
            }
        """)
        
        # Create main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Create header with title and toggle button
        self.header = QWidget()
        self.header.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.header.setStyleSheet("background-color: #ffffff; border-bottom: 1px solid #cccccc;")
        self.header_layout = QHBoxLayout(self.header)
        self.header_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create toggle button
        self.toggle_button = QToolButton()
        self.toggle_button.setArrowType(Qt.RightArrow)
        self.toggle_button.setStyleSheet("QToolButton { border: none; background: transparent; }")
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.toggle_button.setFixedSize(20, 20)
        
        # Create title label
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-weight: bold;")
        
        # Add to header layout
        self.header_layout.addWidget(self.toggle_button)
        self.header_layout.addWidget(self.title_label)
        self.header_layout.addStretch()
        
        # Create content container
        self.content_container = QWidget()
        self.content_container.setVisible(False)
        self.content_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        
        # Add widgets to main layout
        self.main_layout.addWidget(self.header)
        self.main_layout.addWidget(self.content_container)
        
        # Connect signals
        self.toggle_button.clicked.connect(self.toggle_content)
        self.header.mousePressEvent = self.header_clicked
        
        # Initialize state
        self.collapsed = True
        self.content_layout = None
    
    def header_clicked(self, event):
        """Handle click on the header to toggle content"""
        self.toggle_content()
    
    def toggle_content(self):
        """Toggle section between expanded and collapsed states"""
        self.collapsed = not self.collapsed
        self.toggle_button.setArrowType(Qt.DownArrow if not self.collapsed else Qt.RightArrow)
        self.content_container.setVisible(not self.collapsed)
        
        # Ensure proper geometry updates
        self.adjustSize()
        self.updateGeometry()
        
        # Update parent if it's a scroll area to ensure proper scrolling
        parent = self.parent()
        while parent:
            if isinstance(parent, QScrollArea):
                parent.updateGeometry()
            parent = parent.parent()
    
    def setContentLayout(self, layout):
        """Set the content layout for this section"""
        if self.content_container.layout():
            QWidget().setLayout(self.content_container.layout())
        
        self.content_layout = layout
        self.content_container.setLayout(layout)
        
        # Start collapsed
        self.content_container.setVisible(False)
        self.collapsed = True
        self.toggle_button.setArrowType(Qt.RightArrow) 