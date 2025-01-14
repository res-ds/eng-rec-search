import os

from openai import OpenAI

from src.vector_search import SimilarIssue

INSTRUCT_MODEL = os.environ["INSTRUCT_MODEL"]


def _generate_response(open_ai_client: OpenAI, prompt: str) -> str | None:
    response = open_ai_client.chat.completions.create(
        model=INSTRUCT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )
    return response.choices[0].message.content


def _augment_prompt(prompt: str, similar_issues: list[SimilarIssue]) -> str:
    previous_issues = "\n\n".join([f"## Issue {i}:\n{_issue}" for i, _issue in enumerate(similar_issues, start=1)])

    augmented_prompt = f"""
    You are an expert turbine performance engineer.
    You are given a current issue symptoms and previous issues with their symptoms, recommendations and resolutions as
    information.
    Generate a reasonable recommendation on what to do to resolve the current issue in a very succinct way (max. 50
    words).
    Use only the provided previous issues to recommend actions.

    # Current Issue Symptoms:
    {prompt}

    # Previous Issues:
    {previous_issues}
    """
    return augmented_prompt


def get_suggested_recommendation(open_ai_client: OpenAI, prompt: str, similar_issues: list[SimilarIssue]) -> str | None:
    augmented_prompt = _augment_prompt(prompt, similar_issues)
    return _generate_response(open_ai_client, augmented_prompt)
