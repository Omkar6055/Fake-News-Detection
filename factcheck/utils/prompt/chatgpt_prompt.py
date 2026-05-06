decompose_prompt = """
Decompose the text into atomic claims. Output JSON with key "claims" containing a list of self-contained factual statements.

Rules:
1. Each claim should be concise (<15 words) and self-contained.
2. Use complete names instead of pronouns (he/she/it/this).
3. Preserve locations, time periods, organizations, and proper nouns.

Example:
Text: Mary is a five-year old girl, she likes playing piano and she doesn't like cookies.
Output:
{{"claims": ["Mary is a five-year old girl.", "Mary likes playing piano.", "Mary doesn't like cookies."]}}

Text: {doc}
Output:
"""

restore_prompt = """Given a text and facts derived from it, map each fact to its source span in the text.
Output a JSON dict where keys are facts and values are the corresponding text spans.
Spans should concatenate to form the full original text.

Example:
Text: Mary is a five-year old girl, she likes playing piano and she doesn't like cookies.
Facts: ["Mary is a five-year old girl.", "Mary likes playing piano.", "Mary doesn't like cookies."]
Output:
{{"Mary is a five-year old girl.":"Mary is a five-year old girl,",
"Mary likes playing piano.":"she likes playing piano",
"Mary doesn't like cookies.":"and she doesn't like cookies."}}

Text: {doc}
Facts: {claims}
Output:
"""

checkworthy_prompt = """
Evaluate each statement: can its factuality be objectively verified? Respond in JSON with statement as key, "Yes" or "No" with brief reason as value.

Rules:
- Opinions = "No", Factual claims = "Yes"
- Vague references (e.g. "he is a professor") without clear subject = "No"

Example:
1. Gary Smith is a professor of economics.
2. He is a professor at MBZUAI.
3. Obama is the president of the UK.
Output:
{{
    "Gary Smith is a professor of economics.": "Yes (Verifiable factual claim about Gary Smith.)",
    "He is a professor at MBZUAI.": "No (Unclear who 'he' refers to.)",
    "Obama is the president of the UK.": "Yes (Verifiable claim about political leadership.)"
}}

Statements:
{texts}
Output:
"""

qgen_prompt = """Given a claim, generate the minimum questions needed to verify it. Output JSON with key "Questions" containing a list.

Example:
Claim: The Stanford Prison Experiment was conducted in the basement of Encina Hall.
Output: {{"Questions":["Where was Stanford Prison Experiment conducted?"]}}

Claim: {claim}
Output:
"""

verify_prompt = """
Decide if the evidence supports, refutes, or is irrelevant to the claim.
Output JSON with keys "reasoning" (brief explanation) and "relationship" ("SUPPORTS", "REFUTES", or "IRRELEVANT").

Example:
[claim]: MBZUAI is in Abu Dhabi, UAE.
[evidence]: MBZUAI is located in Masdar City, Abu Dhabi, UAE.
Output:
{{
    "reasoning": "Evidence confirms MBZUAI is in Abu Dhabi, UAE.",
    "relationship": "SUPPORTS"
}}

[claim]: {claim}
[evidences]: {evidence}
Output:
"""


class ChatGPTPrompt:
    decompose_prompt = decompose_prompt
    restore_prompt = restore_prompt
    checkworthy_prompt = checkworthy_prompt
    qgen_prompt = qgen_prompt
    verify_prompt = verify_prompt
