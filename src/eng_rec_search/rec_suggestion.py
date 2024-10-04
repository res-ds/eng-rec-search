import os

import streamlit as st
from openai import AzureOpenAI

from eng_rec_search.vector_search import SimilarIssue


@st.cache_resource
def get_open_ai_client() -> AzureOpenAI:
    return AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    )


def _generate_response(open_ai_client: AzureOpenAI, prompt: str) -> str | None:
    response = open_ai_client.chat.completions.create(
        model=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
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
    Generate a reasonable recomandation on what to do to resolve the current issue in a very succint way (max. 50
    words).
    Use only the provided previous issues to recommend actions.

    # Current Issue Symptoms:
    {prompt}

    # Previous Issues:
    {previous_issues}
    """
    return augmented_prompt


def get_suggested_recommendation(
    open_ai_client: AzureOpenAI, prompt: str, similar_issues: list[SimilarIssue]
) -> str | None:
    augmented_prompt = _augment_prompt(prompt, similar_issues)
    return _generate_response(open_ai_client, augmented_prompt)
