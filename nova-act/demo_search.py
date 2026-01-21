"""
Nova Act Demo: Search Amazon (AWS IAM Authentication)
"""
from nova_act import NovaAct, workflow

@workflow(workflow_definition_name="demo-search", model_id="nova-act-latest")
def search_amazon():
    with NovaAct(
        starting_page="https://www.amazon.com",
        headless=False
    ) as nova:
        result = nova.act("Search for 'best selling cell phones' and tell me the first 3 product names")
        print(result)

if __name__ == "__main__":
    search_amazon()
