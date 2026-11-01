from __future__ import annotations

import base64
import os
import time

import httpx

from ..models import Listing


class EbayAuthError(RuntimeError):
    pass


class EbayBrowseSource:
    """Live eBay listings via the official Browse API.

    Requires a free eBay developer account. Set the following env vars:
        EBAY_CLIENT_ID      - your App ID (Client ID)
        EBAY_CLIENT_SECRET  - your Cert ID (Client Secret)
        EBAY_MARKETPLACE    - optional, defaults to EBAY_US

    Docs: https://developer.ebay.com/api-docs/buy/browse/overview.html
    """

    name = "ebay"
    _AUTH_URL = "https://api.ebay.com/identity/v1/oauth2/token"
    _SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    _SCOPE = "https://api.ebay.com/oauth/api_scope"

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        marketplace: str | None = None,
        timeout: float = 15.0,
    ) -> None:
        self._client_id = client_id or os.getenv("EBAY_CLIENT_ID")
        self._client_secret = client_secret or os.getenv("EBAY_CLIENT_SECRET")
        self._marketplace = marketplace or os.getenv("EBAY_MARKETPLACE", "EBAY_US")
        self._client = httpx.Client(timeout=timeout)
        self._token: str | None = None
        self._token_expires_at: float = 0.0

        if not self._client_id or not self._client_secret:
            raise EbayAuthError(
                "EBAY_CLIENT_ID and EBAY_CLIENT_SECRET must be set to use the live eBay source."
            )

    def _get_token(self) -> str:
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token

        credentials = f"{self._client_id}:{self._client_secret}".encode()
        encoded = base64.b64encode(credentials).decode()
        resp = self._client.post(
            self._AUTH_URL,
            headers={
                "Authorization": f"Basic {encoded}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials", "scope": self._SCOPE},
        )
        if resp.status_code != 200:
            raise EbayAuthError(f"eBay auth failed: {resp.status_code} {resp.text}")
        payload = resp.json()
        self._token = payload["access_token"]
        self._token_expires_at = time.time() + int(payload.get("expires_in", 7200))
        return self._token

    def search(self, keyword: str, limit: int = 50) -> list[Listing]:
        token = self._get_token()
        resp = self._client.get(
            self._SEARCH_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "X-EBAY-C-MARKETPLACE-ID": self._marketplace,
                "Accept": "application/json",
            },
            # Fixed-price listings only: an auction's current bid is not its price.
            params={"q": keyword, "limit": min(limit, 200), "filter": "buyingOptions:{FIXED_PRICE}"},
        )
        resp.raise_for_status()
        items = resp.json().get("itemSummaries", []) or []
        listings: list[Listing] = []
        for item in items:
            price = item.get("price", {}) or {}
            amount = price.get("value")
            if amount is None:
                continue
            shipping = 0.0
            options = item.get("shippingOptions") or []
            if options:
                cost = (options[0] or {}).get("shippingCost", {}) or {}
                try:
                    shipping = float(cost.get("value") or 0.0)
                except (TypeError, ValueError):
                    shipping = 0.0
            listings.append(
                Listing(
                    id=str(item.get("itemId") or item.get("legacyItemId") or ""),
                    title=item.get("title") or "(no title)",
                    price=float(amount),
                    currency=price.get("currency", "USD"),
                    url=item.get("itemWebUrl"),
                    condition=item.get("condition"),
                    shipping=shipping,
                    seller=(item.get("seller") or {}).get("username"),
                    image_url=(item.get("image") or {}).get("imageUrl"),
                )
            )
        return listings
