"""
File Upload Page
================
Upload and manage your data files.
"""

import streamlit as st
import httpx
import pandas as pd
from datetime import datetime
import os

st.set_page_config(page_title="Upload Files", page_icon="📁", layout="wide")

# Backend API URL
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def init_session_state():
    """Initialize session state."""
    if "session_id" not in st.session_state:
        import uuid
        st.session_state.session_id = str(uuid.uuid4())
    
    if "uploaded_files_info" not in st.session_state:
        st.session_state.uploaded_files_info = []


def upload_file_to_backend(file) -> dict:
    """Upload a file to the backend API."""
    try:
        files = {'file': (file.name, file.getvalue(), file.type or 'application/octet-stream')}
        data = {'session_id': st.session_state.session_id}
        
        response = httpx.post(
            f"{BACKEND_URL}/api/v1/upload",
            files=files,
            data=data,
            timeout=60.0
        )
        
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {"success": False, "error": response.text}
            
    except httpx.ConnectError:
        return {"success": False, "error": "Cannot connect to backend. Is it running?"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def fetch_uploaded_files() -> list:
    """Fetch list of uploaded files from backend."""
    try:
        response = httpx.get(
            f"{BACKEND_URL}/api/v1/files",
            params={"session_id": st.session_state.session_id},
            timeout=30.0
        )
        if response.status_code == 200:
            return response.json().get("files", [])
        return []
    except:
        return []


def delete_file_from_backend(file_id: str) -> dict:
    """Delete a file from the backend API."""
    try:
        response = httpx.delete(
            f"{BACKEND_URL}/api/v1/files/{file_id}",
            timeout=30.0
        )
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {"success": False, "error": response.text}
    except httpx.ConnectError:
        return {"success": False, "error": "Cannot connect to backend. Is it running?"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    init_session_state()
    
    # Header
    st.markdown("# Upload Your Data Files")
    st.markdown("Upload CSV or Excel files to analyze. We'll automatically detect schemas and time periods.")
    
    st.divider()
    
    # Two columns layout for UPLOAD only
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # File uploader
        st.markdown("### Upload New Files")
        
        uploaded_files = st.file_uploader(
            "Drag and drop files here",
            type=["csv", "xlsx", "xls"],
            accept_multiple_files=True,
            help="Supported formats: CSV, Excel (.xlsx, .xls)"
        )
        
        if uploaded_files:
            st.markdown("---")
            st.markdown("### 📋 Processing Files...")
            
            progress_bar = st.progress(0)
            
            for i, file in enumerate(uploaded_files):
                progress = (i + 1) / len(uploaded_files)
                progress_bar.progress(progress)
                
                with st.container():
                    col_a, col_b = st.columns([3, 1])
                    
                    with col_a:
                        st.markdown(f"**{file.name}**")
                    
                    with col_b:
                        with st.spinner("Uploading..."):
                            result = upload_file_to_backend(file)
                        
                        if result["success"]:
                            st.success("✓ Done")
                        else:
                            st.error(f"✗ Failed: {result['error'][:50]}")
                
                # Show file details in expander (outside columns context to avoid nesting issues)
                if result.get("success"):
                    file_info = result["data"]["file"]
                    with st.expander(f"📄 {file.name} - Details"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Rows", file_info.get("row_count", 0))
                        with col2:
                            st.metric("Columns", file_info.get("column_count", 0))
                        with col3:
                            st.metric("Period", file_info.get("time_period", "N/A"))
                        
                        st.markdown("**Columns Detected:**")
                        
                        # Numeric columns
                        numeric = file_info.get("numeric_columns", [])
                        if numeric:
                            st.markdown(f"📊 **Numeric:** `{', '.join(numeric)}`")
                        
                        # Categorical columns  
                        categorical = file_info.get("categorical_columns", [])
                        if categorical:
                            st.markdown(f"🏷️ **Categorical:** `{', '.join(categorical)}`")
                        
                        # Date columns
                        dates = file_info.get("date_columns", [])
                        if dates:
                            st.markdown(f"📅 **Date:** `{', '.join(dates)}`")
            
            progress_bar.empty()
            st.success(f"✅ Uploaded {len(uploaded_files)} file(s) successfully!")
    
    with col2:
        # Session info
        st.markdown("### 📊 Session Info")
        
        st.markdown(f"**Session ID:**")
        st.code(st.session_state.session_id[:16] + "...")
        
        # Fetch and show uploaded files
        files = fetch_uploaded_files()
        
        st.metric("Files Uploaded", len(files))
        
        if files:
            st.markdown("---")
            st.markdown("### 📂 Your Files")
            
            for f in files:
                with st.container():
                    # Use a simple layout without nested columns if inside a column already
                    # OR move this section out of 'col2' entirely
                    
                    # Fix: Use st.write with columns only if we are at root level
                    # Since we are inside col2, let's use a simpler layout:
                    
                    st.markdown(f"**📄 {f.get('filename')}**")
                    st.caption(f"📅 {f.get('time_period', 'Unknown')} • {f.get('row_count', 0)} rows")
                    
                    if st.button("🗑️", key=f"del_{f['id']}"):
                        delete_file_from_backend(f['id'])
                        st.rerun()
                    
                    st.divider()
        else:
            st.info("Upload files to start analyzing")
    
    # Sidebar info
    with st.sidebar:
        st.markdown("### Tips")
        st.markdown("""
        **Best Practices:**
        - Use descriptive filenames with dates (e.g., `sales_nov_2024.csv`)
        - Ensure consistent column names across files
        - Clean data before uploading (remove empty rows)
        
        **Supported Formats:**
        - CSV (comma-separated)
        - Excel (.xlsx, .xls)
        
        **Time Period Detection:**
        We auto-detect periods from filenames:
        - `nov_2024` → November 2024
        - `Q1_2025` → Q1 2025
        - `2024` → Year 2024
        """)
        
        st.markdown("---")
        
        # Backend status
        st.markdown("### 🔗 Backend Status")
        try:
            health = httpx.get(f"{BACKEND_URL}/health", timeout=5.0)
            if health.status_code == 200:
                st.success("✅ Connected")
            else:
                st.warning("⚠️ Unhealthy")
        except:
            st.error("❌ Disconnected")


if __name__ == "__main__":
    main()
