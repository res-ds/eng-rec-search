import streamlit as st
from annotated_text import annotated_text
from dotenv import load_dotenv

from utils import _get_vector_searcher, _mock_chart, _parse_issue_tuple

load_dotenv()


def _show_similar() -> None:
    st.session_state.sidebar_state = "expanded"
    vector_searcher = _get_vector_searcher()
    issues = [_parse_issue_tuple(i) for i in vector_searcher.search(st.session_state.eng_rec)["result"]["data_array"]]
    st.session_state.similar_issues = issues


def _submit_recommendation() -> None:
    if st.session_state.eng_rec:
        st.toast(f"Recommendation submitted: \n{st.session_state.eng_rec[:10]}", icon="🚀")
    else:
        st.toast("Please enter a recommendation!", icon="🚨")


TITLE = "Engineering Recommendation Search"

if "sidebar_state" not in st.session_state:
    st.session_state.sidebar_state = "collapsed"

st.set_page_config(
    page_title="Engineering Recommendation Search",
    page_icon="🛠",
    layout="wide",
    initial_sidebar_state=st.session_state.sidebar_state,
)

st.markdown(
    """
<style>
	[data-testid="stDecoration"] {
		display: none;
	}

</style>""",
    unsafe_allow_html=True,
)

hide_streamlit_style = """
<style>
    #root > div:nth-child(1) > div > div > div > div > section > div {padding-top: 0rem;}
</style>

"""

st.markdown(hide_streamlit_style, unsafe_allow_html=True)

st.title(TITLE)

with st.sidebar:
    if st.session_state.get("similar_issues", None):
        st.title("Similar Issues")
        for _issue in st.session_state.similar_issues:
            with st.expander(_issue.title, expanded=True):
                annotated_text([list(i.items()) for i in _issue.tags])
                st.write(_issue.content)

with st.container(border=True):
    st.subheader("Current Issue")
    with st.container(border=True):
        st.markdown("A new issue has been detected on Turbine 1. Please provide a recommendation.")
        st.plotly_chart(_mock_chart(), use_container_width=True)

    eng_rec = st.text_area(
        "Engineering Recommendation", value="E.g. Pitch hydraulic oil issue", height=100, key="eng_rec"
    )

    col1, col2 = st.columns(2)
    col1.button("Search similar issues", on_click=_show_similar)
    col2.button("Submit recommendation", on_click=_submit_recommendation)
