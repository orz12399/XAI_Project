import React, { useState } from 'react';
import './Upload.css';

const Upload = ({ onUpload }) => {
    const [dragActive, setDragActive] = useState(false);

    const handleDrag = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true);
        } else if (e.type === "dragleave") {
            setDragActive(false);
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            onUpload(e.dataTransfer.files[0]);
        }
    };

    const handleChange = (e) => {
        e.preventDefault();
        if (e.target.files && e.target.files[0]) {
            onUpload(e.target.files[0]);
        }
    };

    return (
        <div className="upload-card" onDragEnter={handleDrag}>
            <form className="upload-form" onDragEnter={handleDrag} onDragOver={handleDrag} onDragLeave={handleDrag} onDrop={handleDrop}>
                <input type="file" id="file-upload" multiple={false} onChange={handleChange} accept=".csv, .xlsx, .xls" />
                <label htmlFor="file-upload" className={dragActive ? "drag-active" : ""}>
                    <div>
                        <p>Drag and drop your CSV/Excel file here</p>
                        <p className="or-text">or</p>
                        <button className="upload-button" onClick={(e) => { e.preventDefault(); document.getElementById('file-upload').click() }}>
                            Browse Files
                        </button>
                    </div>
                </label>
            </form>
        </div>
    );
};

export default Upload;
