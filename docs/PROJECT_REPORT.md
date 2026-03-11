Section 1.2: Agentic AI Rationale (Draft Report) solmaz
Why "Agentic" instead of a Traditional ML Model?
Traditional cryptocurrency return models (like simple LSTMs or Regression scripts) are typically "static." They process a fixed dataset and output a single number. Our project adopts an Agentic Framework for three primary reasons:

Dynamic Tool Use (ReAct Logic):
Unlike a script that expects a CSV, an Agent can use external tools. In our architecture, the agent is equipped with a Data Retrieval Tool (calling APIs like Binance or CoinGecko) and a Financial Analysis Tool. This allows the system to fetch live market data autonomously rather than relying on stale datasets.

Handling Multi-Modal Complexity:
Crypto returns are influenced by more than just historical price. An agentic approach allows for Multi-Agent Orchestration. We can deploy a "Technical Analyst Agent" to look at price trends and a "Sentiment Analyst Agent" to scan news/social media. A lead "Coordinator Agent" then synthesizes these diverse outputs into a final return report.

Self-Correction and Reasoning:
Traditional models often produce "black-box" outputs. By using an agentic loop (Reason + Act), our system generates a "Chain of Thought." This provides the user with the reasoning behind a predicted return (e.g., "I am predicting a 2% return because the RSI is oversold AND recent news indicates a positive regulatory shift"). This transparency is vital for financial applications.

Innovation & Real-World Viability
Our solution bridges the gap between a raw predictive model and a functional financial advisor. By automating the entire pipeline—from data sourcing to final risk assessment—we reduce the "human-in-the-loop" requirement, making it a scalable solution for real-time portfolio monitoring.
