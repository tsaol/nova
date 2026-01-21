"""
Nova Act Demo: Extract structured data from Amazon Best Sellers
"""
from nova_act import NovaAct

with NovaAct(starting_page="https://www.amazon.com/gp/bestsellers/wireless/7072561011") as nova:
    result = nova.act(
        "Extract the top 5 best-selling cellphones with rank, name, price, and rating",
        schema={
            "phones": [{
                "rank": "int",
                "name": "str",
                "price": "str",
                "rating": "str"
            }]
        }
    )
    print("Top 5 Best-Selling Cellphones:")
    for phone in result.parsed_response.get("phones", []):
        print(f"#{phone['rank']}: {phone['name']} - {phone['price']} ({phone['rating']})")
