const recentFiles = [
    { name: "Project_Report.pdf", date: "Sep 20, 2025", type: "pdf" },
    { name: "Design_Specs.png", date: "Sep 19, 2025", type: "image" },
    { name: "Financial_Statement.pdf", date: "Sep 18, 2025", type: "pdf" },
    { name: "Meeting_Notes.pdf", date: "Sep 17, 2025", type: "pdf" },
    { name: "Screenshot_2025.png", date: "Sep 16, 2025", type: "image" },
    { name: "Research_Paper.pdf", date: "Sep 15, 2025", type: "pdf" },
    { name: "Diagram.jpg", date: "Sep 14, 2025", type: "image" }
];

const recentFilesContainer = document.getElementById('recent-files');
const themeToggle = document.getElementById('theme-toggle');
const uploadBtn = document.getElementById('upload-btn');
const fileUpload = document.getElementById('file-upload');

function populateRecentFiles() {
    recentFilesContainer.innerHTML = '';
    recentFiles.forEach(file => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';

        const fileIcon = document.createElement('div');
        fileIcon.className = 'file-icon';

        // Detect PDF or image by extension or MIME type
        if (file.type === 'pdf' || (file.name && file.name.toLowerCase().endsWith('.pdf'))) {
            fileIcon.innerHTML = '<i class="fas fa-file-pdf"></i>';
        } else {
            fileIcon.innerHTML = '<i class="fas fa-file-image"></i>';
        }

        const fileInfo = document.createElement('div');
        fileInfo.className = 'file-info';

        const fileName = document.createElement('div');
        fileName.className = 'file-name';
        fileName.textContent = file.name || 'Unnamed';

        const fileDate = document.createElement('div');
        fileDate.className = 'file-date';
        fileDate.textContent = file.date || '';

        fileInfo.appendChild(fileName);
        fileInfo.appendChild(fileDate);
        fileItem.appendChild(fileIcon);
        fileItem.appendChild(fileInfo);
        recentFilesContainer.appendChild(fileItem);
    });
}

themeToggle.addEventListener('click', () => {
    document.body.classList.toggle('dark-mode');
    const icon = themeToggle.querySelector('i');
    const text = themeToggle.querySelector('span');
    if (document.body.classList.contains('dark-mode')) {
        icon.className = 'fas fa-sun';
        text.textContent = 'Light';
    } else {
        icon.className = 'fas fa-moon';
        text.textContent = 'Dark';
    }
});

// Open file picker when button clicked
uploadBtn.addEventListener('click', () => {
    fileUpload.click();
});

fileUpload.addEventListener('change', (e) => {
    const today = new Date();
    // For each uploaded file: add to recentFiles and re-render
    Array.from(e.target.files).forEach(file => {
        // determine type
        let type = '';
        if (file.type === "application/pdf" || file.name.endsWith('.pdf')) {
            type = 'pdf';
        } else {
            type = 'image'; // basic assumption for demonstration
        }
        recentFiles.unshift({
            name: file.name,
            date: today.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
            type: type
        });
    });
    populateRecentFiles();
});

uploadBtn.addEventListener('keydown', (evt) => {
    if (evt.key === "Enter" || evt.key === " ") {
        fileUpload.click();
    }
});

// Initialize the app
populateRecentFiles();
