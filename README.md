# Market Sentiment & Trading Behavior Analysis

## Executive Summary
This project analyzes how Bitcoin market sentiment (Fear & Greed Index) influences trader performance and behavior. By combining sentiment data with historical trading records, the study identifies patterns to improve profitability, risk control, and strategy design.

## 📋 Setup

### Prerequisites
- Python 3.8+
- Jupyter Notebook

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/Market-Sentiment-Trading-Behavior-Analysis.git
   cd Market-Sentiment-Trading-Behavior-Analysis
   ```

2. **Install dependencies**
   ```bash
   pip install pandas numpy matplotlib seaborn jupyter
   ```

## 🚀 How to Run

1. **Start Jupyter Notebook**
   ```bash
   jupyter notebook
   ```

2. **Open the notebook**
   - Navigate to `project.ipynb`
   - Click to open

3. **Run the analysis**
   - Click `Cell` → `Run All`
   - Or press `Shift + Enter` to run cells one by one

## 📁 Project Files

- `project.ipynb` - Main analysis notebook
- `data/` - Input data files (BTC Fear & Greed Index, trading data)
- `outputs/` - Generated visualizations

## 📝 Output

After running the notebook, visualizations will be saved in the `outputs/` folder.

---

## Methodology

**Data Sources**
- Bitcoin Fear & Greed Index (daily sentiment)
- Historical trading data (PnL, leverage, positions, trade type)

**Data Processing**
- Merged sentiment + trading data by date  
- Classified sentiment: Fear, Greed, Neutral  
- Calculated ROI, win rate, and risk proxies  
- Identified contrarian vs non-contrarian trades  
- Segmented Spot vs Derivatives trading  

**Analytical Approach**
- Performance comparison across sentiment regimes  
- Contrarian vs non-contrarian profitability  
- Risk-adjusted return analysis  
- Behavioral pattern analysis  

**Key Questions**
- Does performance (PnL, win rate, drawdown proxy) differ between Fear vs Greed days?  
- Do traders change behavior based on sentiment (frequency, leverage, long/short bias, position size)?  

---

## Key Insights

**Performance vs Sentiment**
- **Fear** days make the most money but are twice as risky..  
- You win just as often in any market, but Fear and Greed pay bigger—and lose bigger.  
- **Neutral** markets offer **stability** at the cost of profits—half the risk, half the reward.  

**Behavior vs Sentiment**
- Traders increase **frequency and position size during fear** periods.  
- Fear-driven aggression does **not translate to higher returns**.  
- Greed periods show lower activity but **better trade efficiency**.  

**Strategy & Style**
- **Contrarian trades** generate ~2× higher profit than non-contrarian.  
- **Spot trading** outperforms derivatives in consistency and risk-adjusted returns.  

---

## Strategy Recommendations

- **Adopt contrarian approach:** Buy in fear, sell in greed.  
- **Focus on greed periods:** Higher ROI and win rate observed.  
- **Prefer spot over derivatives:** Better consistency and lower risk.  
- **Control overtrading in fear markets:** High activity ≠ better returns.  
- **Use neutral sentiment for entries:** Strongest risk-adjusted opportunities.  
- **Track sentiment daily:** Adjust leverage, size, and exposure accordingly.  

---

## Conclusion
Trader behavior shifts significantly with market sentiment, but higher activity does not always yield better results.  
Best performance comes from:
- Contrarian positioning  
- Sentiment-aware execution  
- Strong risk discipline  

---
*Analysis Date: 2026-02-05*

