Milestone 2 Project Report: Agentic Crypto Return Service


Submission Date: February 10, 2026

Project Repository: siagripsy/Agentic-Crypto-Return-Service

1. Project Overview
The Agentic Crypto Return Analysis Service is an autonomous AI system that evaluates historical cryptocurrency market regimes to generate probabilistic return scenarios. Unlike traditional single-point forecasting, this project provides a distribution of potential outcomes, allowing for more robust risk management in highly volatile markets.

2. Data Preparation & Handling (Rubric: 4/4)
Data Status: We have integrated real-time and historical data pipelines via the CoinGecko, Binance, and Yahoo Finance APIs.

Preprocessing Steps: * Interpolation: Missing time-series data points were filled to maintain continuity.

Scaling: Applied Min-Max normalization to price and volume features.

Versioning: Raw data is stored in data/raw/ and processed versions in data/processed/.

Challenges: To mitigate API rate limits, we implemented a local caching system that allows the prototype to remain functional during intensive testing without redundant API calls.

3. Feature Engineering Rationale (Rubric: 3/3)
Selected Features: Market Regime Clusters (Bull, Bear, Sideways), Relative Strength Index (RSI), and 7/25-day Simple Moving Averages (SMA).

Rationale: These features act as the "sensory inputs" for our AI Agent. By clustering these technical indicators, the system identifies the current "market state," allowing it to reason based on historical precedents rather than raw price alone.

4. Baseline Model & Core Prototype (Rubric: 5/5)
Core Prototype: We have developed a FastAPI backend skeleton (in the /api directory), which defines the system's service endpoints.

Baseline Model Performance: Our baseline utilizes K-Means Clustering for market regime detection and Linear Regression for initial return estimations.

[INSERT YOUR GOOGLE COLAB SCREENSHOT HERE]
Figure 1: Demonstration of the regime detection baseline and data visualization generated during our Google Colab testing phase.

Initial Results: The model successfully separates market regimes. While identifying trends, the prototype confirms that a simple linear baseline is insufficient for crypto's non-linear volatility, justifying our shift toward an agentic framework.

5. Technical Adaptability & Understanding (Rubric: 3/3)
Adaptations: Based on initial data exploration, we moved from predicting a single "target price" to Probabilistic Scenario Generation.

Refined Path: We are now pursuing a ReAct (Reason + Act) Agentic framework for Milestone 3, which will allow the system to explain the "why" behind its generated scenarios.

6. Progress & Planning (Rubric: 3/3)
Status Review: Milestone 2 goals (Data pipeline, API skeleton, and baseline) are complete.

3-Week Plan (Target: Milestone 3):

Integration: Connecting the modeling logic to the FastAPI endpoints.

Scenario Engine: Developing a Monte Carlo simulator for return distributions.

UI Prototype: Designing a basic Streamlit dashboard for user interaction.

7. Professionalism & Collaboration (Rubric: 2/2)
Workflow: We utilize a Gitflow branching strategy (main, dev, and feature branches) with over 35 commits showing active daily progress.

Management: Our Trello Board tracks task completion and documentation milestones to ensure transparent team communication.

8. References
[1] S. Tedy and Solmaz, "Agentic-Crypto-Return-Service Source Code," GitHub, 2026. [Online]. Available: https://github.com/siagripsy/Agentic-Crypto-Return-Service.

[2] "Project Management and Task Tracking," Trello, 2026. [Online Management Tool].

[3] Google Gemini, "AI Collaborative Documentation and Architecture Support," Google AI, Feb. 2026. [Generative AI chat].

[4] CoinGecko, "Cryptocurrency Data API Documentation," 2026. [Online]. Available: https://www.coingecko.com/en/api/documentation.

[5] Binance, "Binance Spot API Docs," 2026. [Online]. Available: https://binance-docs.github.io/apidocs/spot/en/.
