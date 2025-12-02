# core/wave/client.py
import os, json, requests

class WaveClient:
    def __init__(self, pat: str, business_id: str, endpoint: str = "https://gql.waveapps.com/graphql/public"):
        self.pat = pat
        self.business_id = business_id
        self.endpoint = endpoint

    def _headers(self):
        return {"Authorization": f"Bearer {self.pat}", "Content-Type": "application/json"}

    def query_invoices_since(self, iso_since: str):
        # Minimal GraphQL for invoices + line items; refine as needed
        q = {
            "query": """
            query ($businessId: ID!, $cursor: String) {
              business(id: $businessId) {
                invoices(pageInfo: { startingAfter: $cursor }) {
                  edges {
                    node { id createdAt status items { product { id name } quantity } }
                    cursor
                  }
                  pageInfo { hasNextPage endCursor }
                }
              }
            }
            """,
            "variables": {"businessId": self.business_id, "cursor": None}
        }
        r = requests.post(self.endpoint, headers=self._headers(), data=json.dumps(q))
        r.raise_for_status()
        return r.json()

