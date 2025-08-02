# Open Deep Think - Streamlit Frontend

A beautiful, interactive web interface for the Open Deep Think API built with Streamlit.

## Features

### 🎨 **Beautiful UI**
- Modern, responsive design with gradient headers
- Real-time thinking process visualization
- Interactive charts and metrics
- Clean, intuitive interface

### 🧠 **Deep Think Integration**
- Full integration with Deep Think API
- Configurable thinking parameters (paths, top-k, timeout)
- Real-time status monitoring
- Service health checks

### 📊 **Rich Visualizations**
- Thinking process metrics and gauges
- Execution time visualization
- Success rate and confidence indicators
- Interactive evaluation charts

### 🔍 **Detailed Results**
- Complete pipeline breakdown (Plan → Think → Critique → Refine)
- Individual candidate analysis
- Scoring matrices and evaluations
- Synthesis process transparency

### 📚 **Session Management**
- Query history with timestamps
- Previous results browsing
- Persistent session state
- Quick access to past queries

## Quick Start

### 1. Start the Backend
First, make sure your Deep Think API backend is running:
```bash
# In terminal 1
source venv/bin/activate
python scripts/start_server.py
```

### 2. Start the Frontend
```bash
# In terminal 2 (new terminal)
source venv/bin/activate
python scripts/start_frontend.py
```

### 3. Open Your Browser
The frontend will automatically open at: **http://localhost:8501**

## Usage Guide

### 🏁 **Getting Started**
1. **Service Status**: Check the sidebar for service health (should show ✅ Healthy)
2. **Configuration**: Adjust thinking parameters in the sidebar
3. **Ask Questions**: Type your question in the main text area
4. **Think Deep**: Click the "🧠 Think Deep" button
5. **Explore Results**: Review the answer and detailed breakdown

### ⚙️ **Configuration Options**

| Setting | Description | Range | Default |
|---------|-------------|-------|---------|
| **API Endpoint** | Backend API URL | URL | `http://localhost:8000` |
| **Thinking Paths** | Parallel reasoning paths | 1-16 | 8 |
| **Top Candidates** | Final synthesis candidates | 1-10 | 3 |
| **Timeout** | Maximum processing time | 30-300s | 120s |

### 💡 **Example Questions**

**Mathematical Reasoning:**
- "Prove that the square root of 2 is irrational"
- "Explain the Basel problem and its solution"

**Scientific Concepts:**
- "How does quantum entanglement work?"
- "What causes the greenhouse effect?"

**Problem Solving:**
- "Design a fair voting system for online communities"
- "How would you approach solving traffic congestion in cities?"

**Creative Thinking:**
- "What are innovative ways to reduce plastic waste?"
- "How might we reimagine education for the digital age?"

## Interface Overview

### 📊 **Main Dashboard**
- **Query Input**: Large text area for your questions
- **Action Buttons**: Think Deep, Clear
- **Answer Display**: Primary response from Deep Think
- **Thinking Visualization**: Real-time metrics and progress

### 📈 **Metrics Panel**
- **Thinking Paths**: Number of parallel reasoning attempts
- **Success Rate**: Percentage of successful candidates
- **Top Candidates**: Final synthesis input count
- **Confidence**: Overall answer confidence level
- **Execution Time**: Visual gauge of processing time

### 🔍 **Detailed Results Tabs**
1. **📋 Plan**: Query analysis and approach planning
2. **💭 Candidates**: Individual thinker results and reasoning
3. **📊 Critique**: Evaluation scores and rankings
4. **✨ Synthesis**: Final answer composition process

### 📚 **History Panel**
- **Recent Queries**: Last 10 questions with timestamps
- **Quick Access**: Click to expand previous results
- **Metadata**: Execution stats for each query

## Troubleshooting

### Common Issues

**❌ "Service Offline" Status**
- Ensure backend is running: `python scripts/start_server.py`
- Check API endpoint in sidebar settings
- Verify port 8000 is not blocked

**⚠️ "Service Degraded" Status**
- API key might be invalid or expired  
- Check backend logs for Gemini API errors
- Health check may be failing temporarily

**🐌 Slow Response Times**
- Reduce number of thinking paths (try 4-6 instead of 8)
- Decrease timeout if needed
- Check network connectivity

**🔄 Frontend Won't Start**
- Install dependencies: `pip install -r frontend/requirements.txt`
- Ensure virtual environment is activated
- Check if port 8501 is available

### Debug Mode

For detailed debugging:
1. Check backend logs in the server terminal
2. Open browser developer tools (F12)
3. Monitor network requests in the Network tab
4. Check console for JavaScript errors

## Advanced Features

### 🎯 **API Configuration**
- **Custom Endpoints**: Point to different backend instances
- **Load Balancing**: Switch between multiple backend servers
- **Development Mode**: Connect to localhost vs production

### 📊 **Data Export**
- Results can be copied from the interface
- JSON responses available in detailed view
- History can be manually saved

### 🔧 **Customization**
- Modify `streamlit_app.py` for custom themes
- Adjust visualization charts in the plotting sections
- Extend with additional metrics or visualizations

## Technical Details

### Architecture
- **Frontend**: Streamlit Python web app
- **Communication**: HTTP REST API calls to backend
- **Visualization**: Plotly charts and Streamlit components
- **State Management**: Streamlit session state

### Dependencies
- `streamlit>=1.28.0` - Web framework
- `requests>=2.31.0` - HTTP client
- `plotly>=5.17.0` - Interactive charts
- `pandas>=2.1.0` - Data manipulation

### Performance
- **Latency**: ~100ms UI overhead + backend processing time
- **Concurrency**: Single user per session (standard Streamlit)
- **Memory**: ~50MB base + data for visualizations
- **Scalability**: Can run multiple instances on different ports

## Development

### Local Development
```bash
# Install in development mode
pip install -e .

# Start with auto-reload
streamlit run frontend/streamlit_app.py --server.runOnSave true
```

### Customization
- **Styling**: Modify CSS in the `st.markdown()` calls
- **Layout**: Adjust column widths and component placement
- **Features**: Add new tabs, metrics, or visualizations
- **API Integration**: Extend with additional backend endpoints

## Support

For issues or questions:
1. Check backend server status and logs
2. Verify API connectivity with CLI tool: `python scripts/cli_test.py health`
3. Review browser console for JavaScript errors
4. Ensure all dependencies are installed correctly

---

🎨 **Enjoy your beautiful Deep Think experience!** 🧠