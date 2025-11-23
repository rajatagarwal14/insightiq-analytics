# InsightIQ Analytics by Black Lab AI

![InsightIQ Analytics](https://img.shields.io/badge/AI-Business%20Intelligence-06b6d4)
![Python](https://img.shields.io/badge/Python-3.9+-blue)
![Status](https://img.shields.io/badge/Status-Production%20Ready-success)

## 🚀 AI-Powered Business Intelligence Platform

Transform your data into actionable insights with AI-powered analysis. Upload any Excel or CSV file and get intelligent visualizations, executive summaries, and data-driven recommendations in seconds.

### ✨ Features

- **🤖 AI-Powered Analysis**: Advanced LLM-driven insights using Groq API
- **📊 Smart Chart Generation**: Automatically selects the best visualizations
- **📈 Executive Insights**: C-level summaries and actionable recommendations
- **🎯 Pattern Detection**: Identifies trends, anomalies, and correlations
- **♿ Accessible Design**: Grandmother-friendly charts with large fonts and annotations
- **🔄 Multi-Format Support**: Excel (xls, xlsx, xlsm, xlsb), CSV, ODS files
- **🛡️ Graceful Fallbacks**: Works even when AI rate limits are hit

### 🎨 Design Philosophy

**Distinct Cyan Tech Theme** - Unlike our purple wellness-focused MindWell AI, InsightIQ features a professional cyan/turquoise color scheme designed for business intelligence and data analysis.

### 🏗️ Technology Stack

- **Backend**: Python Flask
- **AI**: Groq API (llama-3.3-70b-versatile)
- **Data Science**: Pandas, NumPy, Matplotlib, Seaborn, Scikit-learn
- **Deployment**: Render (PaaS)

### 📦 Deployment Instructions

#### Option 1: Render Dashboard (Recommended)

1. **Push to GitHub**:
   ```bash
   cd /Users/rajat/Downloads/insightiq-analytics
   git init
   git add .
   git commit -m "Initial commit - InsightIQ Analytics"
   git remote add origin YOUR_GITHUB_REPO_URL
   git push -u origin main
   ```

2. **Deploy on Render**:
   - Go to [render.com/dashboard](https://dashboard.render.com/)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Render will auto-detect settings from `render.yaml`
   - Click "Create Web Service"
   - Your app will be live at: `https://insightiq-analytics.onrender.com`

#### Option 2: Render Blueprint

```bash
# Deploy directly using render.yaml
render deploy --blueprint render.yaml
```

### 🌐 Environment Variables

The app requires the following environment variable:

- `GROQ_API_KEY`: Your Groq API key (already configured in render.yaml)

### 🔗 Black Lab AI Apps Portfolio

This is part of the **Black Lab AI Apps** portfolio:

- **MindWell AI** (🧠): AI-powered mental wellness companion
- **InsightIQ Analytics** (📊): AI-driven business intelligence platform

Visit our landing page: `/blacklab-ai-apps/index.html`

### 📊 System Architecture

```
User Upload → Flask API → Data Cleaning → AI Analysis → Chart Generation → HTML Report
                ↓
         Groq API (LLM)
                ↓
        Smart Fallbacks (if rate limited)
```

### 🎯 AI Features

1. **Smart Chart Selection**: AI analyzes data structure and recommends optimal visualizations
2. **Executive Insights**: Generates business-focused interpretations
3. **Data Quality Assessment**: Automatic completeness and consistency checks
4. **Format Correction**: Fixes common data issues (currency symbols, percentages, etc.)

### 🔒 Security & Privacy

- No data is stored permanently
- All processing happens in-memory
- Files are discarded after analysis
- CORS enabled for frontend integration

### 🎨 Brand Colors

- **Primary**: #06b6d4 (Cyan 500)
- **Secondary**: #0891b2 (Cyan 600)
- **Accent**: #f0fdff (Cyan 50)

### 📞 Support

Part of Black Lab AI - Advanced AI Solutions
- Website: [blacklabai.com](https://blacklabai.com)
- Apps Portfolio: [Apps Landing Page](/blacklab-ai-apps/index.html)

---

**Built with ❤️ by Black Lab AI** | Powered by Advanced AI Technology
