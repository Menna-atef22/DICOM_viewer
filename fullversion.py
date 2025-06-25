import os
import sys
import random
import string

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QAction, QFileDialog, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QHBoxLayout, QLineEdit, QDialog, QLabel, QInputDialog,QPushButton,QScrollArea,
    QStatusBar, QGridLayout,QWidget, QLabel,QMessageBox, QInputDialog
)
from PyQt5.QtCore import Qt, QTimer
import pydicom
import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class DICOMViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("DICOM Viewer")
        self.setGeometry(100, 100, 800, 600)

        # Step 1: Create a single central widget and set it once
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Step 2: Create the main layout for the central widget
        self.main_layout = QVBoxLayout(self.central_widget)  # Attach layout to central_widget

        # Step 3: Canvas for image display (2D single-slice view)
        self.canvas = DICOMImageCanvas(self)  # Create canvas as a class attribute
        self.main_layout.addWidget(self.canvas)  # Add the canvas to the layout

        # Step 4: Scroll area for grid display
        self.grid_scroll_area = QScrollArea(self)
        self.grid_scroll_area.setWidgetResizable(True)
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_scroll_area.setWidget(self.grid_container)
        self.main_layout.addWidget(self.grid_scroll_area)
        self.grid_scroll_area.setVisible(False)  # Hide grid initially

        # Step 5: Toolbar
        toolbar = self.addToolBar("Main Toolbar")

        # Open File Action
        open_action = QAction(QIcon(r"F:\Projects\DicomViewer\pythonProject\Icons\upload-file.png"),"Open DICOM", self)
        open_action.triggered.connect(self.open_dicom_file)
        toolbar.addAction(open_action)

        # Open Folder Action
        open_folder_action = QAction(QIcon(r"F:\Projects\DicomViewer\pythonProject\Icons\folder.png"),"Open DICOM Folder", self)
        open_folder_action.triggered.connect(self.open_dicom_folder)
        toolbar.addAction(open_folder_action)

        # Show Attributes Action
        attributes_action = QAction(QIcon(r"F:\Projects\DicomViewer\pythonProject\Icons\ui.png"),"Show Attributes", self)
        attributes_action.triggered.connect(self.show_attributes_window)
        toolbar.addAction(attributes_action)

        # Show Details Action
        details_action = QAction(QIcon(r"F:\Projects\DicomViewer\pythonProject\Icons\list.png"),"Show Details", self)
        details_action.triggered.connect(self.show_details_window)
        toolbar.addAction(details_action)

        # Play Video Action
        play_video_action = QAction(QIcon(r"F:\Projects\DicomViewer\pythonProject\Icons\play.png"),"Play Video", self)
        play_video_action.triggered.connect(self.toggle_video_mode)
        toolbar.addAction(play_video_action)

        # Anonymize Action
        anonymize_action = QAction(QIcon(r"F:\Projects\DicomViewer\pythonProject\Icons\anonymous.png"),"Anonymize DICOM", self)
        anonymize_action.triggered.connect(self.anonymize_dicom)
        toolbar.addAction(anonymize_action)

        # Toggle Tiles Action
        self.toggle_tiles_action = QAction(QIcon(r"F:\Projects\DicomViewer\pythonProject\Icons\grid.png"),"Show Tiles", self)
        self.toggle_tiles_action.setEnabled(False)  # Initially disabled
        self.toggle_tiles_action.triggered.connect(self.display_folder_as_tiles)
        toolbar.addAction(self.toggle_tiles_action)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Data variables
        self.dicom_data = None
        self.dicom_files = []  # List to store paths of all DICOM files in the folder
        self.dicom_frames = []  # Store multiple frames
        self.video_mode = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.play_video)
        self.current_frame = 0
        self.current_mode = "single"  # Can be "single" or "tiles"
        self.total_slices = 0
        self.columns = 5  # Fixed number of columns in the grid

    def open_dicom_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open DICOM File", "", "DICOM Files (*.dcm)")
        if file_name:
            try:
                self.dicom_data = pydicom.dcmread(file_name)

                # Prompt for anonymization
                reply = QMessageBox.question(
                    self,
                    "Anonymize DICOM",
                    "Would you like to anonymize this DICOM file?",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply == QMessageBox.Yes:
                    prefix, ok = QInputDialog.getText(self, "Anonymization Prefix", "Enter prefix for anonymization:")
                    if ok and prefix:
                        self.anonymize_file(self.dicom_data, prefix)
                        self.dicom_data.save_as(file_name)
                        self.status_bar.showMessage("DICOM file anonymized and saved.", 5000)

                # Check for cine DICOM or single-frame
                if hasattr(self.dicom_data, "NumberOfFrames") and self.dicom_data.NumberOfFrames > 1:
                    self.dicom_frames = [self.dicom_data.pixel_array[i] for i in range(self.dicom_data.NumberOfFrames)]
                    self.video_mode = True
                    self.timer.start(100)
                    self.status_bar.showMessage("Cine DICOM loaded.", 5000)
                else:
                    self.dicom_frames = [self.dicom_data.pixel_array]
                    self.video_mode = False
                    self.timer.stop()
                    self.status_bar.showMessage("Single-frame DICOM loaded.", 5000)

                self.update_display()
            except Exception as e:
                self.status_bar.showMessage(f"Failed to load DICOM file: {e}", 5000)

    def open_dicom_folder(self):
        # Open a dialog to select a DICOM folder
        folder_path = QFileDialog.getExistingDirectory(self, "Select DICOM Folder")
        if folder_path:
            # List all DICOM files in the folder
            dicom_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if
                           f.endswith(('.dcm'))]
            if dicom_files:
                # Save file paths and load the DICOM frames
                self.dicom_files = dicom_files  # Store file paths
                self.load_dicom_frames(dicom_files)
            else:
                # Notify the user if no DICOM files were found
                self.status_bar.showMessage("No DICOM files found in the selected folder.", 5000)

    def load_dicom_frames(self, file_paths):
        try:
            self.dicom_frames = [pydicom.dcmread(f).pixel_array for f in file_paths]
            self.dicom_data = pydicom.dcmread(file_paths[0])  # Metadata from the first file
            self.current_frame = 0
            self.video_mode = False
            self.timer.stop()
            self.update_display()

            # **Enable the "Show Tiles" button after frames are loaded**
            if self.dicom_frames:
                self.toggle_tiles_action.setEnabled(True)

            self.total_slices = len(self.dicom_frames)

            # Display the first slice as 2D
            self.canvas.display_image(self.dicom_frames[0])
            self.canvas.setVisible(True)
            self.grid_scroll_area.setVisible(False)
            self.current_mode = "single"

            self.status_bar.showMessage(f"Loaded {len(file_paths)} files from folder.", 5000)
        except Exception as e:
            self.status_bar.showMessage(f"Error loading folder: {e}", 5000)


    def toggle_video_mode(self):
        if len(self.dicom_frames) > 1:
            self.video_mode = not self.video_mode
            if self.video_mode:
                self.timer.start(100)  # 10 FPS
            else:
                self.timer.stop()

    def play_video(self):
        self.current_frame = (self.current_frame + 1) % len(self.dicom_frames)
        self.update_display()

    def update_display(self):
        self.canvas.display_image(self.dicom_frames[self.current_frame])

    def anonymize_dicom(self):
        # Prompt user for prefix
        prefix, ok = QInputDialog.getText(self, "Anonymization Prefix", "Enter prefix for anonymization:")
        if ok and prefix:
            for file_path in self.dicom_files:
                try:
                    dicom_data = pydicom.dcmread(file_path)
                    self.anonymize_file(dicom_data, prefix)
                    dicom_data.save_as(file_path)
                    print(f"Anonymized {file_path}")
                except Exception as e:
                    print(f"Error anonymizing {file_path}: {e}")

    def anonymize_file(self, dicom_data, prefix):
        # Critical DICOM tags to anonymize
        critical_tags = [
            'PatientName', 'PatientID', 'PatientBirthDate', 'PatientSex',
            'IssuerOfPatientID', 'StudyInstanceUID', 'SeriesInstanceUID','InstitutionName','InstitutionAddress','ReferringPhysicianName'
        ]

        # Random string generator
        def generate_random_string(length=8):
            return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

        # Anonymize each critical tag
        for tag in critical_tags:
            if tag in dicom_data:
                original_value = dicom_data[tag].value
                random_value = prefix + generate_random_string(6)
                dicom_data[tag].value = random_value
                print(f"Anonymized {tag}: {original_value} -> {random_value}")

    def show_attributes_window(self):
        if not self.dicom_data:
            return

        self.attributes_window = DICOMAttributesWindow(self.dicom_data)
        self.attributes_window.show()

    def show_details_window(self):
        if not self.dicom_data:
            return

        self.details_window = DICOMDetailsWindow(self.dicom_data)
        self.details_window.show()

    def display_single_slice(self, index=0):
            """Display a single DICOM slice."""
            if not self.dicom_frames:
                return

            self.canvas.display_image(self.dicom_frames[index])
            self.canvas.setVisible(True)
            self.grid_scroll_area.setVisible(False)
            self.current_mode = "single"
            self.toggle_tiles_action.setText("Show Tiles")

    def display_folder_as_tiles(self):
        """Toggle between tiles view and single-slice view."""
        if self.current_mode == "single":
            # Switch to tiles view
            if not self.dicom_frames:
                return

            # Clear existing items from grid
            for i in reversed(range(self.grid_layout.count())):
                widget = self.grid_layout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()

            # Set spacing and margins to 0 to make tiles touch each other
            self.grid_layout.setSpacing(0)  # Remove spacing between tiles
            self.grid_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins around the grid

            num_slices = len(self.dicom_frames)
            num_rows = int(np.ceil(num_slices / self.columns))

            for idx, frame in enumerate(self.dicom_frames):
                row = idx // self.columns
                col = idx % self.columns

                # Create and add new canvas for each slice
                canvas = DICOMImageCanvas(self)
                canvas.display_image(frame)
                canvas.setFixedSize(250, 250)  # Increase tile size to 250×250 pixels

                # Connect the canvas click event to show the slice
                canvas.mousePressEvent = lambda event, index=idx: self.show_slice_from_tile(index)
                self.grid_layout.addWidget(canvas, row, col)

            self.canvas.setVisible(False)  # Hide single-slice view
            self.grid_scroll_area.setVisible(True)  # Show tiles view
            self.current_mode = "tiles"
            self.toggle_tiles_action.setText("Show Single Slice")
        else:
            # Switch to single-slice view
            self.canvas.setVisible(True)
            self.grid_scroll_area.setVisible(False)
            self.current_mode = "single"
            self.toggle_tiles_action.setText("Show Tiles")

    def show_slice_from_tile(self, index):
        """Switch to single-slice view and display the selected slice."""
        self.current_frame = index
        self.display_single_slice(index)


class DICOMImageCanvas(FigureCanvas):
    def __init__(self, parent=None):
        fig = Figure()
        self.ax = fig.add_subplot(111)
        super().__init__(fig)
        self.setParent(parent)
        self.ax.axis('off')

    def display_image(self, pixel_array):
        self.ax.clear()
        self.ax.imshow(pixel_array, cmap='gray')
        self.ax.axis('off')
        self.draw()

class DICOMAttributesWindow(QDialog):
    def __init__(self, dicom_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DICOM Attributes")
        self.setGeometry(150, 150, 600, 400)

        self.dicom_data = dicom_data

        layout = QVBoxLayout(self)
        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Search by Tag Name...")
        self.search_bar.textChanged.connect(self.filter_table)
        layout.addWidget(self.search_bar)

        self.table = QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Tag ID", "VR", "Tag Name", "Value"])
        layout.addWidget(self.table)

        self.populate_table()

    def populate_table(self):
        self.table.setRowCount(0)
        for elem in self.dicom_data:
            if elem.VR != 'SQ':  # Skip sequences
                row_position = self.table.rowCount()
                self.table.insertRow(row_position)
                self.table.setItem(row_position, 0, QTableWidgetItem(str(elem.tag)))
                self.table.setItem(row_position, 1, QTableWidgetItem(elem.VR))
                self.table.setItem(row_position, 2, QTableWidgetItem(elem.keyword))
                self.table.setItem(row_position, 3, QTableWidgetItem(str(elem.value)))

    def filter_table(self, text):
        for i in range(self.table.rowCount()):
            tag_name = self.table.item(i, 2).text().lower()
            self.table.setRowHidden(i, text.lower() not in tag_name)

class DICOMDetailsWindow(QDialog):
    def __init__(self, dicom_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DICOM Details")
        self.setGeometry(200, 200, 600, 500)

        self.dicom_data = dicom_data

        layout = QVBoxLayout(self)

        # Details Display
        self.details_label = QLabel(self)
        self.details_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.details_label.setWordWrap(True)
        layout.addWidget(self.details_label)

        self.populate_details()

    def populate_details(self):
        def format_date(date_str):
            if len(date_str) == 8:  # e.g., "YYYYMMDD"
                return f"{date_str[4:6]}/{date_str[6:8]}/{date_str[:4]}"
            return date_str

        def format_time(time_str):
            if len(time_str) >= 6:  # e.g., "HHMMSS"
                return f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
            return time_str

        details = []

        # Patient Information
        patient_details = [
            f"Patient's Name: {self.dicom_data.get('PatientName', 'N/A')}",
            f"Patient ID: {self.dicom_data.get('PatientID', 'N/A')}",
            f"Patient's Sex: {self.dicom_data.get('PatientSex', 'N/A')}",
            f"Patient's Birth Date: {format_date(self.dicom_data.get('PatientBirthDate', 'N/A'))}",
        ]
        details.append("Patient\n" + "\n".join(patient_details) + "\n")

        # Station Information
        station_details = [
            f"Manufacturer: {self.dicom_data.get('Manufacturer', 'N/A')}",
            f"Manufacturer's Model Name: {self.dicom_data.get('ManufacturerModelName', 'N/A')}",
            f"Station Name: {self.dicom_data.get('StationName', 'N/A')}",
        ]
        details.append("Station\n" + "\n".join(station_details) + "\n")

        # Study Information
        study_details = [
            f"Study Instance UID: {self.dicom_data.get('StudyInstanceUID', 'N/A')}",
            f"Study Date: {format_date(self.dicom_data.get('StudyDate', 'N/A'))}",
            f"Study Time: {format_time(self.dicom_data.get('StudyTime', 'N/A'))}",
            f"Study ID: {self.dicom_data.get('StudyID', 'N/A')}",
            f"Accession Number: {self.dicom_data.get('AccessionNumber', 'N/A')}",
            f"Study Description: {self.dicom_data.get('StudyDescription', 'N/A')}",
        ]
        details.append("Study\n" + "\n".join(study_details) + "\n")

        # Series Information
        series_details = [
            f"Series Instance UID: {self.dicom_data.get('SeriesInstanceUID', 'N/A')}",
            f"Series Date: {format_date(self.dicom_data.get('SeriesDate', 'N/A'))}",
            f"Series Time: {format_time(self.dicom_data.get('SeriesTime', 'N/A'))}",
            f"Series Number: {self.dicom_data.get('SeriesNumber', 'N/A')}",
            f"Modality: {self.dicom_data.get('Modality', 'N/A')}",
            f"Referring Physician's Name: {self.dicom_data.get('ReferringPhysicianName', 'N/A')}",
            f"Institution Name: {self.dicom_data.get('InstitutionName', 'N/A')}",
            f"Institutional Department Name: {self.dicom_data.get('InstitutionalDepartmentName', 'N/A')}",
            f"Body Part Examined: {self.dicom_data.get('BodyPartExamined', 'N/A')}",
        ]
        details.append("Series\n" + "\n".join(series_details) + "\n")

        # DICOM Object Information
        dicom_object_details = [
            f"SOP Instance UID: {self.dicom_data.get('SOPInstanceUID', 'N/A')}",
            f"Image Type: {self.dicom_data.get('ImageType', 'N/A')}",
            f"SOP Class UID: {self.dicom_data.get('SOPClassUID', 'N/A')}",
            f"Transfer Syntax UID: {self.dicom_data.get('TransferSyntaxUID', 'N/A')}",
            f"Instance Number: {self.dicom_data.get('InstanceNumber', 'N/A')}",
            f"Image Comments: {self.dicom_data.get('ImageComments', 'N/A')}",
            f"Photometric Interpretation: {self.dicom_data.get('PhotometricInterpretation', 'N/A')}",
            f"Samples per Pixel: {self.dicom_data.get('SamplesPerPixel', 'N/A')}",
            f"Pixel Representation: {self.dicom_data.get('PixelRepresentation', 'N/A')}",
            f"Columns: {self.dicom_data.get('Columns', 'N/A')}",
            f"Rows: {self.dicom_data.get('Rows', 'N/A')}",
            f"Bits Allocated: {self.dicom_data.get('BitsAllocated', 'N/A')}",
            f"Bits Stored: {self.dicom_data.get('BitsStored', 'N/A')}",
        ]
        details.append("DICOM Object\n" + "\n".join(dicom_object_details))

        # Image Plane Information
        pixel_spacing = self.dicom_data.get('PixelSpacing', ['N/A', 'N/A'])
        image_plane_details = [
            f"Pixel Spacing: {', '.join(map(str, pixel_spacing))}"
        ]
        details.append("Image Plane\n" + "\n".join(image_plane_details) + "\n")

        # Image Acquisition Information
        image_acquisition_details = [
            f"KVP: {self.dicom_data.get('KVP', 'N/A')}",
        ]
        details.append("Image Acquisition\n" + "\n".join(image_acquisition_details))

        # Set all details to the QLabel
        self.details_label.setText("\n\n".join(details))

def main():
    app = QApplication(sys.argv)
    viewer = DICOMViewer()
    viewer.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
