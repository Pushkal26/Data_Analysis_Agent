"""
Chat Interface Page
===================
Conversational interface to "Talk to Your Data".
"""

import streamlit as st
import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os

st.set_page_config(page_title="Chat with Data", page_icon="💬", layout="wide")

# Backend API URL
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def init_session_state():
    """Initialize session state for chat."""
    if "session_id" not in st.session_state:
        import uuid
        st.session_state.session_id = str(uuid.uuid4())
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "show_code" not in st.session_state:
        st.session_state.show_code = False


def fetch_files_from_backend() -> list:
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


def send_message_to_backend(message: str) -> dict:
    """Send a chat message to the backend API."""
    try:
        response = httpx.post(
            f"{BACKEND_URL}/api/v1/chat",
            json={
                "session_id": st.session_state.session_id,
                "message": message
            },
            timeout=120.0
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"status": "error", "response": f"Error: {response.text}"}
            
    except httpx.ConnectError:
        return {"status": "error", "response": "❌ Cannot connect to backend server."}
    except httpx.ReadTimeout:
        return {"status": "error", "response": "⏱️ Request timed out. Try a simpler query."}
    except Exception as e:
        return {"status": "error", "response": f"Error: {str(e)}"}


def create_chart(result_data: dict, query: str) -> go.Figure:
    """Create an appropriate chart based on the result data."""
    if not result_data or result_data.get("type") != "dataframe":
        return None
    
    data = result_data.get("data", [])
    if not data:
        return None
    
    df = pd.DataFrame(data)
    columns = df.columns.tolist()
    
    # Determine chart type based on data
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
    
    if len(df) <= 10 and len(categorical_cols) >= 1 and len(numeric_cols) >= 1:
        # Bar chart for small grouped data
        x_col = categorical_cols[0]
        y_col = numeric_cols[0]
        
        fig = px.bar(
            df, x=x_col, y=y_col,
            title=f"{y_col} by {x_col}",
            color=x_col,
            template="plotly_dark"
        )
        fig.update_layout(
            showlegend=False,
            xaxis_title=x_col,
            yaxis_title=y_col,
            font=dict(size=12),
        )
        return fig
    
    elif len(df) > 10 and len(numeric_cols) >= 1:
        # Line chart for time series or larger datasets
        if categorical_cols:
            x_col = categorical_cols[0]
        else:
            x_col = df.index
        y_col = numeric_cols[0]
        
        fig = px.line(
            df, x=x_col, y=y_col,
            title=f"{y_col} Trend",
            template="plotly_dark",
            markers=True
        )
        return fig
    
    return None


def render_result_data(result_data: dict, query: str):
    """Render result data with table and chart."""
    if not result_data:
        return
    
    data_type = result_data.get("type")
    
    if data_type == "dataframe":
        data = result_data.get("data", [])
        if data:
            df = pd.DataFrame(data)
            
            # Create tabs for table and chart
            tab1, tab2 = st.tabs(["📊 Chart", "📋 Table"])
            
            with tab1:
                chart = create_chart(result_data, query)
                if chart:
                    st.plotly_chart(chart, use_container_width=True)
                else:
                    st.info("No suitable chart for this data")
            
            with tab2:
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True,
                )
                
    elif data_type == "dict":
        st.json(result_data.get("data", {}))
    elif data_type == "value":
        st.info(f"**Result:** {result_data.get('data')}")


def main():
    init_session_state()
    
    # Fetch files
    files = fetch_files_from_backend()
    
    # Sidebar
    with st.sidebar:
        st.markdown("### 📊 Session Info")
        st.caption(f"ID: {st.session_state.session_id[:8]}...")
        
        st.markdown("---")
        
        # Files info
        st.markdown("### 📂 Your Data Files")
        if files:
            for f in files:
                st.markdown(f"**{f.get('filename')}**")
                st.caption(f"📅 {f.get('time_period', 'N/A')} • {f.get('row_count', 0)} rows")
                st.markdown("")
        else:
            st.warning("No files uploaded")
            if st.button("Upload Files", use_container_width=True):
                st.switch_page("pages/1_📁_Upload.py")
        
        st.markdown("---")
        
        # Settings
        st.markdown("### ⚙️ Settings")
        st.session_state.show_code = st.toggle("Show generated code", value=st.session_state.show_code)
        
        # Clear chat
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        
        st.markdown("---")
        
        # Backend status
        try:
            health = httpx.get(f"{BACKEND_URL}/health", timeout=5.0)
            if health.status_code == 200:
                st.success("✅ Backend connected")
            else:
                st.warning("⚠️ Backend unhealthy")
        except:
            st.error("❌ Backend offline")
    
    # Main content
    st.markdown("# 💬 Talk to Your Data")
    st.markdown("Ask questions about your data in natural language.")
    
    # Check if files are uploaded
    if not files:
        st.warning("⚠️ **No files uploaded yet.** Please upload your data files first.")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("📁 Go to Upload", use_container_width=True, type="primary"):
                st.switch_page("pages/1_📁_Upload.py")
        st.stop()
    
    # File summary
    with st.expander(f"📂 **{len(files)} Data File(s) Available**", expanded=False):
        cols = st.columns(len(files))
        for col, f in zip(cols, files):
            with col:
                st.metric(f.get('filename', 'File')[:20], f.get('time_period', 'N/A'))
                st.caption(f"{f.get('row_count', 0)} rows × {f.get('column_count', 0)} cols")
    
    st.divider()
    
    # Chat container
    chat_container = st.container()
    
    with chat_container:
        # Display chat history
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
                # Show result data if available
                if msg["role"] == "assistant" and msg.get("result_data"):
                    render_result_data(msg.get("result_data"), msg.get("query", ""))
                
                # Show code if enabled
                if msg["role"] == "assistant" and st.session_state.show_code and msg.get("code"):
                    with st.expander("🐍 Generated Code"):
                        st.code(msg["code"], language="python")
                
                # Show recommendations
                if msg["role"] == "assistant" and msg.get("recommendations"):
                    recs = msg.get("recommendations", [])
                    if recs:
                        st.markdown("**💡 Recommendations:**")
                        for rec in recs[:2]:
                            st.markdown(f"- {rec}")
    
    # Quick actions
    st.markdown("### 🎯 Quick Questions")
    quick_cols = st.columns(5)
    quick_questions = [
        "Average revenue by region",
        "Total units sold",
        "Top 5 products",
        "Revenue trend",
        "Compare periods",
    ]
    
    for col, q in zip(quick_cols, quick_questions):
        with col:
            if st.button(q, key=f"quick_{q}", use_container_width=True, disabled=not files):
                # Process this query
                st.session_state.messages.append({
                    "role": "user",
                    "content": q,
                })
                
                with st.spinner("🔍 Analyzing..."):
                    response = send_message_to_backend(q)
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response.get("response", ""),
                    "result_data": response.get("analysis", {}).get("result_data") if response.get("analysis") else None,
                    "recommendations": response.get("analysis", {}).get("recommendations") if response.get("analysis") else [],
                    "code": None,  # Would need to fetch from analysis details
                    "query": q,
                })
                st.rerun()
    
    st.divider()
    
    # Chat input
    if prompt := st.chat_input("Ask a question about your data...", disabled=not files):
        # Add user message
        st.session_state.messages.append({
            "role": "user",
            "content": prompt,
        })
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get response from backend
        with st.chat_message("assistant"):
            with st.spinner("🔍 Analyzing your data..."):
                response = send_message_to_backend(prompt)
            
            response_text = response.get("response", "No response received")
            st.markdown(response_text)
            
            # Show result data
            if response.get("analysis") and response["analysis"].get("result_data"):
                render_result_data(response["analysis"]["result_data"], prompt)
            
            # Show recommendations
            if response.get("analysis") and response["analysis"].get("recommendations"):
                recs = response["analysis"]["recommendations"]
                if recs:
                    st.markdown("**💡 Recommendations:**")
                    for rec in recs[:2]:
                        st.markdown(f"- {rec}")
            
            # Show processing time
            if response.get("processing_time_ms"):
                st.caption(f"⏱️ Processed in {response['processing_time_ms']/1000:.1f}s")
        
        # Add assistant message to history
        st.session_state.messages.append({
            "role": "assistant",
            "content": response_text,
            "result_data": response.get("analysis", {}).get("result_data") if response.get("analysis") else None,
            "recommendations": response.get("analysis", {}).get("recommendations") if response.get("analysis") else [],
            "query": prompt,
        })


if __name__ == "__main__":
    main()
