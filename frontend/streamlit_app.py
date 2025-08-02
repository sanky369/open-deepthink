"""
Streamlit frontend for Open Deep Think API.
"""
import streamlit as st
import requests
import json
import time
from typing import Dict, Any, Optional
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import pandas as pd

# Page configuration
st.set_page_config(
    page_title="Open Deep Think",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 1rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .subtitle {
        text-align: center;
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    
    .thinking-paths {
        display: flex;
        justify-content: space-around;
        margin: 1rem 0;
    }
    
    .thinking-path {
        background: #f0f2f6;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem;
        border-left: 4px solid #667eea;
    }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    
    .status-healthy { color: #28a745; }
    .status-degraded { color: #ffc107; }
    .status-unhealthy { color: #dc3545; }
</style>
""", unsafe_allow_html=True)

class DeepThinkAPI:
    """API client for Open Deep Think service."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
    
    def health_check(self, detailed: bool = True) -> Dict[str, Any]:
        """Check service health."""
        try:
            params = {"check_api": "false", "include_details": str(detailed).lower()}
            response = requests.get(f"{self.base_url}/health", params=params, timeout=10)
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def think(self, query: str, n_paths: int = 8, top_k: int = 3, timeout: int = 120) -> Dict[str, Any]:
        """Send query to Deep Think pipeline."""
        try:
            payload = {
                "query": query,
                "n_paths": n_paths,
                "top_k": top_k,
                "timeout": timeout
            }
            
            response = requests.post(
                f"{self.base_url}/think",
                json=payload,
                timeout=timeout + 30
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                return {"success": False, "error": f"HTTP {response.status_code}", "details": error_data}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_info(self) -> Dict[str, Any]:
        """Get service information."""
        try:
            response = requests.get(f"{self.base_url}/info", timeout=10)
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

def init_session_state():
    """Initialize session state variables."""
    if 'api_client' not in st.session_state:
        st.session_state.api_client = DeepThinkAPI()
    if 'thinking_history' not in st.session_state:
        st.session_state.thinking_history = []
    if 'current_thinking' not in st.session_state:
        st.session_state.current_thinking = False

def display_header():
    """Display the main header."""
    st.markdown('<h1 class="main-header">🧠 Open Deep Think</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Parallel reasoning AI powered by Gemini 2.5 Pro</p>', unsafe_allow_html=True)

def display_service_status():
    """Display service status in sidebar."""
    st.sidebar.markdown("### 🏥 Service Status")
    
    with st.spinner("Checking service health..."):
        health_result = st.session_state.api_client.health_check()
    
    if health_result["success"]:
        status = health_result["data"].get("status", "unknown")
        timestamp = health_result["data"].get("timestamp", "")
        
        if status == "healthy":
            st.sidebar.markdown('<span class="status-healthy">✅ Healthy</span>', unsafe_allow_html=True)
        elif status == "degraded":
            st.sidebar.markdown('<span class="status-degraded">⚠️ Degraded</span>', unsafe_allow_html=True)
        else:
            st.sidebar.markdown('<span class="status-unhealthy">❌ Unhealthy</span>', unsafe_allow_html=True)
        
        if timestamp:
            st.sidebar.caption(f"Last checked: {timestamp[:19]}")
    else:
        st.sidebar.markdown('<span class="status-unhealthy">❌ Offline</span>', unsafe_allow_html=True)
        st.sidebar.caption(f"Error: {health_result['error']}")

def display_configuration_panel():
    """Display configuration options in sidebar."""
    st.sidebar.markdown("### ⚙️ Configuration")
    
    # API endpoint configuration
    api_url = st.sidebar.text_input(
        "API Endpoint",
        value="http://localhost:8000",
        help="Base URL of the Open Deep Think API"
    )
    
    if api_url != st.session_state.api_client.base_url:
        st.session_state.api_client = DeepThinkAPI(api_url)
    
    st.sidebar.markdown("### 🧠 Thinking Parameters")
    
    # Thinking parameters
    n_paths = st.sidebar.slider(
        "Thinking Paths",
        min_value=1,
        max_value=16,
        value=8,
        help="Number of parallel reasoning paths"
    )
    
    top_k = st.sidebar.slider(
        "Top Candidates",
        min_value=1,
        max_value=min(10, n_paths),
        value=min(3, n_paths),
        help="Number of top candidates to refine"
    )
    
    timeout = st.sidebar.slider(
        "Timeout (seconds)",
        min_value=30,
        max_value=960,
        value=300,
        help="Maximum processing time"
    )
    
    return n_paths, top_k, timeout

def display_thinking_visualization(metadata: Dict[str, Any]):
    """Display thinking process visualization."""
    st.markdown("### 🔄 Thinking Process")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Thinking Paths",
            metadata.get("n_paths", 0),
            help="Number of parallel reasoning paths generated"
        )
    
    with col2:
        candidates_generated = metadata.get("candidates_generated", 0)
        candidates_failed = metadata.get("candidates_failed", 0)
        success_rate = (candidates_generated / (candidates_generated + candidates_failed) * 100) if (candidates_generated + candidates_failed) > 0 else 0
        st.metric(
            "Success Rate",
            f"{success_rate:.1f}%",
            help="Percentage of successful thinking paths"
        )
    
    with col3:
        st.metric(
            "Top Candidates Used",
            metadata.get("top_k_used", 0),
            help="Number of top candidates used for final synthesis"
        )
    
    with col4:
        confidence = metadata.get("confidence_level", "unknown")
        confidence_color = {
            "high": "🟢", "medium": "🟡", "low": "🔴"
        }.get(confidence.lower(), "⚪")
        st.metric(
            "Confidence",
            f"{confidence_color} {confidence.title()}",
            help="Overall confidence in the final answer"
        )
    
    # Execution time chart
    if "execution_time_seconds" in metadata:
        exec_time = metadata["execution_time_seconds"]
        
        # Create a simple progress visualization
        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = exec_time,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Execution Time (seconds)"},
            gauge = {
                'axis': {'range': [None, 180]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 30], 'color': "lightgray"},
                    {'range': [30, 90], 'color': "gray"},
                    {'range': [90, 180], 'color': "darkgray"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 120
                }
            }
        ))
        
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

def display_detailed_results(detailed_results: Dict[str, Any]):
    """Display detailed pipeline results."""
    if not detailed_results:
        return
    
    st.markdown("### 🔍 Detailed Results")
    
    tabs = st.tabs(["📋 Plan", "💭 Candidates", "📊 Critique", "✨ Synthesis"])
    
    with tabs[0]:  # Plan
        if "plan" in detailed_results:
            plan = detailed_results["plan"]["plan"]
            st.markdown("#### Planning Stage")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Task:**")
                st.info(plan.get("task", "N/A"))
                
                st.markdown("**Key Aspects:**")
                aspects = plan.get("key_aspects", [])
                for aspect in aspects:
                    st.markdown(f"• {aspect}")
            
            with col2:
                st.markdown("**Reasoning Type:**")
                st.code(plan.get("reasoning_type", "N/A"))
                
                st.markdown("**Complexity Level:**")
                st.code(plan.get("complexity_level", "N/A"))
                
                st.markdown("**Thinking Budget:**")
                st.code(f"{plan.get('thinking_budget', 0)} steps")
    
    with tabs[1]:  # Candidates
        if "candidates" in detailed_results:
            candidates = detailed_results["candidates"]
            st.markdown(f"#### Generated Candidates ({len(candidates)})")
            
            for i, candidate in enumerate(candidates):
                with st.expander(f"🤖 Thinker {candidate.get('agent_id', i)} - {candidate.get('approach', 'Unknown approach')}"):
                    
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.markdown("**Reasoning Steps:**")
                        thoughts = candidate.get("thoughts", [])
                        for j, thought in enumerate(thoughts, 1):
                            st.markdown(f"{j}. {thought}")
                    
                    with col2:
                        st.markdown("**Confidence:**")
                        st.code(candidate.get("confidence", "unknown"))
                        
                        st.markdown("**Issues:**")
                        issues = candidate.get("potential_issues", [])
                        if issues:
                            for issue in issues:
                                st.warning(issue)
                        else:
                            st.success("No issues identified")
                    
                    st.markdown("**Final Answer:**")
                    st.success(candidate.get("answer", "No answer provided"))
    
    with tabs[2]:  # Critique
        if "critique" in detailed_results:
            critique = detailed_results["critique"]
            st.markdown("#### Critique & Ranking")
            
            evaluations = critique.get("evaluations", [])
            if evaluations:
                # Create scoring table
                scores_data = []
                for eval_item in evaluations:
                    agent_id = eval_item.get("agent_id", "unknown")
                    scores = eval_item.get("scores", {})
                    total_score = eval_item.get("total_score", 0)
                    
                    scores_data.append({
                        "Agent": f"Thinker {agent_id}",
                        "Correctness": scores.get("correctness", 0),
                        "Completeness": scores.get("completeness", 0),
                        "Clarity": scores.get("clarity", 0),
                        "Insight": scores.get("insight", 0),
                        "Evidence": scores.get("evidence", 0),
                        "Total": total_score
                    })
                
                df = pd.DataFrame(scores_data)
                st.dataframe(df, use_container_width=True)
                
                # Visualization
                fig = px.bar(
                    df.melt(id_vars=["Agent"], 
                           value_vars=["Correctness", "Completeness", "Clarity", "Insight", "Evidence"],
                           var_name="Criteria", value_name="Score"),
                    x="Agent", y="Score", color="Criteria",
                    title="Evaluation Scores by Criteria"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Overall assessment
            st.markdown("**Overall Assessment:**")
            st.info(critique.get("overall_assessment", "No assessment available"))
    
    with tabs[3]:  # Synthesis
        if "synthesis" in detailed_results:
            synthesis = detailed_results["synthesis"]
            st.markdown("#### Synthesis Process")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Synthesis Approach:**")
                st.info(synthesis.get("synthesis_approach", "N/A"))
                
                st.markdown("**Improvements Made:**")
                improvements = synthesis.get("improvements_made", [])
                for improvement in improvements:
                    st.markdown(f"• {improvement}")
            
            with col2:
                st.markdown("**Sources Used:**")
                sources = synthesis.get("sources_used", [])
                for source in sources:
                    agent_id = source.get("agent_id", "unknown")
                    weight = source.get("contribution_weight", "medium")
                    weight_emoji = {"high": "🔥", "medium": "🔸", "low": "🔹"}.get(weight, "🔸")
                    st.markdown(f"{weight_emoji} **Thinker {agent_id}** ({weight} contribution)")
                    
                    elements = source.get("elements_borrowed", [])
                    for element in elements:
                        st.markdown(f"  - {element}")

def display_history():
    """Display thinking history."""
    if not st.session_state.thinking_history:
        st.info("No previous questions asked yet. Start by asking a question above!")
        return
    
    st.markdown("### 📚 History")
    
    for i, entry in enumerate(reversed(st.session_state.thinking_history[-10:])):  # Show last 10
        with st.expander(f"🕐 {entry['timestamp']} - {entry['query'][:50]}{'...' if len(entry['query']) > 50 else ''}"):
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown("**Answer:**")
                st.markdown(entry['answer'])
            
            with col2:
                st.markdown("**Metadata:**")
                st.json({
                    "paths": entry['metadata'].get('n_paths'),
                    "time": f"{entry['metadata'].get('execution_time_seconds', 0):.1f}s",
                    "confidence": entry['metadata'].get('confidence_level')
                })

def main():
    """Main Streamlit application."""
    init_session_state()
    display_header()
    
    # Sidebar
    display_service_status()
    n_paths, top_k, timeout = display_configuration_panel()
    
    # Main content
    st.markdown("### 💭 Ask Deep Think")
    
    # Query input
    query = st.text_area(
        "Enter your question:",
        height=100,
        placeholder="Ask me anything! For example:\n• Explain quantum entanglement\n• How would you solve climate change?\n• What's the best approach to learn machine learning?",
        help="Type your question here. Deep Think will generate multiple reasoning paths and synthesize the best answer."
    )
    
    # Action buttons
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        think_button = st.button("🧠 Think Deep", type="primary", disabled=st.session_state.current_thinking or not query.strip())
    
    with col2:
        clear_button = st.button("🗑️ Clear", disabled=st.session_state.current_thinking)
    
    if clear_button:
        st.rerun()
    
    # Process thinking request
    if think_button and query.strip():
        st.session_state.current_thinking = True
        
        with st.spinner("🧠 Deep Think is processing your query..."):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Simulate progress updates
            for i in range(100):
                time.sleep(0.05)  # Small delay for visual effect
                progress_bar.progress(i + 1)
                
                if i < 20:
                    status_text.text("📋 Planning the approach...")
                elif i < 60:
                    status_text.text(f"💭 Generating {n_paths} parallel thinking paths...")
                elif i < 80:
                    status_text.text("📊 Critiquing and ranking candidates...")
                else:
                    status_text.text("✨ Synthesizing the final answer...")
            
            # Make API call
            result = st.session_state.api_client.think(query, n_paths, top_k, timeout)
        
        st.session_state.current_thinking = False
        progress_bar.empty()
        status_text.empty()
        
        if result["success"]:
            data = result["data"]
            
            # Display main answer
            st.markdown("### 💡 Answer")
            st.markdown(data["answer"])
            
            # Display thinking visualization
            display_thinking_visualization(data["metadata"])
            
            # Display detailed results if available
            if "detailed_results" in data and data["detailed_results"]:
                display_detailed_results(data["detailed_results"])
            
            # Add to history
            st.session_state.thinking_history.append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "query": query,
                "answer": data["answer"],
                "metadata": data["metadata"]
            })
            
            # Success message
            exec_time = data["metadata"].get("execution_time_seconds", 0)
            candidates = data["metadata"].get("candidates_generated", 0)
            st.success(f"✅ Deep Think completed in {exec_time:.1f} seconds with {candidates} thinking paths!")
            
        else:
            st.error(f"❌ Deep Think failed: {result['error']}")
            if "details" in result:
                with st.expander("Error Details"):
                    st.json(result["details"])
    
    # Display history
    if st.session_state.thinking_history:
        st.markdown("---")
        display_history()
    
    # Footer
    st.markdown("---")
    st.markdown(
        "🧠 **Open Deep Think** - Parallel reasoning AI system | "
        "Built with ❤️ using FastAPI, Gemini 2.5 Pro, and Streamlit"
    )

if __name__ == "__main__":
    main()