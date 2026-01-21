"""
Nova Act Demo: Google Search
"""
from nova_act import NovaAct

with NovaAct(starting_page="https://www.google.com") as nova:
    nova.act("Search for 'Amazon Nova Act AWS'")
    nova.act("Click on the first search result")
    nova.act("Summarize the main content of this page")
