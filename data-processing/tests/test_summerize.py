import textwrap

from notebooks.t01_summarize import DistilledIssue, _distilled_issue_to_single_markdown, _raw_issue_to_single_markdown


def test__raw_issue_to_single_markdown():
    issue = {"Issue Title": "title", "Description": "description", "Closing Comment": "closing_comment"}
    expected = "# title\n\n## Description\ndescription\n\n## Closing Comment\nclosing_comment\n"
    assert _raw_issue_to_single_markdown(issue) == expected


def test__distilled_issue_to_single_markdown():
    distilled_issue = DistilledIssue(
        symptoms="sample_symptoms", recommendation="sample_recommendation", resolution="sample_resolution"
    )

    expected = textwrap.dedent("""\
        # Issue
        ## Symptoms
        sample_symptoms

        ## Recommendation
        sample_recommendation

        ## Resolution
        sample_resolution
        """)
    assert _distilled_issue_to_single_markdown(distilled_issue) == expected
