REMOVE_STREAMLIT_BAR = """
<style>
	[data-testid="stDecoration"] {
		display: none;
	}
</style>
"""
REMOVE_STREAMLIT_HEAD = """
<style>
    #root > div:nth-child(1) > div > div > div > div > section > div {padding-top: 0rem;}
</style>
"""

REMOVE_STREAMLIT_CONTROLS = """
<style>
.stApp [data-testid="stToolbar"]{
    display:none;
}
</style>
"""
