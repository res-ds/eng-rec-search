import streamlit as st
from annotated_text import annotated_text

from src.custom_mocks import mock_chart
from src.rec_suggestion import get_suggested_recommendation
from src.resources import get_open_ai_client
from src.styling import CUSTOM_STYLES_TO_APPLY
from src.vector_search import SimilarIssue, get_vector_searcher


def _show_similar() -> None:
    st.session_state.sidebar_state = "expanded"
    with st.spinner("Searching for similar issues..."):
        _get_similar_issues()


def _get_similar_issues() -> None:
    vector_searcher = get_vector_searcher()
    st.session_state.similar_issues = vector_searcher.search(st.session_state.issue_description)


def _submit_recommendation() -> None:
    if st.session_state.recommendation_text:
        st.toast("Recommendation submitted", icon="🚀")
        st.balloons()
    else:
        st.toast("Please enter a recommendation!", icon="🚨")


def _show_recommendation() -> None:
    if not st.session_state.get("similar_issues", None):
        _get_similar_issues()
    open_ai_client = get_open_ai_client()
    st.session_state.recommendation_text = get_suggested_recommendation(
        open_ai_client, prompt=st.session_state.issue_description, similar_issues=st.session_state["similar_issues"]
    )


TITLE = "🛠️🔍 Engineering Recommendation Helper"

if "sidebar_state" not in st.session_state:
    st.session_state.sidebar_state = "collapsed"

st.set_page_config(
    page_title="Engineering Recommendation Search",
    page_icon="🛠",
    layout="wide",
    initial_sidebar_state=st.session_state.sidebar_state,
)

for i in CUSTOM_STYLES_TO_APPLY:
    st.markdown(i, unsafe_allow_html=True)

st.title(TITLE)


@st.dialog("Full Issue Details", width="large")
def _issue_popup(_issue: SimilarIssue) -> None:
    title, content = _issue.original.split("\n", maxsplit=1)
    st.title(title.lstrip("# "))
    annotated_text(_issue.get_tags())
    st.markdown(content)


with st.sidebar:
    if st.session_state.get("similar_issues", None):
        st.title("Similar Issues")
        for _issue in st.session_state.similar_issues:
            _issue_title = _issue.original.split("\n")[0].lstrip("# ")
            with st.expander(_issue_title, expanded=True):
                st.write(_issue.summary)
                if st.button(label=":eye: view details", key=_issue.id):
                    _issue_popup(_issue)

with st.container(border=True):
    st.markdown("A new issue has been detected on Turbine 1. Please provide a recommendation.")
    st.plotly_chart(mock_chart(), use_container_width=True)

st.text_area("Issue Description", height=100, key="issue_description", value="E.g. Pitch hydraulic oil issue")

col1, col2 = st.columns(2)
col1.button("Search similar issues", on_click=_show_similar)
gen_rec = col2.button("Generate recommendation", on_click=_show_recommendation)

if gen_rec:
    st.text_area("Engineer Recommendation", height=100, key="recommendation_text")
    st.button("Submit recommendation", on_click=_submit_recommendation)
