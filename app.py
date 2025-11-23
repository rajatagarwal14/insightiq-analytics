"""
WORLD-CLASS EXCEL ANALYZER - AI-DRIVEN INSIGHTS ENGINE
=======================================================
This enhanced version uses LLM to intelligently determine:
- What charts to create based on data characteristics
- What business insights to extract
- What patterns and anomalies exist
- What recommendations to make

Like having a senior data analyst review your data!
"""

from flask import Flask, request, jsonify, render_template_string
import pandas as pd
import numpy as np
import io
import json
import base64
from typing import Dict, List, Any, Tuple
import traceback
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import os
import re
from pathlib import Path
from scipy import stats
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

# Load environment
def load_env_file():
    # Try multiple .env file locations
    env_files = [
        Path(__file__).parent / ".env",
        Path(__file__).parent / ".env.groq",
        Path(__file__).parent / ".env.huggingface"
    ]
    
    for env_file in env_files:
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip().strip('"').strip("'")
            break

def setup_api_key():
    """Interactive API key setup on first run"""
    env_file = Path(__file__).parent / ".env"
    
    # Check if API key is already configured
    load_env_file()
    api_key = os.getenv("GROQ_API_KEY", "")
    
    if api_key and api_key != "":
        # Key exists, use it
        return api_key
    
    # No API key found - interactive setup
    print("\n" + "=" * 70)
    print("  🔑 FIRST TIME SETUP - Groq API Key Required")
    print("=" * 70)
    print()
    print("This analyzer uses AI to provide intelligent insights.")
    print("You need a FREE Groq API key to enable AI features.")
    print()
    print("📝 How to get your API key:")
    print("   1. Go to: https://console.groq.com/")
    print("   2. Sign up for a free account")
    print("   3. Create an API key")
    print("   4. Copy the key (starts with 'gsk_')")
    print()
    print("⚠️  Note: Your API key will be stored locally in .env")
    print("   Keep this file private and never share it!")
    print()
    print("=" * 70)
    print()
    
    # Get API key from user
    while True:
        api_key = input("Enter your Groq API key (or 'skip' to continue without AI): ").strip()
        
        if api_key.lower() == 'skip':
            print("\n⚠️  Skipping AI setup. You'll get basic analysis without AI insights.")
            choice = input("Continue anyway? (y/n): ").strip().lower()
            if choice == 'y':
                return ""
            else:
                continue
        
        # Validate format
        if not api_key.startswith('gsk_'):
            print("❌ Invalid format. Groq API keys start with 'gsk_'")
            print("Example: gsk_AbCdEfGhIjKlMnOpQrStUvWxYz1234567890")
            retry = input("\nTry again? (y/n): ").strip().lower()
            if retry != 'y':
                return ""
            continue
        
        if len(api_key) < 30:
            print("❌ API key seems too short. Please check and try again.")
            retry = input("\nTry again? (y/n): ").strip().lower()
            if retry != 'y':
                return ""
            continue
        
        # Save to .env file
        try:
            with open(env_file, 'w') as f:
                f.write("# Groq API Configuration\n")
                f.write("# Keep this file private!\n\n")
                f.write(f"GROQ_API_KEY={api_key}\n")
            
            os.environ["GROQ_API_KEY"] = api_key
            
            print("\n✅ API key saved successfully!")
            print(f"📁 Saved to: {env_file}")
            print()
            print("🎉 Setup complete! Starting analyzer...\n")
            return api_key
            
        except Exception as e:
            print(f"\n❌ Error saving API key: {e}")
            print("Please check file permissions and try again.")
            retry = input("\nTry again? (y/n): ").strip().lower()
            if retry != 'y':
                return ""

# Run setup on import
api_key = setup_api_key()
if not api_key:
    print("⚠️  Running without AI features. Charts will be basic.")
    print("   To enable AI later, run setup again or create .env.huggingface manually.\n")

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

# LLM Configuration
LLM_CONFIG = {
    "provider": os.getenv("LLM_PROVIDER", "groq"),
    "groq": {
        "base_url": "https://api.groq.com/openai/v1/chat/completions",
        "api_key": os.getenv("GROQ_API_KEY", ""),
        "model": "llama-3.3-70b-versatile",  # Updated to current model
        "timeout": 30
    }
}


class WorldClassAnalyzer:
    """AI-Powered Data Analyzer that thinks like a senior business analyst"""
    
    MAX_ROWS = 100000
    MAX_COLS = 1000
    
    def __init__(self):
        self.data = None
        self.sheets = {}
        self.file_hash = None
        self.analysis_context = {}
    
    def _clean_numeric_data(self, data: pd.Series) -> pd.Series:
        """Clean numeric data by removing currency symbols, commas, and percentages"""
        if data.dtype == 'object' or data.dtype == 'string':
            # Convert to string and clean
            cleaned = data.astype(str).str.replace(r'[\$£€¥₹,\s%]', '', regex=True)
            # Remove any remaining non-numeric characters except . and -
            cleaned = cleaned.str.replace(r'[^0-9.\-]', '', regex=True)
            # Convert to numeric
            return pd.to_numeric(cleaned, errors='coerce')
        return pd.to_numeric(data, errors='coerce')
        
    def load_excel(self, file_content: bytes, filename: str = "") -> Dict[str, Any]:
        """Load and validate data - supports ALL Excel formats (xls, xlsx, xlsm, xlsb, odf, ods, odt) and CSV"""
        try:
            self.file_hash = hash(file_content)
            file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
            
            # CSV files
            if file_ext == 'csv':
                for encoding in ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'utf-16']:
                    try:
                        df = pd.read_csv(io.BytesIO(file_content), encoding=encoding)
                        self.sheets = {"Sheet1": df}
                        self.data = df
                        file_type = "CSV"
                        break
                    except (UnicodeDecodeError, Exception):
                        continue
                else:
                    return {"success": False, "error": "Unable to decode CSV file"}
            
            # Excel and other spreadsheet formats
            elif file_ext in ['xlsx', 'xls', 'xlsm', 'xlsb', 'odf', 'ods', 'odt']:
                try:
                    # Try with engine auto-detection
                    excel_file = pd.ExcelFile(io.BytesIO(file_content))
                    sheet_names = excel_file.sheet_names[:1]  # First sheet only
                    self.sheets = {sheet: excel_file.parse(sheet) for sheet in sheet_names}
                    self.data = self.sheets[sheet_names[0]]
                    file_type = f"Excel ({file_ext.upper()})"
                except Exception as e1:
                    # Fallback: Try different engines
                    engines = ['openpyxl', 'xlrd', 'odf', 'pyxlsb']
                    loaded = False
                    
                    for engine in engines:
                        try:
                            excel_file = pd.ExcelFile(io.BytesIO(file_content), engine=engine)
                            sheet_names = excel_file.sheet_names[:1]
                            self.sheets = {sheet: excel_file.parse(sheet) for sheet in sheet_names}
                            self.data = self.sheets[sheet_names[0]]
                            file_type = f"Excel ({file_ext.upper()})"
                            loaded = True
                            break
                        except:
                            continue
                    
                    if not loaded:
                        return {
                            "success": False, 
                            "error": f"Unable to read {file_ext.upper()} file. Error: {str(e1)}"
                        }
            
            # Try as Excel if no extension or unknown extension
            else:
                try:
                    excel_file = pd.ExcelFile(io.BytesIO(file_content))
                    sheet_names = excel_file.sheet_names[:1]
                    self.sheets = {sheet: excel_file.parse(sheet) for sheet in sheet_names}
                    self.data = self.sheets[sheet_names[0]]
                    file_type = "Excel"
                except:
                    return {
                        "success": False,
                        "error": f"Unsupported file format. Please use Excel (xls, xlsx, xlsm, xlsb) or CSV files."
                    }
            
            # Validate data size
            if len(self.data) > self.MAX_ROWS:
                return {"success": False, "error": f"File too large. Max {self.MAX_ROWS:,} rows"}
            
            if len(self.data.columns) > self.MAX_COLS:
                return {"success": False, "error": f"Too many columns. Max {self.MAX_COLS:,} columns"}
            
            if len(self.data) == 0:
                return {"success": False, "error": "File is empty or has no data"}
            
            # Auto-detect and transform key-value pair data structures
            self.data = self._auto_transform_data_structure(self.data)
            
            return {
                "success": True,
                "rows": len(self.data),
                "columns": len(self.data.columns),
                "file_type": file_type
            }
        except Exception as e:
            return {"success": False, "error": f"Error loading file: {str(e)}"}
    
    def _auto_transform_data_structure(self, df: pd.DataFrame) -> pd.DataFrame:
        """Automatically detect and transform key-value pair data structures"""
        
        # Skip if already well-structured (many columns or many rows)
        if len(df.columns) > 3 or len(df) > 50:
            return df
        
        # Detect key-value pair structure (2 columns, first is labels, second is values)
        if len(df.columns) == 2:
            col1, col2 = df.columns[0], df.columns[1]
            
            # Check if first column looks like metric names and second like values
            first_col_text_ratio = df[col1].apply(lambda x: isinstance(x, str)).sum() / len(df)
            second_col_mixed = df[col2].apply(lambda x: pd.to_numeric(x, errors='coerce')).notna().sum()
            
            # If first column is mostly text and contains metric-like names
            if first_col_text_ratio > 0.7:
                metric_keywords = ['rate', 'count', 'percent', 'score', 'value', 'amount', 'total', 
                                  'average', 'frequency', 'cap', 'win', 'conversion', 'ctr', 'pacing']
                
                # Check if any metric keywords appear in first column
                has_metrics = any(
                    any(keyword in str(val).lower() for keyword in metric_keywords)
                    for val in df[col1].dropna()
                )
                
                if has_metrics or second_col_mixed > len(df) * 0.3:
                    print(f"   🔄 Auto-detected key-value format. Transforming data...")
                    
                    # Try to separate numeric and text metrics
                    df_copy = df.copy()
                    df_copy['is_numeric'] = pd.to_numeric(df_copy[col2], errors='coerce').notna()
                    
                    numeric_metrics = df_copy[df_copy['is_numeric']].copy()
                    text_metrics = df_copy[~df_copy['is_numeric']].copy()
                    
                    # Create transformed dataframe with metrics as columns
                    transformed = pd.DataFrame()
                    
                    # Add numeric metrics as columns
                    for _, row in numeric_metrics.iterrows():
                        metric_name = str(row[col1]).strip()
                        metric_value = pd.to_numeric(row[col2], errors='coerce')
                        transformed[metric_name] = [metric_value]
                    
                    # Add text metrics as columns if they're important (like campaign names)
                    for _, row in text_metrics.iterrows():
                        metric_name = str(row[col1]).strip()
                        metric_value = str(row[col2])
                        # Only add if it looks like a name/identifier, not a long description
                        if len(metric_value) < 100:
                            transformed[metric_name] = [metric_value]
                    
                    if len(transformed.columns) > 0:
                        print(f"   ✓ Transformed to {len(transformed.columns)} metric columns")
                        return transformed
        
        return df
    
    def deep_data_profiling(self) -> Dict[str, Any]:
        """Comprehensive data profiling with statistical analysis"""
        if self.data is None:
            return {"error": "No data loaded"}
        
        profile = {
            "basic_info": self._get_basic_info(),
            "column_profiles": self._profile_columns(),
            "data_quality": self._assess_data_quality(),
            "relationships": self._find_relationships(),
            "patterns": self._detect_patterns(),
            "anomalies": self._detect_anomalies()
        }
        
        self.analysis_context = profile
        return profile
    
    def _get_basic_info(self) -> Dict[str, Any]:
        """Extract basic dataset information"""
        return {
            "shape": {"rows": len(self.data), "columns": len(self.data.columns)},
            "column_names": list(self.data.columns),
            "dtypes": {col: str(dtype) for col, dtype in self.data.dtypes.items()},
            "memory_usage_mb": self.data.memory_usage(deep=True).sum() / (1024 * 1024)
        }
    
    def _profile_columns(self) -> Dict[str, Dict[str, Any]]:
        """Detailed profiling of each column"""
        profiles = {}
        
        for col in self.data.columns:
            try:
                profile = {
                    "dtype": str(self.data[col].dtype),
                    "null_count": int(self.data[col].isnull().sum()),
                    "null_percentage": float((self.data[col].isnull().sum() / len(self.data)) * 100),
                    "unique_count": int(self.data[col].nunique()),
                    "unique_percentage": float((self.data[col].nunique() / len(self.data)) * 100)
                }
                
                if pd.api.types.is_numeric_dtype(self.data[col]):
                    profile.update(self._profile_numeric_column(col))
                    profile["column_type"] = "numeric"
                elif pd.api.types.is_datetime64_any_dtype(self.data[col]):
                    profile.update(self._profile_datetime_column(col))
                    profile["column_type"] = "datetime"
                else:
                    profile.update(self._profile_categorical_column(col))
                    profile["column_type"] = "categorical"
                
                profiles[col] = profile
            except Exception as e:
                profiles[col] = {
                    "error": f"Error profiling column: {str(e)}",
                    "column_type": "unknown"
                }
        
        return profiles
    
    def _profile_numeric_column(self, col: str) -> Dict[str, Any]:
        """Profile numeric columns with advanced stats"""
        data = self.data[col].dropna()
        
        if len(data) == 0:
            return {}
        
        try:
            # Clean and convert to numeric
            data = self._clean_numeric_data(data).dropna()
            
            if len(data) == 0:
                return {"error": "No valid numeric values"}
            
            return {
                "min": float(data.min()),
                "max": float(data.max()),
                "mean": float(data.mean()),
                "median": float(data.median()),
                "std": float(data.std()),
                "skewness": float(data.skew()),
                "kurtosis": float(data.kurtosis()),
                "q25": float(data.quantile(0.25)),
                "q75": float(data.quantile(0.75)),
                "iqr": float(data.quantile(0.75) - data.quantile(0.25)),
                "outlier_count": int(self._count_outliers(data)),
                "zeros_count": int((data == 0).sum()),
                "negative_count": int((data < 0).sum())
            }
        except Exception as e:
            return {"error": f"Error profiling numeric column: {str(e)}"}
    
    def _count_outliers(self, data: pd.Series) -> int:
        """Count outliers using IQR method"""
        try:
            # Clean and ensure data is numeric
            data = self._clean_numeric_data(data).dropna()
            if len(data) == 0:
                return 0
            
            q1, q3 = data.quantile([0.25, 0.75])
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            return int(((data < lower) | (data > upper)).sum())
        except:
            return 0
    
    def _profile_datetime_column(self, col: str) -> Dict[str, Any]:
        """Profile datetime columns"""
        try:
            data = self.data[col].dropna()
            
            if len(data) == 0:
                return {}
            
            return {
                "min_date": str(data.min()),
                "max_date": str(data.max()),
                "date_range_days": (data.max() - data.min()).days,
                "is_sorted": data.is_monotonic_increasing or data.is_monotonic_decreasing
            }
        except Exception as e:
            return {"error": f"Error profiling datetime column: {str(e)}"}
    
    def _profile_categorical_column(self, col: str) -> Dict[str, Any]:
        """Profile categorical columns"""
        try:
            data = self.data[col].dropna()
            
            if len(data) == 0:
                return {}
            
            value_counts = data.value_counts()
            
            return {
                "top_5_values": {str(k): int(v) for k, v in value_counts.head(5).items()},
                "most_common": str(value_counts.index[0]),
                "most_common_frequency": int(value_counts.iloc[0]),
                "entropy": float(stats.entropy(value_counts)),
                "is_constant": len(value_counts) == 1
            }
        except Exception as e:
            return {"error": f"Error profiling categorical column: {str(e)}"}
    
    def _assess_data_quality(self) -> Dict[str, Any]:
        """Comprehensive data quality assessment"""
        return {
            "total_missing": int(self.data.isnull().sum().sum()),
            "missing_percentage": float((self.data.isnull().sum().sum() / (len(self.data) * len(self.data.columns))) * 100),
            "duplicate_rows": int(self.data.duplicated().sum()),
            "duplicate_percentage": float((self.data.duplicated().sum() / len(self.data)) * 100),
            "columns_with_missing": [col for col in self.data.columns if self.data[col].isnull().any()],
            "constant_columns": [col for col in self.data.columns if self.data[col].nunique() <= 1],
            "high_cardinality_columns": [col for col in self.data.columns if self.data[col].nunique() > len(self.data) * 0.95]
        }
    
    def _find_relationships(self) -> Dict[str, Any]:
        """Find correlations and relationships between columns"""
        numeric_cols = self.data.select_dtypes(include=['number']).columns.tolist()
        
        if len(numeric_cols) < 2:
            return {"correlations": {}}
        
        corr_matrix = self.data[numeric_cols].corr()
        
        # Find strong correlations
        strong_correlations = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                corr_value = corr_matrix.iloc[i, j]
                if abs(corr_value) > 0.7:  # Strong correlation threshold
                    strong_correlations.append({
                        "col1": corr_matrix.columns[i],
                        "col2": corr_matrix.columns[j],
                        "correlation": float(corr_value),
                        "strength": "strong positive" if corr_value > 0 else "strong negative"
                    })
        
        return {
            "numeric_columns": numeric_cols,
            "correlation_matrix": corr_matrix.to_dict(),
            "strong_correlations": strong_correlations
        }
    
    def _detect_patterns(self) -> Dict[str, Any]:
        """Detect patterns in data"""
        patterns = {
            "has_time_series": False,
            "has_categories": False,
            "has_hierarchical": False,
            "potential_id_columns": [],
            "potential_measure_columns": [],
            "potential_dimension_columns": []
        }
        
        # Detect potential ID columns
        for col in self.data.columns:
            if self.data[col].nunique() == len(self.data):
                patterns["potential_id_columns"].append(col)
        
        # Detect datetime columns (time series)
        datetime_cols = self.data.select_dtypes(include=['datetime64']).columns.tolist()
        if datetime_cols:
            patterns["has_time_series"] = True
        
        # Detect categorical dimensions
        for col in self.data.columns:
            if pd.api.types.is_object_dtype(self.data[col]):
                unique_ratio = self.data[col].nunique() / len(self.data)
                if 0.01 < unique_ratio < 0.5:  # Good cardinality for dimensions
                    patterns["potential_dimension_columns"].append(col)
                    patterns["has_categories"] = True
        
        # Detect numeric measures
        numeric_cols = self.data.select_dtypes(include=['number']).columns.tolist()
        patterns["potential_measure_columns"] = numeric_cols
        
        return patterns
    
    def _detect_anomalies(self) -> Dict[str, Any]:
        """Detect anomalies and outliers"""
        anomalies = {
            "outlier_columns": [],
            "suspicious_patterns": []
        }
        
        for col in self.data.select_dtypes(include=['number']).columns:
            data = self.data[col].dropna()
            if len(data) > 0:
                outlier_count = self._count_outliers(data)
                outlier_percentage = (outlier_count / len(data)) * 100
                
                if outlier_percentage > 5:  # More than 5% outliers
                    anomalies["outlier_columns"].append({
                        "column": col,
                        "outlier_count": int(outlier_count),
                        "outlier_percentage": float(outlier_percentage)
                    })
        
        # Check for suspicious patterns
        for col in self.data.columns:
            if self.data[col].nunique() == 1:
                anomalies["suspicious_patterns"].append(f"Column '{col}' has only one unique value")
            
            if self.data[col].isnull().sum() == len(self.data):
                anomalies["suspicious_patterns"].append(f"Column '{col}' is completely empty")
        
        return anomalies
    
    def ai_driven_chart_selection(self) -> List[Dict[str, Any]]:
        """Use AI to intelligently select which charts to create"""
        
        # Prepare data summary for LLM
        summary = self._prepare_summary_for_llm()
        
        prompt = f"""You are a senior data analyst reviewing REAL BUSINESS DATA with ACTUAL NUMERIC VALUES. Your job is to recommend charts that visualize THE NUMBERS, not describe the dataset structure.

🔴 CRITICAL: You are looking at REAL BUSINESS METRICS with ACTUAL VALUES below. Analyze the NUMBERS, not the column names.

ACTUAL DATA SAMPLES (First 5 rows of actual business data):
{json.dumps(summary.get('sample_data', {}), indent=2)}

NUMERIC COLUMN STATISTICS (These are REAL business metrics):
{json.dumps(summary.get('column_statistics', {}), indent=2)}

Available Columns:
- Numeric metrics: {', '.join(summary.get('numeric_columns', [])[:10])}
- Categorical dimensions: {', '.join(summary.get('categorical_columns', [])[:10])}

Your Task:
1. Look at the ACTUAL VALUES in sample_data above
2. Identify which numeric columns have meaningful ranges (not IDs)
3. Recommend charts that visualize BUSINESS PERFORMANCE TRENDS
4. Focus on distributions, comparisons, and correlations OF THE ACTUAL NUMBERS

🎯 Recommend 5-7 visualizations that show:
- How business metrics are DISTRIBUTED (histograms/box plots)
- RELATIONSHIPS between different metrics (scatter plots)
- COMPARISONS across categories (bar charts)
- CORRELATIONS between variables (heatmaps)

For EACH chart, specify:
- chart_type: histogram, scatter, bar, heatmap, box, or line
- column(s): Use EXACT column names from the data
- reason: What business pattern this reveals
- insight: What decision-makers learn from this

RETURN ONLY valid JSON array (no markdown, no explanation):
[
  {{
    "chart_type": "histogram",
    "column": "exact_column_name",
    "reason": "Shows distribution of metric values",
    "insight": "Identify normal ranges vs outliers"
  }}
]"""
        
        try:
            response = self._call_llm(prompt)
            # Extract JSON from response
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                chart_recommendations = json.loads(json_match.group())
                # Auto-fix AI response format issues
                chart_recommendations = self._fix_chart_recommendations(chart_recommendations)
                return chart_recommendations
            else:
                # Fallback to smart defaults
                return self._smart_default_charts()
        except Exception as e:
            print(f"   ⚠️  AI chart selection failed: {str(e)[:100]}")
            print(f"   ℹ️  Using smart default charts instead")
            return self._smart_default_charts()
    
    def _prepare_summary_for_llm(self) -> Dict[str, Any]:
        """Prepare concise summary for LLM with actual data examples"""
        numeric_cols = self.data.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = self.data.select_dtypes(include=['object']).columns.tolist()
        datetime_cols = self.data.select_dtypes(include=['datetime64']).columns.tolist()
        
        # Include actual sample data WITH STATISTICS to help AI understand context
        sample_data = {}
        column_stats = {}
        for col in list(self.data.columns)[:15]:
            sample_vals = self.data[col].dropna().head(5).tolist()
            sample_data[col] = [str(v)[:100] for v in sample_vals]  # Limit string length
            
            # Add statistics for numeric columns
            if col in numeric_cols:
                numeric_data = self._clean_numeric_data(self.data[col]).dropna()
                if len(numeric_data) > 0:
                    column_stats[col] = {
                        'mean': float(numeric_data.mean()),
                        'min': float(numeric_data.min()),
                        'max': float(numeric_data.max()),
                        'median': float(numeric_data.median())
                    }
        
        return {
            "rows": len(self.data),
            "columns": len(self.data.columns),
            "column_names": list(self.data.columns)[:15],
            "sample_data": sample_data,
            "column_statistics": column_stats,
            "numeric_columns": numeric_cols[:10],
            "categorical_columns": categorical_cols[:10],
            "datetime_columns": datetime_cols,
            "patterns": self.analysis_context.get("patterns", {}),
            "data_quality": {
                "missing_percentage": self.analysis_context.get("data_quality", {}).get("missing_percentage", 0),
                "has_outliers": len(self.analysis_context.get("anomalies", {}).get("outlier_columns", [])) > 0
            },
            "relationships": {
                "strong_correlations": len(self.analysis_context.get("relationships", {}).get("strong_correlations", []))
            }
        }
    
    def _fix_chart_recommendations(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Automatically fix common AI response format issues"""
        fixed = []
        
        for rec in recommendations:
            chart_type = rec.get("chart_type", "").lower()
            
            # Fix scatter plots with comma-separated or " vs " columns
            if chart_type == "scatter":
                col = rec.get("column", "")
                if col:
                    # Split by " vs " or comma
                    if " vs " in col.lower():
                        parts = [c.strip() for c in col.split(" vs ")]
                    elif "," in col:
                        parts = [c.strip() for c in col.split(",")]
                    else:
                        parts = []
                    
                    if len(parts) >= 2:
                        rec["x_column"] = parts[0]
                        rec["y_column"] = parts[1]
                        if "column" in rec:
                            del rec["column"]
            
            # Fix bar/histogram with comma-separated or " vs " columns (take first one)
            elif chart_type in ["bar", "histogram"]:
                col = rec.get("column", "")
                if col:
                    if " vs " in col.lower():
                        parts = [c.strip() for c in col.split(" vs ")]
                        rec["column"] = parts[0]
                    elif "," in col:
                        parts = [c.strip() for c in col.split(",")]
                        rec["column"] = parts[0]
            
            # Fix heatmap/box with comma-separated or " vs " columns (convert to array)
            elif chart_type in ["heatmap", "box"]:
                col = rec.get("column", "")
                cols = rec.get("columns", [])
                
                # If 'column' exists and has separators, split it
                if col:
                    if " vs " in col.lower():
                        cols = [c.strip() for c in col.split(" vs ")]
                        rec["columns"] = cols
                        if "column" in rec:
                            del rec["column"]
                    elif "," in col:
                        cols = [c.strip() for c in col.split(",")]
                        rec["columns"] = cols
                        if "column" in rec:
                            del rec["column"]
                # If 'columns' is a string with separators, split it
                elif isinstance(cols, str):
                    if " vs " in cols.lower():
                        rec["columns"] = [c.strip() for c in cols.split(" vs ")]
                    elif "," in cols:
                        rec["columns"] = [c.strip() for c in cols.split(",")]
            
            fixed.append(rec)
        
        return fixed
    
    def _smart_default_charts(self) -> List[Dict[str, Any]]:
        """Fallback: Smart default chart selection based on data types"""
        charts = []
        
        numeric_cols = self.data.select_dtypes(include=['number']).columns.tolist()[:4]
        categorical_cols = self.data.select_dtypes(include=['object']).columns.tolist()[:3]
        
        # Distribution of first numeric
        if numeric_cols:
            charts.append({
                "chart_type": "histogram",
                "column": numeric_cols[0],
                "reason": "Understand distribution of values",
                "insight": "Shows if data is normally distributed or skewed"
            })
        
        # Correlation heatmap
        if len(numeric_cols) > 1:
            charts.append({
                "chart_type": "heatmap",
                "columns": numeric_cols,
                "reason": "Identify relationships between numeric variables",
                "insight": "Reveals which variables move together"
            })
        
        # Category distribution
        if categorical_cols:
            charts.append({
                "chart_type": "bar",
                "column": categorical_cols[0],
                "reason": "Show frequency of categories",
                "insight": "Identifies most common categories"
            })
        
        # Scatter plot if 2+ numeric
        if len(numeric_cols) >= 2:
            charts.append({
                "chart_type": "scatter",
                "x_column": numeric_cols[0],
                "y_column": numeric_cols[1],
                "reason": "Examine relationship between two variables",
                "insight": "Shows if variables are related"
            })
        
        # Box plot for outliers
        if numeric_cols:
            charts.append({
                "chart_type": "box",
                "columns": numeric_cols[:4],
                "reason": "Detect outliers and distribution spread",
                "insight": "Identifies unusual values that need investigation"
            })
        
        return charts
    
    def create_ai_recommended_charts(self, recommendations: List[Dict[str, Any]]) -> Dict[str, str]:
        """Create charts based on AI recommendations"""
        charts = {}
        
        for idx, rec in enumerate(recommendations):
            try:
                chart_type = rec.get("chart_type", "").lower()
                print(f"      → Creating {chart_type} chart ({idx+1}/{len(recommendations)})...")
                
                if chart_type == "histogram":
                    img = self._create_histogram(rec)
                elif chart_type == "scatter":
                    img = self._create_scatter(rec)
                elif chart_type == "bar":
                    img = self._create_bar(rec)
                elif chart_type == "heatmap":
                    img = self._create_heatmap(rec)
                elif chart_type == "box":
                    img = self._create_box(rec)
                elif chart_type == "line":
                    img = self._create_line(rec)
                else:
                    print(f"        ⚠️ Unknown chart type: {chart_type}")
                    continue
                
                if img:
                    charts[f"chart_{idx+1}_{chart_type}"] = img
                    print(f"        ✓ Success")
                else:
                    print(f"        ✗ Failed (returned None) - Column: {rec.get('column', rec.get('columns', 'unknown'))}")
            except Exception as e:
                print(f"        ✗ Error creating {chart_type}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        return charts
    
    def _create_histogram(self, rec: Dict) -> str:
        """Create histogram"""
        col = rec.get("column") or rec.get("x_column")
        if not col:
            print(f"          ⚠️ No column specified in recommendation: {rec}")
            return None
        if col not in self.data.columns:
            print(f"          ⚠️ Column '{col}' not found. Available: {list(self.data.columns)[:5]}")
            return None
        
        fig = None
        try:
            fig, ax = plt.subplots(figsize=(12, 8))
            # Clean and convert to numeric
            data = self._clean_numeric_data(self.data[col]).dropna()
            if len(data) == 0:
                print(f"          ⚠️ No valid numeric data in column '{col}' (sample: {self.data[col].head(2).tolist()})")
                plt.close(fig)
                return None
            
            # Create histogram with better visibility
            n, bins, patches = ax.hist(data, bins=min(20, len(data.unique())), 
                                      color='#4CAF50', edgecolor='white', linewidth=2, alpha=0.8)
            
            # Add statistics annotation
            mean_val = data.mean()
            median_val = data.median()
            ax.axvline(mean_val, color='red', linestyle='--', linewidth=3, label=f'Average: {mean_val:.1f}')
            ax.axvline(median_val, color='orange', linestyle='--', linewidth=3, label=f'Middle: {median_val:.1f}')
            
            # Large, clear title
            ax.set_title(f'{col}\nHow values are spread out', fontsize=20, fontweight='bold', pad=20)
            ax.set_xlabel(col, fontsize=16, fontweight='bold')
            ax.set_ylabel('How many', fontsize=16, fontweight='bold')
            
            # Larger tick labels
            ax.tick_params(axis='both', labelsize=14)
            ax.legend(fontsize=14, loc='best')
            ax.grid(alpha=0.3, linewidth=1.5)
            plt.tight_layout()
            return self._fig_to_base64(fig)
        except Exception as e:
            print(f"          ⚠️ Histogram failed for '{col}': {e}")
            if fig:
                plt.close(fig)
            return None
    
    def _create_scatter(self, rec: Dict) -> str:
        """Create scatter plot"""
        x_col = rec.get("x_column")
        y_col = rec.get("y_column")
        
        if not x_col or not y_col:
            print(f"          ⚠️ Scatter needs x_column and y_column, got: {rec}")
            return None
        
        if x_col not in self.data.columns:
            print(f"          ⚠️ X column '{x_col}' not found")
            return None
        if y_col not in self.data.columns:
            print(f"          ⚠️ Y column '{y_col}' not found")
            return None
        
        try:
            fig, ax = plt.subplots(figsize=(12, 8))
            # Clean and convert to numeric
            x_data = self._clean_numeric_data(self.data[x_col])
            y_data = self._clean_numeric_data(self.data[y_col])
            # Remove rows with NaN
            valid_data = pd.DataFrame({'x': x_data, 'y': y_data}).dropna()
            if len(valid_data) == 0:
                print(f"          ⚠️ No valid numeric data after cleaning")
                plt.close(fig)
                return None
            
            # Bigger, colorful scatter points
            ax.scatter(valid_data['x'], valid_data['y'], s=150, alpha=0.7, 
                      c=valid_data['y'], cmap='viridis', edgecolors='black', linewidth=2)
            
            # Add trend line if possible
            try:
                z = np.polyfit(valid_data['x'], valid_data['y'], 1)
                p = np.poly1d(z)
                ax.plot(valid_data['x'], p(valid_data['x']), "r--", linewidth=3, label='Trend')
                ax.legend(fontsize=14)
            except:
                pass
            
            ax.set_title(f'How {x_col} affects {y_col}', fontsize=20, fontweight='bold', pad=20)
            ax.set_xlabel(x_col, fontsize=16, fontweight='bold')
            ax.set_ylabel(y_col, fontsize=16, fontweight='bold')
            ax.tick_params(axis='both', labelsize=14)
            ax.grid(alpha=0.3, linewidth=1.5)
            plt.tight_layout()
            return self._fig_to_base64(fig)
        except Exception as e:
            print(f"          ⚠️ Scatter plot failed: {e}")
            if 'fig' in locals():
                plt.close(fig)
            return None
    
    def _create_bar(self, rec: Dict) -> str:
        """Create bar chart"""
        col = rec.get("column")
        if not col:
            print(f"          ⚠️ Bar chart needs 'column' parameter, got: {rec}")
            return None
        if col not in self.data.columns:
            print(f"          ⚠️ Column '{col}' not found")
            return None
        
        try:
            fig, ax = plt.subplots(figsize=(12, 10))
            # Convert all values to strings to avoid type errors
            value_counts = self.data[col].astype(str).value_counts().head(8)
            if len(value_counts) == 0:
                plt.close(fig)
                return None
            
            # Horizontal bars are easier to read
            colors = plt.cm.Set3(range(len(value_counts)))
            bars = ax.barh(range(len(value_counts)), value_counts.values, color=colors, edgecolor='black', linewidth=2)
            ax.set_yticks(range(len(value_counts)))
            ax.set_yticklabels(value_counts.index, fontsize=14)
            
            # Add value labels on bars
            for i, (bar, value) in enumerate(zip(bars, value_counts.values)):
                ax.text(value, i, f' {value}', va='center', fontsize=14, fontweight='bold')
            
            ax.set_title(f'Most Common {col}', fontsize=20, fontweight='bold', pad=20)
            ax.set_xlabel('Count', fontsize=16, fontweight='bold')
            ax.tick_params(axis='x', labelsize=14)
            ax.grid(axis='x', alpha=0.3, linewidth=1.5)
            plt.tight_layout()
            return self._fig_to_base64(fig)
        except Exception as e:
            print(f"          ⚠️ Bar chart failed: {e}")
            if 'fig' in locals():
                plt.close(fig)
            return None
    
    def _create_heatmap(self, rec: Dict) -> str:
        """Create correlation heatmap (or comparison chart for single row)"""
        cols = rec.get("columns", [])
        if not cols:
            cols = self.data.select_dtypes(include=['number']).columns.tolist()[:10]
        
        # Filter to only existing columns
        cols = [c for c in cols if c in self.data.columns]
        
        if len(cols) < 2:
            print(f"          ⚠️ Heatmap needs 2+ numeric columns, got {len(cols)}")
            return None
        
        try:
            # Clean and convert to numeric, this will filter out non-numeric columns
            numeric_data = self.data[cols].apply(self._clean_numeric_data).dropna()
            
            # Keep only columns that have valid numeric data
            valid_cols = [col for col in numeric_data.columns if numeric_data[col].notna().sum() > 0]
            if len(valid_cols) < 2:
                print(f"          ⚠️ Only {len(valid_cols)} columns with numeric data")
                return None
            
            numeric_data = numeric_data[valid_cols]
            
            # If only 1 row, create a comparison bar chart instead of correlation
            if len(numeric_data) < 2:
                print(f"          ℹ️  Single row detected - creating comparison chart instead")
                fig, ax = plt.subplots(figsize=(12, 8))
                
                # Get values from the single row
                values = numeric_data.iloc[0]
                
                # Normalize values to 0-100 scale for comparison
                max_val = values.max()
                min_val = values.min()
                if max_val != min_val:
                    normalized = ((values - min_val) / (max_val - min_val)) * 100
                else:
                    normalized = pd.Series([50] * len(values), index=values.index)
                
                # Create horizontal bar chart
                colors = plt.cm.RdYlGn(normalized / 100)
                bars = ax.barh(range(len(normalized)), normalized, color=colors, edgecolor='black', linewidth=2)
                
                # Add value labels
                for i, (bar, val, orig_val) in enumerate(zip(bars, normalized, values)):
                    ax.text(bar.get_width() + 2, i, f'{orig_val:.2f}', 
                           va='center', fontsize=14, fontweight='bold')
                
                ax.set_yticks(range(len(normalized)))
                ax.set_yticklabels(normalized.index, fontsize=13)
                ax.set_xlabel('Relative Strength (0-100)', fontsize=16, fontweight='bold')
                ax.set_title('Metric Comparison\n(Higher is stronger)', 
                           fontsize=20, fontweight='bold', pad=20)
                ax.set_xlim(0, 110)
                ax.tick_params(axis='x', labelsize=14)
                ax.grid(axis='x', alpha=0.3, linestyle='--')
                plt.tight_layout()
                return self._fig_to_base64(fig)
            
            # Normal correlation heatmap for 2+ rows
            fig, ax = plt.subplots(figsize=(10, 8))
            corr = numeric_data.corr()
            sns.heatmap(corr, annot=True, fmt='.2f', cmap='RdYlGn', center=0, ax=ax, 
                       square=True, linewidths=2, cbar_kws={'shrink': 0.8},
                       annot_kws={'size': 14, 'weight': 'bold'})
            
            ax.set_title('How things relate to each other\n(Green = go together, Red = opposite)', 
                        fontsize=18, fontweight='bold', pad=20)
            ax.tick_params(axis='both', labelsize=13)
            plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
            plt.setp(ax.get_yticklabels(), rotation=0)
            plt.tight_layout()
            return self._fig_to_base64(fig)
        except Exception as e:
            print(f"          ⚠️ Heatmap failed: {e}")
            if 'fig' in locals():
                plt.close(fig)
            return None
    
    def _create_box(self, rec: Dict) -> str:
        """Create box plot"""
        # Try to get columns from various parameter names
        cols = rec.get("columns", [])
        if not cols:
            col = rec.get("column")
            if col:
                cols = [col]
        
        if not cols:
            cols = self.data.select_dtypes(include=['number']).columns.tolist()[:5]
        
        if not cols:
            print(f"          ⚠️ Box plot needs numeric columns, got: {rec}")
            return None
        
        # Filter to only existing columns
        cols = [c for c in cols if c in self.data.columns]
        if not cols:
            print(f"          ⚠️ None of the specified columns exist")
            return None
        
        try:
            fig, ax = plt.subplots(figsize=(12, 6))
            # Clean and convert to numeric
            numeric_data = self.data[cols].apply(self._clean_numeric_data).dropna()
            if len(numeric_data) == 0:
                print(f"          ⚠️ No valid numeric data in columns: {cols}")
                plt.close(fig)
                return None
            bp = numeric_data.boxplot(ax=ax, patch_artist=True, return_type='dict',
                                     widths=0.6, boxprops=dict(facecolor='lightblue', linewidth=2),
                                     medianprops=dict(color='red', linewidth=3),
                                     whiskerprops=dict(linewidth=2),
                                     capprops=dict(linewidth=2),
                                     flierprops=dict(marker='o', markersize=10, markerfacecolor='red', alpha=0.5))
            
            ax.set_title('Value Ranges\n(Box = normal, Dots = unusual)', fontsize=20, fontweight='bold', pad=20)
            ax.set_ylabel('Value', fontsize=16, fontweight='bold')
            ax.tick_params(axis='both', labelsize=14)
            ax.grid(alpha=0.3, linewidth=1.5)
            plt.xticks(rotation=45, ha='right', fontsize=13)
            plt.tight_layout()
            return self._fig_to_base64(fig)
        except Exception as e:
            print(f"          ⚠️ Box plot failed: {e}")
            if 'fig' in locals():
                plt.close(fig)
            return None
    
    def _create_line(self, rec: Dict) -> str:
        """Create line chart (for time series)"""
        x_col = rec.get("x_column")
        y_col = rec.get("y_column")
        
        if not x_col or not y_col or x_col not in self.data.columns or y_col not in self.data.columns:
            return None
        
        try:
            fig, ax = plt.subplots(figsize=(12, 6))
            # Clean and convert y to numeric
            y_data = self._clean_numeric_data(self.data[y_col])
            x_data = self.data[x_col]
            
            # Create clean dataframe
            plot_data = pd.DataFrame({'x': x_data, 'y': y_data}).dropna()
            if len(plot_data) == 0:
                plt.close(fig)
                return None
            
            ax.plot(range(len(plot_data)), plot_data['y'], marker='o', color='#06b6d4', linewidth=2)
            ax.set_xticks(range(len(plot_data)))
            ax.set_xticklabels([str(x)[:20] for x in plot_data['x']], rotation=45, ha='right')
            ax.set_title(f'{y_col} over {x_col}\n{rec.get("insight", "")}', fontsize=12, fontweight='bold')
            ax.set_xlabel(x_col)
            ax.set_ylabel(y_col)
            ax.grid(alpha=0.3)
            plt.tight_layout()
            return self._fig_to_base64(fig)
        except Exception as e:
            print(f"Line chart creation failed: {e}")
            if 'fig' in locals():
                plt.close(fig)
            return None
    
    def _fig_to_base64(self, fig) -> str:
        """Convert figure to base64"""
        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode('utf-8')
    
    def generate_executive_insights(self) -> Dict[str, Any]:
        """Generate comprehensive business insights using AI"""
        
        summary = self._prepare_summary_for_llm()
        
        # Build concrete examples of actual data
        data_examples = []
        for col in list(self.data.columns)[:8]:
            sample_vals = self.data[col].dropna().head(3).tolist()
            data_examples.append(f"{col}: {sample_vals}")
        
        prompt = f"""You are a business analyst presenting ACTUAL BUSINESS PERFORMANCE to executives. You have real data with real numbers in front of you.

🔴 CRITICAL: Analyze the ACTUAL VALUES below, not column names or file structure.

REAL DATA EXAMPLES (Actual rows from the business):
{chr(10).join(data_examples)}

NUMERIC METRICS WITH REAL STATISTICS:
{json.dumps(summary.get('column_statistics', {}), indent=2)}

BUSINESS CONTEXT:
- Total Records: {summary.get('rows')} business transactions/records
- Numeric Metrics Available: {', '.join(summary.get('numeric_columns', [])[:8])}
- Key Dimensions: {', '.join(summary.get('categorical_columns', [])[:5])}

STRONG CORRELATIONS (These metrics move together):
{json.dumps(self.analysis_context.get('relationships', {}).get('strong_correlations', [])[:3], indent=2)}

Your Analysis Must Focus On:
✅ ACTUAL METRIC VALUES (numbers you see above)
✅ BUSINESS PERFORMANCE TRENDS in those numbers
✅ COMPARISONS between different metrics
❌ NOT file structure, column names, or data types
❌ NOT generic statements about "data quality"

Provide:

**EXECUTIVE SUMMARY** (2-3 sentences):
What business problem/domain does this data represent? What's the most critical finding from the ACTUAL NUMBERS?

**KEY BUSINESS INSIGHTS** (5-7 specific observations):
- Reference ACTUAL METRIC VALUES and their ranges
- Identify HIGH/LOW performers from the data
- Point out TRENDS or PATTERNS in the numbers
- Compare metrics: "X averages Y while Z shows..."

**DATA QUALITY ISSUES** (only if critical):
Missing values affecting analysis: {summary.get('data_quality', {}).get('missing_percentage', 0):.1f}%

**RECOMMENDED ACTIONS** (3-5 specific steps):
Based on what the NUMBERS show, what should the business do?

**INTERESTING PATTERNS**:
What's surprising or notable about the METRIC VALUES? Any outliers or unexpected correlations?

**STRATEGIC QUESTIONS** this data answers:
What business decisions can be made using these ACTUAL METRICS?

🎯 Remember: Talk about BUSINESS PERFORMANCE shown in the numbers, not about the dataset itself."""
        
        try:
            insights = self._call_llm(prompt)
            return {
                "success": True,
                "insights": insights,
                "analysis_depth": "comprehensive"
            }
        except Exception as e:
            error_msg = str(e)
            if "rate_limit" in error_msg.lower() or "429" in error_msg:
                fallback_msg = "⚠️ **AI Rate Limit Reached**: The Groq API has reached its daily token limit. Using basic statistical analysis instead.\n\n" + self._generate_basic_insights()
            else:
                fallback_msg = f"⚠️ **AI Analysis Unavailable**: {error_msg[:200]}\n\n" + self._generate_basic_insights()
            
            return {
                "success": False,
                "insights": fallback_msg,
                "fallback": True
            }
    
    def _generate_basic_insights(self) -> str:
        """Fallback: Generate basic insights without LLM"""
        insights = []
        
        # Dataset size
        insights.append(f"Dataset contains {len(self.data):,} rows and {len(self.data.columns)} columns")
        
        # Data quality
        missing_pct = self.analysis_context.get("data_quality", {}).get("missing_percentage", 0)
        if missing_pct > 10:
            insights.append(f"⚠️ Data quality concern: {missing_pct:.1f}% of values are missing")
        
        # Outliers
        outlier_cols = self.analysis_context.get("anomalies", {}).get("outlier_columns", [])
        if outlier_cols:
            insights.append(f"Found outliers in {len(outlier_cols)} columns - may need investigation")
        
        # Correlations
        strong_corr = self.analysis_context.get("relationships", {}).get("strong_correlations", [])
        if strong_corr:
            top_corr = strong_corr[0]
            insights.append(f"Strong relationship found: {top_corr['col1']} and {top_corr['col2']} ({top_corr['correlation']:.2f})")
        
        return "\n".join(f"• {insight}" for insight in insights)
    
    def _call_llm(self, prompt: str) -> str:
        """Call LLM API"""
        if not HAS_REQUESTS:
            raise Exception("requests library not installed")
        
        provider = LLM_CONFIG.get("provider")
        config = LLM_CONFIG.get(provider, {})
        
        if provider == "groq":
            return self._call_groq(prompt, config)
        else:
            raise Exception(f"Provider {provider} not configured")
    
    def _call_groq(self, prompt: str, config: Dict) -> str:
        """Call Groq API"""
        api_key = config.get("api_key", "")
        if not api_key:
            raise Exception("Groq API key not configured")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": config.get("model", "llama-3.3-70b-versatile"),
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1500
        }
        
        response = requests.post(
            config["base_url"],
            headers=headers,
            json=payload,
            timeout=config.get("timeout", 30)
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            raise Exception(f"API Error {response.status_code}: {response.text}")


# Create analyzer instance
analyzer = WorldClassAnalyzer()

# CORS
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    return response

# Routes
@app.route('/')
def home():
    """Landing page - FIXED for popup blockers"""
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>InsightIQ Analytics - AI Business Intelligence</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
                min-height: 100vh; display: flex; align-items: center; justify-content: center;
                padding: 20px;
            }
            .container { 
                background: white; padding: 40px; border-radius: 15px; 
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                max-width: 900px; width: 100%; text-align: center;
            }
            h1 { color: #06b6d4; font-size: 2.5em; margin-bottom: 10px; }
            .badge { 
                background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
                color: white; padding: 5px 15px; border-radius: 20px;
                font-size: 0.8em; display: inline-block; margin: 10px 0 20px;
            }
            .upload-area {
                border: 3px dashed #06b6d4; border-radius: 12px;
                padding: 50px; margin: 30px 0; cursor: pointer;
                background: #f8f9ff; transition: all 0.3s;
            }
            .upload-area:hover { background: #eef1ff; transform: scale(1.02); }
            .upload-area.dragover { background: #e0e7ff; border-color: #5a67d8; }
            
            .status {
                display: none; margin: 20px 0; padding: 15px;
                border-radius: 8px; font-size: 14px;
            }
            .status.show { display: block; }
            .status.loading { background: #e3f2fd; color: #1976d2; }
            .status.success { background: #e8f5e9; color: #388e3c; }
            .status.error { background: #ffebee; color: #d32f2f; }
            
            .spinner {
                border: 3px solid #f3f3f3; border-top: 3px solid #06b6d4;
                border-radius: 50%; width: 20px; height: 20px;
                animation: spin 1s linear infinite;
                display: inline-block; margin-right: 10px; vertical-align: middle;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            .btn {
                background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
                color: white; padding: 15px 30px; border: none;
                border-radius: 10px; font-size: 16px; font-weight: 600;
                cursor: pointer; transition: all 0.3s;
                box-shadow: 0 4px 15px rgba(6, 182, 212, 0.4);
                text-decoration: none; display: inline-block; margin: 10px;
            }
            .btn:hover { transform: translateY(-2px); }
            .btn:disabled { opacity: 0.5; cursor: not-allowed; }
            
            .features { 
                display: grid; grid-template-columns: 1fr 1fr;
                gap: 15px; margin-top: 30px; text-align: left;
            }
            .feature { 
                padding: 15px; background: #f8f9ff; border-radius: 8px;
                border-left: 4px solid #06b6d4;
            }
            .feature h3 { color: #06b6d4; font-size: 1em; margin-bottom: 5px; }
            .feature p { font-size: 0.85em; color: #666; }
            
            #reportFrame {
                display: none; width: 100%; height: 600px;
                border: 2px solid #06b6d4; border-radius: 10px;
                margin-top: 20px;
            }
            #reportFrame.show { display: block; }
            
            .action-buttons { display: none; margin-top: 15px; }
            .action-buttons.show { display: block; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 InsightIQ Analytics</h1>
            <div class="badge">AI Business Intelligence • Smart Analysis • Data-Driven Decisions</div>
            
            <div class="upload-area" id="uploadArea">
                <div style="font-size: 60px;">📊</div>
                <h2 style="margin: 15px 0;">Drop Your Data Here</h2>
                <p style="color: #666;">Excel (xls, xlsx, xlsm, xlsb) or CSV files up to 50MB</p>
                <input type="file" id="fileInput" accept=".xlsx,.xls,.xlsm,.xlsb,.csv,.ods,.odt" style="display:none">
            </div>
            
            <div class="status" id="status"></div>
            
            <div class="action-buttons" id="actionButtons">
                <a href="#" class="btn" id="downloadBtn" download="analysis_report.html">📥 Download Report</a>
                <button class="btn" onclick="window.open(downloadBtn.href, '_blank')">🔗 Open in New Tab</button>
                <button class="btn" id="newAnalysisBtn">📊 New Analysis</button>
            </div>
            
            <iframe id="reportFrame"></iframe>
            
            <div class="features">
                <div class="feature">
                    <h3>🤖 AI Chart Selection</h3>
                    <p>Intelligently chooses the most insightful visualizations</p>
                </div>
                <div class="feature">
                    <h3>📈 Executive Summary</h3>
                    <p>Business-focused insights, not just statistics</p>
                </div>
                <div class="feature">
                    <h3>🔍 Deep Profiling</h3>
                    <p>Patterns, anomalies, and relationships</p>
                </div>
                <div class="feature">
                    <h3>💡 Recommendations</h3>
                    <p>Actionable next steps based on your data</p>
                </div>
            </div>
        </div>

        <script>
            const uploadArea = document.getElementById('uploadArea');
            const fileInput = document.getElementById('fileInput');
            const statusDiv = document.getElementById('status');
            const reportFrame = document.getElementById('reportFrame');
            const actionButtons = document.getElementById('actionButtons');
            const downloadBtn = document.getElementById('downloadBtn');
            const newAnalysisBtn = document.getElementById('newAnalysisBtn');
            
            let currentReport = null;
            
            uploadArea.addEventListener('click', () => fileInput.click());
            fileInput.addEventListener('change', (e) => {
                if (e.target.files[0]) handleFile(e.target.files[0]);
            });
            
            uploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadArea.classList.add('dragover');
            });
            uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('dragover'));
            uploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadArea.classList.remove('dragover');
                if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
            });
            
            async function handleFile(file) {
                const validTypes = ['.xlsx', '.xls', '.xlsm', '.xlsb', '.csv', '.ods', '.odt', '.odf'];
                const fileExt = '.' + file.name.split('.').pop().toLowerCase();
                
                if (!validTypes.includes(fileExt)) {
                    showStatus('❌ Invalid file type. Please select Excel (xlsx, xls, xlsm, xlsb) or CSV files', 'error');
                    return;
                }
                
                if (file.size > 50 * 1024 * 1024) {
                    showStatus('❌ File too large. Maximum size: 50MB', 'error');
                    return;
                }
                
                showStatus('<span class="spinner"></span>Analyzing... This may take 30-45 seconds', 'loading');
                uploadArea.style.display = 'none';
                
                const formData = new FormData();
                formData.append('file', file);
                
                try {
                    const response = await fetch('/api/analyze', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (!response.ok) {
                        const errorText = await response.text();
                        showStatus('❌ Server error: ' + errorText, 'error');
                        uploadArea.style.display = 'block';
                        return;
                    }
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        showStatus('✅ Analysis complete!', 'success');
                        
                        // Decode base64 HTML if needed
                        let htmlReport = data.html_report;
                        if (data.is_base64) {
                            htmlReport = atob(htmlReport);
                        }
                        currentReport = htmlReport;
                        
                        // Show report inline (no popup!)
                        const blob = new Blob([currentReport], { type: 'text/html' });
                        const url = URL.createObjectURL(blob);
                        reportFrame.src = url;
                        reportFrame.classList.add('show');
                        
                        // Setup download
                        downloadBtn.href = url;
                        downloadBtn.download = 'analysis_report_' + file.name.replace(/\\.[^/.]+$/, '') + '.html';
                        actionButtons.classList.add('show');
                    } else {
                        showStatus('❌ Error: ' + (data.error || 'Analysis failed'), 'error');
                        uploadArea.style.display = 'block';
                    }
                } catch (error) {
                    showStatus('❌ Error: ' + error.message + ' (Check browser console for details)', 'error');
                    console.error('Full error:', error);
                    uploadArea.style.display = 'block';
                }
            }
            
            function showStatus(message, type) {
                statusDiv.innerHTML = message;
                statusDiv.className = 'status show ' + type;
            }
            
            newAnalysisBtn.addEventListener('click', () => {
                reportFrame.classList.remove('show');
                actionButtons.classList.remove('show');
                uploadArea.style.display = 'block';
                fileInput.value = '';
                statusDiv.classList.remove('show');
            });
        </script>
    </body>
    </html>
    """)

@app.route('/api/analyze', methods=['POST', 'OPTIONS'])
def analyze_file():
    """Main analysis endpoint"""
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"})
    
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file uploaded"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "error": "No file selected"}), 400
        
        print(f"\n🚀 Starting world-class analysis: {file.filename}")
        
        # Load data
        file_content = file.read()
        load_result = analyzer.load_excel(file_content, file.filename)
        if not load_result.get("success"):
            return jsonify(load_result), 400
        
        print(f"   ✓ Loaded: {load_result['rows']:,} rows × {load_result['columns']} columns")
        
        # Deep profiling
        print("   🔍 Deep profiling...")
        profile = analyzer.deep_data_profiling()
        
        # AI-driven chart selection
        print("   🤖 AI selecting optimal charts...")
        chart_recommendations = analyzer.ai_driven_chart_selection()
        print(f"   ✓ Recommended {len(chart_recommendations)} charts")
        
        # Create recommended charts
        print("   📊 Creating visualizations...")
        charts = analyzer.create_ai_recommended_charts(chart_recommendations)
        print(f"   ✓ Created {len(charts)} charts")
        
        # Generate executive insights
        print("   💡 Generating executive insights...")
        insights = analyzer.generate_executive_insights()
        
        # Generate HTML report
        print("   📝 Building report...")
        html_report = generate_executive_report(
            file.filename,
            profile,
            charts,
            chart_recommendations,
            insights
        )
        
        print(f"   ✅ Analysis complete!\n")
        print(f"   📊 Report size: {len(html_report):,} bytes\n")
        
        # Base64 encode the HTML to avoid JSON escaping issues
        import base64
        html_b64 = base64.b64encode(html_report.encode('utf-8')).decode('ascii')
        
        response = jsonify({
            "success": True,
            "html_report": html_b64,
            "is_base64": True,
            "chart_count": len(charts)
        })
        
        # Add explicit headers to prevent issues
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        response.headers['Cache-Control'] = 'no-cache'
        
        return response
        
    except Exception as e:
        print(f"   ❌ ERROR: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

def generate_executive_report(filename, profile, charts, recommendations, insights):
    """Generate beautiful executive report"""
    
    # Build charts section
    charts_html = ""
    for idx, (chart_name, chart_data) in enumerate(charts.items()):
        rec = recommendations[idx] if idx < len(recommendations) else {}
        title = rec.get('reason', chart_name.replace('_', ' ').title())
        insight = rec.get('insight', '')
        
        charts_html += f"""
        <div class="chart-card">
            <h3 style="color: #06b6d4; font-size: 1.3em; margin-bottom: 15px;">&#128200; {title}</h3>
            {f'<p class="chart-insight"><strong>Insight:</strong> {insight}</p>' if insight else ''}
            <img src="data:image/png;base64,{chart_data}" alt="{title}">
        </div>
        """
    
    # Build insights section with markdown formatting
    insights_text = insights.get('insights', 'No insights available')
    
    # Convert markdown-style formatting to HTML
    insights_formatted = insights_text
    # Bold: **text** -> <strong>text</strong>
    import re
    insights_formatted = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', insights_formatted)
    # Bullet points: - text -> <li>• text</li>
    insights_formatted = re.sub(r'^- (.+)$', r'<li>• \1</li>', insights_formatted, flags=re.MULTILINE)
    # Numbered lists: 1. text -> <li>• text</li>
    insights_formatted = re.sub(r'^\d+\.\s+(.+)$', r'<li>• \1</li>', insights_formatted, flags=re.MULTILINE)
    # Wrap consecutive <li> tags in <ul>
    insights_formatted = re.sub(r'(<li>.*?</li>)\s*(?=<li>)', r'\1', insights_formatted, flags=re.DOTALL)
    insights_formatted = re.sub(r'(<li>.*?</li>)', r'<ul>\1</ul>', insights_formatted, flags=re.DOTALL)
    # Fix multiple <ul> tags
    insights_formatted = re.sub(r'</ul>\s*<ul>', '', insights_formatted)
    # Line breaks
    insights_formatted = insights_formatted.replace('\n\n', '<br><br>').replace('\n', '<br>')
    
    insights_html = f"""
    <div class="section">
        <div class="insights-section">
            <h2 style="color: #0ea5e9; margin-bottom: 20px;">&#127919; Executive Insights</h2>
            <div class="insight-content">
                {insights_formatted}
            </div>
        </div>
    </div>
    """
    
    # Data quality section
    quality = profile.get('data_quality', {})
    quality_html = f"""
    <div class="section">
        <h2>&#128203; Data Quality Assessment</h2>
        <div class="quality-grid">
            <div class="quality-card">
                <div class="quality-label">Completeness</div>
                <div class="quality-value">{100 - quality.get('missing_percentage', 0):.1f}%</div>
                <div class="quality-detail">{quality.get('total_missing', 0):,} missing values</div>
            </div>
            <div class="quality-card">
                <div class="quality-label">Uniqueness</div>
                <div class="quality-value">{100 - quality.get('duplicate_percentage', 0):.1f}%</div>
                <div class="quality-detail">{quality.get('duplicate_rows', 0):,} duplicates</div>
            </div>
        </div>
    </div>
    """
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Executive Analysis Report - {filename}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f7fa; color: #333; line-height: 1.6;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 40px 20px; }}
        
        .header {{ 
            background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
            color: white; padding: 50px 40px; border-radius: 15px;
            margin-bottom: 30px; box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .header .subtitle {{ opacity: 0.9; font-size: 1.1em; }}
        .header .meta {{ margin-top: 20px; font-size: 0.9em; opacity: 0.8; }}
        
        .section {{ 
            background: white; padding: 40px; border-radius: 12px;
            margin-bottom: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        h2 {{ color: #06b6d4; margin-bottom: 25px; font-size: 1.8em; }}
        h3 {{ color: #555; margin: 15px 0; font-size: 1.3em; }}
        
        .chart-card {{ 
            background: #f0fdff; padding: 25px; border-radius: 10px;
            margin: 25px 0; border-left: 4px solid #06b6d4;
        }}
        .chart-card img {{ 
            max-width: 100%; height: auto; border-radius: 8px;
            margin-top: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .chart-insight {{ 
            color: #666; font-style: italic; margin: 10px 0;
            padding: 10px; background: white; border-radius: 6px;
        }}
        
        .insights-section {{ 
            background: linear-gradient(to bottom, #f0f9ff 0%, #e0f2fe 100%);
            padding: 35px; border-radius: 12px; border-left: 6px solid #0ea5e9;
            box-shadow: 0 4px 15px rgba(14, 165, 233, 0.1);
        }}
        .insight-content {{ 
            font-size: 1.1em; line-height: 1.9; color: #333;
        }}
        .insight-content strong {{
            color: #0369a1; font-weight: 700;
        }}
        .insight-content ul {{
            margin: 15px 0; padding-left: 0; list-style: none;
        }}
        .insight-content li {{
            padding: 12px 20px; margin: 8px 0;
            background: white; border-radius: 8px;
            border-left: 4px solid #0ea5e9;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }}
        .insight-content br {{
            display: block; content: ""; margin: 8px 0;
        }}
        
        .quality-grid {{ 
            display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px; margin-top: 20px;
        }}
        .quality-card {{ 
            background: linear-gradient(135deg, #f8f9ff 0%, #eef1ff 100%);
            padding: 25px; border-radius: 10px; text-align: center;
            border: 2px solid #e0e7ff;
        }}
        .quality-label {{ font-size: 0.9em; color: #666; margin-bottom: 10px; }}
        .quality-value {{ 
            font-size: 2.5em; font-weight: bold; color: #06b6d4;
            margin: 10px 0;
        }}
        .quality-detail {{ font-size: 0.85em; color: #999; }}
        
        .footer {{ 
            text-align: center; padding: 40px; color: #999;
            font-size: 0.9em; margin-top: 40px;
        }}
        
        @media print {{
            body {{ background: white; }}
            .section {{ box-shadow: none; border: 1px solid #ddd; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>&#128202; Executive Analysis Report</h1>
            <div class="subtitle">AI-Powered Data Intelligence Platform</div>
            <div class="meta">
                &#128196; <strong>{filename}</strong> &nbsp;&nbsp;&bull;&nbsp;&nbsp; &#128336; {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
            </div>
        </div>
        
        <div class="section">
            <h2>&#128200; Dataset Overview</h2>
            <div class="quality-grid">
                <div class="quality-card">
                    <div class="quality-label">Total Records</div>
                    <div class="quality-value">{profile['basic_info']['shape']['rows']:,}</div>
                </div>
                <div class="quality-card">
                    <div class="quality-label">Data Points</div>
                    <div class="quality-value">{profile['basic_info']['shape']['columns']}</div>
                </div>
                <div class="quality-card">
                    <div class="quality-label">Patterns Detected</div>
                    <div class="quality-value">{len(profile.get('patterns', {}))}</div>
                </div>
            </div>
        </div>
        
        {quality_html}
        
        {insights_html}
        
        <div class="section">
            <h2>&#128200; AI-Recommended Visualizations</h2>
            <p style="color: #666; margin-bottom: 30px; font-size: 1.05em; padding: 15px; background: #f0fdff; border-radius: 8px; border-left: 4px solid #06b6d4;">
                &#128161; <strong>Smart Analysis:</strong> These charts were intelligently selected by AI to reveal the most important patterns and insights in your data.
            </p>
            {charts_html}
        </div>
        
        <div class="footer">
            <p style="font-size: 1.1em; font-weight: 600; color: #06b6d4; margin-bottom: 10px;">InsightIQ Analytics by Black Lab AI</p>
            <p style="color: #999;">AI-Powered Business Intelligence • Generated with cutting-edge analytics</p>
        </div>
    </div>
</body>
</html>"""

if __name__ == '__main__':
    print("=" * 80)
    print("  📊 INSIGHTIQ ANALYTICS - AI Business Intelligence")
    print("=" * 80)
    print()
    print("🚀 Features:")
    print("   • AI-powered data analysis")
    print("   • Smart chart generation")
    print("   • Executive insights")
    print("   • Automatic pattern detection")
    print("   • Beautiful shareable reports")
    print()
    print("🌐 Server: http://127.0.0.1:5001")
    print()
    print("=" * 80)
    print()
    
    app.run(host='0.0.0.0', port=5001, debug=True)
