#!/usr/bin/env python3
"""
Create sample data for testing the Stone Email & Image Processor.
This script creates sample mbox files, images, and PDFs in the data directory.
"""
import os
import email
import mailbox
import random
from pathlib import Path
import time
from email.utils import formatdate
from datetime import datetime, timedelta
import sys

# Make sure we're in the correct directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Import application config
try:
    import config
except ImportError:
    print("Error: Cannot import config module. Make sure you're in the correct directory.")
    sys.exit(1)

def create_sample_mbox(filename, num_emails=20):
    """Create a sample mbox file with the specified number of emails."""
    data_dir = Path(config.MBOX_DIRECTORY)
    data_dir.mkdir(exist_ok=True)
    
    mbox_path = data_dir / filename
    
    mb = mailbox.mbox(str(mbox_path))
    mb.lock()
    
    senders = [
        "john.doe@example.com",
        "jane.smith@example.com",
        "mike.johnson@example.com",
        "sarah.williams@example.com"
    ]
    
    subjects = [
        "Meeting notes", 
        "Project update", 
        "Important: Please review", 
        "Weekly report",
        "Contract for review",
        "Legal question about project",
        "Urgent: System outage reported"
    ]
    
    # Generate emails with random properties
    for i in range(num_emails):
        msg = email.message.EmailMessage()
        
        # Create a random date within the last 30 days
        random_days = random.randint(0, 30)
        random_hours = random.randint(0, 23)
        date = datetime.now() - timedelta(days=random_days, hours=random_hours)
        
        sender = random.choice(senders)
        receiver = random.choice([s for s in senders if s != sender])
        subject = random.choice(subjects)
        message_id = f"<{int(time.time())}.{i}.{hash(sender)}@example.com>"
        
        # Add some keywords from config occasionally
        content = f"This is email #{i+1} in the sample mbox file.\n\n"
        if random.random() < 0.3 and config.KEYWORDS:
            keyword = random.choice(config.KEYWORDS)
            content += f"This email contains the keyword: {keyword}.\n"
            subject = f"{subject} [{keyword}]" if random.random() < 0.5 else subject
        
        # Add some thread references occasionally
        if i > 0 and random.random() < 0.4:
            # Reference an earlier email
            ref_idx = random.randint(0, i-1)
            ref_id = f"<{int(time.time())}.{ref_idx}.{hash(sender)}@example.com>"
            msg["References"] = ref_id
            subject = f"Re: {subject}" if random.random() < 0.8 else subject
        
        msg["From"] = sender
        msg["To"] = receiver
        msg["Subject"] = subject
        msg["Date"] = formatdate(time.mktime(date.timetuple()))
        msg["Message-ID"] = message_id
        msg.set_content(content)
        
        mb.add(msg)
    
    mb.unlock()
    mb.close()
    
    print(f"Created sample mbox file with {num_emails} emails: {mbox_path}")
    return mbox_path

def create_sample_image(data_dir, filename):
    """Create a simple sample image (placeholder - simply creates an empty file)."""
    # Note: To create actual images, we'd need a library like PIL/Pillow
    # For simplicity, we'll just create placeholder files
    image_path = data_dir / filename
    
    with open(image_path, 'w') as f:
        f.write("This is a placeholder for a sample image file.")
    
    print(f"Created placeholder image file: {image_path}")
    return image_path

def create_sample_pdf(data_dir, filename):
    """Create a simple sample PDF (placeholder - simply creates an empty file)."""
    # Note: To create actual PDFs, we'd need a library like reportlab
    # For simplicity, we'll just create placeholder files
    pdf_path = data_dir / filename
    
    with open(pdf_path, 'w') as f:
        f.write("This is a placeholder for a sample PDF file.")
    
    print(f"Created placeholder PDF file: {pdf_path}")
    return pdf_path

def main():
    print("Creating sample data for Stone Email & Image Processor...")
    
    data_dir = Path(config.MBOX_DIRECTORY)
    data_dir.mkdir(exist_ok=True)
    
    # Create mbox files
    create_sample_mbox("sample1.mbox", 15)
    create_sample_mbox("sample2.mbox", 10)
    
    # Create placeholder image files
    for i in range(1, 4):
        create_sample_image(data_dir, f"sample{i}.jpg")
    
    # Create placeholder PDF files
    for i in range(1, 3):
        create_sample_pdf(data_dir, f"sample{i}.pdf")
    
    print(f"\nSample data creation complete. Files are in: {data_dir}")
    print("Run the application using: python main.py")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
