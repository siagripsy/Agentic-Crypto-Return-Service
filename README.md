This is a test text for branches.



# Agentic Probabilistic Crypto Return Analysis Service

Capstone project focused on building an agentic AI system that analyzes
historical cryptocurrency market regimes and generates probabilistic
return scenarios to support investment decision making.

⚠️ **Disclaimer:** This project is for academic and research purposes
only. It is NOT financial advice.

------------------------------------------------------------------------

## 📌 Project Overview

This system aims to:

-   Collect crypto market data from CoinGecko and Yahoo Finance
-   Identify historical market regimes and similar periods
-   Generate probabilistic return distributions
-   Recommend portfolio allocation based on user risk profile
-   Provide transparent explanations for all outputs
-   Expose results through an API interface

------------------------------------------------------------------------

## 🧱 Repository Structure

    api/            # FastAPI application and endpoints
    core/           # Modeling, regime detection, scenario generation
    data/
      ├── raw/
      └── processed/
    notebooks/      # Experiments and exploratory analysis
    docs/           # Architecture, project charter, weekly updates
    tests/          # Unit tests
    .github/        # PR and issue templates

------------------------------------------------------------------------

## 🚀 Getting Started

Clone the repository:

``` bash
git clone <REPO_URL>
cd agentic-crypto-return-service
```

Create a virtual environment named **Capstone_env**:

``` bash
python -m venv Capstone_env
```

Activate it:

**Windows**

``` bash
Capstone_env\Scripts\activate
```

**Mac/Linux**

``` bash
source Capstone_env/bin/activate
```

Install dependencies:

``` bash
pip install -r requirements.txt
```

------------------------------------------------------------------------

## ▶️ Running the Project (later milestones)

When the API is implemented:

``` bash
uvicorn api.main:app --reload
```

------------------------------------------------------------------------

## 🌿 Branching Strategy

We follow this workflow:

-   `main`\
    Stable, milestone ready code

-   `dev`\
    Integration branch for ongoing work

-   `feature/<short-description>`\
    Task specific development branches

All merges must go through Pull Requests.

------------------------------------------------------------------------

## 🤝 Team Workflow

1.  Create a feature branch from `dev`
2.  Commit changes with clear messages
3.  Open a Pull Request back to `dev`
4.  At least one team member must approve
5.  Direct pushes to `main` are not allowed

------------------------------------------------------------------------

## 📝 Commit Message Convention

Use short, descriptive messages:

-   `feat: add regime clustering module`
-   `fix: handle missing values`
-   `docs: update architecture diagram`
-   `chore: update dependencies`

------------------------------------------------------------------------

## 📚 Documentation

Full project documentation, including the Project Charter and
architecture design, can be found in the `docs/` directory.

------------------------------------------------------------------------

## 📄 License

This project is licensed under the MIT License.

------------------------------------------------------------------------

## 📍 Status

This repository is under active development as part of a Capstone
project.
