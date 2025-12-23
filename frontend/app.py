"""
Talk to Your Data - Main Application
=====================================
A conversational analytics platform powered by LangGraph.
"""

import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Talk to Your Data",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better styling
st.markdown("""
<style>
    /* Main container */
    .main {
        padding: 1rem 2rem;
    }
    
    /* Headers */
    h1 {
        color: #1E88E5;
        font-weight: 700;
    }
    
    /* Cards */
    .stCard {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    
    /* Buttons */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
    }
    
    /* Chat messages */
    .stChatMessage {
        border-radius: 12px;
        margin: 0.5rem 0;
    }
    
    /* File uploader */
    [data-testid="stFileUploader"] {
        border: 2px dashed #1E88E5;
        border-radius: 12px;
        padding: 1rem;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    }
    
    /* Success/Error boxes */
    .stSuccess, .stError, .stWarning, .stInfo {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    if "session_id" not in st.session_state:
        import uuid
        st.session_state.session_id = str(uuid.uuid4())
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "uploaded_files_count" not in st.session_state:
        st.session_state.uploaded_files_count = 0


def main():
    init_session_state()
    
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("# 💬 Talk to Your Data")
        st.markdown("*AI-powered conversational analytics for your spreadsheets*")
    
    with col2:
        st.markdown("### ")
        st.caption(f"Session: `{st.session_state.session_id[:8]}...`")
    
    st.divider()
    
    # Main content - Feature cards
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 📁 Upload Files")
        st.markdown("""
        Upload your CSV or Excel files. We'll automatically:
        - Extract column types
        - Detect time periods
        - Prepare data for analysis
        """)
        if st.button("Go to Upload →", key="btn_upload", use_container_width=True):
            st.switch_page("pages/1_📁_Upload.py")
    
    with col2:
        st.markdown("### 💬 Chat with Data")
        st.markdown("""
        Ask questions in natural language:
        - "Average revenue by region"
        - "Compare Nov vs Dec sales"
        - "Top 5 products by units"
        """)
        if st.button("Go to Chat →", key="btn_chat", use_container_width=True):
            st.switch_page("pages/2_💬_Chat.py")
    
    with col3:
        st.markdown("### 📊 View Analysis")
        st.markdown("""
        Review your analysis history:
        - Generated insights
        - Data visualizations
        - Export results
        """)
        if st.button("Go to Analysis →", key="btn_analysis", use_container_width=True):
            st.switch_page("pages/3_📊_Analysis.py")
    
    st.divider()
    
    # How it works section
    st.markdown("## 🔄 How It Works")
    
    cols = st.columns(5)
    steps = [
        ("1️⃣", "Upload", "Upload CSV/Excel files"),
        ("2️⃣", "Parse", "Auto-detect schema"),
        ("3️⃣", "Ask", "Ask in natural language"),
        ("4️⃣", "Analyze", "AI generates code"),
        ("5️⃣", "Insights", "Get results & charts"),
    ]
    
    for col, (icon, title, desc) in zip(cols, steps):
        with col:
            st.markdown(f"### {icon}")
            st.markdown(f"**{title}**")
            st.caption(desc)
    
    st.divider()
    
    # Example queries
    st.markdown("## 🎯 Example Queries You Can Ask")
    
    examples = [
        "What is the average revenue by region?",
        "Show me the top 5 products by total units sold",
        "Compare revenue between November and December 2024",
        "What's the total discount given per product category?",
        "Which region has the highest growth rate?",
    ]
    
    for i, example in enumerate(examples):
        st.code(example, language=None)
    
    # Footer
    st.divider()
    st.caption("Built with ❤️ using Streamlit, FastAPI, LangGraph, and GPT-4")


if __name__ == "__main__":
    main()
