# System Architecture (W5)

This document provides a high level visualization of the Agentic
Probabilistic Crypto Return Analysis Service.

------------------------------------------------------------------------

## High Level Architecture Diagram

``` mermaid
flowchart LR
    Client("Client") -->|"HTTP"| API("api: FastAPI")
    API -->|"AR"| SVC("core/services")
    SVC -->|"run_analysis"| AG("core/agents")

    AG -->|"Q"| DA("core/data_access")
    DA -->|"DS, FS"| AG

    DRAW[("data/raw")] -->|"raw"| PL("core/pipelines")
    PL -->|"artifacts"| DPROC[("data/processed")]
    AG -->|"optional"| PL

    AG -->|"FS"| RD("core/regime_detection")
    RD -->|"RS"| AG

    AG -->|"FS, MC"| MD("core/models")
    MD -->|"MO"| AG

    AG -->|"MO, SC, RS"| SE("core/scenario_engine")
    SE -->|"SS"| AG

    AG -->|"SS, RC"| RK("core/risk")
    RK -->|"RR"| AG

    AG -->|"optional"| PF("core/portfolio")
    PF -->|"PR"| AG

    AG -->|"RES"| SVC
    SVC -->|"RES"| API
    API -->|"HTTP"| Client
```

------------------------------------------------------------------------

## Legend (Abbreviations)

-   AR: AnalysisRequest\
-   RES: AnalysisResult\
-   Q: MarketDataQuery\
-   DS: MarketDataset\
-   FS: FeatureSet\
-   RS: RegimeState\
-   MC: ModelConfig\
-   MO: ModelOutput\
-   SC: ScenarioConfig\
-   SS: ScenarioSet\
-   RC: RiskConfig\
-   RR: RiskReport\
-   PR: PortfolioResult

------------------------------------------------------------------------

## Notes

-   `api/` handles HTTP validation and response serialization only.
-   `core/agents` orchestrates the end to end workflow.
-   `core/services` is the stable boundary between API and internal
    logic.
-   `data/raw` stores unprocessed inputs.
-   `data/processed` stores curated and versioned artifacts.
-   The diagram reflects an advanced API where scenario and risk
    parameters are explicitly configurable.
