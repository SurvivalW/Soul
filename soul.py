import json
import sys
import os

from pathlib import Path
from PySide6.QtWidgets import QApplication, QMainWindow, QDialog, QVBoxLayout
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QObject, Slot
from PySide6.QtWebChannel import QWebChannel


CACHE_FILE = Path(__file__).with_name(".soul_cache.json")


#========SetupBRIDGE==========================
class SetupBridge(QObject):
    def __init__(self, dialog):
        super().__init__()
        self.dialog = dialog

    @Slot(str, str)
    def saveData(self, username, location):
        data = {
            "Username": username,
            "Location": location
        }
        CACHE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

        print("Data saved to cache.")
        self.dialog.accept()


#========MainBridge==========================
class MainBridge(QObject):
    
    @Slot(result=str)
    def getUsername(self):
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        return data.get("Username", "Stranger")

    @Slot(result=int)
    def getTotalLines(self):
        return Soul.TotalLines

    @Slot(result=int)
    def getPythonLines(self):
        return Soul.PythonLines
    
    @Slot(result=int)
    def getJavaLines(self):
        return Soul.JavaLines
    
    @Slot(result=int)
    def getAssemblyLines(self):
        return Soul.AssemblyLines



#========First time Setup==============
class Setup(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Soul (setup)")
        self.resize(900, 600)

        layout = QVBoxLayout()
        self.view = QWebEngineView()

        # --- Bridge ---
        self.channel = QWebChannel()
        self.bridge = SetupBridge(self)
        self.channel.registerObject("bridge", self.bridge)
        self.view.page().setWebChannel(self.channel)

        html_file = Path(__file__).with_name("setup.html").resolve().as_uri()
        self.view.setUrl(html_file)

        layout.addWidget(self.view)
        self.setLayout(layout)




#========Main=========================
class Soul(QMainWindow):
    PythonLines = 0
    JavaLines = 0
    AssemblyLines = 0

    TotalLines = 0

    bad_folders = {"node_modules", ".git", ".gitignore", "__pycache__", ".venv", "dist", "build", "env"}
    bad_files = {".md", ".markdown", ".MD", ".MARKDOWN", ".png", ".jpg", ".jpeg", ".gif", ".exe", ".dll", ".so", ".dylib", ".class", ".jar", ".zip", ".tar", ".gz", ".pdf", ".json"}



    def __init__(self):
        super().__init__()
        self.setWindowTitle("Soul")
        self.resize(1500, 1200)

        # Center window
        screen = self.screen().availableGeometry()
        size = self.geometry()
        x = (screen.width() - size.width()) // 2
        y = (screen.height() - size.height()) // 2
        self.move(x, y)

        self.view = QWebEngineView()
        html_path = (Path(__file__).parent / "vision.html").resolve().as_uri()
        self.view.setUrl(html_path)

        # --- Bridge ---
        self.channel = QWebChannel()
        self.bridge = MainBridge(self)
        self.channel.registerObject("bridge", self.bridge)
        self.view.page().setWebChannel(self.channel)

        self.setCentralWidget(self.view)
        
        location = json.loads(CACHE_FILE.read_text(encoding="utf-8")).get("Location", "")
        self.CalcStats(location)

        print("\n\n===== Stats =====")
        print("Assembly Lines: ", Soul.AssemblyLines)
        print("Python Lines: ", Soul.PythonLines)
        print("Java Lines: ", Soul.JavaLines)
        print("=================")
        print("Total Lines: ", Soul.TotalLines)


    def CalcStats(self, location):
        location = Path(location)

        if not location.exists() or not location.is_dir():
            print("Invalid location:", location)
            return

        if location.is_symlink():
            print("Symlink detected: ", location)
            return        

        print("checking for files in ", location)
        try:
            children = list(location.iterdir())
        except Exception as e:
            print("Error accessing {location}: {e}")
            return

        for item in children:
            if item.is_dir() and item.name in Soul.bad_folders:
                continue
            if item.is_file() and item.suffix in Soul.bad_files:
                continue

            if item.is_dir():
                print("Found directory: ", item)
                self.CalcStats(item)
            elif item.is_file():
                print("Found file: ", item)
                self.read(item)

    def read(self, path: Path):
        if path.suffix == ".py":            # Python
            print("Reading Python file: ", path)
            lines = self.count_code_lines(path, 1)
            Soul.PythonLines += lines
            Soul.TotalLines += lines
            print("Added ", lines, " lines from ", path)
        elif path.suffix == ".java":            # Java
            print("Reading Java file: ", path)
            lines = self.count_code_lines(path, 2)
            Soul.JavaLines += lines
            Soul.TotalLines += lines
            print("Added ", lines, " lines from ", path)
        elif path.suffix in {".asm", ".s"}:         # Assembly
            print("Reading Assembly file: ", path)
            lines = self.count_code_lines(path, 3)
            Soul.AssemblyLines += lines
            Soul.TotalLines += lines
            print("Added ", lines, " lines from ", path)

    def count_code_lines(self, path: Path, type) -> int:
        if type == 1:  # Python
            try:
                return sum(
                    1
                    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()
                    if line.strip() and not line.strip().startswith("#")        
                )
            except:
                return 0
        
        if type == 2:  # Java
            try:
                return sum(
                    1
                    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()
                    if (
                        (s := line.strip()) 
                        and not s.startswith("//")
                        and not s.startswith("/*")
                        and not s.startswith("*")
                        and not s.startswith("*/")
                    )        
                )
            except:
                return 0
            
        if type == 3:   # Assembly
            try:
                return sum(
                    1
                    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()
                    if line.strip() and not line.strip().startswith(";")
                )
            except:
                return 0

#========Run App======================
def run_soul():
    app = QApplication(sys.argv)

    if not CACHE_FILE.exists():
        setup = Setup()
        result = setup.exec()

        # if setup was killed, quit
        if result == 0:
            print("Setup aborted.")
            return
        
    win = Soul()
    win.show()


    app.exec()


if __name__ == "__main__":
    run_soul()