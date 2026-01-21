"""
Nova Act Demo: Search JD.com (京东)
JD.com is the most popular e-commerce site in China.
"""
from nova_act import NovaAct, workflow

@workflow(workflow_definition_name="demo-search", model_id="nova-act-latest")
def search_jd():
    with NovaAct(
        starting_page="https://search.jd.com/Search?keyword=iPhone%2016",
        headless=False
    ) as nova:
        result = nova.act("告诉我页面上前3个商品的名称和价格", max_steps=5)
        print(result)

if __name__ == "__main__":
    search_jd()
