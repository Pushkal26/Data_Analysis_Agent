"""
Analysis History Page
=====================
View past analysis results, generated code, and insights.
"""

import streamlit as st
import httpx
import pandas as pd
import plotly.express as px
from datetime import datetime
import os

st.set_page_config(page_title="Analysis History", page_icon="📊", layout="wide")

# Backend API URL
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def init_session_state():
    """Initialize session state."""
    if "session_id" not in st.session_state:
        import uuid
        st.session_state.session_id = str(uuid.uuid4())


def fetch_chat_history() -> list:
    """Fetch chat history from backend."""
    try:
        response = httpx.get(
            f"{BACKEND_URL}/api/v1/chat/history",
            params={"session_id": st.session_state.session_id, "limit": 100},
            timeout=30.0
        )
        if response.status_code == 200:
            return response.json().get("messages", [])
        return []
    except:
        return []


def fetch_analysis_details(analysis_id: int) -> dict:
    """Fetch detailed analysis from backend."""
    try:
        response = httpx.get(
            f"{BACKEND_URL}/api/v1/chat/analysis/{analysis_id}",
            timeout=30.0
        )
        if response.status_code == 200:
            return response.json()
        return {}
    except:
        return {}


def create_chart_from_result(result_data: dict):
    """Create a chart from result data."""
    if not result_data or result_data.get("type") != "dataframe":
        return None
    
    data = result_data.get("data", [])
    if not data:
        return None
    
    df = pd.DataFrame(data)
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
    
    if categorical_cols and numeric_cols:
        fig = px.bar(
            df, x=categorical_cols[0], y=numeric_cols[0],
            color=categorical_cols[0],
            template="plotly_dark"
        )
        return fig
    return None


def main():
    init_session_state()
    
    # Sidebar
    with st.sidebar:
        st.markdown("### 📊 Session")
        st.caption(f"ID: {st.session_state.session_id[:8]}...")
        
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
        
        st.markdown("---")
        
        # Navigation
        st.markdown("### 🧭 Navigation")
        if st.button("📁 Upload Files", use_container_width=True):
            st.switch_page("pages/1_📁_Upload.py")
        if st.button("💬 Chat", use_container_width=True):
            st.switch_page("pages/2_💬_Chat.py")
    
    # Main content
    st.markdown("# 📊 Analysis History")
    st.markdown("Review your past analyses, generated code, and insights.")
    
    st.divider()
    
    # Fetch chat history
    messages = fetch_chat_history()
    
    if not messages:
        st.info("📭 No analysis history yet. Start a conversation in the Chat page!")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("💬 Go to Chat", use_container_width=True, type="primary"):
                st.switch_page("pages/2_💬_Chat.py")
        st.stop()
    
    # Filter to assistant messages with analysis
    analyses = [m for m in messages if m.get("role") == "assistant" and m.get("analysis_id")]
    
    if not analyses:
        st.info("No completed analyses yet. Ask some questions in the Chat!")
        st.stop()
    
    # Stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Analyses", len(analyses))
    with col2:
        st.metric("Total Messages", len(messages))
    with col3:
        # Get latest timestamp
        if analyses:
            latest = analyses[-1].get("created_at", "")[:16]
            st.metric("Latest", latest.replace("T", " ") if latest else "N/A")
    
    st.divider()
    
    # Analysis list
    st.markdown("### 📜 Analysis History")
    
    # Display in reverse chronological order
    for i, msg in enumerate(reversed(analyses)):
        analysis_id = msg.get("analysis_id")
        created_at = msg.get("created_at", "")[:16].replace("T", " ")
        content_preview = msg.get("content", "")[:100] + "..." if len(msg.get("content", "")) > 100 else msg.get("content", "")
        
        with st.expander(f"🔍 Analysis #{analysis_id} - {created_at}", expanded=(i == 0)):
            # Show summary
            st.markdown(f"**Response Preview:**")
            st.markdown(content_preview)
            
            # Fetch and show details
            col1, col2 = st.columns([1, 4])
            
            with col1:
                if st.button("📋 View Full Details", key=f"details_{analysis_id}"):
                    st.session_state[f"show_details_{analysis_id}"] = True
            
            # Show full details if requested
            if st.session_state.get(f"show_details_{analysis_id}", False):
                details = fetch_analysis_details(analysis_id)
                
                if details:
                    st.markdown("---")
                    
                    # Metadata row
                    meta_col1, meta_col2, meta_col3, meta_col4 = st.columns(4)
                    with meta_col1:
                        intent = details.get("intent", "N/A")
                        intent_icons = {"aggregate": "📊", "compare": "⚖️", "query": "🔍", "trend": "📈"}
                        st.markdown(f"**Intent:** {intent_icons.get(intent, '❓')} {intent}")
                    with meta_col2:
                        st.markdown(f"**Type:** {details.get('operation_type', 'N/A')}")
                    with meta_col3:
                        status = details.get("status", "unknown")
                        status_icons = {"completed": "✅", "failed": "❌", "pending": "⏳"}
                        st.markdown(f"**Status:** {status_icons.get(status, '❓')} {status}")
                    with meta_col4:
                        exec_time = details.get("execution_time_ms")
                        st.markdown(f"**Time:** {exec_time:.0f}ms" if exec_time else "**Time:** N/A")
                    
                    st.markdown("---")
                    
                    # Query
                    st.markdown("**📝 Original Query:**")
                    st.info(details.get("user_query", "N/A"))
                    
                    # Files used
                    files_used = details.get("files_used", [])
                    if files_used:
                        st.markdown(f"**📂 Files Used:** `{', '.join(files_used)}`")
                    
                    # Tabs for different views
                    tab1, tab2, tab3, tab4 = st.tabs(["📊 Result", "🐍 Code", "💬 Explanation", "🔍 Debug"])
                    
                    with tab1:
                        result_data = details.get("result_data")
                        if result_data and result_data.get("type") == "dataframe":
                            data = result_data.get("data", [])
                            if data:
                                df = pd.DataFrame(data)
                                
                                # Show chart
                                chart = create_chart_from_result(result_data)
                                if chart:
                                    st.plotly_chart(chart, use_container_width=True)
                                
                                # Show table
                                st.dataframe(df, use_container_width=True, hide_index=True)
                        else:
                            st.info("No tabular result data")
                    
                    with tab2:
                        code = details.get("generated_code")
                        if code:
                            st.code(code, language="python")
                            
                            # Copy button
                            st.download_button(
                                "📋 Download Code",
                                code,
                                file_name=f"analysis_{analysis_id}.py",
                                mime="text/plain"
                            )
                        else:
                            st.info("No code generated")
                    
                    with tab3:
                        explanation = details.get("explanation", "No explanation available")
                        st.markdown(explanation)
                        
                        # Recommendations
                        recs = details.get("recommendations", [])
                        if recs:
                            st.markdown("---")
                            st.markdown("**💡 Recommendations:**")
                            for rec in recs:
                                st.markdown(f"- {rec}")
                    
                    with tab4:
                        st.markdown("**🔍 LangGraph Node Path:**")
                        node_history = details.get("node_history", [])
                        if node_history:
                            st.code(" → ".join(node_history))
                        
                        st.markdown("**📋 Plan:**")
                        plan = details.get("plan")
                        if plan:
                            st.json(plan)
                        
                        if details.get("error_message"):
                            st.error(f"**Error:** {details.get('error_message')}")
                else:
                    st.error("Could not fetch analysis details")
    
    st.divider()
    
    # Export section
    st.markdown("### 📤 Export")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊 Export All Results as CSV", use_container_width=True):
            # Collect all results
            all_data = []
            for msg in analyses:
                analysis_id = msg.get("analysis_id")
                if analysis_id:
                    details = fetch_analysis_details(analysis_id)
                    if details:
                        all_data.append({
                            "id": analysis_id,
                            "query": details.get("user_query"),
                            "intent": details.get("intent"),
                            "status": details.get("status"),
                            "execution_time_ms": details.get("execution_time_ms"),
                            "created_at": details.get("created_at"),
                        })
            
            if all_data:
                df = pd.DataFrame(all_data)
                csv = df.to_csv(index=False)
                st.download_button(
                    "⬇️ Download CSV",
                    csv,
                    file_name="analysis_history.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No data to export")


if __name__ == "__main__":
    main()
