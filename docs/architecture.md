# System Architecture (W5)

This document provides a high level visualization of the Agentic Probabilistic Crypto Return Analysis Service.

## High Level Architecture Diagram

```mermaid
flowchart LR
    Client[Client / UI / Consumer] -->|HTTP JSON| API[api (FastAPI)]

    API -->|AnalysisRequest| SVC[core/services]

    SVC -->|run_analysis| AG[core/agents]

    AG -->|MarketDataQuery| DA[core/data_access]
    DA -->|MarketDataset / FeatureSet| AG

    AG -->|optional: build_processed_data| PL[core/pipelines]
    PL -->|artifacts to data/processed| DPROC[(data/processed)]
    DRAW[(data/raw)] --> PL

    AG -->|features| RD[core/regime_detection]
    RD -->|RegimeState| AG

    AG -->|FeatureSet + ModelConfig| MD[core/models]
    MD -->|ModelOutput| AG

    AG -->|ModelOutput + ScenarioConfig + RegimeState| SE[core/scenario_engine]
    SE -->|ScenarioSet| AG

    AG -->|ScenarioSet + RiskConfig| RK[core/risk]
    RK -->|RiskReport| AG

    AG -->|optional| PF[core/portfolio]
    PF -->|PortfolioResult| AG

    AG -->|AnalysisResult| SVC
    SVC -->|AnalysisResult| API
    API -->|HTTP Response JSON| Client
