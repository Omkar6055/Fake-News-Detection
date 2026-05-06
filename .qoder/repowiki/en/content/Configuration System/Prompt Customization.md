# Prompt Customization

<cite>
**Referenced Files in This Document**   
- [sample_prompt.yaml](file://factcheck\config\sample_prompt.yaml) - *Template for YAML-based prompt configuration with enhanced context preservation*
- [base.py](file://factcheck\utils\prompt\base.py) - *Base class definition for prompt templates*
- [chatgpt_prompt.py](file://factcheck\utils\prompt\chatgpt_prompt.py) - *ChatGPT-optimized prompt variants with updated context rules*
- [claude_prompt.py](file://factcheck\utils\prompt\claude_prompt.py) - *Claude-optimized prompt variants with updated context rules*
- [customized_prompt.py](file://factcheck\utils\prompt\customized_prompt.py) - *Extensibility mechanism for custom prompts*
</cite>

## Update Summary
**Changes Made**   
- Updated documentation to reflect enhanced claim decomposition with context preservation
- Added detailed context preservation rules and examples across all prompt templates
- Revised YAML configuration structure section to include new context preservation guidelines
- Updated LLM-specific prompt optimization section with changes to ChatGPT and Claude prompt templates
- Enhanced practical examples to demonstrate context-aware claim decomposition
- Added new examples for geographical, temporal, and entity context preservation
- Updated code snippets to reflect current implementation in all affected files

## Table of Contents
1. [Introduction](#introduction)
2. [Prompt Template Architecture](#prompt-template-architecture)
3. [YAML Configuration Structure](#yaml-configuration-structure)
4. [LLM-Specific Prompt Optimization](#llm-specific-prompt-optimization)
5. [Custom Prompt Extensibility](#custom-prompt-extensibility)
6. [Practical Prompt Modification Examples](#practical-prompt-modification-examples)
7. [Testing and Validation](#testing-and-validation)
8. [Common Issues and Solutions](#common-issues-and-solutions)
9. [Best Practices for Fact-Checking Prompts](#best-practices-for-fact-checking-prompts)

## Introduction
This document provides detailed technical documentation for the Prompt Customization system in OpenFactVerification, an open-source fact-checking framework. The system enables flexible configuration of language model behavior through YAML-based prompt templates that define the behavior across the entire fact-checking pipeline. This documentation covers the architecture of the prompt system, configuration options, and customization capabilities that allow users to adapt the system for different language models, languages, and use cases, with special emphasis on the recently enhanced context preservation capabilities in claim decomposition.

## Prompt Template Architecture
The Prompt Customization system is built around a modular architecture that separates prompt definitions from the core fact-checking logic. The system uses a base class structure defined in `base.py` that establishes the standard interface for all prompt templates.

```python
from dataclasses import dataclass

@dataclass
class BasePrompt:
    decompose_prompt: str = None
    checkworthy_prompt: str = None
    qgen_prompt: str = None
    verify_prompt: str = None
```

This base class defines four key prompt components that correspond to stages in the fact-checking pipeline:
- **decompose_prompt**: Handles claim decomposition with context preservation
- **checkworthy_prompt**: Assesses claim checkworthiness
- **qgen_prompt**: Generates verification queries
- **verify_prompt**: Performs final claim verification

All prompt implementations inherit from or follow the structure of this base class, ensuring consistency across different prompt variants.

**Section sources**   
- [base.py](file://factcheck\utils\prompt\base.py#L1-L10)

## YAML Configuration Structure
The system uses `sample_prompt.yaml` as a template for defining prompt behavior in a structured, human-readable format. The YAML configuration contains four main sections, each corresponding to a stage in the fact-checking pipeline, with significant enhancements to the claim decomposition process.

```yaml
decompose_prompt: |
  Your task is to decompose the text into atomic claims while preserving crucial context.
  The answer should be a JSON with a single key "claims", with the value of a list of strings, where each string should be a context-independent claim, representing one fact.
  
  CRITICAL CONTEXT PRESERVATION RULES:
  1. Each claim should be concise (less than 15 words) and self-contained.
  2. Avoid vague references like 'he', 'she', 'it', 'this', 'the company', 'the man' and use complete names.
  3. PRESERVE geographical locations, time periods, organizations, proper nouns, and causal relationships.
  4. When breaking down complex statements, maintain location/time/entity context in each relevant claim.
  5. Generate at least one claim for each single sentence in the texts.

  EXAMPLES WITH CONTEXT PRESERVATION:
  
  Text: Mary is a five-year old girl, she likes playing piano and she doesn't like cookies.
  Output:
  {{"claims": ["Mary is a five-year old girl.", "Mary likes playing piano.", "Mary doesn't like cookies."]}}

  Text: Protests in Nepal occurred due to social media bans.
  Output:
  {{"claims": ["Protests occurred in Nepal.", "Protests in Nepal were due to social media bans.", "Social media bans were imposed in Nepal."]}}

  Text: Did Elon Musk buy X in 2023?
  Output:
  {{"claims": ["Elon Musk bought X.", "Elon Musk bought X in 2023."]}}

  Text: Was Narendra Modi involved in Godhra riots?
  Output:
  {{"claims": ["Narendra Modi was involved in Godhra riots.", "Godhra riots occurred."]}}

  Text: Apple announced iPhone 15 launch in California during September 2023.
  Output:
  {{"claims": ["Apple announced iPhone 15 launch.", "Apple announced iPhone 15 launch in California.", "Apple announced iPhone 15 launch in September 2023.", "iPhone 15 launch occurred in California during September 2023."]}}

  Text: {doc}
  Output:
```

The enhanced YAML configuration now includes explicit context preservation rules and multiple examples demonstrating how to maintain geographical, temporal, and entity context during claim decomposition. These additions ensure that atomic claims retain essential contextual information that would otherwise be lost in the decomposition process.

**Section sources**   
- [sample_prompt.yaml](file://factcheck\config\sample_prompt.yaml)

## LLM-Specific Prompt Optimization
The system includes specialized prompt templates optimized for different language models and languages. These templates are implemented as separate Python modules that define prompt variants tailored to specific LLM characteristics, with recent updates to enhance context preservation.

### ChatGPT-Optimized Prompts
The `chatgpt_prompt.py` module contains prompts specifically designed for OpenAI's ChatGPT models. These prompts leverage ChatGPT's strengths in following complex instructions and generating structured JSON output.

```python
class ChatGPTPrompt:
    decompose_prompt = decompose_prompt
    restore_prompt = restore_prompt
    checkworthy_prompt = checkworthy_prompt
    qgen_prompt = qgen_prompt
    verify_prompt = verify_prompt
```

Key optimizations include:
- Explicit JSON formatting requirements
- Clear examples with expected output structure
- Step-by-step reasoning instructions
- Error handling guidance
- Enhanced context preservation rules for claim decomposition

The updated `decompose_prompt` now includes comprehensive context preservation guidelines and multiple examples demonstrating proper handling of geographical locations, time periods, organizations, and proper nouns.

### Claude-Optimized Prompts
The `claude_prompt.py` module contains prompts optimized for Anthropic's Claude models. These prompts are designed to work with Claude's constitutional AI principles and long-context capabilities.

Notable differences from ChatGPT prompts:
- More concise instruction sets
- Emphasis on ethical considerations
- Streamlined JSON output specifications
- Context-aware reasoning requirements
- Consistent context preservation rules across all prompt variants

The `claude_prompt.py` file has been updated to include the same context preservation rules and examples as the ChatGPT prompts, ensuring consistent behavior across different LLMs.

### Multilingual Support
The system supports multiple languages through language-specific prompt files. For example, `chatgpt_prompt_zh.py` provides Chinese-language prompts for ChatGPT:

```python
class ChatGPTPromptZH:
    decompose_prompt = decompose_prompt_zh
    checkworthy_prompt = checkworthy_prompt_zh
    qgen_prompt = qgen_prompt_zh
    verify_prompt = verify_prompt_zh
```

This approach allows the system to maintain consistent functionality across different languages while adapting to linguistic and cultural differences in fact-checking practices, including context preservation in multilingual settings.

**Section sources**   
- [chatgpt_prompt.py](file://factcheck\utils\prompt\chatgpt_prompt.py)
- [claude_prompt.py](file://factcheck\utils\prompt\claude_prompt.py)
- [chatgpt_prompt_zh.py](file://factcheck\utils\prompt\chatgpt_prompt_zh.py)

## Custom Prompt Extensibility
The system provides a flexible extensibility mechanism through the `customized_prompt.py` module, allowing users to define their own prompt templates without modifying the core codebase.

```python
class CustomizedPrompt(BasePrompt):
    def __init__(self, CustomizedPrompt):
        if CustomizedPrompt.endswith("yaml"):
            self.prompts = self.load_prompt_yaml(CustomizedPrompt)
        elif CustomizedPrompt.endswith("json"):
            self.prompts = self.load_prompt_json(CustomizedPrompt)
        else:
            raise NotImplementedError(f"File type of {CustomizedPrompt} not implemented.")
        keys = [
            "decompose_prompt",
            "checkworthy_prompt",
            "qgen_prompt",
            "verify_prompt",
        ]

        for key in keys:
            assert key in self.prompts, f"Key {key} not found in the prompt yaml file."
            setattr(self, key, self.prompts[key])
```

This implementation supports:
- YAML and JSON configuration formats
- Runtime loading of custom prompt files
- Validation of required prompt components
- Seamless integration with the existing pipeline

To create a custom prompt template, users can:
1. Copy `sample_prompt.yaml` as a starting point
2. Modify the prompts to suit their needs, ensuring proper context preservation
3. Load the custom template using the `CustomizedPrompt` class

**Section sources**   
- [customized_prompt.py](file://factcheck\utils\prompt\customized_prompt.py#L1-L33)

## Practical Prompt Modification Examples
Users can modify prompts to adjust tone, specificity, or reasoning depth based on their specific requirements, with special attention to context preservation.

### Adjusting Reasoning Depth
To increase reasoning depth in the verification step, modify the `verify_prompt` to include explicit chain-of-thought requirements:

```yaml
verify_prompt: |
  Your task is to evaluate the accuracy of a provided statement using the accompanying evidence. Apply the following reasoning process:
  1. Identify the key factual claims in the statement
  2. Compare each claim against the evidence
  3. Assess the reliability and relevance of the evidence
  4. Determine if the evidence supports, contradicts, or is unrelated to each claim
  5. Provide a final assessment with detailed justification
```

### Changing Tone and Formality
To make prompts more conversational for certain applications:

```yaml
checkworthy_prompt: |
  Help me figure out which of these statements contain facts that can actually be checked. Think about:
  - Is this just someone's opinion, or does it make a claim about reality?
  - Can we find evidence to prove or disprove this?
  - Does it have enough details to be verifiable?
```

### Increasing Specificity
For domain-specific fact-checking (e.g., medical claims), add specialized guidelines:

```yaml
verify_prompt: |
  Your task is to evaluate the accuracy of medical statements using the provided evidence. When assessing medical claims:
  - Prioritize evidence from peer-reviewed studies and reputable health organizations
  - Consider the date of the evidence (medical knowledge evolves)
  - Distinguish between correlation and causation
  - Note any limitations or uncertainties in the evidence
```

### Enhancing Context Preservation
To improve context preservation in claim decomposition:

```yaml
decompose_prompt: |
  Your task is to decompose the text into atomic claims while preserving crucial context.
  The answer should be a JSON with a single key "claims", with the value of a list of strings, where each string should be a context-independent claim, representing one fact.
  
  CRITICAL CONTEXT PRESERVATION RULES:
  1. Each claim should be concise (less than 15 words) and self-contained.
  2. Avoid vague references like 'he', 'she', 'it', 'this', 'the company', 'the man' and use complete names.
  3. PRESERVE geographical locations, time periods, organizations, proper nouns, and causal relationships.
  4. When breaking down complex statements, maintain location/time/entity context in each relevant claim.
  5. Generate at least one claim for each single sentence in the texts.
```

## Testing and Validation
Proper testing of custom prompts is essential to ensure reliable fact-checking performance.

### Syntax Validation
Validate YAML syntax using standard tools:
```bash
python -c "import yaml; print(yaml.safe_load(open('custom_prompt.yaml')))"`
```

### Functional Testing
Test prompts with sample inputs to verify:
- Correct JSON output format
- Appropriate reasoning depth
- Accurate fact-checking behavior
- Proper handling of edge cases
- Effective context preservation in claim decomposition

### Integration Testing
Verify that custom prompts work correctly within the full pipeline:
1. Test claim decomposition accuracy with context preservation
2. Validate checkworthiness assessment
3. Check query generation effectiveness
4. Evaluate final verification reliability

Use the system's test files (e.g., `test_claim_extraction.py`) as a starting point for creating comprehensive test suites.

## Common Issues and Solutions
### Template Variable Mismatches
**Symptom**: Prompts fail to substitute variables like `{claim}` or `{evidence}`
**Solution**: Verify that all template variables in the YAML file match the variables expected by the code. Check for typos in variable names.

### Token Overflow
**Symptom**: LLM responses are truncated or incomplete
**Solution**: 
- Shorten prompt instructions
- Remove redundant examples
- Use more concise language
- Split complex tasks into multiple steps

### LLM-Specific Formatting Issues
**Symptom**: Inconsistent JSON output or formatting errors
**Solution**:
- Add explicit formatting instructions
- Include examples of correctly formatted output
- Implement output parsing with error handling
- Test with the specific LLM version being used

### Performance Degradation
**Symptom**: Slow response times or timeouts
**Solution**:
- Optimize prompt length
- Reduce the number of examples
- Simplify instructions
- Cache frequently used prompt templates

## Best Practices for Fact-Checking Prompts
Follow these guidelines to maximize fact-checking accuracy and consistency:

### Clarity and Precision
- Use unambiguous language
- Define key terms and concepts
- Specify output format requirements
- Provide clear examples

### Consistency Across Pipeline Stages
- Maintain consistent terminology
- Align reasoning approaches across stages
- Ensure smooth handoff between pipeline components
- Use consistent JSON schema for structured output

### Bias Mitigation
- Avoid leading questions
- Include instructions for neutral assessment
- Emphasize evidence-based reasoning
- Encourage consideration of alternative interpretations

### Error Handling
- Include instructions for uncertain cases
- Specify how to handle contradictory evidence
- Define confidence levels for assessments
- Provide guidance for edge cases and exceptions

### Iterative Improvement
- Monitor prompt performance regularly
- Collect feedback from fact-checking results
- A/B test different prompt variants
- Update prompts based on performance data