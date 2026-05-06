# Gemini Integration

<cite>
**Referenced Files in This Document**   
- [GEMINI_README.md](file://GEMINI_README.md)
- [factcheck/utils/llmclient/gemini_client.py](file://factcheck/utils/llmclient/gemini_client.py)
- [factcheck/utils/llmclient/base.py](file://factcheck/utils/llmclient/base.py)
- [factcheck/utils/llmclient/__init__.py](file://factcheck/utils/llmclient/__init__.py)
- [factcheck/core/ClaimVerify.py](file://factcheck/core/ClaimVerify.py)
- [factcheck/core/Decompose.py](file://factcheck/core/Decompose.py)
- [factcheck/core/QueryGenerator.py](file://factcheck/core/QueryGenerator.py)
- [factcheck/core/Retriever/serper_retriever.py](file://factcheck/core/Retriever/serper_retriever.py)
- [factcheck/utils/api_config.py](file://factcheck/utils/api_config.py)
- [factcheck/utils/prompt/chatgpt_prompt.py](file://factcheck/utils/prompt/chatgpt_prompt.py)
- [webapp.py](file://webapp.py)
- [factcheck/config/api_config.yaml](file://factcheck/config/api_config.yaml)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)

## Introduction
The Gemini Integration documentation provides a comprehensive overview of a fact-checking system built around Google's Gemini API. This system is designed to detect fake news by decomposing input text into claims, retrieving relevant evidence via web search, and verifying claims using Gemini's large language models. The integration has been optimized specifically for Gemini, removing support for other LLM providers such as OpenAI and Claude. The system supports both web interface and command-line usage, with configurable models including `gemini-1.5-pro`, `gemini-1.5-flash`, and `gemini-pro`. This document details the architecture, implementation, API interfaces, and practical usage patterns for effective integration and troubleshooting.

## Project Structure
The project follows a modular structure organized by functionality and components. The main application logic resides in the `factcheck` directory, which contains core modules for claim decomposition, evidence retrieval, and verification. The `utils` directory houses shared components including the LLM client abstraction, prompt management, and configuration handling. External API keys are managed through configuration files, and the system provides both a web interface (`webapp.py`) and command-line execution capabilities.

```mermaid
graph TB
subgraph "Main Application"
webapp[webapp.py]
factcheck_module[factcheck/]
end
subgraph "Core Processing"
Decompose[core/Decompose.py]
QueryGenerator[core/QueryGenerator.py]
Retriever[core/Retriever/]
ClaimVerify[core/ClaimVerify.py]
end
subgraph "Utilities"
llmclient[utils/llmclient/]
prompt[utils/prompt/]
api_config[utils/api_config.py]
data_class[utils/data_class.py]
end
subgraph "Configuration"
api_config_yaml[factcheck/config/api_config.yaml]
GEMINI_README[GEMINI_README.md]
end
webapp --> factcheck_module
factcheck_module --> Decompose
factcheck_module --> QueryGenerator
factcheck_module --> Retriever
factcheck_module --> ClaimVerify
factcheck_module --> llmclient
factcheck_module --> prompt
factcheck_module --> api_config
llmclient --> base[BaseClient]
llmclient --> gemini[GeminiClient]
api_config --> api_config_yaml
```

**Diagram sources**
- [factcheck/__init__.py](file://factcheck/__init__.py)
- [webapp.py](file://webapp.py)

**Section sources**
- [factcheck/__init__.py](file://factcheck/__init__.py)
- [webapp.py](file://webapp.py)

## Core Components
The system's core functionality revolves around four main components: claim decomposition, query generation, evidence retrieval, and claim verification. These components work sequentially to analyze input text and produce fact-checking results. The entire pipeline is powered by the GeminiClient, which interfaces with Google's Gemini API for all language model operations. The system uses SERPER_API_KEY for web search functionality and GEMINI_API_KEY for all AI processing tasks. Configuration is centralized through the api_config.yaml file, and the architecture has been streamlined to support only Gemini models, removing legacy support for other LLM providers.

**Section sources**
- [GEMINI_README.md](file://GEMINI_README.md)
- [factcheck/utils/llmclient/gemini_client.py](file://factcheck/utils/llmclient/gemini_client.py)
- [factcheck/core/Decompose.py](file://factcheck/core/Decompose.py)

## Architecture Overview
The system architecture follows a pipeline pattern where input text flows through a series of processing stages. The web interface or command-line input is first processed by the main application controller, which orchestrates the fact-checking workflow. The text is decomposed into individual claims, each claim is used to generate search queries, evidence is retrieved from web search via Serper API, and finally each claim is verified against the collected evidence using Gemini's language model. The architecture is designed with rate limiting in mind, accommodating Gemini's constraint of 15 requests per minute.

```mermaid
graph LR
A[Input Text] --> B[Claim Decomposition]
B --> C[Query Generation]
C --> D[Evidence Retrieval]
D --> E[Claim Verification]
E --> F[Results Aggregation]
F --> G[Output Report]
subgraph "API Dependencies"
D --> H[Serper API]
E --> I[Gemini API]
end
style A fill:#f9f,stroke:#333
style G fill:#bbf,stroke:#333
```

**Diagram sources**
- [factcheck/core/Decompose.py](file://factcheck/core/Decompose.py)
- [factcheck/core/QueryGenerator.py](file://factcheck/core/QueryGenerator.py)
- [factcheck/core/Retriever/serper_retriever.py](file://factcheck/core/Retriever/serper_retriever.py)
- [factcheck/core/ClaimVerify.py](file://factcheck/core/ClaimVerify.py)

## Detailed Component Analysis

### Gemini Client Implementation
The GeminiClient class serves as the primary interface to Google's Gemini API, handling all LLM operations within the fact-checking system. It extends the BaseClient abstract class and implements the necessary methods for API communication, rate limiting, and response processing. The client is configured with a low temperature (0.1) to ensure consistent and deterministic outputs suitable for fact-checking tasks.

```mermaid
classDiagram
class BaseClient {
+str model
+dict api_config
+int max_requests_per_minute
+int request_window
+deque traffic_queue
+TokenUsage usage
+__init__(model, api_config, max_requests_per_minute, request_window)
+_call(messages) str
+_log_usage()
+get_usage() TokenUsage
+reset_usage()
+construct_message_list(prompt_list) list
+get_request_length(messages) int
+call(messages, num_retries, waiting_time) str
+set_model(model) void
+_async_call(messages) coroutine
+multi_call(messages_list) list
+_expire_old_traffic() void
}
class GeminiClient {
+__init__(model, api_config, max_requests_per_minute, request_window)
+_call(messages, **kwargs) str
+_clean_json_response(response_text) str
+_log_usage(usage_metadata) void
+get_request_length(messages) int
+construct_message_list(prompt_list, system_role) list
}
GeminiClient --|> BaseClient : inherits
class TokenUsage {
+str model
+int prompt_tokens
+int completion_tokens
+__init__(model)
+__add__(other) TokenUsage
+__str__() str
}
BaseClient o-- TokenUsage : uses
```

**Diagram sources**
- [factcheck/utils/llmclient/base.py](file://factcheck/utils/llmclient/base.py#L0-L99)
- [factcheck/utils/llmclient/gemini_client.py](file://factcheck/utils/llmclient/gemini_client.py#L0-L104)

**Section sources**
- [factcheck/utils/llmclient/base.py](file://factcheck/utils/llmclient/base.py#L0-L99)
- [factcheck/utils/llmclient/gemini_client.py](file://factcheck/utils/llmclient/gemini_client.py#L0-L104)

### Claim Verification Process
The ClaimVerify component is responsible for assessing the factual accuracy of claims against retrieved evidence. It takes a dictionary of claims and their corresponding evidence, then uses the Gemini model to analyze the relationship between each claim and evidence piece. The verification process includes reasoning generation and relationship classification (support, refute, or neutral).

```mermaid
sequenceDiagram
participant CV as ClaimVerify
participant LLM as GeminiClient
participant P as Prompt
participant E as Evidence
CV->>CV : verify_claims(claim_evidences_dict)
loop For each claim
CV->>P : Generate verification prompt
CV->>LLM : _call(prompt)
LLM->>LLM : Extract user content
LLM->>LLM : Configure generation (temp=0.1)
LLM->>I : generate_content(user_content)
I-->>LLM : Response
LLM->>LLM : Extract text from response
LLM->>LLM : _clean_json_response()
LLM->>LLM : _log_usage()
LLM-->>CV : Verification result
CV->>CV : Create Evidence object
end
CV->>CV : Aggregate results by claim
CV-->>Caller : claim_verifications_dict
```

**Diagram sources**
- [factcheck/core/ClaimVerify.py](file://factcheck/core/ClaimVerify.py#L0-L96)
- [factcheck/utils/llmclient/gemini_client.py](file://factcheck/utils/llmclient/gemini_client.py#L0-L104)

**Section sources**
- [factcheck/core/ClaimVerify.py](file://factcheck/core/ClaimVerify.py#L0-L96)

### Fact-Checking Pipeline Flow
The complete fact-checking process follows a structured workflow from input to output. This flowchart illustrates the step-by-step execution of the system, showing both the main processing path and error handling mechanisms.

```mermaid
flowchart TD
Start([Start]) --> ParseInput["Parse Input Text"]
ParseInput --> IsEmpty{"Text Empty?"}
IsEmpty --> |Yes| ReturnError["Return Error"]
IsEmpty --> |No| DecomposeClaims["Decompose into Claims"]
DecomposeClaims --> HasClaims{"Claims Found?"}
HasClaims --> |No| ReturnNeutral["Return Neutral Result"]
HasClaims --> |Yes| GenerateQueries["Generate Search Queries"]
GenerateQueries --> RetrieveEvidence["Retrieve Evidence via Serper"]
RetrieveEvidence --> HasEvidence{"Evidence Found?"}
HasEvidence --> |No| UseClaimAsEvidence["Use Claim as Evidence"]
HasEvidence --> |Yes| Continue
UseClaimAsEvidence --> Continue
Continue --> VerifyClaims["Verify Claims with Gemini"]
VerifyClaims --> ProcessResults["Process Verification Results"]
ProcessResults --> Aggregate["Aggregate Final Results"]
Aggregate --> FormatOutput["Format Output Report"]
FormatOutput --> End([End])
ReturnError --> End
ReturnNeutral --> End
style Start fill:#9f9,stroke:#333
style End fill:#f99,stroke:#333
style ReturnError fill:#f99,stroke:#333
style ReturnNeutral fill:#fd9,stroke:#333
```

**Diagram sources**
- [factcheck/core/Decompose.py](file://factcheck/core/Decompose.py)
- [factcheck/core/QueryGenerator.py](file://factcheck/core/QueryGenerator.py)
- [factcheck/core/Retriever/serper_retriever.py](file://factcheck/core/Retriever/serper_retriever.py)
- [factcheck/core/ClaimVerify.py](file://factcheck/core/ClaimVerify.py)

## Dependency Analysis
The system has a clear dependency hierarchy with well-defined interfaces between components. The core modules depend on utility classes for LLM interaction, configuration management, and data structures. The architecture has been simplified by removing support for multiple LLM providers, resulting in a focused dependency on Google's Gemini API and the Serper API for web search.

```mermaid
graph TD
webapp --> factcheck
factcheck --> Decompose
factcheck --> QueryGenerator
factcheck --> Retriever
factcheck --> ClaimVerify
factcheck --> utils
utils --> llmclient
utils --> prompt
utils --> api_config
utils --> data_class
llmclient --> base
llmclient --> gemini_client
llmclient --> __init__
Retriever --> serper_retriever
Retriever --> google_retriever
Retriever --> base
ClaimVerify --> Evidence[data_class.Evidence]
gemini_client --> google.generativeai
serper_retriever --> requests
style webapp fill:#cfc
style factcheck fill:#cfc
style utils fill:#cfc
style llmclient fill:#cfc
style Retriever fill:#cfc
style ClaimVerify fill:#cfc
```

**Diagram sources**
- [factcheck/__init__.py](file://factcheck/__init__.py)
- [factcheck/utils/llmclient/__init__.py](file://factcheck/utils/llmclient/__init__.py)
- [requirements.txt](file://requirements.txt)

**Section sources**
- [factcheck/__init__.py](file://factcheck/__init__.py)
- [requirements.txt](file://requirements.txt)

## Performance Considerations
The system is optimized for Gemini's rate limits of 15 requests per minute, with built-in traffic management in the BaseClient class. The GeminiClient inherits rate limiting functionality that tracks request timestamps in a deque and enforces the maximum request rate. For high-volume usage, the asynchronous execution pattern allows for efficient batching of requests within the rate limit constraints. The low temperature setting (0.1) reduces variability in responses, improving consistency for fact-checking tasks. Token usage is tracked through the TokenUsage class, enabling monitoring of API consumption. For optimal performance, users should consider using the `gemini-1.5-flash` model for faster response times when high reasoning complexity is not required.

**Section sources**
- [factcheck/utils/llmclient/base.py](file://factcheck/utils/llmclient/base.py#L0-L99)
- [factcheck/utils/llmclient/gemini_client.py](file://factcheck/utils/llmclient/gemini_client.py#L0-L104)

## Troubleshooting Guide
Common issues and their solutions:

**API Key Errors**: Ensure both SERPER_API_KEY and GEMINI_API_KEY are set in api_config.yaml. The system will fail if either key is missing or invalid.

**Rate Limit Exceeded**: The system automatically handles rate limiting, but excessive usage may cause delays. Monitor the traffic queue and consider spreading requests over time.

**Empty Response from Gemini**: This may occur due to malformed prompts or API issues. Check the input format and ensure the prompt follows the expected structure.

**No Evidence Retrieved**: Verify that the Serper API key is valid and that the search queries are well-formed. Some claims may not yield relevant search results.

**JSON Parsing Errors**: Gemini responses may include markdown code blocks. The _clean_json_response method handles this, but malformed JSON may still cause parsing issues.

**Model Not Supported**: Only Gemini models are supported. Using other model names will raise a ValueError in the model2client function.

```python
# Example of proper API key configuration
# api_config.yaml
SERPER_API_KEY: "your_serper_api_key_here"
GEMINI_API_KEY: "your_gemini_api_key_here"
```

**Section sources**
- [GEMINI_README.md](file://GEMINI_README.md)
- [factcheck/utils/llmclient/gemini_client.py](file://factcheck/utils/llmclient/gemini_client.py#L0-L104)
- [factcheck/config/api_config.yaml](file://factcheck/config/api_config.yaml)

## Conclusion
The Gemini Integration provides a robust fact-checking system optimized for Google's Gemini API. By focusing exclusively on Gemini models, the system achieves consistent performance and reliable results for claim verification tasks. The architecture follows a clear pipeline pattern with well-defined components for decomposition, evidence retrieval, and verification. The implementation includes proper rate limiting, error handling, and token usage tracking, making it suitable for both development and production use. The system supports multiple interaction methods through both web interface and command-line execution, providing flexibility for different use cases. With proper API key configuration and understanding of the rate limits, users can effectively leverage this tool for fake news detection and factual verification.