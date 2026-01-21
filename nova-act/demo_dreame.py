"""
Nova Act Demo: Search Dreame robot vacuum on Amazon
"""
from nova_act import NovaAct, workflow

@workflow(workflow_definition_name="demo-search", model_id="nova-act-latest")
def search_dreame():
    with NovaAct(
        starting_page="https://www.amazon.com/s?k=dreame+robot+vacuum",
        headless=False
    ) as nova:
        result = nova.act("Tell me the first 3 Dreame robot vacuum products with their names and prices")
        print(result)

if __name__ == "__main__":
    search_dreame()
