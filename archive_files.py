import os
import shutil
from pathlib import Path

def archive_files():
    """
    Moves specified unused files to the Archive directory.
    """
    archive_dir = Path("Archive")
    if not archive_dir.exists():
        print("Archive directory does not exist. Please run setup.py first.")
        return

    files_to_archive = [
        "analyze_threads.py",
        "cleanup_db.py",
        "emails_export.csv",
        "export_to_csv.py",
        "ocr_utils.py",
        "pdf_report.py",
        "report.pdf",
        "templates",
        "text_utils.py",
        "thread_utils.py",
        "web_interface.py",
        "Rock",
        "emails.db 2",
        "emails.db.cpgz"
    ]

    for file_name in files_to_archive:
        file_path = Path(file_name)
        if file_path.exists():
            try:
                destination = archive_dir / file_path.name
                if file_path.is_dir():
                    shutil.move(str(file_path), str(destination))
                else:
                    shutil.move(str(file_path), str(archive_dir))
                print(f"Moved {file_name} to Archive")
            except Exception as e:
                print(f"Error moving {file_name}: {e}")
        else:
            print(f"{file_name} does not exist in the project directory.")

if __name__ == "__main__":
    archive_files()
