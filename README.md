# Agentic Probabilistic Crypto Return Analysis Service

Capstone project for building an agentic AI system that analyzes historical cryptocurrency market regimes and produces probabilistic return scenarios to support investment decision making.

⚠️ This project is for academic and research purposes only. It is NOT financial advice.

---

## 📌 Project Overview

This system aims to:
- Collect crypto market data from CoinGecko and Yahoo Finance
- Detect historical market regimes and similar periods
- Generate probabilistic return distributions
- Recommend portfolio allocation based on user risk profile
- Provide transparent explanations for all outputs

---

## 🧱 Repository Structure


api/ # FastAPI application and endpoints
core/ # Modeling, regime detection, scenario generation
data/
├── raw/
└── processed/
notebooks/ # Experiments and EDA only
docs/ # Architecture, reports, weekly updates
tests/ # Unit tests
.github/ # PR and issue templates



---

## 🚀 Getting Started

Clone the repository:

```bash
git clone <repo_url>
cd agentic-crypto-return-service



## Install Dependencies
pip install -r requirements.txt


## Run API:
uvicorn api.main:app --reload

##🌿 Branching Strategy
We follow this workflow:
main → stable milestone-ready code
dev → integration branch
feature/<name> → task specific branches
All merges must go through Pull Requests.

##🤝 Team Workflow
Create a feature branch from dev
Open a PR back to dev
At least one team member must approve
main is protected

##📄 License
This project is licensed under the MIT License.
